"""Hierarchical recovery screening for CRT Stage 0F.

This is deliberately narrower than the registered full hierarchical SBC. It asks whether a
group-level prediction-precision mean is recoverable when participant-level ``pi`` varies, using the
existing conditional readout fit. It is a screening check and must not be reported as full SBC.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean, stdev

from app.research.crt.recovery import _fit_pi, _simulate

_Z_975 = 1.959963984540054


@dataclass(frozen=True)
class HierarchicalScreenConfig:
    n_participants: int = 24
    n_trials: int = 120
    n_replicates: int = 60
    seed: int = 20261030
    mu_mean: float = 1.20
    mu_sd: float = 0.20
    sigma_mean: float = 0.20
    sigma_sd: float = 0.10
    pi_min: float = 0.40
    pi_max: float = 2.00
    coverage_min: float = 0.90
    coverage_max: float = 0.99
    max_rmse: float = 0.25

    def __post_init__(self) -> None:
        if self.n_participants < 4:
            raise ValueError("n_participants must be at least 4")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.n_replicates <= 0:
            raise ValueError("n_replicates must be positive")
        if self.mu_sd <= 0 or self.sigma_mean <= 0 or self.sigma_sd <= 0:
            raise ValueError("hierarchical scales must be positive")
        if not 0.0 < self.pi_min < self.pi_max:
            raise ValueError("pi bounds must be positive and ordered")


def _draw_pi(rng: random.Random, config: HierarchicalScreenConfig, mu: float, sigma: float) -> float:
    value = rng.gauss(mu, sigma)
    return min(config.pi_max, max(config.pi_min, value))


def _fit_group(
    rng: random.Random,
    config: HierarchicalScreenConfig,
    mu: float,
    sigma: float,
) -> tuple[float, float, list[float]]:
    estimates: list[float] = []
    for index in range(config.n_participants):
        true_pi = _draw_pi(rng, config, mu, sigma)
        participant = _simulate(
            seed=config.seed + 1000 * index + int(true_pi * 1000),
            pi=true_pi,
            n_trials=config.n_trials,
        )
        estimates.append(_fit_pi(participant))
    return mean(estimates), stdev(estimates), estimates


def run_hierarchical_screen(config: HierarchicalScreenConfig | None = None) -> dict[str, object]:
    config = config or HierarchicalScreenConfig()
    rng = random.Random(config.seed)
    estimates: list[float] = []
    truths: list[float] = []
    coverage = 0
    for replicate in range(config.n_replicates):
        mu = rng.gauss(config.mu_mean, config.mu_sd)
        sigma = abs(rng.gauss(config.sigma_mean, config.sigma_sd))
        sigma = max(0.05, sigma)
        mu_hat, sigma_hat, participant_estimates = _fit_group(
            rng,
            config,
            mu,
            sigma,
        )
        truth = mu
        standard_error = max(1e-9, sigma_hat / math.sqrt(config.n_participants))
        low = mu_hat - _Z_975 * standard_error
        high = mu_hat + _Z_975 * standard_error
        if low <= truth <= high:
            coverage += 1
        truths.append(truth)
        estimates.append(mu_hat)

    bias = mean(estimate - truth for estimate, truth in zip(estimates, truths, strict=True))
    rmse = math.sqrt(mean((estimate - truth) ** 2 for estimate, truth in zip(estimates, truths, strict=True)))
    observed_coverage = coverage / config.n_replicates
    passed = (
        config.coverage_min <= observed_coverage <= config.coverage_max
        and rmse <= config.max_rmse
    )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_hierarchical_recovery_screening",
        "status": "screening_only_not_full_sbc",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "n_replicates": config.n_replicates,
            "seed": config.seed,
            "mu_mean": config.mu_mean,
            "mu_sd": config.mu_sd,
            "sigma_mean": config.sigma_mean,
            "sigma_sd": config.sigma_sd,
            "pi_bounds": [config.pi_min, config.pi_max],
        },
        "group_mean_recovery": {
            "bias": round(bias, 6),
            "rmse": round(rmse, 6),
            "coverage": round(observed_coverage, 6),
            "target_coverage": [config.coverage_min, config.coverage_max],
            "mean_estimate": round(mean(estimates), 6),
            "mean_truth": round(mean(truths), 6),
        },
        "decision": (
            "CRT_STAGE0F_HIERARCHICAL_SCREENING_PASS"
            if passed
            else "CRT_STAGE0F_HIERARCHICAL_SCREENING_REVIEW"
        ),
        "note": (
            "Conditional group-mean screening with the existing per-participant readout fit. It does "
            "not sample a joint hierarchical posterior, does not recover M3/M4, and does not replace "
            "the full hierarchical SBC required before human registration."
        ),
    }


__all__ = ["HierarchicalScreenConfig", "run_hierarchical_screen"]
