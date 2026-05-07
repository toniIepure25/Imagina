from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileCreate(BaseModel):
    display_name: str = "Anonymous"
    preferred_task_type: str = "corridor_simple"
    preferred_feedback_style: str = "balanced"


class ImageryProfile(BaseModel):
    user_id: str
    display_name: str
    created_at: datetime
    updated_at: datetime
    local_only: bool = True
    total_sessions: int = 0
    total_minutes: float = 0.0
    max_level_reached: int = 1
    average_iqi: float = Field(default=0.0, ge=0, le=1)
    best_iqi: float = Field(default=0.0, ge=0, le=1)
    average_pid: float = Field(default=1.0, ge=0, le=1)
    best_pid: float = Field(default=1.0, ge=0, le=1)
    fatigue_sensitivity: float = Field(default=0.5, ge=0, le=1)
    preferred_task_type: str = "corridor_simple"
    preferred_feedback_style: str = "balanced"
    optimal_difficulty_estimate: float = Field(default=0.125, ge=0, le=1)
    best_scene_parameters: dict = Field(default_factory=dict)
    progress_history_summary: list[dict] = Field(default_factory=list)
    processed_session_ids: list[str] = Field(default_factory=list)


class ProfileRecommendation(BaseModel):
    user_id: str
    recommended_task: str
    recommended_duration_minutes: int
    recommended_starting_level: int
    rationale: str
