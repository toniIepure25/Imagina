"""Contrastive scene discrimination for the Scene Threshold instrument.

A pair contains the encoded scene and a minimally changed variant. The participant chooses which
option matches the encoded scene. The target side is stored server-side and never appears in a public
payload. The task is a behavioural 2-AFC discrimination task; it does not decode imagery, generate an
image, or claim that a threshold is an imagery-strength measure.
"""
from __future__ import annotations

import colorsys
import hashlib
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from app.core.animus.scene.model import (
    AttributeValue,
    SceneEntity,
    SceneGraph,
    SceneValidationError,
)
from app.core.animus.studio.sdt import (
    SDT_SCORING_VERSION,
    calibration_summary,
    dprime_2afc,
    fit_threshold,
    side_bias,
)

CONTRAST_PROTOCOL_VERSION = "contrast-v1"
CONTRAST_SCORING_VERSION = SDT_SCORING_VERSION
CONTRAST_TASK_FAMILY = "contrast_discrimination"
CONTRAST_RESPONSE_KIND = "two_alternative_choice"
FEATURE_TYPES = ("object_presence", "spatial_position", "object_color")
FORM_IDS = ("A", "B", "C")
DEFAULT_MAX_TRIALS = 16
MIN_MAX_TRIALS = 12
MAX_MAX_TRIALS = 24
TARGET_CRITERION = 0.75
DEFAULT_LAPSE = 0.02
INITIAL_SPATIAL_DELTA = 0.35
INITIAL_COLOR_DELTA = 0.45
MIN_DELTA = 0.02
MAX_DELTA = 0.98
REFLECTION_STRATEGIES = ("visual", "spatial", "verbal", "semantic", "sensorimotor", "guessing")
FORM_OFFSET = {"A": 0, "B": 1, "C": 2}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _digest(*parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _rng(*parts: Any) -> random.Random:
    return random.Random("|".join(str(part) for part in parts))


def _parent_ids(scene: SceneGraph) -> set[str]:
    return {entity.parent_id for entity in scene.entities if entity.parent_id}


def _leaf_props(scene: SceneGraph) -> list[SceneEntity]:
    parents = _parent_ids(scene)
    leaves = [entity for entity in scene.entities if entity.role == "prop" and entity.id not in parents]
    if leaves:
        return leaves
    return [entity for entity in scene.entities if entity.id not in parents]


def _removable_entity(scene: SceneGraph) -> SceneEntity | None:
    candidates = _leaf_props(scene)
    return candidates[0] if candidates else None


def _color_value(entity: SceneEntity) -> str | None:
    attribute = entity.attributes.get("color")
    value = attribute.value if attribute is not None else None
    return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else None


def _color_is_usable(value: str) -> bool:
    red = int(value[1:3], 16) / 255.0
    green = int(value[3:5], 16) / 255.0
    blue = int(value[5:7], 16) / 255.0
    _, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    return saturation >= 0.12 and 0.1 <= lightness <= 0.9


def _color_entities(scene: SceneGraph) -> list[SceneEntity]:
    return [
        entity for entity in _leaf_props(scene)
        if _color_value(entity) is not None and _color_is_usable(_color_value(entity) or "")
    ]


def _spatial_entities(scene: SceneGraph) -> list[SceneEntity]:
    if len(scene.entities) < 2:
        return []
    xs = [entity.position[0] for entity in scene.entities]
    span = max(xs) - min(xs)
    room = max(span, 1.0) * MIN_DELTA
    return [
        entity for entity in _leaf_props(scene)
        if max(entity.position[0] - min(xs), max(xs) - entity.position[0]) >= room
    ]


def _available_feature_types(scene: SceneGraph) -> tuple[str, ...]:
    available: list[str] = []
    if _removable_entity(scene) is not None and len(scene.entities) > 2:
        available.append("object_presence")
    if len(_spatial_entities(scene)) >= 1 and len(scene.entities) >= 2:
        available.append("spatial_position")
    if _color_entities(scene):
        available.append("object_color")
    return tuple(available)


def _shift_hex(color: str, delta: float) -> str:
    red = int(color[1:3], 16) / 255.0
    green = int(color[3:5], 16) / 255.0
    blue = int(color[5:7], 16) / 255.0
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    hue = (hue + _clamp(delta) * 0.5) % 1.0
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#" + "".join(f"{int(round(channel * 255)):02x}" for channel in (red, green, blue))


def _scene_span(scene: SceneGraph) -> float:
    if len(scene.entities) < 2:
        return 1.0
    xs = [entity.position[0] for entity in scene.entities]
    zs = [entity.position[2] for entity in scene.entities]
    return max(max(xs) - min(xs), max(zs) - min(zs), 1.0)


@dataclass(frozen=True)
class ContrastPair:
    trial_id: str
    task_id: str
    trial_index: int
    feature_type: str
    feature_key: str
    prompt: str
    options: tuple[dict[str, Any], ...]
    delta: float | None
    staircase_level: float | None
    preview_seconds: int
    target_side: str = field(repr=False)
    correct_option_id: str = field(repr=False, default="")

    def public_payload(self) -> dict[str, Any]:
        """Return the client payload without the target side, feature label, delta or answer."""
        return {
            "trial_id": self.trial_id,
            "task_id": self.task_id,
            "trial_index": self.trial_index,
            "prompt": self.prompt,
            "options": [dict(option) for option in self.options],
            "preview_seconds": self.preview_seconds,
        }


def _feature_key(feature_type: str, entity: SceneEntity) -> str:
    if feature_type == "object_presence":
        return f"obj:{entity.id}"
    if feature_type == "spatial_position":
        return f"pos:{entity.id}:x"
    if feature_type == "object_color":
        return f"color:{entity.id}"
    raise ValueError(f"unknown feature type {feature_type!r}")


def _choose_entity(scene: SceneGraph, feature_type: str, *, seed: int, form_id: str,
                   trial_index: int, trials: Sequence[Mapping[str, Any]]) -> SceneEntity | None:
    if feature_type == "object_presence":
        candidates = _leaf_props(scene)
        if len(scene.entities) <= 2:
            candidates = []
    elif feature_type == "object_color":
        candidates = _color_entities(scene)
    elif feature_type == "spatial_position":
        candidates = _spatial_entities(scene)
    else:
        candidates = []
    if not candidates:
        return None
    counts = Counter(str(trial.get("feature_key")) for trial in trials if trial.get("feature_key"))
    minimum = min(counts.get(_feature_key(feature_type, entity), 0) for entity in candidates)
    pool = [entity for entity in candidates
            if counts.get(_feature_key(feature_type, entity), 0) == minimum]
    rng = _rng(scene.content_hash(), feature_type, seed, form_id, trial_index, "entity")
    return pool[rng.randrange(len(pool))]


def _variant(scene: SceneGraph, feature_type: str, entity: SceneEntity, delta: float,
             rng: random.Random) -> SceneGraph:
    variant = scene.copy()
    if feature_type == "object_presence":
        variant.entities = [item for item in variant.entities if item.id != entity.id]
        variant.relations = [
            relation for relation in variant.relations
            if relation.subject_id != entity.id and relation.object_id != entity.id
        ]
        return variant
    target = variant.find_entity(entity.id)
    if target is None:
        raise SceneValidationError(f"contrast feature entity {entity.id!r} is missing from the variant")
    if feature_type == "spatial_position":
        span = _scene_span(scene)
        shift = max(MIN_DELTA, _clamp(delta, MIN_DELTA, MAX_DELTA)) * span
        xs = [item.position[0] for item in scene.entities]
        lower, upper = min(xs), max(xs)
        positive_room = upper - target.position[0]
        negative_room = target.position[0] - lower
        if positive_room < shift and negative_room >= shift:
            shift = -shift
        elif positive_room < shift and negative_room < shift:
            shift = max(positive_room, negative_room) * (1.0 if positive_room >= negative_room else -1.0)
        elif rng.random() < 0.5 and negative_room >= shift:
            shift = -shift
        target.position[0] = round(target.position[0] + shift, 6)
        return variant
    if feature_type == "object_color":
        old = target.attributes.get("color")
        value = _color_value(entity)
        if old is None or value is None:
            raise SceneValidationError("object color is not available for this entity")
        target.attributes["color"] = AttributeValue(
            value=_shift_hex(value, delta),
            confidence=old.confidence,
            provenance=old.provenance,
            locked=old.locked,
            source_text=old.source_text,
            renderable=old.renderable,
        )
        return variant
    raise ValueError(f"unknown feature type {feature_type!r}")


def _target_side(*, seed: int, form_id: str, trial_index: int) -> str:
    """Return a seeded, block-balanced target side.

    Strict alternation would be predictable even without correctness feedback, so each block of two
    trials contains one ``a`` and one ``b`` in a seeded order. This keeps the design balanced without
    exposing a deterministic sequence.
    """
    block = trial_index // 2
    first_is_a = _rng(seed, form_id, block, "target_side").random() < 0.5
    even = trial_index % 2 == 0
    return "a" if first_is_a == even else "b"


def _initial_delta(feature_type: str) -> float:
    return INITIAL_COLOR_DELTA if feature_type == "object_color" else INITIAL_SPATIAL_DELTA


def _next_delta(trials: Sequence[Mapping[str, Any]], feature_type: str) -> float:
    history = [
        trial for trial in trials
        if trial.get("feature_type") == feature_type
        and trial.get("delta") is not None
        and trial.get("correct") is not None
        and not bool(trial.get("abstained"))
    ]
    delta = _initial_delta(feature_type)
    consecutive_correct = 0
    direction = 0
    reversals = 0
    for trial in history:
        correct = bool(trial["correct"])
        step = 0.08 if reversals < 2 else 0.04
        if correct:
            consecutive_correct += 1
            if consecutive_correct >= 2:
                new_direction = -1
                if direction and new_direction != direction:
                    reversals += 1
                direction = new_direction
                delta = _clamp(delta - step, 0.05, 0.95)
                consecutive_correct = 0
        else:
            consecutive_correct = 0
            new_direction = 1
            if direction and new_direction != direction:
                reversals += 1
            direction = new_direction
            delta = _clamp(delta + step, 0.05, 0.95)
    return round(delta, 4)


def _trial_feature(scene: SceneGraph, *, seed: int, form_id: str, trial_index: int,
                   trials: Sequence[Mapping[str, Any]]) -> tuple[str, SceneEntity] | None:
    available = _available_feature_types(scene)
    if not available:
        return None
    if trial_index in (0, 6) and "object_presence" in available:
        feature_type = "object_presence"
    elif trial_index == 1 and "spatial_position" in available:
        feature_type = "spatial_position"
    else:
        adaptive = [feature_type for feature_type in ("spatial_position", "object_color")
                    if feature_type in available]
        if adaptive:
            offset = FORM_OFFSET.get(form_id, 0)
            feature_type = adaptive[(trial_index + offset) % len(adaptive)]
        else:
            feature_type = available[trial_index % len(available)]
    entity = _choose_entity(scene, feature_type, seed=seed, form_id=form_id,
                            trial_index=trial_index, trials=trials)
    if entity is None:
        return None
    return feature_type, entity


def build_pair(scene: SceneGraph, *, feature_type: str, feature_key: str, delta: float | None,
               seed: int, form_id: str, trial_index: int, preview_seconds: int = 5) -> ContrastPair:
    entity_id = feature_key.split(":")[1] if ":" in feature_key else ""
    entity = scene.find_entity(entity_id)
    if entity is None:
        raise SceneValidationError(f"contrast feature entity {entity_id!r} is not in the scene")
    rng = _rng(scene.content_hash(), feature_type, feature_key, delta, seed, form_id, trial_index)
    effective_delta = None if feature_type == "object_presence" else (
        delta if delta is not None else _initial_delta(feature_type)
    )
    variant = _variant(scene, feature_type, entity, float(effective_delta or 0.0), rng)
    if feature_type == "spatial_position" and effective_delta is not None:
        moved = variant.find_entity(entity.id)
        if moved is not None:
            effective_delta = round(
                abs(moved.position[0] - entity.position[0]) / _scene_span(scene), 6)
    elif feature_type == "object_color" and effective_delta is not None:
        before = _color_value(entity)
        moved = variant.find_entity(entity.id)
        after = _color_value(moved) if moved is not None else None
        if before is not None and after is not None:
            before_hue = colorsys.rgb_to_hls(
                int(before[1:3], 16) / 255.0, int(before[3:5], 16) / 255.0,
                int(before[5:7], 16) / 255.0)[0]
            after_hue = colorsys.rgb_to_hls(
                int(after[1:3], 16) / 255.0, int(after[3:5], 16) / 255.0,
                int(after[5:7], 16) / 255.0)[0]
            distance = abs(after_hue - before_hue)
            distance = min(distance, 1.0 - distance)
            effective_delta = round(distance / 0.5, 6)
    target_side = _target_side(seed=seed, form_id=form_id, trial_index=trial_index)
    options: list[dict[str, Any]] = []
    for side in ("a", "b"):
        candidate = scene if side == target_side else variant
        options.append({
            "id": side,
            "label": f"Scene {side.upper()}",
            "scene": candidate.to_dict(),
        })
    trial_id = "ctr_" + _digest(scene.content_hash(), feature_type, feature_key, effective_delta,
                                seed, form_id, trial_index)[:20]
    task_id = "cst_" + _digest(CONTRAST_PROTOCOL_VERSION, scene.content_hash(), feature_type,
                               feature_key, effective_delta, seed, form_id, trial_index)[:24]
    return ContrastPair(
        trial_id=trial_id,
        task_id=task_id,
        trial_index=trial_index,
        feature_type=feature_type,
        feature_key=feature_key,
        prompt="Which scene matches the one you saw?",
        options=tuple(options),
        delta=effective_delta,
        staircase_level=effective_delta,
        preview_seconds=max(1, min(15, int(preview_seconds))),
        target_side=target_side,
        correct_option_id=target_side,
    )


def next_trial(scene: SceneGraph, session: Mapping[str, Any], trials: Sequence[Mapping[str, Any]]
               ) -> ContrastPair | None:
    max_trials = int(session.get("max_trials") or DEFAULT_MAX_TRIALS)
    trial_index = len(trials)
    if trial_index >= max_trials:
        return None
    selected = _trial_feature(
        scene,
        seed=int(session.get("seed") or 0),
        form_id=str(session.get("form_id") or "A"),
        trial_index=trial_index,
        trials=trials,
    )
    if selected is None:
        return None
    feature_type, entity = selected
    delta = None if feature_type == "object_presence" else _next_delta(trials, feature_type)
    return build_pair(
        scene,
        feature_type=feature_type,
        feature_key=_feature_key(feature_type, entity),
        delta=delta,
        seed=int(session.get("seed") or 0),
        form_id=str(session.get("form_id") or "A"),
        trial_index=trial_index,
    )


def score_trial(pair: ContrastPair, *, choice: str, confidence: float, abstained: bool = False
                ) -> dict[str, Any]:
    if abstained:
        return {
            "answered": False,
            "correct": None,
            "choice": "",
            "confidence": round(_clamp(confidence, 0.5, 1.0), 6),
            "brier": None,
        }
    if choice not in ("a", "b"):
        raise ValueError("choice must be 'a' or 'b'")
    correct = choice == pair.target_side
    confidence_value = round(_clamp(confidence, 0.5, 1.0), 6)
    return {
        "answered": True,
        "correct": bool(correct),
        "choice": choice,
        "confidence": confidence_value,
        "brier": round((confidence_value - (1.0 if correct else 0.0)) ** 2, 6),
    }


def summarize_contrast(session: Mapping[str, Any], trials: Sequence[Mapping[str, Any]],
                       *, bootstrap: int = 240) -> dict[str, Any]:
    answered = [
        trial for trial in trials
        if not bool(trial.get("abstained")) and trial.get("correct") is not None
    ]
    pairs = [(float(trial.get("confidence") or 0.5), bool(trial.get("correct")))
             for trial in answered]
    thresholds: dict[str, Any] = {}
    for feature_type in ("spatial_position", "object_color"):
        feature_trials = [trial for trial in answered if trial.get("feature_type") == feature_type]
        if feature_trials:
            thresholds[feature_type] = fit_threshold(
                feature_trials,
                seed=int(session.get("seed") or 0),
                bootstrap=bootstrap,
            )
    notes: list[str] = [
        "Thresholds are within-scene normalized change magnitudes; they are not comparable across scenes.",
        "A lower threshold means finer discrimination; it is not an imagery-strength score.",
    ]
    if any(item.get("threshold") is None for item in thresholds.values()):
        notes.append("Some thresholds were withheld because there was not enough answered evidence.")
    if any(item.get("censored") for item in thresholds.values()):
        notes.append("A censored threshold reached the search boundary; do not extrapolate it.")
    return {
        "protocol_version": CONTRAST_PROTOCOL_VERSION,
        "scoring_version": CONTRAST_SCORING_VERSION,
        "n_trials": len(trials),
        "n_answered": len(answered),
        "coverage": round(len(answered) / len(trials), 6) if trials else None,
        "dprime": dprime_2afc(sum(1 for trial in answered if trial.get("correct")), len(answered)),
        "side_bias": side_bias([str(trial.get("choice") or "") for trial in answered]),
        "thresholds": thresholds,
        "calibration": calibration_summary(pairs),
        "notes": notes,
    }


def validate_reflection(strategies: Iterable[str]) -> list[str]:
    values: list[str] = []
    for strategy in strategies:
        cleaned = str(strategy).strip().lower()
        if cleaned not in REFLECTION_STRATEGIES:
            raise ValueError(f"unknown strategy {strategy!r}")
        if cleaned not in values:
            values.append(cleaned)
    if len(values) > len(REFLECTION_STRATEGIES):
        raise ValueError("too many strategies")
    return values


__all__ = [
    "CONTRAST_PROTOCOL_VERSION",
    "CONTRAST_SCORING_VERSION",
    "CONTRAST_TASK_FAMILY",
    "CONTRAST_RESPONSE_KIND",
    "FEATURE_TYPES",
    "FORM_IDS",
    "DEFAULT_MAX_TRIALS",
    "MIN_MAX_TRIALS",
    "MAX_MAX_TRIALS",
    "TARGET_CRITERION",
    "DEFAULT_LAPSE",
    "REFLECTION_STRATEGIES",
    "ContrastPair",
    "build_pair",
    "next_trial",
    "score_trial",
    "summarize_contrast",
    "validate_reflection",
]
