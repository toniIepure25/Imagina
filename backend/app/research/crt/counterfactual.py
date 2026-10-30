"""Dual-hypothesis counterfactual prediction for Stage 0E.

A single prediction can be produced by a generic forward model. A dual prediction asks the participant
to predict the test outcome under two source hypotheses, which makes the counterfactual alternative
explicit and yields a measurable perceived diagnosticity.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from app.research.crt.model import IMAGINED, SEEN, TEST_IDS, posterior_predictive, prediction_likelihood
from app.research.crt.simulate import SimulationConfig, _participant_params, run_condition


@dataclass(frozen=True)
class CounterfactualConfig:
    n_participants: int = 24
    n_trials: int = 60
    seed: int = 20261030
    max_tests: int = 2

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.max_tests <= 0:
            raise ValueError("max_tests must be positive")


def hypothesis_predictions(test: int, pi: float = 1.0) -> tuple[float, float]:
    """Predicted positive-outcome probability under seen and imagined hypotheses."""

    return (
        prediction_likelihood(test, SEEN, pi),
        prediction_likelihood(test, IMAGINED, pi),
    )


def counterfactual_discrepancy(test: int, pi: float = 1.0) -> float:
    """Perceived diagnosticity: how differently the two hypotheses predict the test outcome."""

    seen, imagined = hypothesis_predictions(test, pi)
    return abs(seen - imagined)


def hypothesis_surprise(prediction: float, outcome: bool) -> float:
    """Absolute prediction error for one hypothesis."""

    return abs(float(prediction) - (1.0 if outcome else 0.0))


def belief_predictive_probability(prior: Sequence[float], test: int, pi: float = 1.0) -> float:
    """Convenience wrapper used by the dual-prediction analysis."""

    return posterior_predictive(prior, test, pi)


def _simulation_config(config: CounterfactualConfig) -> SimulationConfig:
    return SimulationConfig(
        n_participants=config.n_participants,
        n_trials=config.n_trials,
        seed=config.seed,
        max_tests=config.max_tests,
        prediction_source="belief",
        source_update="outcome",
    )


def _summary_accuracy(summary: dict[str, object]) -> float:
    return float(summary["accuracy"])


def run_counterfactual_simulation(config: CounterfactualConfig | None = None) -> dict[str, object]:
    """Compare single, dual, and dual non-diagnostic prediction on a fixed test sequence."""

    config = config or CounterfactualConfig()
    base = _simulation_config(config)
    params_list = _participant_params(base)
    single = run_condition(
        base,
        "active_predict",
        "fixed",
        params_list=params_list,
        prediction_mode="diagnostic",
        prediction_format="single",
    )
    dual = run_condition(
        base,
        "active_predict",
        "fixed",
        params_list=params_list,
        prediction_mode="diagnostic",
        prediction_format="dual",
    )
    dual_nondiagnostic = run_condition(
        base,
        "active_predict",
        "fixed",
        params_list=params_list,
        prediction_mode="nondiagnostic",
        prediction_format="dual",
    )
    single_summary = _aggregate(single)
    dual_summary = _aggregate(dual)
    nondiagnostic_summary = _aggregate(dual_nondiagnostic)
    single_accuracy = _summary_accuracy(single_summary)
    dual_accuracy = _summary_accuracy(dual_summary)
    nondiagnostic_accuracy = _summary_accuracy(nondiagnostic_summary)
    dual_gain = dual_accuracy - single_accuracy
    specificity_gain = dual_accuracy - nondiagnostic_accuracy
    discrepancy_values = [
        test.counterfactual_discrepancy
        for participant in dual
        for trial in participant.trials
        for test in trial.tests
        if test.counterfactual_discrepancy is not None
    ]
    discrepancy = mean(discrepancy_values) if discrepancy_values else 0.0
    passed = dual_gain >= 0.02 and specificity_gain >= 0.02 and discrepancy >= 0.05
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_dual_hypothesis_counterfactual_prediction",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "max_tests": config.max_tests,
            "test_ids": list(TEST_IDS),
        },
        "condition_summaries": {
            "single_diagnostic": single_summary,
            "dual_diagnostic": dual_summary,
            "dual_nondiagnostic": nondiagnostic_summary,
        },
        "contrasts": {
            "dual_gain_over_single": round(dual_gain, 6),
            "specificity_gain_over_nondiagnostic": round(specificity_gain, 6),
            "mean_counterfactual_discrepancy": round(discrepancy, 6),
            "dual_prediction_accuracy_seen": dual_summary["prediction_accuracy_seen"],
            "dual_prediction_accuracy_imagined": dual_summary["prediction_accuracy_imagined"],
        },
        "decision": "CRT_STAGE0E_COUNTERFACTUAL_PASS"
        if passed
        else "CRT_STAGE0E_COUNTERFACTUAL_REVIEW",
        "note": (
            "The dual diagnostic arm asks for predictions under seen and imagined hypotheses. It is "
            "compared with a single prediction and a dual non-diagnostic prediction on the same fixed "
            "test sequence. A REVIEW means the current design does not yet earn the counterfactual label; "
            "it is not evidence against the construct."
        ),
    }


def _aggregate(participants: Sequence[object]) -> dict[str, object]:
    from app.research.crt.simulate import _aggregate as aggregate

    return aggregate(participants)  # type: ignore[arg-type]


__all__ = [
    "CounterfactualConfig",
    "belief_predictive_probability",
    "counterfactual_discrepancy",
    "hypothesis_predictions",
    "hypothesis_surprise",
    "run_counterfactual_simulation",
]
