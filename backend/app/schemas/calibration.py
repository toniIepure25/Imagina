from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CalibrationCompleteInput(BaseModel):
    duration_seconds: int = Field(default=30, ge=5, le=600)
    mode: Literal["simulated", "manual", "replay", "lsl_stub", "lsl"] = "simulated"
    focus: int = Field(ge=1, le=10)
    relaxation: int = Field(ge=1, le=10)
    vividness: int = Field(ge=1, le=10)
    fatigue: int = Field(ge=1, le=10)
    notes: str | None = None


class CalibrationProfile(BaseModel):
    calibration_id: str
    session_id: str
    user_id: str | None = None
    created_at: datetime
    duration_seconds: int
    mode: str
    baseline_focus: float
    baseline_relaxation: float
    baseline_vividness: float
    baseline_fatigue: float
    baseline_theta_power: float
    baseline_alpha_power: float
    baseline_beta_power: float
    baseline_theta_beta_ratio: float
    baseline_signal_quality: float
    calibration_quality_score: float = Field(ge=0, le=1)
    warnings: list[str]
    normalization_params: dict
    notes: str | None = None

    provider_id: str | None = None
    provider_type: str | None = None
    real_eeg: bool = False
    stream_name: str | None = None
    channel_count: Optional[int] = Field(default=None, ge=0)
    channel_names: list[str] | None = None
    sampling_rate_hz: Optional[float] = Field(default=None, gt=0)
    artifact_warning_count: int = Field(default=0, ge=0)
    preprocessing_version: str | None = None
