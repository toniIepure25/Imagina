"""Closed-loop latency and robustness benchmark (simulation; synthetic streams).

Two different quantities are reported and must not be conflated:
- CPU processing time per stage (wall clock on this machine);
- data age at decision time (decision time minus newest aligned sample), which includes simulated transport latency
  and windowing but NOT sensor/amplifier delay or display/render delay.
True neural-to-feedback latency requires a hardware marker loop (e.g. photodiode on the display fed back into the
acquisition) and is reported as NOT MEASURED.
"""
from __future__ import annotations

import asyncio
import time

import numpy as np

from app.multimodal.acquisition.base import FaultPlan
from app.multimodal.runtime import ClosedLoopSession, ScriptedEvent, SessionConfig
from app.multimodal.schemas import Modality

ALL = [Modality.EEG, Modality.ECG, Modality.EDA, Modality.RESPIRATION, Modality.FNIRS]


def _dist(v) -> dict:
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
            "p99": float(np.percentile(v, 99)), "max": float(v.max())}


def _run(cfg: SessionConfig) -> tuple[ClosedLoopSession, dict]:
    s = ClosedLoopSession(cfg)
    summ = s.run()
    return s, summ


def stage_report(s: ClosedLoopSession) -> dict:
    keys = sorted({k for st in s.stage_ms for k in st if k.endswith("_ms") or k.startswith("data_age_")})
    return {k: _dist([st.get(k) for st in s.stage_ms]) for k in keys}


SCENARIOS = {
    "baseline_5_streams": {},
    "eeg_512hz": {"eeg_rate": 512.0},
    "eeg_1000hz_16ch": {"eeg_rate": 1000.0, "eeg_channels": 16},
    "jitter_20ms_latency_50ms": {"faults": {m: FaultPlan(jitter_s=0.02, transport_latency_s=0.05) for m in ALL}},
    "packet_loss_5pct": {"faults": {m: FaultPlan(dropouts=[(float(t), float(t) + 1.0) for t in range(20, 300, 20)])
                                    for m in ALL}},
    "drift_500ppm": {"faults": {Modality.EEG: FaultPlan(clock_drift_ppm=500.0, clock_offset_s=30.0),
                                Modality.ECG: FaultPlan(clock_drift_ppm=-500.0)}},
    "eeg_dropout_disconnect": {"faults": {Modality.EEG: FaultPlan(disconnect_at_s=100.0, reconnect_after_s=1000.0)}},
}


def run_scenarios(duration: float = 180.0) -> dict:
    out = {}
    for name, spec in SCENARIOS.items():
        cfg = SessionConfig(session_id=f"lat-{name}", duration_s=duration, mode="feedback_research",
                            faults=spec.get("faults", {}), eeg_channels=spec.get("eeg_channels", 8))
        s = ClosedLoopSession(cfg)
        if "eeg_rate" in spec:
            s.providers[Modality.EEG].rate_hz = spec["eeg_rate"]
        t0 = time.perf_counter()
        summ = s.run()
        states = [st["controller_state"] for st in s.stage_ms]
        out[name] = {"wall_s": time.perf_counter() - t0, "final_state": summ["final_state"],
                     "safety_codes": summ["safety_codes"], "n_ticks": summ["n_ticks"],
                     "state_counts": {k: states.count(k) for k in set(states)}, "stages": stage_report(s),
                     "max_alignment_uncertainty_ms": summ["sync_health"]["max_alignment_uncertainty_ms"]}
    return out


def transition_checks() -> dict:
    checks = {}
    s, summ = _run(SessionConfig(duration_s=100, mode="feedback_research",
                                 events=[ScriptedEvent(t=70, kind="pause")]))
    checks["manual_pause_to_PAUSED"] = summ["final_state"] == "PAUSED"
    _, summ = _run(SessionConfig(duration_s=160, mode="feedback_research",
                                 faults={Modality.EEG: FaultPlan(disconnect_at_s=80.0, reconnect_after_s=1000.0)}))
    checks["sensor_dropout_to_SAFE_FALLBACK"] = summ["final_state"] == "SAFE_FALLBACK"
    _, summ = _run(SessionConfig(duration_s=100, mode="feedback_research",
                                 events=[ScriptedEvent(t=70, kind="emergency_stop")]))
    checks["emergency_stop_to_TERMINATED"] = summ["final_state"] == "TERMINATED"
    from app.multimodal.controller import ControllerConfig

    _, summ = _run(SessionConfig(duration_s=120, mode="feedback_research",
                                 controller=ControllerConfig(session_limit_s=80)))
    checks["time_limit_to_TERMINATED"] = summ["final_state"] == "TERMINATED"
    _, summ = _run(SessionConfig(duration_s=100, mode="feedback_research",
                                 events=[ScriptedEvent(t=70, kind="report_text", value="I feel unreal")]))
    checks["distress_report_to_SAFE_FALLBACK"] = summ["final_state"] == "SAFE_FALLBACK"
    return checks


def http_dispatch(n: int = 200) -> dict:
    """In-process ASGI round trip for GET /corridor/latest (serialization + routing, no network or rendering)."""
    import tempfile

    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.storage import database

    database.DB_PATH = str(tempfile.mkdtemp() + "/latency.db")

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            await c.post("/api/multimodal/sessions", json={"session_id": "lat-http", "duration_s": 70})
            ts = []
            for _ in range(n):
                a = time.perf_counter()
                r = await c.get("/api/multimodal/sessions/lat-http/corridor/latest")
                ts.append((time.perf_counter() - a) * 1e3)
                assert r.status_code == 200
            return ts

    return _dist(asyncio.run(go()))


def run(fast: bool = False) -> dict:
    import os
    import platform

    return {
        "machine": {"platform": platform.platform(), "python": platform.python_version(), "cpus": os.cpu_count()},
        "notes": ["CPU stage times are processing costs on this machine, not physiological latency.",
                  "data_age_* = decision time minus newest aligned sample; includes simulated transport latency.",
                  "Dream Corridor rendering latency: NOT MEASURED (browser/WebGL; needs photodiode loop).",
                  "Sensor-to-host latency: NOT MEASURED (no hardware)."],
        "scenarios": run_scenarios(90.0 if fast else 180.0),
        "transitions": transition_checks(),
        "http_corridor_dispatch_ms": http_dispatch(50 if fast else 200),
    }
