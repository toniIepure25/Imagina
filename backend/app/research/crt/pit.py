"""Posterior PIT calibration screening for the CRT source model.

This is a randomized probability-integral-transform check, not full hierarchical SBC. It tests
whether the assumed generative source model produces calibrated posterior probabilities for the true
source. Full SBC with group-level parameters and misspecified likelihoods remains future work.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean

from app.research.crt.model import (
    ALL_TESTS,
    DEFAULT_PRIOR,
    SOURCES,
    outcome_likelihood,
    posterior_from_outcome,
)


@dataclass(frozen=True)
class PitConfig:
    n_simulations: int = 1000
    n_tests: int = 2
    bins: int = 10
    seed: int = 20261030
    max_bin_deviation: float = 0.25

    def __post_init__(self) -> None:
        if self.n_simulations <= 0:
            raise ValueError("n_simulations must be positive")
        if self.n_tests <= 0:
            raise ValueError("n_tests must be positive")
        if self.bins < 2:
            raise ValueError("bins must be at least two")


def posterior_probability_true_source(
    true_source: int,
    n_tests: int,
    rng: random.Random,
    prior: tuple[float, ...] = DEFAULT_PRIOR,
) -> float:
    posterior = _posterior_for_true_source(true_source, n_tests, rng, prior)
    return float(posterior[true_source])


def _posterior_for_true_source(
    true_source: int,
    n_tests: int,
    rng: random.Random,
    prior: tuple[float, ...],
) -> tuple[float, ...]:
    posterior = prior
    available = list(ALL_TESTS)
    for _ in range(n_tests):
        test = rng.choice(available)
        available.remove(test)
        outcome = rng.random() < outcome_likelihood(test, true_source)
        posterior = posterior_from_outcome(posterior, test, outcome)
    return tuple(posterior)


def posterior_pit(
    true_source: int,
    n_tests: int,
    rng: random.Random,
    prior: tuple[float, ...] = DEFAULT_PRIOR,
) -> float:
    """Randomized probability-integral transform of the posterior CDF at the true source."""

    posterior = _posterior_for_true_source(true_source, n_tests, rng, prior)
    lower = sum(posterior[:true_source])
    upper = lower + posterior[true_source]
    return lower + rng.random() * (upper - lower)


def run_pit_calibration(config: PitConfig | None = None) -> dict[str, object]:
    config = config or PitConfig()
    rng = random.Random(config.seed)
    values = []
    for _ in range(config.n_simulations):
        true_source = rng.randrange(len(SOURCES))
        values.append(posterior_pit(true_source, config.n_tests, rng))
    counts = [0 for _ in range(config.bins)]
    for value in values:
        index = min(config.bins - 1, max(0, int(value * config.bins)))
        counts[index] += 1
    expected = len(values) / config.bins
    deviations = [abs(count - expected) / expected for count in counts]
    max_deviation = max(deviations)
    chi_square = sum((count - expected) ** 2 / expected for count in counts)
    chi_square_critical = 21.666 if config.bins == 10 else 2.0 * config.bins
    passed = max_deviation <= config.max_bin_deviation and chi_square <= chi_square_critical
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_posterior_pit_calibration",
        "config": {
            "n_simulations": config.n_simulations,
            "n_tests": config.n_tests,
            "bins": config.bins,
            "seed": config.seed,
            "max_bin_deviation": config.max_bin_deviation,
        },
        "histogram": counts,
        "summary": {
            "mean_pit": round(mean(values), 6),
            "max_bin_deviation": round(max_deviation, 6),
            "max_bin_deviation_threshold": config.max_bin_deviation,
            "chi_square": round(chi_square, 6),
            "chi_square_critical": chi_square_critical,
        },
        "decision": "CRT_STAGE0E_PIT_PASS" if passed else "CRT_STAGE0E_PIT_REVIEW",
        "note": (
            "Randomized PIT calibration for the source posterior under the assumed generative model. "
            "This is a necessary design check, not a fit to human data and not full hierarchical "
            "simulation-based calibration."
        ),
    }


__all__ = ["PitConfig", "posterior_pit", "posterior_probability_true_source", "run_pit_calibration"]
