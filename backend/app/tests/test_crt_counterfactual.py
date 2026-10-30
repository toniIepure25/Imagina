"""Tests for Stage 0E dual-hypothesis counterfactual prediction."""
from __future__ import annotations

import pytest

from app.research.crt.counterfactual import (
    CounterfactualConfig,
    counterfactual_discrepancy,
    hypothesis_predictions,
    hypothesis_surprise,
    run_counterfactual_simulation,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_hypothesis_predictions_diverge_for_a_diagnostic_test() -> None:
    seen, imagined = hypothesis_predictions(0, 1.2)
    assert seen != pytest.approx(imagined)
    assert counterfactual_discrepancy(0, 1.2) > 0.0


def test_hypothesis_surprise_is_zero_for_a_perfect_prediction() -> None:
    assert hypothesis_surprise(1.0, True) == pytest.approx(0.0)
    assert hypothesis_surprise(0.0, False) == pytest.approx(0.0)


def test_dual_prediction_report_is_deterministic() -> None:
    config = CounterfactualConfig(n_participants=8, n_trials=30, seed=7)
    first = run_counterfactual_simulation(config)
    second = run_counterfactual_simulation(config)
    assert first == second


def test_report_exposes_both_hypothesis_accuracies_and_discrepancy() -> None:
    report = run_counterfactual_simulation(CounterfactualConfig(n_participants=8, n_trials=30, seed=7))
    contrasts = report["contrasts"]
    assert contrasts["mean_counterfactual_discrepancy"] > 0.0
    assert contrasts["dual_prediction_accuracy_seen"] is not None
    assert contrasts["dual_prediction_accuracy_imagined"] is not None


def test_dual_prediction_does_not_yet_clear_the_counterfactual_gate() -> None:
    report = run_counterfactual_simulation(CounterfactualConfig(n_participants=24, n_trials=60, seed=20261030))
    assert report["decision"] == "CRT_STAGE0E_COUNTERFACTUAL_REVIEW"
    assert report["contrasts"]["dual_gain_over_single"] < 0.02
