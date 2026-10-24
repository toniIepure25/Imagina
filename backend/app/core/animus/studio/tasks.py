"""Deterministic behavioural practice tasks for the Studio.

Every task is generated locally from the current symbolic scene. The answer is never sent to the client:
the same task can be rebuilt from ``(scene, task_type, seed, difficulty)`` when the response arrives. This
keeps the API stateless without hiding a neural target or pretending the task measures imagery content.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any

from app.core.animus.scene.model import (
    ALLOWED_STYLES,
    ALLOWED_TIMES,
    ALLOWED_WEATHER,
    SceneGraph,
    SceneValidationError,
)
from app.core.animus.studio.reconstruction import (
    OBJECT_TASK,
    RECONSTRUCTION_TASK_TYPES,
    SCORING_VERSION,
    SPATIAL_TASK,
    build_reconstruction_plan,
    score_spatial_placement,
    score_token_selection,
)

TASK_TYPES = (
    "attribute_recall",
    "style_recall",
    "candidate_discrimination",
    "spatial_view",
    "control_choice",
    OBJECT_TASK,
    SPATIAL_TASK,
)

TASK_SPECS: dict[str, dict[str, Any]] = {
    "attribute_recall": {
        "dimension": "stability",
        "title": "Time of day",
        "prompt": "Which time of day did the hidden scene use?",
        "preview_seconds": 5,
    },
    "style_recall": {
        "dimension": "stability",
        "title": "Visual style",
        "prompt": "Which visual style did the hidden scene use?",
        "preview_seconds": 5,
    },
    "candidate_discrimination": {
        "dimension": "discrimination",
        "title": "Closer candidate",
        "prompt": "Which candidate changes fewer scene details from the hidden scene?",
        "preview_seconds": 6,
    },
    "spatial_view": {
        "dimension": "spatial",
        "title": "Opposite viewpoint",
        "prompt": "If the camera moved to the opposite side of the scene, which position would it use?",
        "preview_seconds": 6,
    },
    "control_choice": {
        "dimension": "control",
        "title": "Edit intention",
        "prompt": "Which edit achieves the stated goal without changing unrelated details?",
        "preview_seconds": 5,
    },
    OBJECT_TASK: {
        "dimension": "stability",
        "title": "Object reconstruction",
        "prompt": "Which objects were in the hidden scene? Select every object you remember.",
        "preview_seconds": 5,
    },
    SPATIAL_TASK: {
        "dimension": "spatial",
        "title": "Spatial layout",
        "prompt": "Place each object where it was in the hidden scene.",
        "preview_seconds": 6,
    },
}


@dataclass(frozen=True)
class GeneratedTask:
    task_type: str
    dimension: str
    prompt: str
    options: tuple[dict[str, Any], ...]
    correct_option_id: str
    difficulty: float
    task_seed: int
    preview_seconds: int
    task_id: str = ""
    response_kind: str = "option"
    tokens: tuple[dict[str, Any], ...] = ()
    layout: dict[str, Any] | None = None
    answer: dict[str, Any] = field(default_factory=dict, repr=False)

    def public_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "dimension": self.dimension,
            "prompt": self.prompt,
            "options": [dict(option) for option in self.options],
            "difficulty": round(float(self.difficulty), 3),
            "task_seed": self.task_seed,
            "preview_seconds": self.preview_seconds,
            "response_kind": self.response_kind,
            "tokens": [dict(token) for token in self.tokens],
            "layout": dict(self.layout) if self.layout is not None else None,
        }


def _option_count(difficulty: float, *, minimum: int = 2, maximum: int = 4) -> int:
    span = maximum - minimum
    return max(minimum, min(maximum, minimum + int(round(max(0.0, min(1.0, difficulty)) * span))))


def _shuffled_options(rng: random.Random, values: list[tuple[str, Any]],
                      labels: list[str] | None = None) -> tuple[list[dict[str, Any]], str]:
    items = list(values)
    rng.shuffle(items)
    options: list[dict[str, Any]] = []
    correct_id = ""
    for index, (correct_marker, value) in enumerate(items):
        option_id = chr(ord("a") + index)
        option = {"id": option_id, "label": labels[index] if labels else str(value), "value": value}
        if correct_marker == "correct":
            correct_id = option_id
        options.append(option)
    return options, correct_id


def _attribute_recall(scene: SceneGraph, rng: random.Random, difficulty: float) -> GeneratedTask:
    correct = scene.atmosphere.time_of_day
    values = [("correct", correct)] + [("distractor", value) for value in ALLOWED_TIMES if value != correct]
    count = _option_count(difficulty, minimum=2, maximum=4)
    selected = [values[0]]
    rng.shuffle(values[1:])
    selected.extend(values[1:count])
    options, correct_id = _shuffled_options(rng, selected)
    spec = TASK_SPECS["attribute_recall"]
    return GeneratedTask(
        task_type="attribute_recall", dimension="stability", prompt=spec["prompt"],
        options=tuple(options), correct_option_id=correct_id, difficulty=difficulty,
        task_seed=0, preview_seconds=spec["preview_seconds"],
    )


def _style_recall(scene: SceneGraph, rng: random.Random, difficulty: float) -> GeneratedTask:
    correct = scene.style
    values = [("correct", correct)] + [("distractor", value) for value in ALLOWED_STYLES if value != correct]
    count = _option_count(difficulty, minimum=2, maximum=4)
    selected = [values[0]]
    rng.shuffle(values[1:])
    selected.extend(values[1:count])
    options, correct_id = _shuffled_options(rng, selected)
    spec = TASK_SPECS["style_recall"]
    return GeneratedTask(
        task_type="style_recall", dimension="stability", prompt=spec["prompt"],
        options=tuple(options), correct_option_id=correct_id, difficulty=difficulty,
        task_seed=0, preview_seconds=spec["preview_seconds"],
    )


def _next_value(options: tuple[str, ...], current: str) -> str:
    index = options.index(current) if current in options else 0
    return options[(index + 1) % len(options)]


def _scene_distance(source: SceneGraph, candidate: SceneGraph) -> int:
    distance = 0
    if source.style != candidate.style:
        distance += 1
    if source.atmosphere.time_of_day != candidate.atmosphere.time_of_day:
        distance += 1
    if source.atmosphere.weather != candidate.atmosphere.weather:
        distance += 1
    source_ids = {entity.id for entity in source.entities}
    candidate_ids = {entity.id for entity in candidate.entities}
    distance += len(source_ids.symmetric_difference(candidate_ids))
    for entity in source.entities:
        other = next((item for item in candidate.entities if item.id == entity.id), None)
        if other is None:
            continue
        if entity.rotation != other.rotation:
            distance += 1
        for path, attribute in entity.attributes.items():
            if path in other.attributes and other.attributes[path].value != attribute.value:
                distance += 1
    return distance


def _candidate_discrimination(scene: SceneGraph, rng: random.Random,
                              difficulty: float) -> GeneratedTask:
    near = scene.copy()
    near.atmosphere.time_of_day = _next_value(ALLOWED_TIMES, near.atmosphere.time_of_day)
    far = near.copy()
    far.atmosphere.weather = _next_value(ALLOWED_WEATHER, far.atmosphere.weather)
    if difficulty >= 0.55:
        far.style = _next_value(ALLOWED_STYLES, far.style)
    if difficulty >= 0.8:
        far.camera.fov = round(min(90.0, far.camera.fov + 8.0), 6)

    near_distance = _scene_distance(scene, near)
    far_distance = _scene_distance(scene, far)
    if far_distance <= near_distance:
        far.camera.fov = round(min(90.0, far.camera.fov + 12.0), 6)
        far_distance = _scene_distance(scene, far)

    options = [
        {"id": "a", "label": "Candidate A", "scene": near.to_dict()},
        {"id": "b", "label": "Candidate B", "scene": far.to_dict()},
    ]
    rng.shuffle(options)
    correct_id = next(option["id"] for option in options if option["label"] == "Candidate A")
    spec = TASK_SPECS["candidate_discrimination"]
    return GeneratedTask(
        task_type="candidate_discrimination", dimension="discrimination", prompt=spec["prompt"],
        options=tuple(options), correct_option_id=correct_id, difficulty=difficulty,
        task_seed=0, preview_seconds=spec["preview_seconds"],
    )


def _spatial_view(scene: SceneGraph, rng: random.Random, difficulty: float) -> GeneratedTask:
    x, y, z = scene.camera.position
    opposite = [round(-x, 6), round(y, 6), round(-z, 6)]
    candidates = [
        [round(z, 6), round(y, 6), round(-x, 6)],
        [round(-z, 6), round(y, 6), round(x, 6)],
        [round(x, 6), round(y, 6), round(z, 6)],
        [round(x + 2.0, 6), round(y, 6), round(z, 6)],
    ]
    seen = {tuple(opposite)}
    distractors = []
    for value in candidates:
        key = tuple(value)
        if key not in seen:
            seen.add(key)
            distractors.append(value)
    fallback_index = 1
    while len(distractors) < 3 and fallback_index <= 3:
        value = [round(opposite[0] + float(fallback_index), 6), round(y, 6),
                 round(opposite[2] - float(fallback_index), 6)]
        key = tuple(value)
        if key not in seen:
            seen.add(key)
            distractors.append(value)
        fallback_index += 1
    values = [("correct", opposite)] + [("distractor", value) for value in distractors]
    count = _option_count(difficulty, minimum=2, maximum=4)
    selected = [values[0]]
    rng.shuffle(values[1:])
    selected.extend(values[1:count])
    options, correct_id = _shuffled_options(
        rng, selected, labels=[f"Position {i + 1}" for i in range(len(selected))])
    spec = TASK_SPECS["spatial_view"]
    return GeneratedTask(
        task_type="spatial_view", dimension="spatial", prompt=spec["prompt"],
        options=tuple(options), correct_option_id=correct_id, difficulty=difficulty,
        task_seed=0, preview_seconds=spec["preview_seconds"],
    )


def _control_choice(scene: SceneGraph, rng: random.Random, difficulty: float) -> GeneratedTask:
    current = scene.atmosphere.time_of_day
    target = "dawn" if current != "dawn" else "dusk"
    values = [
        ("correct", f"Set time of day to {target}; keep style and weather"),
        ("distractor", f"Set time of day to {target}; also switch the style"),
        ("distractor", "Set weather to rain"),
        ("distractor", f"Set time of day to {current}"),
    ]
    count = _option_count(difficulty, minimum=2, maximum=4)
    selected = [values[0]]
    rng.shuffle(values[1:])
    selected.extend(values[1:count])
    options, correct_id = _shuffled_options(rng, selected)
    spec = TASK_SPECS["control_choice"]
    return GeneratedTask(
        task_type="control_choice", dimension="control",
        prompt=f"{spec['prompt']} Goal: change the time of day to {target}.",
        options=tuple(options), correct_option_id=correct_id, difficulty=difficulty,
        task_seed=0, preview_seconds=spec["preview_seconds"],
    )


def _task_id(scene: SceneGraph, task_type: str, seed: int, difficulty: float, *,
             scoring_version: str = "") -> str:
    material = f"{scene.content_hash()}|{task_type}|{seed}|{round(float(difficulty), 3):.3f}"
    if scoring_version:
        material += f"|{scoring_version}"
    return "task_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def build_task(scene: SceneGraph, task_type: str, *, seed: int,
               difficulty: float = 0.5) -> GeneratedTask:
    if task_type not in TASK_SPECS:
        raise SceneValidationError(f"unknown task type {task_type!r}")
    try:
        seed = int(seed)
    except (TypeError, ValueError) as exc:
        raise SceneValidationError("task seed must be an integer") from exc
    if not -(2**31) <= seed <= 2**31 - 1:
        raise SceneValidationError("task seed is out of range")
    difficulty = round(max(0.0, min(1.0, float(difficulty))), 3)
    rng = random.Random(f"{seed}:{task_type}:{scene.content_hash()}")
    if task_type == "attribute_recall":
        task = _attribute_recall(scene, rng, difficulty)
    elif task_type == "style_recall":
        task = _style_recall(scene, rng, difficulty)
    elif task_type == "candidate_discrimination":
        task = _candidate_discrimination(scene, rng, difficulty)
    elif task_type == "spatial_view":
        task = _spatial_view(scene, rng, difficulty)
    elif task_type in RECONSTRUCTION_TASK_TYPES:
        plan = build_reconstruction_plan(scene, task_type, seed=seed, difficulty=difficulty)
        if plan is None:
            fallback = "attribute_recall" if task_type == OBJECT_TASK else "spatial_view"
            return build_task(scene, fallback, seed=seed, difficulty=difficulty)
        return GeneratedTask(
            task_type=plan.task_type, dimension=plan.dimension, prompt=plan.prompt,
            options=(), correct_option_id="", difficulty=difficulty, task_seed=seed,
            preview_seconds=plan.preview_seconds, response_kind=plan.response_kind,
            tokens=plan.tokens, layout=plan.layout, answer=plan.answer,
            task_id=_task_id(scene, plan.task_type, seed, difficulty,
                             scoring_version=SCORING_VERSION),
        )
    else:
        task = _control_choice(scene, rng, difficulty)
    return GeneratedTask(
        task_type=task.task_type, dimension=task.dimension, prompt=task.prompt,
        options=task.options, correct_option_id=task.correct_option_id,
        difficulty=task.difficulty, task_seed=seed, preview_seconds=task.preview_seconds,
        task_id=_task_id(scene, task.task_type, seed, task.difficulty),
    )


def score_response(task: GeneratedTask, response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise SceneValidationError("response must be an object")
    if task.response_kind == "token_selection":
        outcome = score_token_selection(task.tokens, task.answer, response)
    elif task.response_kind == "spatial_placement":
        outcome = score_spatial_placement(task.tokens, task.answer, task.layout, response)
    else:
        selected = response.get("option_id")
        if not isinstance(selected, str) or selected not in {option["id"] for option in task.options}:
            raise SceneValidationError("response must reference one of the offered options")
        correct = selected == task.correct_option_id
        outcome = {
            "score": 1.0 if correct else 0.0,
            "correct": correct,
            "selected_option_id": selected,
            "correct_option_id": task.correct_option_id,
            "response_kind": "option",
            "error_profile": {
                "omissions": 0,
                "intrusions": 0,
                "object_precision": None,
                "object_recall": None,
                "mean_spatial_error": None,
                "spatial_n": 0,
            },
        }
    outcome["dimension"] = task.dimension
    outcome["task_type"] = task.task_type
    return outcome


__all__ = [
    "TASK_TYPES",
    "TASK_SPECS",
    "GeneratedTask",
    "build_task",
    "score_response",
]
