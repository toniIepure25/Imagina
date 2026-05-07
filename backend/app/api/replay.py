from fastapi import APIRouter, HTTPException

from app.schemas.replay import ReplayRequest
from app.services import replay_service
from app.storage import event_store

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.post("/demo")
async def create_demo(data: ReplayRequest | None = None):
    req = data or ReplayRequest()
    session = await replay_service.create_demo_session(
        scenario=req.scenario, seed=req.seed, duration_windows=req.duration_windows
    )
    return {"session_id": session.session_id, "status": "demo_created"}


@router.get("/{session_id}/events")
async def get_events(session_id: str):
    events = await event_store.list_events(session_id)
    if not events:
        raise HTTPException(404, "No events found for session")
    return [e.model_dump(mode="json") for e in events]


@router.post("/{session_id}/pause")
async def pause(session_id: str):
    replay_service.pause_replay(session_id)
    return {"status": "paused"}


@router.post("/{session_id}/resume")
async def resume(session_id: str):
    replay_service.resume_replay(session_id)
    return {"status": "resumed"}
