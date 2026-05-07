from fastapi import APIRouter, HTTPException

from app.core.errors import SessionNotFoundError
from app.schemas.state import BaselineInput, SelfReportInput
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["state"])


@router.post("/{session_id}/baseline")
async def set_baseline(session_id: str, data: BaselineInput):
    try:
        await session_service.store_baseline(session_id, data.model_dump())
        return {"status": "ok", "session_id": session_id}
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")


@router.post("/{session_id}/self-report")
async def submit_self_report(session_id: str, data: SelfReportInput):
    try:
        await session_service.store_self_report(session_id, data.model_dump())
        return {"status": "ok", "session_id": session_id}
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")
