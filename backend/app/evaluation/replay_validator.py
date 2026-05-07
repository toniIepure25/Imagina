from app.storage import event_store


async def validate_replay(session_id: str) -> dict:
    events = await event_store.list_events(session_id)
    ordered = all(events[i].timestamp <= events[i + 1].timestamp for i in range(len(events) - 1))
    return {
        "session_id": session_id,
        "event_count": len(events),
        "ordered": ordered,
        "has_feature_vectors": any(ev.event_type == "feature_vector" for ev in events),
        "has_feedback": any(ev.event_type == "feedback_action" for ev in events),
    }
