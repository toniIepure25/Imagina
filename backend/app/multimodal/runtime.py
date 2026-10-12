"""Closed-loop session runtime for simulation and deterministic replay.

acquire -> validate quality -> synchronize/window -> features -> calibrate/estimate -> safety gates -> policy ->
Dream Corridor action -> (synthetic) participant response -> log.

The synthetic responder is a scripted stand-in used to exercise the software path; its ratings are not
participant data.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from app.multimodal.acquisition import synthetic_signals as ss
from app.multimodal.acquisition.base import ArrayStreamProvider, FaultPlan, LifecycleState
from app.multimodal.acquisition.registry import create_synthetic
from app.multimodal.acquisition.replay import FileReplayProvider
from app.multimodal.controller import (
    POLICY_REGISTRY,
    ControllerConfig,
    ControllerState,
    Decision,
    FeedbackAuthorization,
    FeedbackController,
    GateInputs,
    verify_trace,
)
from app.multimodal.corridor import corridor_action
from app.multimodal.estimator import (
    CalibrationProfile,
    ImageryState,
    ImageryStateEstimator,
    SelfReport,
    calibrate,
    perception_imagination_distance,
)
from app.multimodal.processing.common import Feature, FeatureSet
from app.multimodal.processing.ecg import ecg_features
from app.multimodal.processing.eda import eda_features
from app.multimodal.processing.eeg import eeg_features
from app.multimodal.processing.fnirs import FnirsMetadataError, to_hemoglobin
from app.multimodal.processing.respiration import respiration_features
from app.multimodal.schemas import Marker, Modality, stable_hash
from app.multimodal.storage import ConsentRecord, SessionStore
from app.multimodal.sync import SyncedWindow, SyncEngine

WINDOW_S = {Modality.EEG: 4.0, Modality.ECG: 30.0, Modality.EDA: 20.0, Modality.RESPIRATION: 30.0,
            Modality.FNIRS: 60.0}


class ScriptedEvent(BaseModel):
    t: float
    kind: Literal["report_text", "discomfort", "emergency_stop", "pause", "resume"]
    value: str | float = ""


class SessionConfig(BaseModel):
    session_id: str = "mm-sim"
    participant_pseudo_id: str = "P-synthetic"
    modalities: list[Modality] = Field(default_factory=lambda: [Modality.EEG, Modality.ECG, Modality.EDA,
                                                                 Modality.RESPIRATION, Modality.FNIRS])
    source: Literal["synthetic", "replay"] = "synthetic"
    replay_paths: dict[Modality, str] = Field(default_factory=dict)
    duration_s: float = Field(default=180.0, gt=0, le=3600)
    tick_s: float = Field(default=2.0, gt=0)
    calibration_s: float = 40.0
    baseline_s: float = 10.0
    seed: int = 7
    mode: Literal["shadow", "feedback_research"] = "shadow"
    policy: str = "bounded_rules"
    faults: dict[Modality, FaultPlan] = Field(default_factory=dict)
    report_every_ticks: int = 5
    eeg_channels: int = 8
    authorization: FeedbackAuthorization | None = None
    controller: ControllerConfig = Field(default_factory=ControllerConfig)
    events: list[ScriptedEvent] = Field(default_factory=list)
    store_root: str | None = None
    fnirs_ppf: float = 6.0


class SyntheticResponder:
    """Scripted SYNTHETIC participant: ratings depend on latent engagement, displayed cue strength and time."""

    def __init__(self, seed: int, blocks: list[ss.ConditionBlock]) -> None:
        self.rng = np.random.default_rng(seed + 101)
        self.blocks = blocks

    def report(self, t: float, cue_shown: float, discomfort: float | None, text: str) -> SelfReport:
        eng = next((b.engagement for b in self.blocks if b.start_s <= t < b.start_s + b.duration_s), 0.0)
        fatigue = float(np.clip(t / 1500.0 + self.rng.normal(0, 0.03), 0, 1))
        viv = float(np.clip(0.3 + 0.3 * eng + 0.2 * cue_shown - 0.2 * fatigue + self.rng.normal(0, 0.05), 0, 1))
        return SelfReport(time=t, vividness=viv, spatial_detail=float(np.clip(viv - 0.1, 0, 1)),
                          voluntary_control=float(np.clip(0.5 + self.rng.normal(0, 0.1), 0, 1)),
                          immersion=float(np.clip(viv * 0.8 + 0.1, 0, 1)), effort=0.4, fatigue=fatigue,
                          discomfort=discomfort, reality_orientation=0.95, free_text=text)


def _features(m: Modality, sw, info, ppf: float) -> FeatureSet | None:
    if sw is None or sw.data.shape[0] < 4:
        return None
    fs, sk, t0 = sw.rate_hz, info.source_kind, float(sw.times[0])
    try:
        if m == Modality.EEG:
            return eeg_features(sw.data, fs, info.channel_names, info.stream_id, sk, t0)
        if m == Modality.ECG:
            return ecg_features(sw.data[:, 0], fs, info.stream_id, sk, t0)
        if m == Modality.EDA:
            return eda_features(sw.data[:, 0], fs, info.stream_id, sk, t0)[0]
        if m == Modality.RESPIRATION:
            return respiration_features(sw.data[:, 0], fs, info.stream_id, sk, t0)
        if m == Modality.FNIRS:
            hb = to_hemoglobin(info, sw.data, ppf=ppf, band=(0.02, 0.5))
            long_idx = [k for k, p in enumerate(hb.pair_names) if p not in hb.short_pairs]
            f = FeatureSet(modality=m, stream_id=info.stream_id, source_kind=sk, t_start=t0,
                           t_end=float(sw.times[-1]), quality=float(np.mean(list(hb.sci.values()))))
            tail = max(1, int(10 * fs))
            f.add(Feature(name="hbo_recent_mean", value=float(hb.hbo[-tail:, long_idx].mean() * 1e6), unit="uM",
                          method=";".join(hb.log), confidence=f.quality,
                          reason="hemodynamic response lags neural activity by ~5 s"))
            return f
    except (FnirsMetadataError, ValueError) as e:
        f = FeatureSet(modality=m, stream_id=info.stream_id, source_kind=sk, t_start=t0, t_end=t0, quality=0.0)
        f.flags.append(f"processing_refused:{e}")
        return f
    return None


class ClosedLoopSession:
    def __init__(self, cfg: SessionConfig) -> None:
        self.cfg = cfg
        self.blocks = ss.default_blocks(cfg.duration_s + 120.0)
        self.providers: dict[Modality, ArrayStreamProvider] = {}
        for m in cfg.modalities:
            faults = cfg.faults.get(m)
            if cfg.source == "replay":
                self.providers[m] = FileReplayProvider(Path(cfg.replay_paths[m]), m, faults=faults)
            else:
                kw = {"duration_s": cfg.duration_s + 120.0, "seed": cfg.seed + list(Modality).index(m),
                      "faults": faults, "blocks": self.blocks}
                if m == Modality.EEG:
                    kw["n_channels"] = cfg.eeg_channels
                self.providers[m] = create_synthetic(m, **kw)
        self.sync = SyncEngine()
        policy_cls = POLICY_REGISTRY[cfg.policy]
        self.controller = FeedbackController(policy=policy_cls() if cfg.policy != "sham_yoked" else policy_cls([]),
                                             config=cfg.controller, authorization=cfg.authorization)
        self.responder = SyntheticResponder(cfg.seed, self.blocks)
        self.estimator = ImageryStateEstimator()
        self.profile: CalibrationProfile | None = None
        self.log: list[dict] = []
        self.latencies_ms: list[float] = []
        self.sync_snapshots: list[dict] = []
        self.store = SessionStore(Path(cfg.store_root)) if cfg.store_root else None
        self.recorders = {}

    def _block(self, t: float) -> str:
        return next((b.label for b in self.blocks if b.start_s <= t < b.start_s + b.duration_s), "rest")

    def _acquire(self, t: float) -> None:
        for m, p in self.providers.items():
            sid = p.info.stream_id
            if p.state == LifecycleState.LOST:
                if p.try_reconnect(t):
                    self.sync.set_connected(sid, True)
                else:
                    continue
            chunk = p.read(t)
            if p.state == LifecycleState.LOST:
                self.sync.set_connected(sid, False)
            if chunk is not None:
                self.sync.ingest(chunk)
                if sid in self.recorders:
                    self.recorders[sid].append(chunk)

    def start(self) -> None:
        cfg = self.cfg
        if self.store:
            self.store.create_session(cfg.session_id, cfg.participant_pseudo_id,
                                      ConsentRecord(protocol_id="SIMULATION", consent_version="n/a"),
                                      extra={"mode": cfg.mode, "source": cfg.source})
        for p in self.providers.values():
            info = p.connect(0.0)
            self.sync.add_stream(info)
            if self.store:
                self.recorders[info.stream_id] = self.store.recorder(cfg.session_id, info)
        for b in self.blocks:
            if b.start_s < cfg.duration_s:
                self.sync.add_marker(Marker(label=b.label, local_time=b.start_s, duration_s=b.duration_s))
        self.source_kinds = {p.info.source_kind.value for p in self.providers.values()}
        self.controller.transition(ControllerState.CALIBRATION, 0.0, "session start", self.source_kinds)
        self._calib, self._perc = [], []
        self._report: SelfReport | None = None
        self._events = sorted(cfg.events, key=lambda e: e.t)
        self._pending_text, self._discomfort = "", None
        self.t, self.k = 0.0, 0
        self.finished = False

    def command(self, kind: str, value: str | float = "") -> None:
        self._events.insert(0, ScriptedEvent(t=self.t, kind=kind, value=value))

    @property
    def done(self) -> bool:
        return (self.finished or self.t >= self.cfg.duration_s - 1e-9
                or self.controller.state == ControllerState.TERMINATED)

    def step(self) -> dict | None:
        cfg, ctrl = self.cfg, self.controller
        if self.done:
            return None
        t = self.t = round(self.t + cfg.tick_s, 6)
        self.k += 1
        k = self.k
        t0 = time.perf_counter()
        for ev in [e for e in self._events if e.t <= t]:
            self._events.remove(ev)
            if ev.kind == "emergency_stop":
                ctrl.emergency_stop(t)
            elif ev.kind == "pause":
                ctrl.pause(t)
            elif ev.kind == "resume" and ctrl.state == ControllerState.PAUSED:
                ctrl.transition(ControllerState.ACTIVE_SHADOW, t, "manual resume", self.source_kinds)
            elif ev.kind == "report_text":
                self._pending_text = str(ev.value)
            elif ev.kind == "discomfort":
                self._discomfort = float(ev.value)
        if ctrl.state == ControllerState.TERMINATED:
            return None
        self._acquire(t)
        windows: dict[float, SyncedWindow] = {}
        fsets: dict[Modality, FeatureSet] = {}
        for m, p in self.providers.items():
            dur = WINDOW_S[m]
            if dur not in windows:
                windows[dur] = self.sync.window(t, dur)
            sw = windows[dur].streams[p.info.stream_id]
            if sw.usable:
                f = _features(m, sw, p.info, cfg.fnirs_ppf)
                if f is not None:
                    fsets[m] = f
        block = self._block(t)
        if ctrl.state == ControllerState.CALIBRATION:
            self._calib.append(fsets)
            if block == "perception":
                self._perc.append(fsets)
            if t >= cfg.calibration_s:
                self.profile = calibrate(cfg.participant_pseudo_id, self._calib, self._perc)
                self.estimator = ImageryStateEstimator(self.profile)
                ctrl.transition(ControllerState.BASELINE, t, f"calibrated on {len(self._calib)} windows")
        elif ctrl.state == ControllerState.BASELINE and t >= cfg.calibration_s + cfg.baseline_s:
            target = (ControllerState.FEEDBACK_RESEARCH if cfg.mode == "feedback_research"
                      else ControllerState.ACTIVE_SHADOW)
            ctrl.transition(target, t, f"mode={cfg.mode}", self.source_kinds)
        last_cue = self.log[-1]["corridor"]["scene"]["scene_clarity"] if self.log else 0.3
        if k % cfg.report_every_ticks == 0 or self._pending_text or self._discomfort is not None:
            self._report = self.responder.report(t, (last_cue - 0.3) / 0.6, self._discomfort, self._pending_text)
        report = self._report
        state: ImageryState = self.estimator.estimate(t, fsets, report)
        fresh = report is not None and report.time == t
        gate = self._gates(t, windows, fsets, self.source_kinds, report.free_text if fresh else "",
                           report.discomfort if fresh else None)
        main = windows[min(windows)] if windows else None
        pre_state = ctrl.state.value
        dec: Decision = ctrl.tick(t, state, gate, {"cue_cap": 1.0})
        self._pending_text, self._discomfort = "", None
        act = corridor_action(cfg.session_id, dec)
        pid = perception_imagination_distance(fsets, self.profile) if self.profile else {"value": None}
        self.latencies_ms.append((time.perf_counter() - t0) * 1e3)
        if k % 5 == 0:
            self.sync_snapshots.append({"t": t, **self.sync.health(t)})
        entry = {
            "tick": k, "t": t, "block": block, "pre_tick_state": pre_state, "state": state.model_dump(mode="json"),
            "gates": gate.model_dump(mode="json"), "decision": dec.model_dump(mode="json"),
            "corridor": act.model_dump(mode="json", exclude={"scene": {"timestamp"}}),
            "features": {m.value: {n: f.value for n, f in fs.features.items()} | {"_quality": fs.quality}
                         for m, fs in fsets.items()},
            "pid_research_metric": pid, "self_report": report.model_dump() if fresh else None,
            "window_alignment_uncertainty_s": main.max_alignment_uncertainty_s if main else None,
        }
        self.log.append(entry)
        return entry

    def finish(self) -> dict:
        if not self.finished:
            for r in self.recorders.values():
                r.close()
            self.finished = True
        return self.summary()

    def run(self) -> dict:
        self.start()
        while self.step() is not None:
            pass
        return self.finish()

    def _gates(self, t, windows, fsets, source_kinds, text, discomfort) -> GateInputs:
        stale, disc, usable, unc = [], [], 0, []
        unknown = False
        for m, p in self.providers.items():
            sw = windows[WINDOW_S[m]].streams[p.info.stream_id]
            if not sw.connected:
                disc.append(m.value)
            elif sw.stale:
                stale.append(m.value)
            if sw.usable:
                usable += 1
            if sw.alignment_uncertainty_s is None:
                unknown = True
            else:
                unc.append(sw.alignment_uncertainty_s)
        q = [f.quality for f in fsets.values()]
        return GateInputs(usable_streams=usable, stale_streams=stale, disconnected_streams=disc,
                          max_alignment_uncertainty_s=None if unknown or not unc else max(unc),
                          mean_quality=float(np.mean(q)) if q else 0.0, source_kinds=sorted(source_kinds),
                          self_report_text=text, discomfort=discomfort)

    def summary(self) -> dict:
        trace = self.controller.trace
        lat = np.array(self.latencies_ms) if self.latencies_ms else np.zeros(1)
        out = {
            "session_id": self.cfg.session_id, "source_kinds": sorted({p.info.source_kind.value
                                                                       for p in self.providers.values()}),
            "mode": self.cfg.mode, "policy": self.cfg.policy, "n_ticks": len(self.log),
            "final_state": self.controller.state.value, "transitions": self.controller.transitions,
            "n_delivered": sum(d.delivered for d in trace),
            "n_holds": sum(bool(d.hold_reason) for d in trace),
            "safety_codes": sorted({f["code"] for d in trace for f in d.safety_findings}),
            "trace_valid": verify_trace(trace), "decision_hash": trace[-1].hash if trace else None,
            "calibration": self.profile.to_dict() if self.profile else None,
            "latency_ms": {"p50": float(np.percentile(lat, 50)), "p95": float(np.percentile(lat, 95)),
                           "max": float(lat.max()), "note": "wall-clock processing per tick on this machine"},
            "sync_health": self.sync.health(self.log[-1]["t"] if self.log else 0.0),
            "provider_health": {m.value: p.health() for m, p in self.providers.items()},
            "disclaimer": ("Simulation/replay run with a scripted synthetic responder. Outputs exercise the "
                           "software path and are not participant outcomes."),
        }
        if self.store:
            self.store.write_jsonl(self.cfg.session_id, "decisions.jsonl", self.log)
            self.store.write_json(self.cfg.session_id, "summary.json", out)
        return out


def replay_controller(log: list[dict], cfg: SessionConfig) -> dict:
    """Re-run the controller on logged estimates, gate inputs and runtime transitions; decisions must reproduce
    bit-for-bit (verified through the hash chain)."""
    policy_cls = POLICY_REGISTRY[cfg.policy]
    ctrl = FeedbackController(policy=policy_cls() if cfg.policy != "sham_yoked" else policy_cls([]),
                              config=cfg.controller, authorization=cfg.authorization)
    ctrl.restore_state(ControllerState.CALIBRATION)
    ctrl._start_t = 0.0
    mismatches = []
    for entry in log:
        ctrl.restore_state(ControllerState(entry["pre_tick_state"]))
        d = ctrl.tick(entry["t"], ImageryState(**entry["state"]), GateInputs(**entry["gates"]), {"cue_cap": 1.0})
        if d.hash != entry["decision"]["hash"]:
            mismatches.append(entry["tick"])
    return {"n": len(log), "mismatches": mismatches, "reproduced": not mismatches,
            "final_hash": ctrl.trace[-1].hash if ctrl.trace else None}


def run_session(cfg: SessionConfig) -> tuple[ClosedLoopSession, dict]:
    s = ClosedLoopSession(cfg)
    return s, s.run()


def session_digest(log: list[dict]) -> str:
    return stable_hash([e["decision"]["hash"] for e in log])
