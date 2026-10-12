"""Multimodal research command-center API.

Sessions here are SYNTHETIC or REPLAY simulations held in memory. Live sensor sessions are not exposed through
the API; real-sensor feedback additionally requires a FeedbackAuthorization and defaults to ACTIVE_SHADOW.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.multimodal.acquisition.registry import list_descriptors
from app.multimodal.controller import AuthorizationError, ControllerState
from app.multimodal.protocols import (
    PROTOCOLS,
    run_protocol_a,
    run_protocol_b,
    run_protocol_c,
    run_protocol_causal,
    run_protocol_d,
)
from app.multimodal.runtime import ClosedLoopSession, ScriptedEvent, SessionConfig, replay_controller
from app.multimodal.schemas import Modality

router = APIRouter(prefix="/api/multimodal", tags=["multimodal"])

MAX_SESSIONS = 20
_sessions: OrderedDict[str, ClosedLoopSession] = OrderedDict()
CHECKLIST = Path(__file__).resolve().parents[3] / "docs" / "hardware_validation_checklist.json"

TIMELINE_FEATURES = {
    "eeg": ["posterior_rel_alpha", "theta_beta_ratio"], "ecg": ["heart_rate", "rmssd"],
    "eda": ["tonic_scl", "scr_rate"], "respiration": ["resp_rate"], "fnirs": ["hbo_recent_mean"],
}


class CreateSession(BaseModel):
    session_id: str = Field(default="mm-demo", pattern=r"^[A-Za-z0-9_-]{1,40}$")
    modalities: list[Modality] = Field(default_factory=lambda: [Modality.EEG, Modality.ECG, Modality.EDA,
                                                                 Modality.RESPIRATION, Modality.FNIRS])
    duration_s: float = Field(default=180.0, gt=0, le=1200)
    seed: int = 7
    mode: Literal["shadow", "feedback_research"] = "shadow"
    policy: Literal["bounded_rules", "pid_controller_iqi", "no_feedback"] = "bounded_rules"
    run_to_end: bool = True
    events: list[ScriptedEvent] = Field(default_factory=list)


class Command(BaseModel):
    action: Literal["pause", "resume", "emergency_stop", "report_text", "discomfort"]
    value: str | float = ""


def _get(session_id: str) -> ClosedLoopSession:
    s = _sessions.get(session_id)
    if s is None:
        raise HTTPException(404, "session not found")
    return s


def _status(s: ClosedLoopSession) -> dict:
    return {"session_id": s.cfg.session_id, "t": s.t, "duration_s": s.cfg.duration_s, "done": s.done,
            "controller_state": s.controller.state.value, "mode": s.cfg.mode, "policy": s.cfg.policy,
            "source_kinds": sorted(s.source_kinds), "n_ticks": len(s.log)}


@router.get("/modalities")
async def modalities():
    return {"modalities": [m.value for m in Modality], "providers": [d.describe() for d in list_descriptors()]}


@router.post("/sessions")
async def create_session(req: CreateSession):
    cfg = SessionConfig(session_id=req.session_id, modalities=req.modalities, duration_s=req.duration_s,
                        seed=req.seed, mode=req.mode, policy=req.policy, events=req.events)
    s = ClosedLoopSession(cfg)
    try:
        s.start()
        if req.run_to_end:
            while s.step() is not None:
                pass
    except AuthorizationError as e:
        raise HTTPException(403, str(e)) from e
    _sessions[req.session_id] = s
    _sessions.move_to_end(req.session_id)
    while len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)
    return s.finish() if s.done else _status(s)


@router.get("/sessions")
async def list_sessions():
    return [_status(s) for s in _sessions.values()]


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    s = _get(session_id)
    return s.summary() | {"status": _status(s)}


@router.post("/sessions/{session_id}/step")
async def step(session_id: str, n: int = 1):
    s = _get(session_id)
    out = []
    for _ in range(max(1, min(n, 50))):
        e = s.step()
        if e is None:
            break
        out.append(_compact(e))
    if s.done:
        s.finish()
    return {"status": _status(s), "ticks": out}


@router.post("/sessions/{session_id}/command")
async def command(session_id: str, cmd: Command):
    s = _get(session_id)
    if cmd.action == "emergency_stop":
        s.controller.emergency_stop(s.t, "operator emergency stop")
        s.finish()
    else:
        s.command(cmd.action, cmd.value)
    return _status(s)


def _compact(e: dict) -> dict:
    dims = e["state"]["dimensions"]
    return {
        "t": e["t"], "block": e["block"], "controller_state": e["decision"]["controller_state"],
        "delivered": e["decision"]["delivered"], "hold_reason": e["decision"]["hold_reason"],
        "adaptation_note": e["decision"]["adaptation_note"],
        "safety": [f["code"] for f in e["decision"]["safety_findings"]],
        "applied": e["decision"]["applied"], "confidence": e["state"]["overall_confidence"], "iqi": e["state"]["iqi"],
        "dimensions": {k: {"value": d["value"], "uncertainty": d["uncertainty"], "evidence": d["evidence_class"]}
                       for k, d in dims.items()},
        "features": {m: {n: v.get(n) for n in names} | {"quality": v.get("_quality")}
                     for m, names in TIMELINE_FEATURES.items() if (v := e["features"].get(m)) is not None},
        "alignment_uncertainty_ms": None if e["window_alignment_uncertainty_s"] is None
        else e["window_alignment_uncertainty_s"] * 1e3,
        "pid_research_metric": e["pid_research_metric"].get("value"),
        "scene": {k: e["corridor"]["scene"][k] for k in ("scene_clarity", "texture_detail", "fog_density",
                                                          "breathing_cue_strength", "prompt_text")},
        "audio": e["corridor"]["audio"],
    }


@router.get("/sessions/{session_id}/timeline")
async def timeline(session_id: str, start_tick: int = 0):
    s = _get(session_id)
    return {"status": _status(s), "ticks": [_compact(e) for e in s.log[start_tick:]]}


@router.get("/sessions/{session_id}/sync")
async def sync_health(session_id: str):
    s = _get(session_id)
    return {"current": s.sync.health(s.t), "snapshots": s.sync_snapshots[-50:]}


@router.get("/sessions/{session_id}/decisions")
async def decisions(session_id: str, limit: int = 50):
    s = _get(session_id)
    return [e["decision"] for e in s.log[-max(1, min(limit, 500)):]]


@router.get("/sessions/{session_id}/corridor/latest")
async def corridor_latest(session_id: str):
    s = _get(session_id)
    if not s.log:
        raise HTTPException(404, "no actions yet")
    return s.log[-1]["corridor"]


@router.post("/sessions/{session_id}/replay-verify")
async def replay_verify(session_id: str):
    s = _get(session_id)
    if not s.log:
        raise HTTPException(409, "session has no decisions")
    r = replay_controller(json.loads(json.dumps(s.log)), s.cfg)
    trace = s.controller.trace
    return r | {"original_final_hash": trace[-1].hash if trace else None,
                "terminated_by_operator": s.controller.state == ControllerState.TERMINATED}


@router.get("/protocols")
async def protocols():
    return PROTOCOLS


@router.post("/protocols/{protocol_id}/run")
async def run_protocol(protocol_id: str, seed: int = 0):
    runners = {"A": lambda: run_protocol_a(seed=seed, n_permutations=4), "B": lambda: run_protocol_b(seed=seed),
               "C": lambda: run_protocol_c(seed=seed), "D": lambda: run_protocol_d(seed=seed)}
    if protocol_id in runners:
        return json.loads(json.dumps(runners[protocol_id](), default=float))
    if protocol_id in {"E", "F", "G"}:
        return json.loads(json.dumps(run_protocol_causal(protocol_id, seed=seed), default=float))
    raise HTTPException(404, "unknown protocol")


@router.get("/hardware-checklist")
async def hardware_checklist():
    if not CHECKLIST.exists():
        raise HTTPException(404, "checklist not found")
    return json.loads(CHECKLIST.read_text(encoding="utf-8"))
