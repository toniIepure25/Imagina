"""ANIMUS REST API — closed-loop imagination amplifier (ANIMUS-P1).

Thin FastAPI layer over ``AnimusService``. Simulated/behavioral only (claim levels L0/L1); no endpoint can
raise the claim level. Benchmark runs here are bounded so the API stays responsive.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.animus.evidence_registry import registry_snapshot
from app.core.animus.service import AnimusSessionError, animus_service

router = APIRouter(prefix="/animus", tags=["animus"])


class CreateSessionRequest(BaseModel):
    mode: str = "amplifier"
    controller: str = "ANIMUS_ACTIVE"
    seed: int = 20260909
    max_iterations: int = 8
    observation_mode: str | None = None
    target_index: int | None = None


class FeedbackRequest(BaseModel):
    channel: str
    candidate_id: str | None = None
    preferred_embedding: list[float] | None = None
    closer: bool | None = None
    attribute: str | None = None
    target_option: str | None = None
    direction: str | None = None
    object: str | None = None
    op: str | None = None
    confidence: float | None = None
    text: str | None = None
    strength: float | None = None


class GenerateRequest(BaseModel):
    n: int = 1
    jitter: float = 0.0


class BenchmarkRequest(BaseModel):
    n_targets: int = 8
    seed_families: list[int] = [1]


def _guard(fn):
    try:
        return fn()
    except AnimusSessionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/health")
async def health():
    return {"status": "ok", "system": "ANIMUS", "milestone": "ANIMUS-P1",
            "claim_ceiling": "L1_BEHAVIORAL_ASSISTED"}


@router.get("/scientific-registry")
async def scientific_registry():
    return registry_snapshot()


@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
    return _guard(lambda: animus_service.create_session(
        mode=req.mode, controller=req.controller, seed=req.seed,
        max_iterations=req.max_iterations, observation_mode=req.observation_mode,
        target_index=req.target_index))


@router.post("/sessions/{sid}/observe")
async def observe(sid: str):
    # synthetic/benchmark sessions gather observations inside step(); expose a single step here.
    return _guard(lambda: animus_service.step(sid))


@router.post("/sessions/{sid}/step")
async def step(sid: str):
    return _guard(lambda: animus_service.step(sid))


@router.post("/sessions/{sid}/next-action")
async def next_action(sid: str):
    return _guard(lambda: animus_service.next_action(sid))


@router.post("/sessions/{sid}/generate")
async def generate(sid: str, req: GenerateRequest):
    return _guard(lambda: animus_service.generate_candidate(sid, n=req.n, jitter=req.jitter))


@router.post("/sessions/{sid}/feedback")
async def feedback(sid: str, req: FeedbackRequest):
    raw = {k: v for k, v in req.model_dump().items() if v is not None}
    return _guard(lambda: animus_service.apply_feedback(sid, raw))


@router.post("/sessions/{sid}/stop")
async def stop(sid: str):
    return _guard(lambda: animus_service.stop(sid))


@router.delete("/sessions/{sid}")
async def delete(sid: str):
    return _guard(lambda: animus_service.delete(sid))


@router.get("/sessions/{sid}")
async def get_session(sid: str):
    return _guard(lambda: animus_service.state(sid))


@router.get("/sessions/{sid}/belief")
async def get_belief(sid: str):
    return _guard(lambda: animus_service.belief(sid))


@router.get("/sessions/{sid}/candidates")
async def get_candidates(sid: str):
    return _guard(lambda: animus_service.candidates(sid))


@router.get("/sessions/{sid}/timeline")
async def get_timeline(sid: str):
    return _guard(lambda: animus_service.timeline(sid))


@router.get("/sessions/{sid}/replay")
async def get_replay(sid: str):
    return _guard(lambda: animus_service.replay(sid))


@router.get("/sessions/{sid}/amplification-summary")
async def amplification_summary(sid: str):
    return _guard(lambda: animus_service.amplification_summary(sid))


@router.post("/benchmarks/run")
async def run_benchmark(req: BenchmarkRequest):
    from app.core.animus.benchmark import run_campaign
    n = min(req.n_targets, 24)          # bounded for API responsiveness
    campaign = run_campaign(n_targets=n, seed_families=tuple(req.seed_families[:2] or [1]),
                            max_iterations=8)
    from app.research.animus.run_animus_p1_benchmark import decide, determinism_audit, privacy_audit, summarize
    per = summarize(campaign)
    return {"per_controller": per,
            "decision": decide(per, privacy_audit(), determinism_audit(n_targets=4))}
