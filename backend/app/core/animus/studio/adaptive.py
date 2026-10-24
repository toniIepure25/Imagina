"""Adaptive task selection for the ANIMUS reconstruction instrument.

The policy is inspectable and deliberately small: a coverage floor for dimensions with almost no evidence,
then expected information gain over the Beta posterior. Calibration is measured on every trial rather than
being selected as a separate dimension. This is a heuristic for local practice, not a validated
computerized-adaptive-testing model.
"""
from __future__ import annotations

import math
from typing import Any

from app.core.animus.studio.profile import estimate_from_stats

TASK_FOR_DIMENSION = {
    "stability": ("object_reconstruction", "attribute_recall", "style_recall"),
    "discrimination": ("candidate_discrimination",),
    "spatial": ("spatial_layout", "spatial_view"),
    "control": ("control_choice",),
}

SELECTABLE_DIMENSIONS = tuple(TASK_FOR_DIMENSION)


def _uncertainty(dimension: str, stats: dict[str, Any] | None) -> float:
    return float(estimate_from_stats(stats).get("uncertainty") or 1.0)


def _n(dimension: str, stats: dict[str, Any] | None) -> int:
    return int(estimate_from_stats(stats).get("n") or 0)


def entropy(probability: float) -> float:
    p = max(1e-9, min(1.0 - 1e-9, float(probability)))
    return float(-(p * math.log(p) + (1.0 - p) * math.log(1.0 - p)))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def expected_information_gain(stats: dict[str, Any] | None, difficulty: float) -> float:
    """Expected reduction in outcome entropy from one binary trial.

    The Beta posterior is summarized by its mean; difficulty shifts the predicted success probability. The
    result is a ranking signal for task selection, not a learning-rate or intelligence estimate.
    """
    summary = estimate_from_stats(stats)
    mean = float(summary.get("estimate") or 0.5)
    mean = max(0.02, min(0.98, mean))
    probability = max(0.02, min(0.98, _sigmoid(math.log(mean / (1.0 - mean))
                                               + (0.5 - float(difficulty)) * 2.0)))
    alpha = max(0.001, float((stats or {}).get("alpha") or 1.0))
    beta = max(0.001, float((stats or {}).get("beta") or 1.0))
    total = alpha + beta
    after_correct = (alpha + 1.0) / (total + 1.0)
    after_incorrect = alpha / (total + 1.0)
    posterior_entropy = (probability * entropy(after_correct)
                         + (1.0 - probability) * entropy(after_incorrect))
    return round(max(0.0, entropy(probability) - posterior_entropy), 6)


def _task_type(dimension: str, trial_index: int, seed: int) -> str:
    options = TASK_FOR_DIMENSION[dimension]
    return options[(max(0, trial_index) + abs(int(seed))) % len(options)]


def select_action(stats_by_dimension: dict[str, dict[str, Any]], *, trial_index: int,
                  seed: int = 0, difficulty: float = 0.45) -> dict[str, Any]:
    """Choose a dimension, task type, and reason for the next trial."""
    if trial_index < 2:
        dimension = "stability"
        task_type = "object_reconstruction" if trial_index == 0 else "attribute_recall"
        return {
            "dimension": dimension,
            "task_type": task_type,
            "difficulty": max(0.1, min(0.9, float(difficulty))),
            "reason": "calibration_warmup",
            "expected_gain": None,
        }

    sparse = [name for name in SELECTABLE_DIMENSIONS
              if _n(name, stats_by_dimension.get(name)) < 2]
    if sparse:
        dimension = min(sparse, key=lambda name: (_n(name, stats_by_dimension.get(name)),
                                                  -_uncertainty(name, stats_by_dimension.get(name)),
                                                  name))
        reason = "coverage_floor"
        expected_gain = None
    else:
        gains = {
            name: expected_information_gain(stats_by_dimension.get(name), difficulty)
            for name in SELECTABLE_DIMENSIONS
        }
        dimension = max(SELECTABLE_DIMENSIONS,
                        key=lambda name: (gains[name], _uncertainty(name, stats_by_dimension.get(name)),
                                          -SELECTABLE_DIMENSIONS.index(name)))
        reason = "information_gain"
        expected_gain = gains[dimension]

    return {
        "dimension": dimension,
        "task_type": _task_type(dimension, trial_index, seed),
        "difficulty": max(0.1, min(0.9, float(difficulty))),
        "reason": reason,
        "expected_gain": expected_gain,
    }


def update_difficulty(current: float, recent_scores: list[float]) -> float:
    """A conservative challenge-point controller with a bounded step."""
    if not recent_scores:
        return max(0.1, min(0.9, float(current)))
    recent = [max(0.0, min(1.0, float(score))) for score in recent_scores[-5:]]
    mean = sum(recent) / len(recent)
    step = 0.0
    if mean >= 0.8:
        step = 0.08
    elif mean <= 0.5:
        step = -0.08
    return round(max(0.1, min(0.9, float(current) + step)), 3)


def action_payload(stats_by_dimension: dict[str, dict[str, Any]], *, trial_index: int,
                   seed: int, recent_scores: list[float],
                   current_difficulty: float) -> dict[str, Any]:
    action = select_action(stats_by_dimension, trial_index=trial_index, seed=seed,
                           difficulty=current_difficulty)
    action["difficulty"] = update_difficulty(current_difficulty, recent_scores)
    action["trial_index"] = max(0, int(trial_index))
    return action


__all__ = [
    "TASK_FOR_DIMENSION",
    "SELECTABLE_DIMENSIONS",
    "select_action",
    "update_difficulty",
    "action_payload",
    "entropy",
    "expected_information_gain",
]
