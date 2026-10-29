"""Simulation-based power check for the Stage 1 test-retest reliability target.

The check uses a two-occasion, two-way random-effects ICC(2,1) and a normal-approximation lower
confidence bound. It is a planning tool, not a substitute for the registered analysis.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean

from app.research.prm.model import normal_ppf


@dataclass(frozen=True)
class PowerConfig:
    n_participants: int = 180
    n_simulations: int = 2000
    seed: int = 20261029
    lower_bound_target: float = 0.60
    alpha: float = 0.05

    def __post_init__(self) -> None:
        if self.n_participants < 4:
            raise ValueError("n_participants must be at least 4")
        if self.n_simulations <= 0:
            raise ValueError("n_simulations must be positive")
        if not 0.0 < self.lower_bound_target < 1.0:
            raise ValueError("lower_bound_target must be between 0 and 1")


def icc_2_1(first: list[float], second: list[float]) -> float:
    """Two-way random-effects, absolute-agreement, single-measure ICC for two occasions."""
    if len(first) != len(second):
        raise ValueError("occasion vectors must have equal length")
    n = len(first)
    if n < 2:
        raise ValueError("at least two participants are required")
    k = 2
    grand = mean(first + second)
    subject_means = [(a + b) / 2.0 for a, b in zip(first, second)]
    occasion_means = [mean(first), mean(second)]
    ms_between = k * sum((value - grand) ** 2 for value in subject_means) / (n - 1)
    ms_occasion = n * sum((value - grand) ** 2 for value in occasion_means) / (k - 1)
    residual = 0.0
    for a, b, subject_mean in zip(first, second, subject_means):
        residual += (a - subject_mean - occasion_means[0] + grand) ** 2
        residual += (b - subject_mean - occasion_means[1] + grand) ** 2
    ms_error = residual / ((n - 1) * (k - 1))
    denominator = ms_between + (k - 1) * ms_error + k * (ms_occasion - ms_error) / n
    if denominator <= 0:
        return 0.0
    return (ms_between - ms_error) / denominator


def approximate_lower_bound(icc: float, n_participants: int, alpha: float = 0.05) -> float:
    """Normal-approximation lower bound on the ICC; documented as approximate."""
    clipped = min(0.999, max(-0.999, icc))
    z = math.atanh(clipped)
    standard_error = 1.0 / math.sqrt(max(3, n_participants - 3))
    critical = abs(normal_ppf(alpha / 2.0))
    return math.tanh(z - critical * standard_error)


def simulate_power(
    true_icc: float,
    config: PowerConfig,
) -> dict[str, float]:
    if not -0.99 < true_icc < 0.99:
        raise ValueError("true_icc must be between -0.99 and 0.99")
    rng = random.Random(config.seed)
    estimates: list[float] = []
    lower_bounds: list[float] = []
    for _ in range(config.n_simulations):
        first = [rng.gauss(0.0, 1.0) for _ in range(config.n_participants)]
        second = [
            true_icc * value + math.sqrt(max(0.0, 1.0 - true_icc**2)) * rng.gauss(0.0, 1.0)
            for value in first
        ]
        estimate = icc_2_1(first, second)
        estimates.append(estimate)
        lower_bounds.append(approximate_lower_bound(estimate, config.n_participants, config.alpha))
    power = sum(1 for bound in lower_bounds if bound > config.lower_bound_target) / len(lower_bounds)
    return {
        "true_icc": round(true_icc, 4),
        "mean_estimate": round(mean(estimates), 6),
        "mean_lower_bound": round(mean(lower_bounds), 6),
        "power": round(power, 6),
    }


def run_power(config: PowerConfig) -> dict[str, object]:
    scenarios = [0.65, 0.70, 0.75, 0.80]
    results = [simulate_power(value, config) for value in scenarios]
    target = next(result for result in results if result["true_icc"] == 0.75)
    decision = "PASS" if target["power"] >= 0.80 else "REVIEW"
    return {
        "protocol": "ANIMUS-SIM-v1",
        "analysis": "two_occasion_icc_2_1_normal_approximation",
        "config": {
            "n_participants": config.n_participants,
            "n_simulations": config.n_simulations,
            "seed": config.seed,
            "lower_bound_target": config.lower_bound_target,
            "alpha": config.alpha,
        },
        "scenarios": results,
        "decision": f"PRM_STAGE0_POWER_{decision}",
        "note": (
            "Planning approximation only. The registered analysis will use the actual ICC "
            "confidence-interval method and the observed variance components."
        ),
    }


def check_power() -> dict[str, object]:
    report = run_power(PowerConfig(n_participants=180, n_simulations=1000, seed=7))
    if report["decision"] != "PRM_STAGE0_POWER_PASS":
        raise AssertionError(f"power gate failed: {report['scenarios']}")
    return report


__all__ = [
    "PowerConfig",
    "approximate_lower_bound",
    "check_power",
    "icc_2_1",
    "run_power",
    "simulate_power",
]
