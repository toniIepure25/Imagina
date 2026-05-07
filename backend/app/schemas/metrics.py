from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StateEstimate(BaseModel):
    session_id: str
    timestamp: datetime
    window_index: int
    attention_stability: float = Field(ge=0, le=1)
    relaxation: float = Field(ge=0, le=1)
    imagery_engagement: float = Field(ge=0, le=1)
    behavioral_consistency: float = Field(ge=0, le=1)
    fatigue: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class PIDEstimate(BaseModel):
    session_id: str
    timestamp: datetime
    window_index: int
    pid: float = Field(ge=0, le=1)
    neural_proxy_distance: float = Field(ge=0, le=1)
    behavioral_distance: float = Field(ge=0, le=1)
    uncertainty_component: float = Field(ge=0, le=1)
    interpretation: Literal["excellent", "good", "unstable", "fatigue_risk", "unknown"]


class IQIEstimate(BaseModel):
    session_id: str
    timestamp: datetime
    window_index: int
    iqi: float = Field(ge=0, le=1)
    stability_component: float = Field(ge=0, le=1)
    engagement_component: float = Field(ge=0, le=1)
    relaxation_component: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
