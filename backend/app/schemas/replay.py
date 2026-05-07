from pydantic import BaseModel


class ReplayRequest(BaseModel):
    scenario: str = "improving_user"
    seed: int = 42
    duration_windows: int = 30
