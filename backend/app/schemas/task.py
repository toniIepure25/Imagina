from pydantic import BaseModel


class ImageryTask(BaseModel):
    task_id: str
    name: str
    description: str
    target_scene: str
    base_duration_seconds: int
    window_seconds: int = 10
    starting_level: int = 1
    max_level: int = 8
