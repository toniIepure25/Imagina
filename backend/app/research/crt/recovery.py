"""Belief-based parameter recovery, SBC, and model recovery for Stage 0E.

The checks are deliberately conditional: ``d``, guessing, and response bias are fixed, and the free
parameter is the prediction readout precision ``pi``. This is not full hierarchical SBC. It tests
whether the repaired readout is identifiable and calibrated before any human study.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean

from app.research.crt.model import (
    DEFAULT_PRIOR,
    AgentParams,
    apply_prediction_bias,
    choose_source_probabilities,
    posterior_from_outcome,
    posterior_predictive,
)
from app.research.crt.simulate import ParticipantResult, SimulationConfig, run_condition

PI_MIN = 0.40
PI_MAX = 2.00
PI_STEP = 0.05
PI_GRID = tuple(round(PI_MIN + index * PI_STEP, 10) for index in range(33))
B_PI_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
SBC_BINS = 10
SBC_CRITICAL = 21.666


@dataclass(frozen=True)
class RecoveryConfig:
    n_participants: int = 24
    n_trials: int = 240
    n_sbc: int = 200
    n_model_participants: int = 24
    seed: int = 20261030
    max_tests: int = 2
    max_relative_rmse: float = 0.25
    max_abs_bias: float = 0.15
    min_correlation: float = 0.70
    min_model_accuracy: float = 0.80

    def __post_init__(self) -> None:
        for name in ("n_participants", "n_trials", "n_sbc", "n_model_participants", "max_tests"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0.0 <= self.max_relative_rmse <= 1.0:
            raise ValueError("max_relative_rmse must be in [0, 1]")
        if not 0.0 <= self.min_correlation <= 1.0:
            raise ValueError("min_correlation must be in [0, 1]")


def _params(pi: float, b_pi: float = 0.0) -> AgentParams:
    return AgentParams(
        beta=2.0,
        lam=0.0,
        gamma=0.0,
        tau=0.0,
        d=1.0,
        pi=pi,
        b_pi=b_pi,
        guess=0.0,
        bias=0.0,
        lapse=0.0,
        confidence_noise=0.05,
        mix=1.0,
        alpha=0.0,
    )


def _simulate(
    seed: int,
    pi: float,
    *,
    b_pi: float = 0.0,
    prediction_mode: str = "diagnostic",
    n_trials: int = 60,
    max_tests: int = 2,
) -> ParticipantResult:
    config = SimulationConfig(
        n_participants=1,
        n_trials=n_trials,
        seed=seed,
        max_tests=max_tests,
        d_mean=1.0,
        d_sd=0.0,
        pi_mean=pi,
        pi_sd=0.0,
        b_pi_mean=b_pi,
        b_pi_sd=0.0,
        guess_mean=0.0,
        guess_sd=0.0,
        bias_mean=0.0,
        bias_sd=0.0,
        prediction_mode=prediction_mode,
        prediction_source="belief",
        prediction_format="single",
        source_update="outcome",
    )
    participants = run_condition(
        config,
        "active_predict",
        "fixed",
        params_list=[_params(pi, b_pi)],
        prediction_mode=prediction_mode,
        prediction_source="belief",
        source_update="outcome",
    )
    return participants[0]


def _prediction_log_likelihood(participant: ParticipantResult, pi: float) -> float:
    total = 0.0
    for trial in participant.trials:
        posterior = DEFAULT_PRIOR
        for test in trial.tests:
            probability = posterior_predictive(posterior, test.test, pi)
            if test.predicted is not None:
                total += math.log(max(1e-12, probability if test.predicted else 1.0 - probability))
            posterior = posterior_from_outcome(posterior, test.test, test.outcome, 1.0)
    return total


def _source_log_likelihood(participant: ParticipantResult, b_pi: float = 0.0) -> float:
    total = 0.0
    for trial in participant.trials:
        posterior = DEFAULT_PRIOR
        predictions: list[tuple[bool, float]] = []
        for test in trial.tests:
            if test.predicted is not None and test.prediction_confidence is not None:
                predictions.append((bool(test.predicted), float(test.prediction_confidence)))
            posterior = posterior_from_outcome(posterior, test.test, test.outcome, 1.0)
        probabilities = choose_source_probabilities(
            apply_prediction_bias(posterior, predictions, b_pi),
            guess=0.0,
            bias=0.0,
        )
        total += math.log(max(1e-12, probabilities[trial.choice]))
    return total


def _null_prediction_log_likelihood(participant: ParticipantResult) -> float:
    count = sum(1 for trial in participant.trials for test in trial.tests if test.predicted is not None)
    return count * math.log(0.5)


def _total_log_likelihood(
    participant: ParticipantResult,
    pi: float,
    *,
    b_pi: float = 0.0,
    include_prediction: bool = True,
) -> float:
    source = _source_log_likelihood(participant, b_pi)
    if include_prediction:
        return source + _prediction_log_likelihood(participant, pi)
    return source


def _fit_pi(participant: ParticipantResult, *, include_prediction: bool = True) -> float:
    return max(
        PI_GRID,
        key=lambda candidate: _total_log_likelihood(participant, candidate, include_prediction=include_prediction),
    )


def _posterior_weights(participant: ParticipantResult) -> tuple[float, ...]:
    log_weights = [_prediction_log_likelihood(participant, candidate) for candidate in PI_GRID]
    maximum = max(log_weights)
    weights = [math.exp(value - maximum) for value in log_weights]
    total = sum(weights)
    return tuple(value / total for value in weights)


def _randomized_pit(participant: ParticipantResult, true_pi: float, rng: random.Random) -> float:
    weights = _posterior_weights(participant)
    lower = sum(weight for value, weight in zip(PI_GRID, weights, strict=True) if value < true_pi)
    if true_pi <= PI_GRID[0]:
        return lower
    if true_pi >= PI_GRID[-1]:
        return 1.0
    nearest = min(range(len(PI_GRID)), key=lambda index: abs(PI_GRID[index] - true_pi))
    return min(1.0, max(0.0, lower + rng.random() * weights[nearest]))


def _correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean_x = mean(xs)
    mean_y = mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys))
    return 0.0 if denominator == 0.0 else numerator / denominator


def _sbc(config: RecoveryConfig) -> dict[str, object]:
    rng = random.Random(config.seed + 11)
    values = []
    for index in range(config.n_sbc):
        true_pi = rng.uniform(PI_MIN, PI_MAX)
        participant = _simulate(
            config.seed + 10_000 + index,
            true_pi,
            n_trials=config.n_trials,
            max_tests=config.max_tests,
        )
        values.append(_randomized_pit(participant, true_pi, rng))
    counts = [0 for _ in range(SBC_BINS)]
    for value in values:
        counts[min(SBC_BINS - 1, max(0, int(value * SBC_BINS)))] += 1
    expected = len(values) / SBC_BINS
    deviations = [abs(count - expected) / expected for count in counts]
    max_deviation = max(deviations)
    chi_square = sum((count - expected) ** 2 / expected for count in counts)
    mean_pit = mean(values)
    passed = chi_square <= SBC_CRITICAL and 0.45 <= mean_pit <= 0.55
    return {
        "n_simulations": config.n_sbc,
        "true_pi_range": [PI_MIN, PI_MAX],
        "histogram": counts,
        "mean_pit": round(mean_pit, 6),
        "max_bin_deviation": round(max_deviation, 6),
        "chi_square": round(chi_square, 6),
        "chi_square_critical": SBC_CRITICAL,
        "passed": passed,
    }


def _parameter_recovery(config: RecoveryConfig) -> dict[str, object]:
    rng = random.Random(config.seed + 21)
    truths: list[float] = []
    estimates: list[float] = []
    for index in range(config.n_participants):
        true_pi = rng.uniform(PI_MIN, PI_MAX)
        participant = _simulate(
            config.seed + 20_000 + index,
            true_pi,
            n_trials=config.n_trials,
            max_tests=config.max_tests,
        )
        truths.append(true_pi)
        estimates.append(_fit_pi(participant))
    errors = [estimate - truth for estimate, truth in zip(estimates, truths, strict=True)]
    rmse = math.sqrt(mean(error * error for error in errors))
    bias = mean(errors)
    correlation = _correlation(truths, estimates)
    relative_rmse = rmse / (PI_MAX - PI_MIN)
    passed = (
        abs(bias) <= config.max_abs_bias
        and relative_rmse <= config.max_relative_rmse
        and correlation >= config.min_correlation
    )
    return {
        "n_participants": config.n_participants,
        "n_trials": config.n_trials,
        "true_pi": [round(value, 6) for value in truths],
        "estimated_pi": [round(value, 6) for value in estimates],
        "bias": round(bias, 6),
        "rmse": round(rmse, 6),
        "relative_rmse": round(relative_rmse, 6),
        "correlation": round(correlation, 6),
        "thresholds": {
            "max_abs_bias": config.max_abs_bias,
            "max_relative_rmse": config.max_relative_rmse,
            "min_correlation": config.min_correlation,
        },
        "passed": passed,
    }


def _bic(log_likelihood: float, n_observations: int, n_parameters: int) -> float:
    return -2.0 * log_likelihood + n_parameters * math.log(max(1, n_observations))


def _model_recovery(config: RecoveryConfig) -> dict[str, object]:
    rng = random.Random(config.seed + 31)
    outcomes = []
    for true_model in ("M0", "M2"):
        for index in range(config.n_model_participants):
            pi = rng.uniform(PI_MIN, PI_MAX)
            participant = _simulate(
                config.seed + 30_000 + index,
                pi,
                b_pi=0.4 if true_model == "M2" else 0.0,
                prediction_mode="none" if true_model == "M0" else "diagnostic",
                n_trials=config.n_trials,
                max_tests=config.max_tests,
            )
            source_ll = _source_log_likelihood(participant)
            m0_ll = source_ll + _null_prediction_log_likelihood(participant)
            m0_bic = _bic(m0_ll, n_observations=config.n_trials, n_parameters=0)
            m2_ll = max(
                _total_log_likelihood(participant, candidate, b_pi=bias, include_prediction=True)
                for candidate in PI_GRID
                for bias in B_PI_GRID
            )
            m2_bic = _bic(m2_ll, n_observations=config.n_trials, n_parameters=2)
            recovered = "M2" if m2_bic < m0_bic else "M0"
            outcomes.append((true_model, recovered))
    correct = sum(1 for true_model, recovered in outcomes if true_model == recovered)
    accuracy = correct / len(outcomes)
    confusion = {
        true_model: {
            recovered_model: sum(
                1 for truth, guess in outcomes if truth == true_model and guess == recovered_model
            )
            for recovered_model in ("M0", "M2")
        }
        for true_model in ("M0", "M2")
    }
    return {
        "n_participants_per_model": config.n_model_participants,
        "models": ["M0", "M2"],
        "confusion": confusion,
        "balanced_accuracy": round(accuracy, 6),
        "threshold": config.min_model_accuracy,
        "passed": accuracy >= config.min_model_accuracy,
    }


def run_recovery(config: RecoveryConfig | None = None) -> dict[str, object]:
    config = config or RecoveryConfig()
    parameter = _parameter_recovery(config)
    sbc = _sbc(config)
    model = _model_recovery(config)
    passed = bool(parameter["passed"] and sbc["passed"] and model["passed"])
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_belief_parameter_sbc_and_model_recovery",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "max_tests": config.max_tests,
            "n_sbc": config.n_sbc,
            "n_model_participants": config.n_model_participants,
            "seed": config.seed,
            "pi_grid": [PI_MIN, PI_MAX, PI_STEP],
            "fixed_parameters": ["d=1.0", "guess=0.0", "bias=0.0"],
        },
        "parameter_recovery": parameter,
        "sbc": sbc,
        "model_recovery": model,
        "decision": "CRT_STAGE0E_RECOVERY_PASS" if passed else "CRT_STAGE0E_RECOVERY_REVIEW",
        "note": (
            "Conditional SBC and recovery for the belief-based prediction precision pi, plus a "
            "BIC comparison of M0 (no prediction) and M2 (single belief readout). d, guessing, and "
            "response bias are fixed. This is not full hierarchical SBC and not human evidence."
        ),
    }


__all__ = [
    "PI_GRID",
    "RecoveryConfig",
    "run_recovery",
]
