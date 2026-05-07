from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackAction(BaseModel):
    session_id: str
    timestamp: datetime
    window_index: int
    action_id: str
    scene_clarity: float = Field(ge=0, le=1)
    blur: float = Field(ge=0, le=1)
    wall_distortion: float = Field(ge=0, le=1)
    light_stability: float = Field(ge=0, le=1)
    texture_detail: float = Field(ge=0, le=1)
    particle_stability: float = Field(ge=0, le=1)
    door_complexity: float = Field(ge=0, le=1)
    fog_density: float = Field(ge=0, le=1)
    color_saturation: float = Field(ge=0, le=1)
    breathing_cue_strength: float = Field(ge=0, le=1)
    prompt_text: str = ""
    reason: str = ""
