from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EEGSampleWindow(BaseModel):
    """Simulated EEG-like signal window. Clearly marked as simulated in V1."""

    session_id: str
    timestamp: datetime
    window_index: int
    sampling_rate_hz: int = 256
    duration_seconds: float = 2.0
    channels: list[str] = ["Fz", "Cz", "Pz", "Oz"]
    samples: Optional[list[list[float]]] = None
    simulated: bool = True
    generator_version: str = "sim_v1"
