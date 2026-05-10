from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EEGSampleWindow(BaseModel):
    """EEG signal window. simulated=True for V1/V2 simulated providers; real EEG uses simulated=False."""

    session_id: str
    timestamp: datetime
    window_index: int
    sampling_rate_hz: int = 256
    duration_seconds: float = 2.0
    channels: list[str] = ["Fz", "Cz", "Pz", "Oz"]
    samples: Optional[list[list[float]]] = None
    simulated: bool = True
    generator_version: str = "sim_v1"

    provider_id: str | None = None
    provider_type: str | None = None
    stream_name: str | None = None
    stream_type: str | None = None
    source_id: str | None = None
    nominal_sampling_rate_hz: Optional[float] = Field(default=None, gt=0)
    effective_sampling_rate_hz: Optional[float] = Field(default=None, gt=0)
    channel_names: list[str] | None = None
    channel_count: Optional[int] = Field(default=None, ge=0)
    channel_units: list[str] | None = None
    window_start_time_lsl: float | None = None
    window_end_time_lsl: float | None = None
    dropped_samples: Optional[int] = Field(default=None, ge=0)
    artifact_flags: list[str] | None = None
    signal_quality: Optional[float] = Field(default=None, ge=0, le=1)
    raw_persisted: bool = False
    preprocessing_version: str | None = None
