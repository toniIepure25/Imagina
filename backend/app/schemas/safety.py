from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SafetyEvent(BaseModel):
    session_id: str
    timestamp: datetime
    severity: Literal["info", "warning", "stop"]
    event_type: Literal[
        "fatigue_high",
        "dissociation_warning",
        "overeffort",
        "signal_unstable",
        "session_too_long",
    ]
    message: str
    recommended_action: str
