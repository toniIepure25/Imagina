from datetime import datetime

from pydantic import BaseModel, Field


class CurriculumState(BaseModel):
    session_id: str
    timestamp: datetime
    current_level: int = Field(ge=1, le=8)
    level_name: str
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    difficulty: float = Field(ge=0, le=1)
    reason: str = ""
