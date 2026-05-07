from app.schemas.task import ImageryTask

TASKS: dict[str, ImageryTask] = {
    "corridor_simple": ImageryTask(
        task_id="corridor_simple",
        name="Simple Corridor Stabilization",
        description="Imagine a simple corridor and maintain its stability over time.",
        target_scene="corridor",
        base_duration_seconds=300,
        window_seconds=10,
        starting_level=1,
        max_level=8,
    ),
    "corridor_doors": ImageryTask(
        task_id="corridor_doors",
        name="Corridor With Doors",
        description=(
            "Imagine a corridor with doors on either side. "
            "Stabilize the corridor and then the doors."
        ),
        target_scene="corridor_doors",
        base_duration_seconds=300,
        window_seconds=10,
        starting_level=1,
        max_level=8,
    ),
    "memory_room": ImageryTask(
        task_id="memory_room",
        name="Memory Room Return",
        description=(
            "Enter a door in the corridor and stabilize "
            "a familiar room from memory."
        ),
        target_scene="memory_room",
        base_duration_seconds=300,
        window_seconds=10,
        starting_level=3,
        max_level=8,
    ),
}


def list_tasks() -> list[ImageryTask]:
    return list(TASKS.values())


def get_task(task_id: str) -> ImageryTask | None:
    return TASKS.get(task_id)
