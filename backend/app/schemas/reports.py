from datetime import datetime

from pydantic import BaseModel


class SessionSummary(BaseModel):
    session_id: str
    duration_seconds: float
    average_pid: float
    best_pid: float
    average_iqi: float
    best_iqi: float
    max_level_reached: int
    best_stability_streak_seconds: float
    fatigue_peak: float
    safety_events_count: int
    recommendation: str
    generated_at: datetime
    signal_provider_id: str | None = None
    scenario: str | None = None
    experiment_run_id: str | None = None
    calibration_quality_score: float | None = None
    real_signal: bool | None = None
    provider_type: str | None = None
