from datetime import datetime

from pydantic import BaseModel


class EventEnvelope(BaseModel):
    event_id: str
    session_id: str
    event_type: str
    timestamp: datetime
    payload: dict
    schema_version: str = "1.0"
