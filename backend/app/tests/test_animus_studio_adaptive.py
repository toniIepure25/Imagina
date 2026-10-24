from __future__ import annotations

import pytest

from app.core.animus.studio.adaptive import (
    SELECTABLE_DIMENSIONS,
    expected_information_gain,
    select_action,
    update_difficulty,
)
from app.core.animus.studio.profile import apply_observation

pytestmark = pytest.mark.core


def _stats(scores: list[float]) -> dict:
    stats = None
    for score in scores:
        stats = apply_observation(stats, score=score, confidence=0.7)
    return stats or {}


def test_calibration_is_cross_cutting_not_selectable():
    assert "calibration" not in SELECTABLE_DIMENSIONS
    action = select_action({}, trial_index=5, seed=3, difficulty=0.45)
    assert action["dimension"] in SELECTABLE_DIMENSIONS


def test_first_two_trials_are_calibration_warmup():
    first = select_action({}, trial_index=0, seed=1)
    second = select_action({}, trial_index=1, seed=1)
    assert first["task_type"] == "object_reconstruction"
    assert second["task_type"] == "attribute_recall"
    assert first["reason"] == second["reason"] == "calibration_warmup"


def test_coverage_floor_prefers_sparse_dimension():
    stats = {
        "stability": _stats([1.0, 1.0, 1.0]),
        "discrimination": _stats([1.0, 1.0, 1.0]),
        "spatial": _stats([1.0]),
        "control": _stats([1.0, 1.0, 1.0]),
    }
    action = select_action(stats, trial_index=7, seed=3)
    assert action["dimension"] == "spatial"
    assert action["reason"] == "coverage_floor"


def test_information_gain_is_deterministic_and_bounded():
    stats = {
        "stability": _stats([1.0, 1.0, 0.0, 1.0]),
        "discrimination": _stats([0.0, 0.0, 0.0, 0.0]),
        "spatial": _stats([1.0, 0.0, 1.0, 0.0]),
        "control": _stats([1.0, 1.0, 1.0, 1.0]),
    }
    first = select_action(stats, trial_index=8, seed=5, difficulty=0.4)
    second = select_action(stats, trial_index=8, seed=5, difficulty=0.4)
    assert first == second
    assert first["reason"] == "information_gain"
    assert 0.0 <= first["expected_gain"] <= 1.0
    assert 0.1 <= first["difficulty"] <= 0.9


def test_expected_gain_is_higher_near_uncertainty():
    uncertain = expected_information_gain({"alpha": 1.0, "beta": 1.0}, 0.5)
    certain = expected_information_gain({"alpha": 20.0, "beta": 1.0}, 0.5)
    assert uncertain > certain


def test_difficulty_updates_are_bounded():
    assert update_difficulty(0.5, [1.0, 1.0, 1.0]) == 0.58
    assert update_difficulty(0.5, [0.0, 0.0, 0.0]) == 0.42
    assert update_difficulty(0.89, [1.0, 1.0, 1.0]) == 0.9
    assert update_difficulty(0.11, [0.0, 0.0, 0.0]) == 0.1
