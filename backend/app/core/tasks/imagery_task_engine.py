"""IMAGINA Task Engine — Predefined imagery task templates."""

TASK_TEMPLATES = [
    {"id": "shape_stabilization", "level": 1, "name": "Simple Shape Stabilization",
     "prompt": "Close your eyes and visualize a simple circle. Hold it as clearly as possible.",
     "target_dimension": "shape", "duration_sec": 90, "difficulty": 1,
     "success_criteria": {"iqi_min": 0.5}, "regression_criteria": {"iqi_max": 0.3},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "procedural"},
    {"id": "color_stabilization", "level": 1, "name": "Color Stabilization",
     "prompt": "Visualize a bright red square. Focus on the color remaining consistent.",
     "target_dimension": "color", "duration_sec": 90, "difficulty": 1,
     "success_criteria": {"iqi_min": 0.5}, "regression_criteria": {"iqi_max": 0.3},
     "self_report": ["vividness", "stability"], "feedback_mode": "procedural"},
    {"id": "brightness_contrast", "level": 2, "name": "Brightness/Contrast",
     "prompt": "Imagine a scene with gradual brightness changes — from dim to bright. Hold the brightness stable.",
     "target_dimension": "brightness", "duration_sec": 120, "difficulty": 2,
     "success_criteria": {"iqi_min": 0.55}, "regression_criteria": {"iqi_max": 0.35},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "procedural"},
    {"id": "motion", "level": 2, "name": "Motion",
     "prompt": "Visualize a slowly rotating spiral. Try to keep the motion smooth and consistent.",
     "target_dimension": "motion", "duration_sec": 120, "difficulty": 2,
     "success_criteria": {"iqi_min": 0.55}, "regression_criteria": {"iqi_max": 0.35},
     "self_report": ["vividness", "stability"], "feedback_mode": "procedural"},
    {"id": "object_detail", "level": 3, "name": "Object Detail",
     "prompt": "Imagine a detailed object — a flower, a clock, or a book. Focus on the fine details.",
     "target_dimension": "detail", "duration_sec": 150, "difficulty": 3,
     "success_criteria": {"iqi_min": 0.60}, "regression_criteria": {"iqi_max": 0.40},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "generative"},
    {"id": "spatial_position", "level": 3, "name": "Spatial Position",
     "prompt": "Visualize an object at a specific location in space. Hold its position steady.",
     "target_dimension": "spatial", "duration_sec": 150, "difficulty": 3,
     "success_criteria": {"iqi_min": 0.60}, "regression_criteria": {"iqi_max": 0.40},
     "self_report": ["vividness", "stability"], "feedback_mode": "procedural"},
    {"id": "scene_construction", "level": 4, "name": "Scene Construction",
     "prompt": "Build a simple scene with multiple objects — a tree, a bench, and clouds. Hold the entire scene.",
     "target_dimension": "scene", "duration_sec": 180, "difficulty": 4,
     "success_criteria": {"iqi_min": 0.65}, "regression_criteria": {"iqi_max": 0.45},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "generative"},
    {"id": "perspective_viewpoint", "level": 4, "name": "Perspective/Viewpoint",
     "prompt": "Imagine a room from a specific viewpoint. Then try to shift your viewpoint slightly while keeping the room stable.",
     "target_dimension": "perspective", "duration_sec": 180, "difficulty": 4,
     "success_criteria": {"iqi_min": 0.60}, "regression_criteria": {"iqi_max": 0.40},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "generative"},
    {"id": "multisensory_scene", "level": 5, "name": "Multisensory Scene",
     "prompt": "Imagine a beach scene with visual details, the sound of waves, and the feeling of warm sand. Hold all sensory dimensions.",
     "target_dimension": "multisensory", "duration_sec": 240, "difficulty": 5,
     "success_criteria": {"iqi_min": 0.65}, "regression_criteria": {"iqi_max": 0.45},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "generative"},
    {"id": "memory_scene", "level": 5, "name": "Memory-Like Scene",
     "prompt": "Recall a familiar place from memory — a childhood room, a favorite cafe. Reconstruct it as vividly as you can.",
     "target_dimension": "memory", "duration_sec": 240, "difficulty": 5,
     "success_criteria": {"iqi_min": 0.65}, "regression_criteria": {"iqi_max": 0.45},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "generative",
     "safety_note": "Choose emotionally neutral memories. Stop if the scene becomes distressing."},
    {"id": "symbolic_scene", "level": 6, "name": "Symbolic/Dream-Like Scene",
     "prompt": "Visualize a dream-like symbolic landscape — floating shapes, flowing colors, abstract forms. Embrace the fluidity.",
     "target_dimension": "symbolic", "duration_sec": 240, "difficulty": 6,
     "success_criteria": {"iqi_min": 0.65}, "regression_criteria": {"iqi_max": 0.45},
     "self_report": ["vividness", "stability"], "feedback_mode": "generative"},
    {"id": "stable_return", "level": 6, "name": "Stable Return-to-Scene",
     "prompt": "Return to a scene you successfully visualized earlier. Can you reconstruct it as clearly as before?",
     "target_dimension": "stability", "duration_sec": 180, "difficulty": 6,
     "success_criteria": {"iqi_min": 0.70}, "regression_criteria": {"iqi_max": 0.50},
     "self_report": ["vividness", "stability", "effort"], "feedback_mode": "procedural"},
]


def get_task(task_id: str) -> dict | None:
    for t in TASK_TEMPLATES:
        if t["id"] == task_id:
            return t.copy()
    return None


def get_tasks_by_level(level: int) -> list[dict]:
    return [t.copy() for t in TASK_TEMPLATES if t["level"] == level]


def get_next_level_task(current_level: int, direction: str) -> dict | None:
    """direction: 'advance', 'stay', 'regress'"""
    target = max(1, min(6, current_level + (1 if direction == "advance" else -1 if direction == "regress" else 0)))
    tasks = get_tasks_by_level(target)
    return tasks[0] if tasks else None
