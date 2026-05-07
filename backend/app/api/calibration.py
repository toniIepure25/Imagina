from fastapi import APIRouter, HTTPException

from app.core.errors import SessionNotFoundError
from app.schemas.calibration import CalibrationCompleteInput, CalibrationProfile
from app.services import calibration_service, session_service

router = APIRouter(prefix="/api/sessions/{session_id}/calibration", tags=["calibration"])


@router.post("/start")
async def start(session_id: str):
    try:
        await session_service.get_session(session_id)
        return await calibration_service.start_calibration(session_id)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")


@router.post("/complete", response_model=CalibrationProfile)
async def complete(session_id: str, data: CalibrationCompleteInput):
    try:
        session = await session_service.get_session(session_id)
        return await calibration_service.complete_calibration(session_id, session.user_id, data)
    except SessionNotFoundError:
        raise HTTPException(404, "Session not found")


@router.get("", response_model=CalibrationProfile)
async def get(session_id: str):
    profile = await calibration_service.get_calibration(session_id)
    if not profile:
        raise HTTPException(404, "Calibration not found")
    return profile
