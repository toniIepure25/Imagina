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

    real_signal: bool = False
    provider_id: str | None = None
    provider_type: str | None = None
    channel_count: Optional[int] = Field(default=None, ge=0)
    sampling_rate_hz: Optional[int] = Field(default=None, gt=0)
    channels_used: list[str] | None = None
    artifact_flags: list[str] | None = None
    blink_score: Optional[float] = Field(default=None, ge=0, le=1)
    muscle_score: Optional[float] = Field(default=None, ge=0, le=1)
    drift_score: Optional[float] = Field(default=None, ge=0, le=1)
    clipping_score: Optional[float] = Field(default=None, ge=0, le=1)
    missing_data_ratio: Optional[float] = Field(default=None, ge=0, le=1)
    preprocessing_version: str | None = None
    feature_version: str | None = None
