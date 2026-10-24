"""Deterministic evaluation-only simulation for Scene Threshold."""
from __future__ import annotations

import pytest

from app.core.animus.scene.model import AttributeValue, SceneEntity, SceneGraph
from app.evaluation.animus_contrast_sim import (
    SimulatedRespondent,
    recovery_check,
    simulate_contrast,
)

pytestmark = pytest.mark.core


def _scene() -> SceneGraph:
    items = [
        SceneEntity(
            id=f"ent_{index:08x}",
            kind=("castle", "tree", "moon", "water", "rock", "lantern")[index % 6],
            label=f"Item {index}",
            role="subject" if index == 0 else "prop",
            position=[float(index) - 2.5, 0.0, float((index * 3) % 7) - 3.0],
            attributes={"color": AttributeValue(value="#8899aa", confidence=0.7)},
        )
        for index in range(6)
    ]
    return SceneGraph(scene_id="scene_12345678", seed=7, title="Simulation scene", entities=items)


def test_simulation_is_deterministic_and_uses_the_public_task():
    first = simulate_contrast(
        _scene(), respondent=SimulatedRespondent(seed=9, threshold=0.3), max_trials=12)
    second = simulate_contrast(
        _scene(), respondent=SimulatedRespondent(seed=9, threshold=0.3), max_trials=12)
    assert [trial["trial_id"] for trial in first.trials] == [
        trial["trial_id"] for trial in second.trials]
    assert first.summary["n_trials"] == 12
    assert first.summary["scoring_version"] == "sdt-v1"
    assert all("target_side" not in trial for trial in first.trials)


def test_sensitive_observer_has_higher_accuracy_than_guesser():
    sensitive = simulate_contrast(
        _scene(),
        respondent=SimulatedRespondent(threshold=0.1, slope=0.05, seed=4),
        max_trials=12,
    )
    guesser = simulate_contrast(
        _scene(),
        respondent=SimulatedRespondent(threshold=0.9, slope=0.2, seed=4, policy="guesser"),
        max_trials=12,
    )
    sensitive_correct = sum(1 for trial in sensitive.trials if trial["correct"])
    guesser_correct = sum(1 for trial in guesser.trials if trial["correct"])
    assert sensitive_correct > guesser_correct
    assert sensitive.summary["dprime"] > guesser.summary["dprime"]


def test_abstainer_reduces_coverage_without_scoring_as_correct():
    simulation = simulate_contrast(
        _scene(),
        respondent=SimulatedRespondent(policy="abstainer", seed=2),
        max_trials=12,
    )
    assert simulation.summary["n_trials"] == 12
    assert simulation.summary["n_answered"] == 0
    assert simulation.summary["coverage"] == 0.0
    assert simulation.summary["dprime"] is None
    assert all(trial["correct"] is None for trial in simulation.trials)


def test_recovery_check_returns_one_row_per_scene_and_threshold():
    rows = recovery_check([_scene()], thresholds=(0.25, 0.4), max_trials=16)
    assert len(rows) == 2
    assert {row["true_threshold"] for row in rows} == {0.25, 0.4}
    assert all(row["n_answered"] == 16 for row in rows)
    assert all(row["estimated_threshold"] is not None for row in rows)
