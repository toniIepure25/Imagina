"""Standalone hierarchical SBC and model recovery for the CRT distortion endpoint.

Scope: the Stage 1D paired false-seen contrast (dual minus single, and dual-nondiagnostic
minus single). The model is a hierarchical normal model with participant-level differences and
known binomial standard errors. It is deliberately standalone (NumPy/SciPy only) so it can be run
without the backend runtime.

This is a full hierarchical model for the endpoint, not a trial-level reimplementation of the CRT
source-monitoring generative model. That distinction is recorded in every artifact.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

SBC_BINS = 10
SBC_CRITICAL = 21.666
MODELS = ("M0", "M2", "M3", "M4")


@dataclass(frozen=True)
class EndpointConfig:
    n_participants: int = 160
    n_sbc: int = 1000
    n_posterior_draws: int = 200
    n_recovery: int = 100
    seed: int = 20261030
    mu_sd: float = 0.05
    tau_scale: float = 0.04
    min_se: float = 0.015
    max_se: float = 0.060
    recovery_threshold: float = 0.85
    coverage_low: float = 0.93
    coverage_high: float = 0.97

    def __post_init__(self) -> None:
        if self.n_participants < 10:
            raise ValueError("n_participants must be at least 10")
        if self.n_sbc <= 0 or self.n_posterior_draws < 20 or self.n_recovery <= 0:
            raise ValueError("simulation counts must be positive")
        if not 0 < self.min_se < self.max_se:
            raise ValueError("standard-error bounds must be positive and ordered")


def _log_prior_mu(mu: float, sd: float) -> float:
    return float(norm.logpdf(mu, loc=0.0, scale=sd))


def _log_prior_tau(tau: float, scale: float) -> float:
    if tau <= 0:
        return -math.inf
    return math.log(2.0 / scale) + float(norm.logpdf(tau, loc=0.0, scale=scale))


def _design(model: str) -> tuple[int, int]:
    mapping = {"M0": (0, 0), "M2": (1, 1), "M3": (1, 0), "M4": (1, 1)}
    return mapping[model]


def _unpack(model: str, x: np.ndarray) -> tuple[float, float, float]:
    free = {"M0": 0, "M2": 1, "M3": 1, "M4": 2}[model]
    mus = [0.0, 0.0]
    if free == 1:
        mus[0] = x[0]
        mus[1] = x[0] if model == "M2" else 0.0
    elif free == 2:
        mus = [x[0], x[1]]
    tau = math.exp(float(x[-1]))
    return mus[0], mus[1], tau


def _log_likelihood(
    model: str,
    x: np.ndarray,
    d: np.ndarray,
    se: np.ndarray,
) -> float:
    mu1, mu2, tau = _unpack(model, x)
    variance = tau * tau + se * se
    residual1 = d[:, 0] - mu1
    residual2 = d[:, 1] - mu2
    variance1 = variance[:, 0]
    variance2 = variance[:, 1]
    return float(
        -0.5 * np.sum(residual1 * residual1 / variance1 + residual2 * residual2 / variance2)
        - 0.5 * np.sum(np.log(2.0 * math.pi * variance1) + np.log(2.0 * math.pi * variance2))
    )


def _log_posterior(model: str, x: np.ndarray, d: np.ndarray, se: np.ndarray, config: EndpointConfig) -> float:
    free = {"M0": 0, "M2": 1, "M3": 1, "M4": 2}[model]
    total = _log_likelihood(model, x, d, se)
    for index in range(free):
        total += _log_prior_mu(float(x[index]), config.mu_sd)
    tau = math.exp(float(x[-1]))
    total += _log_prior_tau(tau, config.tau_scale) + float(x[-1])
    return total


def _initial(model: str) -> np.ndarray:
    free = {"M0": 0, "M2": 1, "M3": 1, "M4": 2}[model]
    return np.concatenate([np.zeros(free), np.array([math.log(0.04)])])


def _fit(model: str, d: np.ndarray, se: np.ndarray, config: EndpointConfig) -> dict[str, object]:
    free = {"M0": 0, "M2": 1, "M3": 1, "M4": 2}[model]
    bounds = [(-0.35, 0.35)] * free + [(-6.0, -1.0)]
    result = minimize(
        lambda x: -_log_posterior(model, x, d, se, config),
        _initial(model),
        method="L-BFGS-B",
        bounds=bounds,
    )
    x = np.asarray(result.x, dtype=float)
    dimension = len(x)
    hessian = np.zeros((dimension, dimension))
    step = 1e-4
    base = _log_posterior(model, x, d, se, config)
    for i in range(dimension):
        for j in range(dimension):
            delta_i = np.zeros(dimension)
            delta_j = np.zeros(dimension)
            delta_i[i] = step
            delta_j[j] = step
            hessian[i, j] = (
                _log_posterior(model, x + delta_i + delta_j, d, se, config)
                - _log_posterior(model, x + delta_i - delta_j, d, se, config)
                - _log_posterior(model, x - delta_i + delta_j, d, se, config)
                + _log_posterior(model, x - delta_i - delta_j, d, se, config)
            ) / (4.0 * step * step)
    hessian = -0.5 * (hessian + hessian.T)
    eigenvalues = np.linalg.eigvalsh(hessian)
    jitter = max(0.0, 1e-6 - float(eigenvalues.min()))
    hessian = hessian + jitter * np.eye(dimension)
    sign, logdet = np.linalg.slogdet(hessian)
    if sign <= 0 or not np.isfinite(logdet):
        covariance = np.eye(dimension) * 1e-4
        log_evidence = -math.inf
    else:
        covariance = np.linalg.inv(hessian)
        log_evidence = base + 0.5 * dimension * math.log(2.0 * math.pi) - 0.5 * logdet
    return {
        "model": model,
        "x": x,
        "covariance": covariance,
        "log_evidence": float(log_evidence),
        "converged": bool(result.success),
    }


def _draw_posterior(fit: dict[str, object], n_draws: int, rng: np.random.Generator) -> np.ndarray:
    x = np.asarray(fit["x"], dtype=float)
    covariance = np.asarray(fit["covariance"], dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.clip(eigenvalues, 1e-10, None)
    root = eigenvectors @ np.diag(np.sqrt(eigenvalues))
    return x + rng.normal(size=(n_draws, len(x))) @ root.T


def _generate(
    model: str,
    rng: np.random.Generator,
    config: EndpointConfig,
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, float]]:
    mu1 = float(rng.normal(0.0, config.mu_sd))
    mu2 = float(rng.normal(0.0, config.mu_sd))
    tau = abs(float(rng.normal(0.0, config.tau_scale)))
    if model == "M0":
        mu1 = mu2 = 0.0
    elif model == "M2":
        mu1 = mu2 = float(rng.normal(0.0, config.mu_sd))
    elif model == "M3":
        mu2 = 0.0
    se = rng.uniform(config.min_se, config.max_se, size=(config.n_participants, 2))
    d = np.column_stack(
        [
            rng.normal(mu1, np.sqrt(tau * tau + se[:, 0] ** 2)),
            rng.normal(mu2, np.sqrt(tau * tau + se[:, 1] ** 2)),
        ]
    )
    return d, se, (mu1, mu2, tau)


def _rank_draws(
    fit: dict[str, object], truth: tuple[float, float], rng: np.random.Generator, n_draws: int
) -> tuple[float, float]:
    draws = _draw_posterior(fit, n_draws, rng)
    free = {"M0": 0, "M2": 1, "M3": 1, "M4": 2}[str(fit["model"])]
    mu1_draws = draws[:, 0] if free >= 1 else np.zeros(len(draws))
    if free == 2:
        mu2_draws = draws[:, 1]
    elif free == 1 and str(fit["model"]) == "M2":
        mu2_draws = draws[:, 0]
    else:
        mu2_draws = np.zeros(len(draws))
    rank1 = float(np.mean(mu1_draws < truth[0]) + rng.random() * np.mean(mu1_draws == truth[0]))
    rank2 = float(np.mean(mu2_draws < truth[1]) + rng.random() * np.mean(mu2_draws == truth[1]))
    return rank1, rank2


def run_sbc(config: EndpointConfig | None = None) -> dict[str, object]:
    config = config or EndpointConfig()
    rng = np.random.default_rng(config.seed)
    ranks: list[float] = []
    ranks_second: list[float] = []
    coverage = 0
    coverage_second = 0
    for _ in range(config.n_sbc):
        d, se, true_params = _generate("M4", rng, config)
        truth = (true_params[0], true_params[1])
        fit = _fit("M4", d, se, config)
        rank1, rank2 = _rank_draws(fit, truth, rng, config.n_posterior_draws)
        ranks.append(rank1)
        ranks_second.append(rank2)
        draws = _draw_posterior(fit, config.n_posterior_draws, rng)
        low, high = np.quantile(draws[:, 0], [0.025, 0.975])
        if low <= truth[0] <= high:
            coverage += 1
        low2, high2 = np.quantile(draws[:, 1], [0.025, 0.975])
        if low2 <= truth[1] <= high2:
            coverage_second += 1
    counts = [0] * SBC_BINS
    counts_second = [0] * SBC_BINS
    for value in ranks:
        counts[min(SBC_BINS - 1, max(0, int(value * SBC_BINS)))] += 1
    for value in ranks_second:
        counts_second[min(SBC_BINS - 1, max(0, int(value * SBC_BINS)))] += 1
    expected = len(ranks) / SBC_BINS
    chi_square = sum((count - expected) ** 2 / expected for count in counts)
    chi_square_second = sum((count - expected) ** 2 / expected for count in counts_second)
    mean_rank = mean(ranks)
    mean_rank_second = mean(ranks_second)
    coverage_rate = coverage / config.n_sbc
    coverage_second_rate = coverage_second / config.n_sbc
    rank_ok = (
        chi_square <= SBC_CRITICAL
        and chi_square_second <= SBC_CRITICAL
        and 0.45 <= mean_rank <= 0.55
        and 0.45 <= mean_rank_second <= 0.55
    )
    coverage_ok = config.coverage_low <= coverage_rate <= config.coverage_high and (
        config.coverage_low <= coverage_second_rate <= config.coverage_high
    )
    return {
        "n_simulations": config.n_sbc,
        "histogram": counts,
        "histogram_second": counts_second,
        "mean_rank": round(mean_rank, 6),
        "mean_rank_second": round(mean_rank_second, 6),
        "chi_square": round(chi_square, 6),
        "chi_square_second": round(chi_square_second, 6),
        "chi_square_critical": SBC_CRITICAL,
        "coverage": round(coverage_rate, 6),
        "coverage_second": round(coverage_second_rate, 6),
        "coverage_target": [config.coverage_low, config.coverage_high],
        "passed": rank_ok and coverage_ok,
    }


def run_model_recovery(config: EndpointConfig | None = None) -> dict[str, object]:
    config = config or EndpointConfig()
    rng = np.random.default_rng(config.seed + 1000)
    confusion = {truth: {guess: 0 for guess in MODELS} for truth in MODELS}
    for truth_model in MODELS:
        for _ in range(config.n_recovery):
            d, se, _ = _generate(truth_model, rng, config)
            fits = [_fit(model, d, se, config) for model in MODELS]
            guess = max(fits, key=lambda fit: float(fit["log_evidence"]))["model"]
            confusion[truth_model][str(guess)] += 1
    correct = sum(confusion[model][model] for model in MODELS)
    total = sum(sum(row.values()) for row in confusion.values())
    balanced = mean(
        confusion[model][model] / max(1, sum(confusion[model].values())) for model in MODELS
    )
    return {
        "n_per_model": config.n_recovery,
        "models": list(MODELS),
        "confusion": confusion,
        "accuracy": round(correct / total, 6),
        "balanced_accuracy": round(balanced, 6),
        "threshold": config.recovery_threshold,
        "passed": balanced >= config.recovery_threshold,
    }


def run_all(config: EndpointConfig | None = None) -> dict[str, object]:
    config = config or EndpointConfig()
    sbc = run_sbc(config)
    recovery = run_model_recovery(config)
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_hierarchical_endpoint_sbc_and_model_recovery",
        "scope": "stage1d_paired_false_seen_endpoint_not_trial_level_crt",
        "config": {
            "n_participants": config.n_participants,
            "n_sbc": config.n_sbc,
            "n_posterior_draws": config.n_posterior_draws,
            "n_recovery": config.n_recovery,
            "seed": config.seed,
            "mu_sd": config.mu_sd,
            "tau_scale": config.tau_scale,
            "recovery_threshold": config.recovery_threshold,
        },
        "sbc": sbc,
        "model_recovery": recovery,
        "decision": (
            "CRT_STAGE0F_HIERARCHICAL_ENDPOINT_PASS"
            if sbc["passed"] and recovery["passed"]
            else "CRT_STAGE0F_HIERARCHICAL_ENDPOINT_REVIEW"
        ),
        "note": (
            "Full hierarchical Bayes for the Stage 1D paired false-seen endpoint (participant-level "
            "differences, group means, between-person SD, known binomial SEs). It is not a trial-level "
            "CRT source-monitoring model and does not authorize human collection."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/crt/CRT_STAGE0F_HIERARCHICAL_SBC.json"))
    parser.add_argument("--recovery-out", type=Path, default=Path("results/crt/CRT_STAGE0F_MODEL_RECOVERY.json"))
    parser.add_argument("--n-sbc", type=int, default=1000)
    parser.add_argument("--n-recovery", type=int, default=100)
    args = parser.parse_args()
    report = run_all(EndpointConfig(n_sbc=args.n_sbc, n_recovery=args.n_recovery))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    recovery = {
        "protocol": report["protocol"],
        "analysis": "stage0f_hierarchical_endpoint_model_recovery",
        "scope": report["scope"],
        "config": report["config"],
        "model_recovery": report["model_recovery"],
        "decision": (
            "CRT_STAGE0F_MODEL_RECOVERY_PASS"
            if report["model_recovery"]["passed"]
            else "CRT_STAGE0F_MODEL_RECOVERY_REVIEW"
        ),
        "note": report["note"],
    }
    args.recovery_out.write_text(json.dumps(recovery, indent=2) + "\n", encoding="utf-8")
    print(report["decision"], report["sbc"]["passed"], report["model_recovery"]["balanced_accuracy"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
