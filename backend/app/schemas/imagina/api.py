"""IMAGINA API Request/Response Pydantic Models."""

from typing import Optional

from pydantic import BaseModel, Field

# --- Request Models ---

class StartSessionRequest(BaseModel):
    user_id: str = "default"
    duration_minutes: int = Field(default=15, ge=1, le=30)
    demo_mode: bool = False
    demo_profile: str = "stable_improving"


class SelfReportRequest(BaseModel):
    task_id: str = "unknown"
    vividness: float = Field(default=5.0, ge=0, le=10)
    stability: float = Field(default=5.0, ge=0, le=10)
    effort: float = Field(default=5.0, ge=0, le=10)
    fatigue: float = Field(default=3.0, ge=0, le=10)
    comfort: float = Field(default=7.0, ge=0, le=10)


class SignalFeaturesRequest(BaseModel):
    features: dict = Field(default_factory=dict)


class CompleteTaskRequest(BaseModel):
    task_id: str
    success_rating: float = Field(default=5.0, ge=0, le=10)


# --- Response Models ---

class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    started_at: str
    demo_mode: bool


class TaskResponse(BaseModel):
    session_id: str
    task_id: str
    task_name: str
    level: int
    prompt: str
    duration_sec: int
    difficulty: int


class StePresponse(BaseModel):
    session_id: str
    iqi_score: float
    pid_score: float
    safety_action: str
    curriculum_action: str
    scene_params: dict
    prompt: str
    state: dict


class SummaryResponse(BaseModel):
    session_id: str
    total_steps: int
    mean_iqi: float
    mean_pid: float
    tasks_completed: list[str]
    curriculum_actions: dict
    safety_actions: dict


class ProfileResponse(BaseModel):
    user_id: str
    session_count: int
    level_success_rates: dict
    preferred_scene_types: list[str]
    last_session_summary: Optional[dict] = None
