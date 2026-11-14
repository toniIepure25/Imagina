"""Tests for the Stage 0D specificity and active-selection controls."""
from __future__ import annotations

import pytest

from app.research.crt.model import AgentParams
from app.research.crt.simulate import (
    SimulationConfig,
    check_selection,
    check_specificity,
    run_selection_simulation,
    run_specificity_simulation,
    simulate_participant,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def _agent() -> AgentParams:
    return AgentParams(beta=2.0, lam=0.25, gamma=0.2, tau=-0.2, pi=1.2, b_pi=0.3, mix=1.0)


def test_nondiagnostic_prediction_is_neutral_for_source_inference() -> None:
    config = SimulationConfig(n_participants=1, n_trials=8, seed=3)
    result = simulate_participant(
        config,
        _agent(),
        seed=99,
        condition="active_predict",
        prediction_mode="nondiagnostic",
    )
    tests = [record for trial in result.trials for record in trial.tests]
    assert tests
    assert all(record.predicted is not None for record in tests)
    assert all(record.counterfactual_discrimination == pytest.approx(0.0) for record in tests)
    assert all(record.meta_eig == pytest.approx(record.eig) for record in tests)


def test_diagnostic_prediction_has_nonzero_counterfactual_discrimination() -> None:
    config = SimulationConfig(n_participants=1, n_trials=8, seed=3)
    result = simulate_participant(
        config,
        _agent(),
        seed=99,
        condition="active_predict",
        prediction_mode="diagnostic",
    )
    tests = [record for trial in result.trials for record in trial.tests]
    assert tests
    assert any(record.counterfactual_discrimination > 0.0 for record in tests)


def test_specificity_control_finds_a_diagnostic_advantage_under_the_legacy_oracle() -> None:
    report = run_specificity_simulation(
        SimulationConfig(
            n_participants=8,
            n_trials=30,
            seed=7,
            prediction_source="oracle",
            source_update="legacy",
        )
    )
    assert report["decision"] == "CRT_STAGE0D_SPECIFICITY_PASS"
    assert report["contrasts"]["accuracy_gain"] > 0.0
    assert report["contrasts"]["prediction_accuracy_diagnostic"] is not None


def test_specificity_control_does_not_reproduce_under_belief_prediction() -> None:
    report = run_specificity_simulation(SimulationConfig(n_participants=24, n_trials=60, seed=7))
    assert report["decision"] == "CRT_STAGE0D_SPECIFICITY_REVIEW"
    assert report["contrasts"]["prediction_accuracy_diagnostic"] < 0.55


def test_specificity_control_holds_the_test_sequence_fixed() -> None:
    report = run_specificity_simulation(
        SimulationConfig(
            n_participants=8,
            n_trials=30,
            seed=7,
            prediction_source="oracle",
            source_update="legacy",
        )
    )
    diagnostic_counts = report["condition_summaries"]["diagnostic"]["test_counts"]
    nondiagnostic_counts = report["condition_summaries"]["nondiagnostic"]["test_counts"]
    assert diagnostic_counts == nondiagnostic_counts


def test_selection_control_decomposes_active_choice_and_adaptive_design() -> None:
    report = run_selection_simulation(
        SimulationConfig(
            n_participants=8,
            n_trials=30,
            seed=7,
            prediction_source="oracle",
            source_update="legacy",
        )
    )
    assert report["decision"] == "CRT_STAGE0D_SELECTION_PASS"
    assert report["contrasts"]["active_choice_gain"] > 0.0
    assert report["contrasts"]["adaptive_design_gain"] > 0.0
    assert set(report["condition_summaries"]) == {"active", "algorithm", "random_passive"}


def test_control_gates_pass() -> None:
    assert check_specificity()["decision"] == "CRT_STAGE0D_SPECIFICITY_PASS"
    assert check_selection()["decision"] == "CRT_STAGE0D_SELECTION_PASS"


def test_invalid_control_modes_are_rejected() -> None:
    with pytest.raises(ValueError):
        SimulationConfig(prediction_mode="unknown")
    with pytest.raises(ValueError):
        SimulationConfig(selection_mode="unknown")
    config = SimulationConfig(n_participants=1, n_trials=2, seed=3)
    with pytest.raises(ValueError):
        simulate_participant(
            config,
            _agent(),
            seed=99,
            condition="active_predict",
            prediction_mode="unknown",
        )
