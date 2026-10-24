"""C3XRA production scanner task (design-only; NO human data collected in this gate).

Frame-accurate imagery+perception presentation driven by the frozen deterministic schedule
(`c3xra_schedule`). The task logic is written against a small `Backend` interface so the EXACT same
control flow runs on:
  * `PsychoPyBackend` — real scanner hardware (TTL trigger, button box, video playback, vsync); imported
    lazily so this module loads with no psychopy/hardware present.
  * `MockBackend`     — hardware-free, deterministic simulator used by the dry-run validator to exercise
    ordering, event emission, timing tolerances and crash-safe logging without a scanner.

Per-trial machine-readable rows are appended to a crash-safe JSONL log (flush + fsync every write), so an
interrupted run can be recovered and validated. No neural data, no outcomes, no vividness/accuracy gating.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from app.research.fmri import c3xra_schedule as S

# Frozen presentation timing (seconds) — mirrors results/c3xra/timing_design_audit.json.
CUE_S = 1.5
IMAGERY_S = 8.0
POSTVIDEO_S = 4.0
EVAL_S = 2.0
GAP_CUE_IMAGERY = (2.0, 6.0)
GAP_IMAGERY_POST = (2.0, 6.0)
GAP_POST_EVAL = (0.5, 1.5)
ITI = (2.0, 6.0)
LEAD_IN_S = 6.0
TAIL_S = 6.0
PERCEPTION_STIM_S = 4.0
PERCEPTION_ITI = (2.0, 4.0)
JITTER_SALT = 0x54494D45  # matches timing audit


def _jitter_seq(seed_index: int, n: int, lo: float, hi: float) -> list[float]:
    import numpy as np
    rng = np.random.default_rng(S.MASTER_SEED ^ JITTER_SALT ^ (seed_index * 2654435761 & 0xFFFFFFFF))
    return [float(rng.uniform(lo, hi)) for _ in range(n)]


class Backend:
    """Presentation backend interface. Implementations MUST be frame/clock accurate."""

    def wait_for_trigger(self) -> float:  # returns t0 (first-TTL time)
        raise NotImplementedError

    def now(self) -> float:
        raise NotImplementedError

    def present(self, kind: str, ident: int, duration: float) -> dict:
        """Show a stimulus for `duration`; return {'onset','offset','dropped_frames'}."""
        raise NotImplementedError

    def poll_button(self) -> int | None:
        return None

    def flip_gap(self, duration: float) -> None:
        raise NotImplementedError


@dataclass
class MockBackend(Backend):
    """Deterministic hardware-free simulator: perfect vsync grid with small seeded frame jitter and a
    fixed trigger latency, so the dry-run can assert prospective timing tolerances."""
    refresh_hz: float = 60.0
    trigger_latency_s: float = 0.004
    frame_jitter_s: float = 0.0005
    seed: int = 0
    _t: float = 0.0
    _rng: object = None

    def __post_init__(self):
        import numpy as np
        self._rng = np.random.default_rng(S.MASTER_SEED ^ 0xB0A7 ^ self.seed)

    def wait_for_trigger(self) -> float:
        self._t += self.trigger_latency_s
        return self._t

    def now(self) -> float:
        return self._t

    def _advance(self, duration: float) -> int:
        frame = 1.0 / self.refresh_hz
        n_frames = max(1, int(round(duration / frame)))
        dropped = 0
        for _ in range(n_frames):
            jit = float(self._rng.normal(0.0, self.frame_jitter_s))
            self._t += frame + jit
            if abs(jit) > frame * 0.5:
                dropped += 1
        return dropped

    def present(self, kind: str, ident: int, duration: float) -> dict:
        onset = self._t
        dropped = self._advance(duration)
        return {"onset": onset, "offset": self._t, "dropped_frames": dropped}

    def poll_button(self) -> int | None:
        return 1  # simulate a button press during evaluation

    def flip_gap(self, duration: float) -> None:
        self._advance(duration)


@dataclass
class CrashSafeLog:
    path: str
    _fh: object = field(default=None, repr=False)

    def open(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, row: dict):
        self._fh.write(json.dumps(row, sort_keys=True) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self):
        if self._fh:
            self._fh.close()


def run_imagery_run(participant: int, unit: int, run: int, backend: Backend,
                    log: CrashSafeLog) -> list[dict]:
    """Present one imagery run (IMAGERY_TRIALS_PER_RUN trials). Emits cue -> imagery -> post-video ->
    evaluation per trial with frozen jittered gaps. Returns the per-trial rows (also logged)."""
    rows = [r for r in S.imagery_trials(participant, max(unit, 1))
            if r["imagery_unit"] == unit and r["run"] == run]
    rows.sort(key=lambda r: r["run_position"])
    n = len(rows)
    gci = _jitter_seq(participant * 100 + unit * 10 + run + 1, n, *GAP_CUE_IMAGERY)
    gip = _jitter_seq(participant * 100 + unit * 10 + run + 2, n, *GAP_IMAGERY_POST)
    gpe = _jitter_seq(participant * 100 + unit * 10 + run + 3, n, *GAP_POST_EVAL)
    iti = _jitter_seq(participant * 100 + unit * 10 + run + 4, n, *ITI)
    t0 = backend.wait_for_trigger()
    backend.flip_gap(LEAD_IN_S)
    out = []
    for i, r in enumerate(rows):
        vid = r["video_id"]
        cue = backend.present("cue", vid, CUE_S)
        backend.flip_gap(gci[i])
        img = backend.present("imagery", vid, IMAGERY_S)
        backend.flip_gap(gip[i])
        post = backend.present("postvideo", vid, POSTVIDEO_S)
        backend.flip_gap(gpe[i])
        ev = backend.present("eval", 0, EVAL_S)
        resp = backend.poll_button()
        backend.flip_gap(iti[i])
        row = {"participant": participant, "imagery_unit": unit, "run": run,
               "run_position": r["run_position"], "video_id": vid, "t0": t0,
               "cue_onset": cue["onset"] - t0, "imagery_onset": img["onset"] - t0,
               "postvideo_onset": post["onset"] - t0, "eval_onset": ev["onset"] - t0,
               "button_response": resp,
               "dropped_frames": cue["dropped_frames"] + img["dropped_frames"]
               + post["dropped_frames"] + ev["dropped_frames"],
               "events_present": ["cue", "imagery", "postvideo", "eval"]}
        log.write(row)
        out.append(row)
    backend.flip_gap(TAIL_S)
    return out


def run_perception_run(participant: int, unit: int, which: str, backend: Backend,
                       log: CrashSafeLog) -> list[dict]:
    """Present one perception run (36 identities of a complete-content run-pair). which in {'A','B'}."""
    pair = [p for p in S.perception_schedule(participant, max(unit, 1)) if p["unit"] == unit][0]
    ids = pair["run_A"] if which == "A" else pair["run_B"]
    iti = _jitter_seq(participant * 1000 + unit * 10 + (1 if which == "A" else 2), len(ids), *PERCEPTION_ITI)
    t0 = backend.wait_for_trigger()
    backend.flip_gap(LEAD_IN_S)
    out = []
    for i, vid in enumerate(ids):
        s = backend.present("perception", vid, PERCEPTION_STIM_S)
        backend.flip_gap(iti[i])
        row = {"participant": participant, "perception_unit": unit, "run": which,
               "position": i + 1, "video_id": vid, "t0": t0, "onset": s["onset"] - t0,
               "dropped_frames": s["dropped_frames"], "events_present": ["perception"]}
        log.write(row)
        out.append(row)
    backend.flip_gap(TAIL_S)
    return out


def _load_psychopy_backend():  # pragma: no cover - requires hardware
    """Lazy real backend; raises a clear message if psychopy is unavailable."""
    try:
        from psychopy import core, event, visual  # noqa: F401
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("PsychoPy not installed; use MockBackend for the hardware-free dry-run") from e
    raise NotImplementedError(
        "PsychoPyBackend is instantiated on the scanner PC only. It wraps visual.Window(waitBlanking=True), "
        "visual.MovieStim for the stimulus clips, a TTL-trigger wait via the sync port, and iohub/keyboard "
        "for the button box. Not exercised in this design-only gate.")
