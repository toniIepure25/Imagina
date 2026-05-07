from fastapi import APIRouter, HTTPException

from app.storage import event_store

router = APIRouter(prefix="/api/sessions", tags=["feedback"])


@router.get("/{session_id}/feedback/latest")
async def get_latest_feedback(session_id: str):
    events = await event_store.list_events(session_id, event_type="feedback_action")
    if not events:
        raise HTTPException(404, "No feedback found for this session")
    return events[-1].payload
