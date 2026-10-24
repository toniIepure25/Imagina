"""Deterministic reconstruction tasks and scoring for the ANIMUS instrument.

Reconstruction is a behavioural proxy: the user rebuilds object content or spatial layout from a
symbolic scene, and the server scores the result against that scene. It does not decode imagery, and the
weights below are a versioned instrument choice rather than a validated psychometric model.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Any

from app.core.animus.scene.library import KIND_LABELS, OBJECT_KINDS
from app.core.animus.scene.model import SceneEntity, SceneGraph, SceneValidationError

SCORING_VERSION = "recon-v1"
RECONSTRUCTION_TASK_TYPES = ("object_reconstruction", "spatial_layout")
OBJECT_TASK = "object_reconstruction"
SPATIAL_TASK = "spatial_layout"


@dataclass(frozen=True)
class ReconstructionPlan:
    task_type: str
    dimension: str
    prompt: str
    tokens: tuple[dict[str, Any], ...]
    layout: dict[str, Any] | None
    preview_seconds: int
    answer: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def response_kind(self) -> str:
        return "token_selection" if self.task_type == OBJECT_TASK else "spatial_placement"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _target_count(difficulty: float) -> int:
    return 2 + int(round(_clamp(difficulty) * 3))


def _token_id(*parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    return "tok_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:14]


def _color(entity: SceneEntity) -> str | None:
    attribute = entity.attributes.get("color")
    value = attribute.value if attribute is not None else None
    return value if isinstance(value, str) and value.startswith("#") else None


def _token(entity: SceneEntity, *, prefix: str, scene_hash: str, task_type: str, seed: int,
           index: int) -> dict[str, Any]:
    return {
        "token_id": prefix + _token_id(scene_hash, task_type, seed, entity.id, index),
        "kind": entity.kind,
        "label": entity.label,
        "role": entity.role,
        "color": _color(entity),
    }


def _decoy_kind(rng: random.Random, blocked: set[str]) -> str:
    kinds = [kind for kind in OBJECT_KINDS if kind not in blocked]
    if not kinds:
        return "custom"
    return kinds[rng.randrange(len(kinds))]


def _object_plan(scene: SceneGraph, rng: random.Random, difficulty: float,
                 scene_hash: str, seed: int) -> ReconstructionPlan | None:
    if len(scene.entities) < 2:
        return None
    count = min(len(scene.entities), _target_count(difficulty))
    targets = rng.sample(list(scene.entities), count)
    tokens = [
        _token(entity, prefix="obj_", scene_hash=scene_hash, task_type=OBJECT_TASK, seed=seed, index=index)
        for index, entity in enumerate(targets)
    ]
    target_ids = {token["token_id"] for token in tokens}
    blocked = {entity.kind for entity in targets}
    decoy_count = 1 + int(round(_clamp(difficulty) * 3))
    for index in range(decoy_count):
        kind = _decoy_kind(rng, blocked)
        blocked.add(kind)
        label = KIND_LABELS.get(kind, kind.title())
        tokens.append({
            "token_id": "dec_" + _token_id(scene_hash, OBJECT_TASK, seed, kind, index),
            "kind": kind,
            "label": label,
            "role": "prop",
            "color": None,
        })
    rng.shuffle(tokens)
    return ReconstructionPlan(
        task_type=OBJECT_TASK,
        dimension="stability",
        prompt="Which objects were in the hidden scene? Select every object you remember.",
        tokens=tuple(tokens),
        layout=None,
        preview_seconds=5,
        answer={"target_token_ids": sorted(target_ids)},
    )


def _normalize_positions(entities: list[SceneEntity]) -> dict[str, tuple[float, float]] | None:
    if len(entities) < 2:
        return None
    xs = [entity.position[0] for entity in entities]
    zs = [entity.position[2] for entity in entities]
    x_span = max(xs) - min(xs)
    z_span = max(zs) - min(zs)
    if max(x_span, z_span) < 1e-6:
        return None
    x_center = (max(xs) + min(xs)) / 2.0
    z_center = (max(zs) + min(zs)) / 2.0
    x_scale = max(x_span / 2.0, 1e-6)
    z_scale = max(z_span / 2.0, 1e-6)
    return {
        entity.id: (
            round(_clamp((entity.position[0] - x_center) / x_scale, -1.0, 1.0), 4),
            round(_clamp((entity.position[2] - z_center) / z_scale, -1.0, 1.0), 4),
        )
        for entity in entities
    }


def _spatial_plan(scene: SceneGraph, rng: random.Random, difficulty: float,
                  scene_hash: str, seed: int) -> ReconstructionPlan | None:
    normalized_all = _normalize_positions(scene.entities)
    if normalized_all is None or len(normalized_all) < 2:
        return None
    count = min(len(scene.entities), _target_count(difficulty))
    targets = rng.sample(list(scene.entities), count)
    normalized = _normalize_positions(targets)
    if normalized is None or len(normalized) < 2:
        return None
    tokens = [
        _token(entity, prefix="loc_", scene_hash=scene_hash, task_type=SPATIAL_TASK, seed=seed, index=index)
        for index, entity in enumerate(targets)
    ]
    target_positions = {token["token_id"]: list(normalized[entity.id])
                        for token, entity in zip(tokens, targets, strict=True)}
    rng.shuffle(tokens)
    tolerance = round(max(0.12, min(0.55, 0.55 - 0.35 * _clamp(difficulty))), 3)
    return ReconstructionPlan(
        task_type=SPATIAL_TASK,
        dimension="spatial",
        prompt="Place each object where it was in the hidden scene.",
        tokens=tuple(tokens),
        layout={"width": 1.0, "height": 1.0, "grid": 7, "tolerance": tolerance},
        preview_seconds=6,
        answer={"target_positions": target_positions},
    )


def build_reconstruction_plan(scene: SceneGraph, task_type: str, *, seed: int,
                              difficulty: float) -> ReconstructionPlan | None:
    if task_type not in RECONSTRUCTION_TASK_TYPES:
        raise SceneValidationError(f"unknown reconstruction task type {task_type!r}")
    rng = random.Random(f"{seed}:{task_type}:{scene.content_hash()}")
    difficulty = round(_clamp(float(difficulty)), 3)
    scene_hash = scene.content_hash()
    if task_type == OBJECT_TASK:
        return _object_plan(scene, rng, difficulty, scene_hash, seed)
    return _spatial_plan(scene, rng, difficulty, scene_hash, seed)


def score_token_selection(tokens: tuple[dict[str, Any], ...], answer: dict[str, Any],
                          response: dict[str, Any]) -> dict[str, Any]:
    selected_raw = response.get("selected_token_ids")
    if not isinstance(selected_raw, list):
        raise SceneValidationError("selected_token_ids must be a list")
    if not all(isinstance(item, str) for item in selected_raw):
        raise SceneValidationError("selected_token_ids must contain strings")
    offered = {token["token_id"] for token in tokens}
    selected = set(selected_raw)
    if not selected.issubset(offered):
        raise SceneValidationError("response references an unknown token")
    target = set(answer.get("target_token_ids") or [])
    if not target:
        raise SceneValidationError("reconstruction task has no target tokens")
    true_positive = len(selected & target)
    false_positive = len(selected - target)
    false_negative = len(target - selected)
    denominator = 2 * true_positive + false_positive + false_negative
    score = (2 * true_positive / denominator) if denominator else 0.0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    return {
        "score": round(score, 6),
        "correct": score >= 0.999,
        "response_kind": "token_selection",
        "error_profile": {
            "omissions": false_negative,
            "intrusions": false_positive,
            "object_precision": round(precision, 4),
            "object_recall": round(recall, 4),
            "mean_spatial_error": None,
            "spatial_n": 0,
        },
        "selected_token_ids": sorted(selected),
        "target_token_count": len(target),
    }


def _placement(value: Any) -> tuple[float, float]:
    if not isinstance(value, dict):
        raise SceneValidationError("each placement must be an object")
    try:
        x = float(value.get("x"))
        z = float(value.get("z"))
    except (TypeError, ValueError) as exc:
        raise SceneValidationError("placement coordinates must be numbers") from exc
    if not math.isfinite(x) or not math.isfinite(z):
        raise SceneValidationError("placement coordinates must be finite")
    if not -1.0 <= x <= 1.0 or not -1.0 <= z <= 1.0:
        raise SceneValidationError("placement coordinates must be between -1 and 1")
    return x, z


def score_spatial_placement(tokens: tuple[dict[str, Any], ...], answer: dict[str, Any],
                            layout: dict[str, Any] | None, response: dict[str, Any]) -> dict[str, Any]:
    raw = response.get("placements")
    if not isinstance(raw, list):
        raise SceneValidationError("placements must be a list")
    offered = {token["token_id"] for token in tokens}
    placements: dict[str, tuple[float, float]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise SceneValidationError("each placement must be an object")
        token_id = item.get("token_id")
        if not isinstance(token_id, str) or token_id not in offered:
            raise SceneValidationError("placement references an unknown token")
        if token_id in placements:
            raise SceneValidationError("placement contains a duplicate token")
        placements[token_id] = _placement(item)
    target_positions = answer.get("target_positions") or {}
    if not target_positions:
        raise SceneValidationError("reconstruction task has no target positions")
    tolerance = float((layout or {}).get("tolerance") or 0.3)
    tolerance = max(0.05, min(0.8, tolerance))
    distances: list[float] = []
    scores: list[float] = []
    for token_id, target in target_positions.items():
        target_x, target_z = float(target[0]), float(target[1])
        if token_id in placements:
            x, z = placements[token_id]
            distance = math.hypot(x - target_x, z - target_z)
        else:
            distance = math.sqrt(8.0)
        distances.append(distance)
        scores.append(max(0.0, 1.0 - distance / (2.0 * tolerance)))
    score = sum(scores) / len(scores) if scores else 0.0
    mean_error = sum(distances) / len(distances) if distances else 0.0
    omissions = len(set(target_positions) - set(placements))
    return {
        "score": round(score, 6),
        "correct": score >= 0.999,
        "response_kind": "spatial_placement",
        "error_profile": {
            "omissions": omissions,
            "intrusions": 0,
            "object_precision": None,
            "object_recall": None,
            "mean_spatial_error": round(mean_error, 4),
            "spatial_n": len(target_positions),
        },
        "placed_token_ids": sorted(placements),
        "target_token_count": len(target_positions),
    }


__all__ = [
    "SCORING_VERSION",
    "RECONSTRUCTION_TASK_TYPES",
    "OBJECT_TASK",
    "SPATIAL_TASK",
    "ReconstructionPlan",
    "build_reconstruction_plan",
    "score_token_selection",
    "score_spatial_placement",
]
