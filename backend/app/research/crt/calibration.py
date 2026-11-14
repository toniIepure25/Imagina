"""Simulation-only calibration design for the CRT test-likelihood table.

The current Stage 0C model assumes six test likelihoods. This module specifies
how a calibration sample would estimate them with a Beta-Binomial model and
which tests would be retained for the confirmatory seen-vs-imagined contrast.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.research.crt.model import IMAGINED, SEEN, SOURCES, TEST_IDS, TEST_LIKELIHOODS

_EPS = 1e-9


@dataclass(frozen=True)
class CalibrationConfig:
    n_participants: int = 40
    trials_per_cell: int = 20
    seed: int = 20261029
    prior_alpha: float = 1.0
    prior_beta: float = 1.0
    noise_sd: float = 0.02
    strong_lr_low: float = 0.75
    strong_lr_high: float = 1.33

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.trials_per_cell <= 0:
            raise ValueError("trials_per_cell must be positive")
        if self.prior_alpha <= 0 or self.prior_beta <= 0:
            raise ValueError("Beta priors must be positive")
        if self.noise_sd < 0:
            raise ValueError("noise_sd must be non-negative")
        if not 0.0 < self.strong_lr_low < 1.0:
            raise ValueError("strong_lr_low must be between 0 and 1")
        if self.strong_lr_high <= 1.0:
            raise ValueError("strong_lr_high must be greater than 1")


def _clip_probability(value: float) -> float:
    return min(1.0 - _EPS, max(_EPS, value))


def simulate_calibration_counts(
    config: CalibrationConfig | None = None,
    true_likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> list[list[tuple[int, int]]]:
    config = config or CalibrationConfig()
    if len(true_likelihoods) != len(TEST_IDS):
        raise ValueError("true_likelihoods must have one row per test")
    for row in true_likelihoods:
        if len(row) != len(SOURCES):
            raise ValueError("true_likelihoods must have one probability per source")
    rng = random.Random(config.seed)
    counts: list[list[tuple[int, int]]] = []
    for row in true_likelihoods:
        test_counts: list[tuple[int, int]] = []
        for probability in row:
            cell_probability = _clip_probability(probability + rng.gauss(0.0, config.noise_sd))
            successes = sum(
                1
                for _ in range(config.n_participants * config.trials_per_cell)
                if rng.random() < cell_probability
            )
            total = config.n_participants * config.trials_per_cell
            test_counts.append((successes, total - successes))
        counts.append(test_counts)
    return counts


def fit_likelihoods(
    counts: Sequence[Sequence[tuple[int, int]]],
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> list[list[float]]:
    if prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("Beta priors must be positive")
    fitted: list[list[float]] = []
    for row in counts:
        fitted_row: list[float] = []
        for successes, failures in row:
            if successes < 0 or failures < 0:
                raise ValueError("counts must be non-negative")
            fitted_row.append((successes + prior_alpha) / (successes + failures + prior_alpha + prior_beta))
        fitted.append(fitted_row)
    return fitted


def likelihood_ratio(fitted: Sequence[Sequence[float]], test: int) -> float:
    if test not in range(len(TEST_IDS)):
        raise ValueError(f"unknown test index: {test}")
    p_seen = _clip_probability(fitted[test][SEEN])
    p_imagined = _clip_probability(fitted[test][IMAGINED])
    return p_seen / p_imagined


def run_calibration(config: CalibrationConfig | None = None) -> dict[str, object]:
    config = config or CalibrationConfig()
    counts = simulate_calibration_counts(config)
    fitted = fit_likelihoods(counts, config.prior_alpha, config.prior_beta)
    rows: list[dict[str, object]] = []
    strong_tests: list[str] = []
    for index, name in enumerate(TEST_IDS):
        ratio = likelihood_ratio(fitted, index)
        strong = ratio <= config.strong_lr_low or ratio >= config.strong_lr_high
        if strong:
            strong_tests.append(name)
        rows.append(
            {
                "test": name,
                "fitted": [round(value, 6) for value in fitted[index]],
                "seen_vs_imagined_lr": round(ratio, 6),
                "strong": strong,
                "counts": [[int(success), int(failure)] for success, failure in counts[index]],
            }
        )
    fluency_index = TEST_IDS.index("fluency")
    fluency_ratio = float(rows[fluency_index]["seen_vs_imagined_lr"])
    passed = len(strong_tests) >= 4 and 0.8 <= fluency_ratio <= 1.25
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0d_hierarchical_beta_binomial_test_calibration",
        "config": {
            "n_participants": config.n_participants,
            "trials_per_cell": config.trials_per_cell,
            "seed": config.seed,
            "prior_alpha": config.prior_alpha,
            "prior_beta": config.prior_beta,
            "noise_sd": config.noise_sd,
            "strong_lr_low": config.strong_lr_low,
            "strong_lr_high": config.strong_lr_high,
        },
        "tests": rows,
        "strong_tests": strong_tests,
        "fluency_lr": round(fluency_ratio, 6),
        "decision": "CRT_STAGE0D_CALIBRATION_PASS" if passed else "CRT_STAGE0D_CALIBRATION_REVIEW",
        "note": (
            "Simulated calibration design only. A human calibration sample must freeze the likelihood "
            "table before the confirmatory CRT study; weak tests are dropped or redesigned."
        ),
    }


def check_calibration() -> dict[str, object]:
    report = run_calibration(
        CalibrationConfig(n_participants=20, trials_per_cell=20, seed=7, noise_sd=0.01)
    )
    if report["decision"] != "CRT_STAGE0D_CALIBRATION_PASS":
        raise AssertionError(f"CRT calibration gate failed: {report['strong_tests']}")
    return report


__all__ = [
    "CalibrationConfig",
    "check_calibration",
    "fit_likelihoods",
    "likelihood_ratio",
    "run_calibration",
    "simulate_calibration_counts",
]
