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


class ErrorEnvelope(BaseModel):
    error: dict[str, Any]


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


def _error(code: str, message: str, status: int = 400, details: dict | None = None):
    payload: dict[str, Any] = {"code": code, "message": message}
    if details:
        payload["details"] = details
    raise HTTPException(status_code=status, detail={"error": payload})


async def _run_to_response(row: dict[str, Any], db=None) -> dict[str, Any]:
    export_ready = False
    replay_verified = False

    if db and row["status"] in ("completed", "completed_with_failures"):
        export_row = await (await db.execute(
            "SELECT export_id FROM export_runs WHERE study_id = ? ORDER BY created_at DESC LIMIT 1",
            (row["study_id"],),
        )).fetchone()
        export_ready = export_row is not None

        replay_rows = await (await db.execute(
            "SELECT match FROM replay_results rr "
            "JOIN research_sessions s ON rr.research_session_id = s.research_session_id "
            "WHERE s.study_id = ?",
            (row["study_id"],),
        )).fetchall()
        if replay_rows and all(r["match"] == 1 for r in replay_rows):
            replay_verified = True

    return RunStatusResponse(
        run_id=row["run_id"],
        study_id=row["study_id"],
        status=row["status"],
        current_phase=row.get("current_phase"),
        sessions_completed=row.get("completed_sessions", 0),
        sessions_failed=row.get("failed_sessions", 0),
        total_sessions=row.get("total_sessions", 0),
        export_ready=export_ready,
        replay_verified=replay_verified,
        error=row.get("error_message"),
    ).model_dump()


async def _ensure_study_exists(db, study_id: str, seed: int) -> None:
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


# --- Run lifecycle ---

@router.post("/studies", status_code=202)
async def create_synthetic_study(
    request: StudyCreateRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        _error("MISSING_IDEMPOTENCY_KEY", "Idempotency-Key header required", 422)

    db = await get_db()
    try:
        await _ensure_study_exists(db, request.study_id, request.seed)
        input_params = request.model_dump()
        run_row = await create_run(
            db, request.study_id, idempotency_key, input_params,
            request.seed, request.participant_count * 3,
        )

        if run_row["status"] != "accepted":
            return await _run_to_response(run_row, db)

        task = asyncio.create_task(_execute_run(run_row["run_id"], request))
        _task_registry[run_row["run_id"]] = task

        return {
            "run_id": run_row["run_id"],
            "status": "accepted",
            "poll_url": f"/api/synthetic-runtime/runs/{run_row['run_id']}",
        }
    except RunConflictError as e:
        _error("IDEMPOTENCY_CONFLICT", str(e), 409)
    finally:
        await db.close()


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)
        return await _run_to_response(row, db)
    finally:
        await db.close()


@router.get("/runs")
async def list_all_runs():
    db = await get_db()
    try:
        rows = await list_runs(db)
        return [await _run_to_response(r, db) for r in rows]
    finally:
        await db.close()


@router.post("/runs/{run_id}/abort")
async def abort_run(run_id: str):
    db = await get_db()
    try:
        row = await request_abort(db, run_id)
        return await _run_to_response(row, db)
    except RunNotFoundError:
        _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)
    except RunTerminalError as e:
        _error("LIFECYCLE_CONFLICT", str(e), 409)
    finally:
        await db.close()


@router.get("/runs/{run_id}/sessions")
async def get_run_sessions(run_id: str):
    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)

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
            _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)

        sessions = await (await db.execute(
            "SELECT research_session_id, participant_id, condition, status, terminal_reason "
            "FROM research_sessions WHERE study_id = ? AND status NOT IN ('completed', 'planned')",
            (row["study_id"],),
        )).fetchall()
        return [dict(s) for s in sessions]
    finally:
        await db.close()


# --- Export ---

@router.post("/runs/{run_id}/export", status_code=202)
async def create_export(run_id: str, allow_overwrite: bool = False):
    from app.research.export_service import ExportExistsError, export_synthetic_dataset

    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)
        if row["status"] not in ("completed", "completed_with_failures"):
            _error("LIFECYCLE_CONFLICT", "Run must be completed before export", 409)

        export_dir = os.path.join(_EXPORT_ROOT, row["study_id"])
        os.makedirs(_EXPORT_ROOT, exist_ok=True)

        result = await export_synthetic_dataset(
            db, row["study_id"], export_dir, allow_overwrite=allow_overwrite,
        )
        return {
            "export_id": result["export_id"],
            "study_id": row["study_id"],
            "package_hash": result["package_hash"],
            "validation": result["validation"],
        }
    except ExportExistsError:
        _error("EXPORT_EXISTS", "Export already exists. Set allow_overwrite=true.", 409)
    finally:
        await db.close()


