"""Tests for the Stage 0E oracle audit and belief-based source updating."""
from __future__ import annotations

import pytest

from app.research.crt.model import DEFAULT_PRIOR, AgentParams, posterior_from_outcome, posterior_predictive
from app.research.crt.model_repair import ModelRepairConfig, check_model_repair, run_model_repair
from app.research.crt.simulate import SimulationConfig, simulate_participant

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def _agent() -> AgentParams:
    return AgentParams(beta=2.0, lam=0.25, gamma=0.2, tau=-0.2, pi=1.2, b_pi=0.3, mix=1.0)


def _replay_outcome_posterior(trial) -> tuple[float, ...]:
    posterior = DEFAULT_PRIOR
    for record in trial.tests:
        posterior = posterior_from_outcome(posterior, record.test, record.outcome)
    return posterior


def test_posterior_predictive_is_source_neutral_when_precision_is_zero() -> None:
    assert posterior_predictive(DEFAULT_PRIOR, 0, 0.0) == pytest.approx(0.5)


def test_belief_prediction_does_not_enter_the_source_update() -> None:
    config = SimulationConfig(n_participants=1, n_trials=12, seed=5, max_tests=2)
    result = simulate_participant(
        config,
        _agent(),
        seed=11,
        condition="active_predict",
        prediction_source="belief",
        source_update="outcome",
    )
    for trial in result.trials:
        replayed = _replay_outcome_posterior(trial)
        assert replayed == pytest.approx(trial.base_posterior)


def test_dual_prediction_does_not_enter_the_source_update() -> None:
    config = SimulationConfig(n_participants=1, n_trials=8, seed=5, max_tests=2)
    result = simulate_participant(
        config,
        _agent(),
        seed=13,
        condition="active_predict",
        prediction_source="belief",
        prediction_format="dual",
        source_update="outcome",
    )
    for trial in result.trials:
        replayed = _replay_outcome_posterior(trial)
        assert replayed == pytest.approx(trial.base_posterior)


def test_legacy_oracle_path_changes_the_posterior_beyond_outcome_only() -> None:
    config = SimulationConfig(n_participants=1, n_trials=12, seed=5, max_tests=2)
    result = simulate_participant(
        config,
        _agent(),
        seed=17,
        condition="active_predict",
        prediction_source="oracle",
        source_update="legacy",
    )
    differences = [
        max(abs(left - right) for left, right in zip(trial.base_posterior, _replay_outcome_posterior(trial)))
        for trial in result.trials
    ]
    assert max(differences) > 1e-6


def test_model_repair_quantifies_oracle_inflation() -> None:
    report = run_model_repair(ModelRepairConfig(n_participants=12, n_trials=30, seed=7))
    assert report["decision"] == "CRT_STAGE0E_MODEL_PASS"
    assert report["audit"]["oracle_inflation"] > 0.02
    assert report["audit"]["double_counting_removed"] is True
    assert report["belief"]["specificity_decision"] == "CRT_STAGE0D_SPECIFICITY_REVIEW"


def test_model_repair_gate_passes() -> None:
    assert check_model_repair()["decision"] == "CRT_STAGE0E_MODEL_PASS"
