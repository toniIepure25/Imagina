from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SelfReport(BaseModel):
    session_id: str
    timestamp: datetime
    vividness: int = Field(ge=1, le=10)
    stability: int = Field(ge=1, le=10)
    focus: int = Field(ge=1, le=10)
    relaxation: int = Field(ge=1, le=10)
    effort: int = Field(ge=1, le=10)
    fatigue: int = Field(ge=1, le=10)
    distraction: int = Field(ge=1, le=10)
    notes: Optional[str] = None


class SelfReportInput(BaseModel):
    vividness: int = Field(ge=1, le=10)
    stability: int = Field(ge=1, le=10)
    focus: int = Field(ge=1, le=10)
    relaxation: int = Field(ge=1, le=10)
    effort: int = Field(ge=1, le=10)
    fatigue: int = Field(ge=1, le=10)
    distraction: int = Field(ge=1, le=10)
    notes: Optional[str] = None


class BaselineInput(BaseModel):
    focus: int = Field(ge=1, le=10)
    relaxation: int = Field(ge=1, le=10)
    vividness: int = Field(ge=1, le=10)
    fatigue: int = Field(ge=1, le=10)
