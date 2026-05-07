from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Condition = Literal[
    "adaptive_curriculum",
    "fixed_curriculum",
    "visual_feedback_only",
    "guided_prompt_feedback",
    "self_report_only",
    "simulated_signal_assisted",
    "catch_trial_control",
]


class ExperimentProtocol(BaseModel):
    protocol_id: str
    name: str
    description: str
    condition: Condition
    task_sequence: list[str]
    duration_minutes: int
    feedback_mode: str
    curriculum_mode: str
    catch_trial_rate: float = Field(ge=0, le=1)
    safety_limits: dict
    metrics_to_collect: list[str]


class ExperimentRunCreate(BaseModel):
    protocol_id: str
    participant_label: str = "anonymous"
    notes: str | None = None


class ExperimentRun(BaseModel):
    run_id: str
    protocol_id: str
    session_ids: list[str] = Field(default_factory=list)
    completed_session_ids: list[str] = Field(default_factory=list)
    planned_sessions: list[dict] = Field(default_factory=list)
    current_step: int = 0
    condition: Condition | None = None
    participant_label: str
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["created", "running", "completed"] = "created"
    notes: str | None = None
    catch_trials: list[int] = Field(default_factory=list)


class ExperimentSessionAttach(BaseModel):
    session_id: str
    completed: bool = False