@router.get("/exports/{study_id}")
async def get_export_status(study_id: str):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT * FROM export_runs WHERE study_id = ? ORDER BY created_at DESC LIMIT 1",
            (study_id,),
        )).fetchone()
        if not row:
            _error("EXPORT_NOT_FOUND", f"No export for study {study_id}", 404)

        export_dir = os.path.join(_EXPORT_ROOT, study_id)
        from app.research.export_service import validate_export
        validation = validate_export(export_dir) if os.path.isdir(export_dir) else {"valid": False}

        return {
            "export_id": row["export_id"],
            "study_id": study_id,
            "data_classification": row["data_classification"],
            "manifest_hash": row["manifest_hash"],
            "export_ready": validation.get("valid", False),
            "validation": validation,
        }
    finally:
        await db.close()


@router.get("/exports/{study_id}/validation")
async def get_export_validation(study_id: str):
    export_dir = os.path.join(_EXPORT_ROOT, study_id)
    if not os.path.isdir(export_dir):
        _error("EXPORT_NOT_FOUND", f"Export directory for {study_id} not found", 404)

    from app.research.export_service import validate_export
    result = validate_export(export_dir)
    return {"study_id": study_id, **result}


# --- Replay ---

@router.post("/runs/{run_id}/replay/{session_id}", status_code=202)
async def create_replay(run_id: str, session_id: str):
    from app.research.replay_validator import replay_session_from_manifest

    db = await get_db()
    try:
        row = await get_run(db, run_id)
        if not row:
            _error("RUN_NOT_FOUND", f"Run {run_id} not found", 404)

        session_row = await (await db.execute(
            "SELECT status FROM research_sessions WHERE research_session_id = ?",
            (session_id,),
        )).fetchone()
        if not session_row:
            _error("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)
        if session_row["status"] != "completed":
            _error("LIFECYCLE_CONFLICT", f"Session is {session_row['status']}, not completed", 409)

        result = await replay_session_from_manifest(db, session_id, persist_result=True)
        return result
    finally:
        await db.close()


@router.get("/replay/{session_id}")
async def get_replay_status(session_id: str):
    db = await get_db()
    try:
        from app.research.replay_validator import get_replay_results
        results = await get_replay_results(db, session_id)
        if not results:
            return {
                "session_id": session_id,
                "replay_verified": False,
                "status": "no_replay",
            }
        latest = results[0]
        return {
            "session_id": session_id,
            "replay_verified": bool(latest["match"]),
            "replay_hash": latest.get("replay_content_hash"),
            "original_hash": latest.get("original_content_hash"),
            "verified_at": latest.get("verified_at"),
            "run_status": latest.get("run_status"),
        }
    finally:
        await db.close()


@router.get("/replay/{session_id}/result")
async def get_replay_result(session_id: str):
    db = await get_db()
    try:
        from app.research.replay_validator import get_replay_results
        results = await get_replay_results(db, session_id)
        if not results:
            _error("REPLAY_NOT_FOUND", f"No replay results for session {session_id}", 404)
        return results[0]
    finally:
        await db.close()


# --- Manifests and seals ---

@router.get("/manifests/{session_id}")
async def get_manifest(session_id: str):
    db = await get_db()
    try:
        from app.research.manifest import get_manifest as _get_manifest
        result = await _get_manifest(db, session_id)
        if not result:
            _error("MANIFEST_NOT_FOUND", f"No manifest for session {session_id}", 404)
        return result
    finally:
        await db.close()


@router.get("/manifests/{session_id}/validation")
async def validate_manifest_endpoint(session_id: str):
    db = await get_db()
    try:
        from app.research.manifest import validate_manifest
        return await validate_manifest(db, session_id)
    finally:
        await db.close()


@router.get("/seals/{session_id}")
async def get_seal(session_id: str):
    db = await get_db()
    try:
        from app.research.manifest import get_completion_seal
        seal = await get_completion_seal(db, session_id)
        if not seal:
            _error("SEAL_NOT_FOUND", f"No completion seal for session {session_id}", 404)
        return seal
    finally:
        await db.close()


@router.get("/seals/{session_id}/integrity")
async def verify_seal(session_id: str):
    db = await get_db()
    try:
        from app.research.manifest import verify_seal_integrity
        return await verify_seal_integrity(db, session_id)
    finally:
        await db.close()


# --- Startup recovery ---

async def recover_interrupted_runs() -> int:
    db = await get_db()
    try:
        count = await mark_interrupted_on_startup(db)
        if count > 0:
            logger.warning("Marked %d interrupted run(s) on startup", count)
        return count
    finally:
        await db.close()


# --- Execution ---

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
