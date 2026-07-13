"""Synthetic runtime API — operator workflow for synthetic-only studies.

All endpoints are restricted to synthetic data classification.
No endpoint can create or run a human_research study.
Run state is persisted in the database and survives process restart.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.research.run_service import (
    RunConflictError,
    RunNotFoundError,
    RunTerminalError,
    check_abort_requested,
    create_run,
    finalize_abort,
    get_run,
    list_runs,
    mark_interrupted_on_startup,
    request_abort,
    update_run_phase,
    update_run_progress,
)
from app.storage.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/synthetic-runtime", tags=["synthetic-runtime"])

_EXPORT_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "synthetic_exports"
)

_task_registry: dict[str, asyncio.Task] = {}


class StudyCreateRequest(BaseModel):
    study_id: str = Field(..., min_length=1, max_length=128)
    participant_count: int = Field(default=6, ge=2, le=60)
    seed: int = Field(default=42)
    trials_per_session: int = Field(default=5, ge=1, le=30)
    windows_per_trial: int = Field(default=3, ge=1, le=20)


class RunStatusResponse(BaseModel):
    run_id: str
    study_id: str
    status: str
    current_phase: str | None = None
    sessions_completed: int = 0
    sessions_failed: int = 0
    total_sessions: int = 0
    export_ready: bool = False
    replay_verified: bool = False
    error: str | None = None


def _run_to_response(row: dict[str, Any]) -> RunStatusResponse:
    return RunStatusResponse(
        run_id=row["run_id"],
        study_id=row["study_id"],
        status=row["status"],
        current_phase=row.get("current_phase"),
        sessions_completed=row.get("completed_sessions", 0),
        sessions_failed=row.get("failed_sessions", 0),
        total_sessions=row.get("total_sessions", 0),
        export_ready=row["status"] in ("completed", "completed_with_failures"),
        replay_verified=False,
        error=row.get("error_message"),
    )


async def _ensure_study_exists(db, study_id: str, seed: int) -> None:
    """Create minimal study record so runtime_runs FK is satisfied."""
    existing = await (await db.execute(
        "SELECT study_id FROM studies WHERE study_id = ?", (study_id,)
    )).fetchone()
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at) "
            "VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?, ?)",
            (study_id, f"Synthetic Study {study_id}", seed, now, now),
        )
        await db.commit()


@router.post("/studies", status_code=202)
async def create_synthetic_study(
    request: StudyCreateRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=422, detail="Idempotency-Key header required")

    db = await get_db()
    try:
        await _ensure_study_exists(db, request.study_id, request.seed)

        input_params = request.model_dump()
        run_row = await create_run(
            db, request.study_id, idempotency_key, input_params,
            request.seed, request.participant_count * 3,
        )

        if run_row["status"] != "accepted":
            return _run_to_response(run_row)

        task = asyncio.create_task(
            _execute_run(run_row["run_id"], request)
        )
        _task_registry[run_row["run_id"]] = task

        return {
            "run_id": run_row["run_id"],
            "status": "accepted",
            "poll_url": f"/api/synthetic-runtime/runs/{run_row['run_id']}",
        }
    except RunConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    finally:
        await db.close()


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_response(row)
    finally:
        await db.close()


@router.get("/runs")
async def list_all_runs():
    db = await get_db()
    try:
        rows = await list_runs(db)
        return [_run_to_response(r) for r in rows]
    finally:
        await db.close()


@router.post("/runs/{run_id}/abort")
async def abort_run(run_id: str):
    db = await get_db()
    try:
        row = await request_abort(db, run_id)
        return _run_to_response(row)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    except RunTerminalError as e:
        raise HTTPException(status_code=409, detail=str(e))
    finally:
        await db.close()


@router.get("/runs/{run_id}/sessions")
async def get_run_sessions(run_id: str):
    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")

        sessions = await (await db.execute(
            "SELECT research_session_id, participant_id, condition, status, "
            "session_index, runtime_seed "
            "FROM research_sessions WHERE study_id = ? ORDER BY research_session_id",
            (row["study_id"],),
        )).fetchall()
        return [dict(s) for s in sessions]
    finally:
        await db.close()


@router.get("/runs/{run_id}/failures")
async def get_run_failures(run_id: str):
    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")

        sessions = await (await db.execute(
            "SELECT research_session_id, participant_id, condition, status, terminal_reason "
            "FROM research_sessions WHERE study_id = ? AND status NOT IN ('completed', 'planned')",
            (row["study_id"],),
        )).fetchall()
        return [dict(s) for s in sessions]
    finally:
        await db.close()


@router.get("/exports/{study_id}")
async def get_export(study_id: str):
    export_dir = os.path.join(_EXPORT_ROOT, study_id)
    if not os.path.isdir(export_dir):
        raise HTTPException(status_code=404, detail="Export not found")
    files = os.listdir(export_dir)
    return {"study_id": study_id, "files": files, "export_dir": study_id}


@router.get("/exports/{study_id}/validation")
async def get_export_validation(study_id: str):
    export_dir = os.path.join(_EXPORT_ROOT, study_id)
    if not os.path.isdir(export_dir):
        raise HTTPException(status_code=404, detail="Export not found")

    from app.research.export_service import validate_export
    result = validate_export(export_dir)
    return {"study_id": study_id, **result}


@router.get("/replay/{study_id}")
async def get_replay_status(study_id: str):
    db = await get_db()
    try:
        rows = await list_runs(db, study_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Study not found")
        latest = rows[0]
        return {
            "study_id": study_id,
            "replay_verified": False,
            "run_status": latest["status"],
        }
    finally:
        await db.close()


@router.post("/replay/{study_id}/start", status_code=202)
async def start_replay_verification(study_id: str):
    return {
        "study_id": study_id,
        "status": "replay_not_implemented_yet",
        "message": "Replay verification is available via CLI and tests. API endpoint pending.",
    }


async def recover_interrupted_runs() -> int:
    db = await get_db()
    try:
        count = await mark_interrupted_on_startup(db)
        if count > 0:
            logger.warning("Marked %d interrupted run(s) on startup", count)
        return count
    finally:
        await db.close()


async def _execute_run(run_id: str, request: StudyCreateRequest):
    from app.research.synthetic_orchestrator import run_synthetic_study

    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        await update_run_phase(db, run_id, "running", "running", started_at=now)

        export_dir = os.path.join(_EXPORT_ROOT, request.study_id)
        os.makedirs(_EXPORT_ROOT, exist_ok=True)

        async def abort_checker():
            return await check_abort_requested(db, run_id)

        result = await run_synthetic_study(
            db=db,
            study_id=request.study_id,
            participant_count=request.participant_count,
            seed=request.seed,
            trials_per_session=request.trials_per_session,
            windows_per_trial=request.windows_per_trial,
            export_dir=export_dir,
            run_id=run_id,
            abort_check=abort_checker,
        )

        completed = result["sessions_completed"]
        failed = result["sessions_failed"]
        await update_run_progress(db, run_id, completed, failed)

        if result.get("aborted"):
            await finalize_abort(db, run_id, completed, "abort_requested")
        else:
            final_status = "completed_with_failures" if failed > 0 else "completed"
            now = datetime.now(timezone.utc).isoformat()
            await update_run_phase(db, run_id, final_status, "completed", ended_at=now)
    except Exception as e:
        try:
            now = datetime.now(timezone.utc).isoformat()
            await update_run_phase(db, run_id, "failed", "failed",
                                   error_message=str(e), ended_at=now)
        except Exception:
            pass
        logger.exception("Run %s failed", run_id)
    finally:
        await db.close()
        _task_registry.pop(run_id, None)
