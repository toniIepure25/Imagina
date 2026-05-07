from fastapi import APIRouter, HTTPException

from app.core.errors import SessionNotFoundError, SessionStateError
from app.schemas.reports import SessionSummary
from app.schemas.session import Session, SessionCreate
from app.services import session_service
from app.services.report_service import generate_summary

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=Session)
async def create(data: SessionCreate):
    return await session_service.create_session(data)


@router.get("/{session_id}", response_model=Session)
async def get(session_id: str):
    try:
        return await session_service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")


@router.get("/{session_id}/summary", response_model=SessionSummary)
async def summary(session_id: str):
    try:
        await session_service.get_session(session_id)
        return await generate_summary(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")


@router.post("/{session_id}/start", response_model=Session)
async def start(session_id: str):
    try:
        return await session_service.start_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")
    except SessionStateError as e:
        raise HTTPException(409, str(e))


@router.post("/{session_id}/stop", response_model=Session)
async def stop(session_id: str):
    try:
        return await session_service.stop_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")
    except SessionStateError as e:
        raise HTTPException(409, str(e))
