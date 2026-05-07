from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    task_id: str = "corridor_simple"
    mode: Literal["simulated", "replay", "manual"] = "simulated"
    signal_provider_id: str = "simulated.default"
    scenario: Optional[str] = "improving_user"
    experiment_run_id: Optional[str] = None
    safety_disclaimer_acknowledged: bool = False


class Session(BaseModel):
    session_id: str
    user_id: str
    display_name: Optional[str] = None
    mode: Literal["simulated", "replay", "manual"] = "simulated"
    status: Literal[
        "created", "calibrating", "running", "paused", "completed", "aborted"
    ] = "created"
    task_id: str = "corridor_simple"
    signal_provider_id: str = "simulated.default"
    scenario: Optional[str] = "improving_user"
    experiment_run_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    safety_disclaimer_acknowledged: bool = False
