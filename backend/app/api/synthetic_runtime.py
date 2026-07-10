"""Synthetic runtime API — operator workflow for synthetic-only studies.

All endpoints are restricted to synthetic data classification.
No endpoint can create or run a human_research study.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/synthetic-runtime", tags=["synthetic-runtime"])

_EXPORT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "synthetic_exports")

_active_runs: dict[str, dict[str, Any]] = {}


class StudyCreateRequest(BaseModel):
    study_id: str = Field(..., min_length=1, max_length=128)
    participant_count: int = Field(default=6, ge=2, le=60)
    seed: int = Field(default=42)
    trials_per_session: int = Field(default=5, ge=1, le=30)
    windows_per_trial: int = Field(default=3, ge=1, le=20)
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class RunStatusResponse(BaseModel):
    run_id: str
    study_id: str
    status: str
    sessions_completed: int = 0
    sessions_failed: int = 0
    total_sessions: int = 0
    export_ready: bool = False
    replay_verified: bool = False
    error: str | None = None


@router.post("/studies", status_code=202)
async def create_synthetic_study(request: StudyCreateRequest):
    if request.study_id in _active_runs:
        existing = _active_runs[request.study_id]
        if existing.get("idempotency_key") == request.idempotency_key:
            return {"run_id": existing["run_id"], "status": existing["status"]}
        raise HTTPException(status_code=409, detail="Study already exists with different parameters")

    run_id = str(uuid.uuid4())
    run_info = {
        "run_id": run_id,
        "study_id": request.study_id,
        "status": "accepted",
        "idempotency_key": request.idempotency_key,
        "sessions_completed": 0,
        "sessions_failed": 0,
        "total_sessions": request.participant_count * 3,
        "export_ready": False,
        "replay_verified": False,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _active_runs[request.study_id] = run_info

    asyncio.create_task(_execute_run(request, run_id))

    return {"run_id": run_id, "status": "accepted", "poll_url": f"/api/synthetic-runtime/runs/{run_id}"}


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    for info in _active_runs.values():
        if info["run_id"] == run_id:
            return RunStatusResponse(**{k: info[k] for k in RunStatusResponse.model_fields})
    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/runs")
async def list_runs():
    return [
        RunStatusResponse(**{k: info[k] for k in RunStatusResponse.model_fields})
        for info in _active_runs.values()
    ]


@router.post("/runs/{run_id}/abort")
async def abort_run(run_id: str):
    for info in _active_runs.values():
        if info["run_id"] == run_id:
            if info["status"] in ("completed", "failed"):
                raise HTTPException(status_code=409, detail=f"Run already {info['status']}")
            info["status"] = "aborted"
            return {"run_id": run_id, "status": "aborted"}
    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/exports/{study_id}")
async def get_export(study_id: str):
    export_dir = os.path.join(_EXPORT_ROOT, study_id)
    if not os.path.isdir(export_dir):
        raise HTTPException(status_code=404, detail="Export not found")

    files = os.listdir(export_dir)
    return {
        "study_id": study_id,
        "files": files,
        "export_dir": study_id,
    }


@router.get("/replay/{study_id}")
async def get_replay_status(study_id: str):
    for info in _active_runs.values():
        if info["study_id"] == study_id:
            return {
                "study_id": study_id,
                "replay_verified": info.get("replay_verified", False),
                "replay_hash": info.get("replay_hash"),
            }
    raise HTTPException(status_code=404, detail="Study not found")


async def _execute_run(request: StudyCreateRequest, run_id: str):
    from app.research.synthetic_orchestrator import run_synthetic_study

    info = _active_runs[request.study_id]
    info["status"] = "running"

    export_dir = os.path.join(_EXPORT_ROOT, request.study_id)
    db_path = os.path.join(_EXPORT_ROOT, f"{request.study_id}.db")
    os.makedirs(_EXPORT_ROOT, exist_ok=True)

    try:
        result = await run_synthetic_study(
            db_path=db_path,
            study_id=request.study_id,
            participant_count=request.participant_count,
            seed=request.seed,
            trials_per_session=request.trials_per_session,
            windows_per_trial=request.windows_per_trial,
            export_dir=export_dir,
        )
        info["sessions_completed"] = result["sessions_completed"]
        info["sessions_failed"] = result["sessions_failed"]
        info["export_ready"] = True
        info["status"] = "completed"
    except Exception as e:
        info["status"] = "failed"
        info["error"] = str(e)
