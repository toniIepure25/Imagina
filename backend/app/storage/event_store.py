import json
import uuid
from datetime import datetime

from app.core.time import utcnow
from app.schemas.events import EventEnvelope
from app.storage.database import get_db


async def append_event(
    session_id: str,
    event_type: str,
    payload: dict,
    timestamp: datetime | None = None,
) -> EventEnvelope:
    ts = timestamp or utcnow()
    envelope = EventEnvelope(
        event_id=str(uuid.uuid4()),
        session_id=session_id,
        event_type=event_type,
        timestamp=ts,
        payload=payload,
    )
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO events "
            "(event_id, session_id, event_type, timestamp, payload, schema_version) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                envelope.event_id,
                envelope.session_id,
                envelope.event_type,
                envelope.timestamp.isoformat(),
                json.dumps(envelope.payload),
                envelope.schema_version,
            ),
        )
        await db.commit()
    finally:
        await db.close()
    return envelope


async def list_events(
    session_id: str, event_type: str | None = None
) -> list[EventEnvelope]:
    db = await get_db()
    try:
        if event_type:
            cursor = await db.execute(
                "SELECT * FROM events WHERE session_id = ? AND event_type = ? "
                "ORDER BY timestamp",
                (session_id, event_type),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            )
        rows = await cursor.fetchall()
        return [
            EventEnvelope(
                event_id=r["event_id"],
                session_id=r["session_id"],
                event_type=r["event_type"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                payload=json.loads(r["payload"]),
                schema_version=r["schema_version"],
            )
            for r in rows
        ]
    finally:
        await db.close()


async def replay_events(session_id: str) -> list[dict]:
    """Return events as plain dicts for replay streaming."""
    events = await list_events(session_id)
    return [e.model_dump(mode="json") for e in events]
