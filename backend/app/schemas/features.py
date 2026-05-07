from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeatureVector(BaseModel):
    session_id: str
    timestamp: datetime
    window_index: int
    theta_power: float = Field(ge=0, le=1)
    alpha_power: float = Field(ge=0, le=1)
    beta_power: float = Field(ge=0, le=1)
    theta_beta_ratio: float = Field(ge=0)
    alpha_stability: float = Field(ge=0, le=1)
    signal_quality: float = Field(ge=0, le=1)
    simulated_imagery_strength: float = Field(ge=0, le=1)
    behavioral_stability: float = Field(ge=0, le=1)
    reaction_time_ms: Optional[float] = None
