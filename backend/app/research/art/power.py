"""Simulation-based reliability power check for the ART Stage 1 plan.

The check treats the two-occasion ART efficiency estimate as a continuous score and evaluates the
two-way random-effects ICC(2,1) lower bound. It is a planning approximation, not the registered
analysis.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean

from app.research.prm.power import approximate_lower_bound, icc_2_1


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


def simulate_power(true_icc: float, config: PowerConfig) -> dict[str, float]:
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
        "protocol": "ANIMUS-ART-v1",
        "analysis": "two_occasion_icc_2_1_normal_approximation",
        "config": {
            "n_participants": config.n_participants,
            "n_simulations": config.n_simulations,
            "seed": config.seed,
            "lower_bound_target": config.lower_bound_target,
            "alpha": config.alpha,
        },
        "scenarios": results,
        "decision": f"ART_STAGE0_POWER_{decision}",
        "note": (
            "Planning approximation only. The registered analysis will use the actual ICC "
            "confidence-interval method and the observed variance components."
        ),
    }


def check_power() -> dict[str, object]:
    report = run_power(PowerConfig(n_participants=180, n_simulations=500, seed=7))
    if report["decision"] != "ART_STAGE0_POWER_PASS":
        raise AssertionError(f"ART power gate failed: {report['scenarios']}")
    return report


__all__ = [
    "PowerConfig",
    "check_power",
    "run_power",
    "simulate_power",
]
