"""Full joint latent-source model for CRT Stage 0H.

This module models the observed test, prediction, outcome, source report, and confidence jointly.
The true source is latent and is marginalized over four states using the participant's sequential
source belief. Test choice is observed; the policy that generated it is not part of this likelihood
and is compared separately out of sample.

Scope: full_joint_source_monitoring_latent_state_not_policy_pomdp. This is a publication-oriented
likelihood, but it is not the final CRT policy POMDP.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp
from scipy.stats import norm

from .trial_model import MissingModelInputError, TrialData

FULL_MODELS: tuple[str, ...] = ("M0", "M2", "M4", "M6", "M7")
FULL_ACTIVE: Mapping[str, tuple[str, ...]] = {
    "M0": (),
    "M2": ("delta_b",),
    "M4": ("delta_b", "delta_dual"),
    "M6": ("gamma_v",),
    "M7": ("gamma_c",),
}
GROUP_NAMES: tuple[str, ...] = (
    "alpha_d",
    "alpha_pi",
    "alpha_b",
    "gamma_v",
    "gamma_c",
    "delta_b",
    "delta_dual",
)
SIGMA_NAMES: tuple[str, ...] = ("sigma_d", "sigma_pi", "sigma_b")
SCOPE = "full_joint_source_monitoring_latent_state_not_policy_pomdp"

TEST_LIKELIHOODS = np.array(
    [
        [0.80, 0.40, 0.25, 0.20],
        [0.30, 0.75, 0.55, 0.20],
        [0.70, 0.65, 0.60, 0.20],
        [0.20, 0.70, 0.25, 0.20],
        [0.25, 0.50, 0.80, 0.20],
        [0.55, 0.55, 0.55, 0.55],
    ],
    dtype=float,
)


@dataclass(frozen=True)
class FullModelConfig:
    n_participants: int = 16
    n_trials: int = 80
    n_sbc: int = 40
    n_posterior_draws: int = 100
    n_recovery: int = 2
    seed: int = 20261031
    max_iter: int = 300
    coverage_low: float = 0.90
    coverage_high: float = 0.99
    recovery_threshold: float = 0.85
    laplace: bool = True

    def __post_init__(self) -> None:
        if self.n_participants < 6:
            raise ValueError("n_participants must be at least 6")
        if self.n_trials < 20:
            raise ValueError("n_trials must be at least 20")
        if self.n_sbc <= 0 or self.n_recovery <= 0:
            raise ValueError("simulation counts must be positive")
        if self.laplace and self.n_posterior_draws < 20:
            raise ValueError("n_posterior_draws must be at least 20 when laplace=True")
        if not 0 < self.coverage_low < self.coverage_high < 1:
            raise ValueError("coverage bounds must be ordered in (0, 1)")


@dataclass(frozen=True)
class FullFit:
    model: str
    group: dict[str, float]
    posterior_draws: np.ndarray
    log_likelihood: float
    bic: float
    converged: bool
    n_parameters: int

    def draw(self, name: str) -> np.ndarray:
        return self.posterior_draws[:, GROUP_NAMES.index(name)]


def _validate_data(data: TrialData) -> None:
    for field in ("test_id", "source_report", "vividness", "prediction_confidence"):
        if getattr(data, field) is None:
            raise MissingModelInputError(f"full model requires trial-level {field!r}")
    if data.source_confidence is None:
        raise MissingModelInputError("full model requires trial-level 'source_confidence'")


def _unpack(model: str, x: np.ndarray, n_participants: int) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    group = dict(zip(GROUP_NAMES, x[: len(GROUP_NAMES)]))
    free = set(FULL_ACTIVE[model])
    for name in ("delta_b", "delta_dual", "gamma_v", "gamma_c"):
        if name not in free:
            group[name] = 0.0
    sigma = np.exp(x[len(GROUP_NAMES) : len(GROUP_NAMES) + len(SIGMA_NAMES)])
    effects = x[len(GROUP_NAMES) + len(SIGMA_NAMES) :].reshape(n_participants, len(SIGMA_NAMES))
    return group, sigma, effects


def _prediction_probability_from_q(q: np.ndarray, pi: np.ndarray) -> np.ndarray:
    """Prediction probability from marginal outcome probability and precision."""
    clipped = np.clip(q, 1e-8, 1.0 - 1e-8)
    return np.clip(expit(pi * np.log(clipped / (1.0 - clipped))), 1e-8, 1.0 - 1e-8)


def source_beliefs(
    data: TrialData,
    group: Mapping[str, float],
    effects: np.ndarray,
) -> np.ndarray:
    """Return the participant's source posterior at the start of every trial.

    The model is sequential within participant and trial order. The initial prior is uniform over
    the four sources. After each outcome, the belief is updated from that outcome only; the
    prediction is a readout and never enters the source likelihood. If ``data.source_belief`` is
    supplied, it is treated as an externally computed version of the same quantity.
    """
    idx = data.participant.astype(int)
    if data.source_belief is not None:
        return np.asarray(data.source_belief, dtype=float)
    if data.test_id is None or data.outcome is None:
        raise MissingModelInputError("source belief reconstruction requires test_id and outcome")

    d = group["alpha_d"] + effects[idx, 0]
    test = data.test_id.astype(int)
    outcome = data.outcome.astype(float)
    base = np.clip(TEST_LIKELIHOODS[test], 1e-6, 1.0 - 1e-6)
    beliefs = np.full((len(idx), 4), 0.25, dtype=float)
    for participant in range(int(idx.max()) + 1 if len(idx) else 0):
        trials = np.flatnonzero(idx == participant)
        belief = np.full(4, 0.25, dtype=float)
        for trial in trials:
            beliefs[trial] = belief
            likelihood = expit(float(d[trial]) * np.log(base[trial] / (1.0 - base[trial])))
            likelihood = likelihood if outcome[trial] == 1.0 else 1.0 - likelihood
            posterior = belief * likelihood
            total = float(posterior.sum())
            belief = posterior / total if total > 0.0 else np.full(4, 0.25, dtype=float)
    return beliefs


def prediction_probability(
    data: TrialData,
    group: Mapping[str, float],
    effects: np.ndarray,
) -> np.ndarray:
    """Model-implied prediction probability, with ``alpha_pi`` counted exactly once.

    The readout is the belief-weighted posterior predictive ``sum_s m_i(s) * p_as``, not an
    unweighted average over latent sources.
    """
    idx = data.participant.astype(int)
    test = data.test_id.astype(int)
    pi = group["alpha_pi"] + effects[idx, 1]
    base = np.clip(TEST_LIKELIHOODS[test], 1e-6, 1.0 - 1e-6)
    beliefs = source_beliefs(data, group, effects)
    q = np.clip(np.sum(beliefs * base, axis=1), 1e-8, 1.0 - 1e-8)
    return _prediction_probability_from_q(q, pi)


def _trial_likelihood(
    data: TrialData,
    group: Mapping[str, float],
    effects: np.ndarray,
) -> np.ndarray:
    idx = data.participant.astype(int)
    report = data.source_report.astype(int)
    test = data.test_id.astype(int)
    outcome = data.outcome.astype(float)
    prediction = data.prediction.astype(float)
    vividness = data.vividness.astype(float)
    prediction_confidence = data.prediction_confidence.astype(float)
    source_confidence = data.source_confidence.astype(float)
    n = len(idx)
    rows = np.arange(n)

    d = group["alpha_d"] + effects[idx, 0]
    b = group["alpha_b"] + effects[idx, 2]

    base = np.clip(TEST_LIKELIHOODS[test], 1e-6, 1.0 - 1e-6)
    outcome_prob = expit(d[:, None] * np.log(base / (1.0 - base)))
    outcome_prob = np.clip(outcome_prob, 1e-8, 1.0 - 1e-8)
    belief = np.clip(source_beliefs(data, group, effects), 1e-12, None)
    pi = group["alpha_pi"] + effects[idx, 1]
    q = np.clip(np.sum(belief * base, axis=1), 1e-8, 1.0 - 1e-8)
    p_pred = _prediction_probability_from_q(q, pi)
    pred_lik = np.where(prediction == 1.0, p_pred, 1.0 - p_pred)

    outcome_lik = np.where(outcome[:, None] == 1.0, outcome_prob, 1.0 - outcome_prob)
    log_joint = np.empty((n, 4), dtype=float)
    for latent_source in range(4):
        report_logits = np.empty((n, 4), dtype=float)
        for candidate in range(4):
            is_latent = candidate == latent_source
            report_logits[:, candidate] = (
                d * is_latent
                + b * (candidate == 0)
                + group["gamma_v"] * (vividness - 0.5) * is_latent
                + group["gamma_c"] * (prediction_confidence - 0.5) * is_latent
                + group["delta_b"] * data.predict * (candidate == 0)
                + group["delta_dual"] * data.dual * (candidate == 0)
            )
        log_report = report_logits - logsumexp(report_logits, axis=1, keepdims=True)
        report_lik = np.exp(log_report[rows, report])
        confidence_mean = 0.5 + 0.25 * (report == latent_source) + 0.10 * (vividness - 0.5)
        confidence_lik = np.clip(norm.pdf(source_confidence, loc=confidence_mean, scale=0.15), 1e-12, None)
        log_joint[:, latent_source] = (
            np.log(belief[:, latent_source])
            + np.log(np.clip(outcome_lik[:, latent_source], 1e-12, None))
            + np.log(np.clip(report_lik, 1e-12, None))
            + np.log(confidence_lik)
        )
    marginal = np.exp(logsumexp(log_joint, axis=1)) * pred_lik
    return np.clip(marginal, 1e-12, None)


def _log_likelihood(data: TrialData, group: Mapping[str, float], effects: np.ndarray) -> float:
    likelihood = _trial_likelihood(data, group, effects)
    return float(np.log(np.clip(likelihood, 1e-12, None)).sum())


def _log_prior(model: str, group: Mapping[str, float], sigma: np.ndarray, effects: np.ndarray) -> float:
    total = 0.0
    for name in GROUP_NAMES:
        if name.startswith(("delta_", "gamma_")):
            total += float(norm.logpdf(group[name], loc=0.0, scale=0.5))
        else:
            total += float(norm.logpdf(group[name], loc=0.0, scale=1.0))
    for value in sigma:
        total += float(norm.logpdf(math.log(value), loc=math.log(0.5), scale=0.5))
    for column, value in enumerate(sigma):
        total += float(norm.logpdf(effects[:, column], loc=0.0, scale=value).sum())
    return total


def _objective(model: str, data: TrialData, x: np.ndarray, n_participants: int) -> float:
    group, sigma, effects = _unpack(model, x, n_participants)
    return -(_log_likelihood(data, group, effects) + _log_prior(model, group, sigma, effects))


def _numerical_hessian(model: str, data: TrialData, x: np.ndarray, n_participants: int) -> np.ndarray:
    dimension = len(x)
    hessian = np.zeros((dimension, dimension))
    base = np.asarray(x, dtype=float)
    for column in range(dimension):
        step = 1e-4 * max(1.0, abs(base[column]))
        plus = base.copy()
        minus = base.copy()
        plus[column] += step
        minus[column] -= step
        hessian[:, column] = (
            _numerical_gradient(model, data, plus, n_participants)
            - _numerical_gradient(model, data, minus, n_participants)
        ) / (2.0 * step)
    return (hessian + hessian.T) / 2.0


def _numerical_gradient(model: str, data: TrialData, x: np.ndarray, n_participants: int) -> np.ndarray:
    base = np.asarray(x, dtype=float)
    gradient = np.zeros_like(base)
    for index in range(len(base)):
        step = 1e-5 * max(1.0, abs(base[index]))
        plus = base.copy()
        minus = base.copy()
        plus[index] += step
        minus[index] -= step
        gradient[index] = (
            _objective(model, data, plus, n_participants) - _objective(model, data, minus, n_participants)
        ) / (2.0 * step)
    return gradient


def fit_full_model(data: TrialData, model: str = "M0", config: FullModelConfig | None = None) -> FullFit:
    if model not in FULL_MODELS:
        raise ValueError(f"unknown full model {model!r}")
    _validate_data(data)
    cfg = config or FullModelConfig()
    n_participants = data.n_participants
    group = {name: 0.0 for name in GROUP_NAMES}
    log_sigma = np.full(len(SIGMA_NAMES), math.log(0.5))
    effects = np.zeros((n_participants, len(SIGMA_NAMES)))
    x0 = np.concatenate(
        [
            np.array([group[name] for name in GROUP_NAMES], dtype=float),
            log_sigma,
            effects.ravel(),
        ]
    )
    result = minimize(
        lambda x: _objective(model, data, x, n_participants),
        x0,
        method="L-BFGS-B",
        options={"maxiter": cfg.max_iter, "ftol": 1e-8},
    )
    map_params = np.asarray(result.x, dtype=float)
    group_map, sigma_map, effects_map = _unpack(model, map_params, n_participants)
    log_likelihood = _log_likelihood(data, group_map, effects_map)
    n_parameters = len(GROUP_NAMES) + len(SIGMA_NAMES) + len(SIGMA_NAMES) * n_participants
    bic = -2.0 * log_likelihood + n_parameters * math.log(len(data.participant))
    if not cfg.laplace:
        return FullFit(
            model=model,
            group=group_map,
            posterior_draws=np.empty((0, len(GROUP_NAMES))),
            log_likelihood=log_likelihood,
            bic=float(bic),
            converged=bool(result.success),
            n_parameters=n_parameters,
        )
    hessian = _numerical_hessian(model, data, map_params, n_participants)
    covariance = np.linalg.pinv((hessian + hessian.T) / 2.0 + np.eye(len(hessian)) * 1e-6)
    group_covariance = covariance[: len(GROUP_NAMES), : len(GROUP_NAMES)]
    group_covariance = _nearest_positive_semidefinite(group_covariance)
    rng = np.random.default_rng(cfg.seed + 31)
    draws = rng.multivariate_normal(
        map_params[: len(GROUP_NAMES)], group_covariance, size=cfg.n_posterior_draws
    )
    free = set(FULL_ACTIVE[model])
    for name in ("delta_b", "delta_dual", "gamma_v", "gamma_c"):
        if name not in free:
            draws[:, GROUP_NAMES.index(name)] = 0.0
    return FullFit(
        model=model,
        group=group_map,
        posterior_draws=draws,
        log_likelihood=log_likelihood,
        bic=float(bic),
        converged=bool(result.success),
        n_parameters=n_parameters,
    )


def _draw_group(rng: np.random.Generator, model: str, effect_scale: float, min_abs_effect: float) -> dict[str, float]:
    active = set(FULL_ACTIVE[model])
    for _ in range(1000):
        group = {
            name: float(rng.normal(0.0, effect_scale if name in active else 1.0))
            for name in GROUP_NAMES
        }
        group["alpha_d"] = float(abs(rng.normal(1.0, 0.5)))
        group["alpha_pi"] = float(abs(rng.normal(1.0, 0.5)))
        group["alpha_b"] = float(rng.normal(0.2, 0.5))
        for name in ("delta_b", "delta_dual", "gamma_v", "gamma_c"):
            if name not in active:
                group[name] = 0.0
        if not active or all(abs(group[name]) >= min_abs_effect for name in active):
            return group
    raise RuntimeError("could not draw an effect-conditioned full-model parameter set")


def simulate_full_data(
    model: str = "M0",
    n_participants: int = 16,
    n_trials: int = 80,
    seed: int = 20261031,
    effect_scale: float = 0.8,
    min_abs_effect: float = 0.25,
    predict_probability: float = 0.5,
    dual_probability: float = 0.5,
    vividness_spread: float = 0.0,
    confidence_spread: float = 0.0,
) -> tuple[TrialData, dict[str, float]]:
    if model not in FULL_MODELS:
        raise ValueError(f"unknown full model {model!r}")
    if not 0 <= predict_probability <= 1 or not 0 <= dual_probability <= 1:
        raise ValueError("predict_probability and dual_probability must be in [0, 1]")
    if vividness_spread < 0 or confidence_spread < 0:
        raise ValueError("vividness_spread and confidence_spread must be non-negative")
    rng = np.random.default_rng(seed)
    group = _draw_group(rng, model, effect_scale, min_abs_effect)
    idx = np.repeat(np.arange(n_participants), n_trials)
    source = rng.integers(0, 4, size=len(idx))
    test = rng.integers(0, 6, size=len(idx))
    predict = rng.binomial(1, predict_probability, size=len(idx)).astype(float)
    dual = rng.binomial(1, dual_probability, size=len(idx)).astype(float)
    vividness = np.clip(
        0.5 + rng.normal(0.0, 0.18 + 0.5 * vividness_spread, size=len(idx)), 0.01, 0.99
    )
    prediction_confidence = np.clip(
        0.5 + rng.normal(0.0, 0.18 + 0.5 * confidence_spread, size=len(idx)), 0.01, 0.99
    )

    effects = rng.normal(0.0, np.exp([math.log(0.5)] * len(SIGMA_NAMES)), size=(n_participants, len(SIGMA_NAMES)))
    d = group["alpha_d"] + effects[idx, 0]
    pi = group["alpha_pi"] + effects[idx, 1]
    b = group["alpha_b"] + effects[idx, 2]

    base = np.clip(TEST_LIKELIHOODS[test], 1e-6, 1.0 - 1e-6)
    prediction = np.zeros(len(idx), dtype=float)
    outcome = np.zeros(len(idx), dtype=float)
    for participant in range(n_participants):
        trials = np.flatnonzero(idx == participant)
        belief = np.full(4, 0.25, dtype=float)
        for trial in trials:
            q = float(np.dot(belief, base[trial]))
            p_pred = _prediction_probability_from_q(
                np.array([q]), np.array([pi[trial]])
            )[0]
            prediction[trial] = float(rng.binomial(1, p_pred))
            source_probability = expit(float(d[trial]) * np.log(base[trial] / (1.0 - base[trial])))
            outcome[trial] = rng.binomial(1, source_probability[source[trial]])
            source_likelihood = (
                source_probability if outcome[trial] == 1.0 else 1.0 - source_probability
            )
            posterior = belief * source_likelihood
            total = float(posterior.sum())
            belief = posterior / total if total > 0.0 else np.full(4, 0.25, dtype=float)

    report_logits = np.empty((len(idx), 4))
    for candidate in range(4):
        report_logits[:, candidate] = (
            d * (candidate == source)
            + b * (candidate == 0)
            + group["gamma_v"] * (vividness - 0.5) * (candidate == source)
            + group["gamma_c"] * (prediction_confidence - 0.5) * (candidate == source)
            + group["delta_b"] * predict * (candidate == 0)
            + group["delta_dual"] * dual * (candidate == 0)
        )
    report_prob = np.exp(report_logits - logsumexp(report_logits, axis=1, keepdims=True))
    report = np.array([rng.choice(4, p=row) for row in report_prob])
    source_confidence = np.clip(
        0.5 + 0.25 * (report == source) + 0.10 * (vividness - 0.5) + rng.normal(0.0, 0.15, size=len(idx)),
        0.01,
        0.99,
    )
    return (
        TrialData(
            participant=idx,
            predict=predict,
            dual=dual,
            diagnosticity=np.clip(base[np.arange(len(idx)), source], 0.0, 1.0),
            imagined=(source == 1).astype(float),
            prediction=prediction,
            outcome=outcome,
            source_correct=(report == source).astype(float),
            vividness=vividness,
            prediction_confidence=prediction_confidence,
            source_confidence=source_confidence,
            test_id=test,
            source=source,
            source_report=report,
        ),
        group,
    )


def _nearest_positive_semidefinite(matrix: np.ndarray) -> np.ndarray:
    symmetric = (matrix + matrix.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    eigenvalues = np.clip(eigenvalues, 1e-8, None)
    return (eigenvectors * eigenvalues) @ eigenvectors.T


def _rank_metrics(ranks: np.ndarray, coverage: np.ndarray) -> dict[str, float]:
    bins = np.linspace(0.0, 1.0, 11)
    counts, _ = np.histogram(ranks, bins=bins)
    expected = len(ranks) / 10.0
    chi_square = float(np.sum((counts - expected) ** 2 / expected)) if expected else float("nan")
    return {
        "mean_rank": float(np.mean(ranks)),
        "coverage": float(np.mean(coverage)),
        "chi_square": chi_square,
        "min_bin": int(counts.min()),
        "max_bin": int(counts.max()),
    }


def run_full_sbc(
    config: FullModelConfig | None = None,
    model: str = "M6",
    analysis_prefix: str = "stage0h",
) -> dict[str, Any]:
    cfg = config or FullModelConfig()
    rng = np.random.default_rng(cfg.seed)
    active = list(FULL_ACTIVE[model])
    targets = active or ["alpha_d"]
    ranks = {name: [] for name in targets}
    coverage = {name: [] for name in targets}
    convergence = 0
    for _ in range(cfg.n_sbc):
        seed = int(rng.integers(0, 2**31 - 1))
        data, truth = simulate_full_data(
            model=model,
            n_participants=cfg.n_participants,
            n_trials=cfg.n_trials,
            seed=seed,
        )
        fit = fit_full_model(data, model=model, config=cfg)
        convergence += int(fit.converged)
        for name in targets:
            draws = fit.draw(name)
            ranks[name].append(float((draws < truth[name]).mean()))
            low, high = np.quantile(draws, [0.025, 0.975])
            coverage[name].append(float(low <= truth[name] <= high))
    metrics = {name: _rank_metrics(np.array(ranks[name]), np.array(coverage[name])) for name in targets}
    passed = all(
        cfg.coverage_low <= metrics[name]["coverage"] <= cfg.coverage_high
        and metrics[name]["chi_square"] <= 21.666
        for name in targets
    )
    return {
        "analysis": f"{analysis_prefix}_full_model_sbc",
        "scope": SCOPE,
        "model": model,
        "target_parameters": targets,
        "config": asdict(cfg),
        "metrics": metrics,
        "convergence_rate": convergence / cfg.n_sbc,
        "decision": (
            f"CRT_{analysis_prefix.upper()}_FULL_MODEL_SBC_PASS"
            if passed
            else f"CRT_{analysis_prefix.upper()}_FULL_MODEL_SBC_REVIEW"
        ),
        "note": (
            "Full joint latent-source model with observed test choice; not the policy POMDP. "
            "Coverage thresholds are screening criteria, not human evidence."
        ),
    }


def run_full_sbc_all(
    config: FullModelConfig | None = None,
    models: Iterable[str] = FULL_MODELS,
) -> dict[str, Any]:
    """Run parameter SBC for every confirmatory model and pool the decision.

    Each model's SBC checks its active coefficients; a PASS requires every model to pass. The
    posterior is the Laplace approximation, so this cannot satisfy a NUTS/NumPyro gate.
    """
    cfg = config or FullModelConfig()
    model_list = tuple(models)
    if not model_list or any(model not in FULL_MODELS for model in model_list):
        raise ValueError("models must be a non-empty subset of FULL_MODELS")
    per_model = {
        model: run_full_sbc(cfg, model=model, analysis_prefix="stage0i")
        for model in model_list
    }
    passed = all(result["decision"].endswith("_PASS") for result in per_model.values())
    return {
        "analysis": "stage0i_full_model_sbc_all",
        "scope": SCOPE,
        "models": list(model_list),
        "config": asdict(cfg),
        "per_model": per_model,
        "convergence_rate": float(np.mean([result["convergence_rate"] for result in per_model.values()])),
        "decision": (
            "CRT_STAGE0I_FULL_MODEL_SBC_PASS"
            if passed
            else "CRT_STAGE0I_FULL_MODEL_SBC_REVIEW"
        ),
        "posterior_backend": "laplace_screening_not_nuts",
        "note": (
            "Laplace parameter SBC for the full latent-source model. It is not NUTS and not human evidence; "
            "the policy POMDP is calibrated separately."
        ),
    }


def run_full_recovery(
    config: FullModelConfig | None = None,
    model_set: Iterable[str] = FULL_MODELS,
    analysis_prefix: str = "stage0h",
) -> dict[str, Any]:
    cfg = config or FullModelConfig()
    models = tuple(model_set)
    if len(models) < 2 or any(model not in FULL_MODELS for model in models):
        raise ValueError("model_set must contain at least two known full models")
    rng = np.random.default_rng(cfg.seed + 101)
    confusion = np.zeros((len(models), len(models)), dtype=int)
    for true_index, true_model in enumerate(models):
        for _ in range(cfg.n_recovery):
            seed = int(rng.integers(0, 2**31 - 1))
            data, _ = simulate_full_data(
                model=true_model,
                n_participants=cfg.n_participants,
                n_trials=cfg.n_trials,
                seed=seed,
            )
            fits = [fit_full_model(data, model=model, config=cfg) for model in models]
            best = int(np.argmin([fit.bic for fit in fits]))
            confusion[true_index, best] += 1
    rows = confusion.sum(axis=1)
    balanced = float(np.mean(np.diag(confusion) / np.maximum(rows, 1)))
    return {
        "analysis": f"{analysis_prefix}_full_model_recovery",
        "scope": SCOPE,
        "models": list(models),
        "selection_status": "pre_specified",
        "config": asdict(cfg),
        "confusion": confusion.tolist(),
        "balanced_accuracy": balanced,
        "decision": (
            f"CRT_{analysis_prefix.upper()}_FULL_MODEL_RECOVERY_PASS"
            if balanced >= cfg.recovery_threshold
            else f"CRT_{analysis_prefix.upper()}_FULL_MODEL_RECOVERY_REVIEW"
        ),
        "note": (
            "BIC-based recovery among pre-specified full joint models. A PASS is simulation evidence "
            "of identifiability, not evidence that humans use any model."
        ),
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def write_artifact(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--sbc", action="store_true")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--model", default="M6", choices=FULL_MODELS)
    parser.add_argument("--out-dir", type=Path, default=Path("results/crt"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.check:
        cfg = FullModelConfig(n_sbc=2, n_recovery=1, n_participants=8, n_trials=30, n_posterior_draws=20, max_iter=100)
        print(json.dumps(_json_ready(run_full_sbc(cfg, args.model)), indent=2))
        return 0
    if args.sbc:
        write_artifact(run_full_sbc(model=args.model), args.out_dir / "CRT_STAGE0H_FULL_MODEL_SBC.json")
        return 0
    if args.recovery:
        write_artifact(
            run_full_recovery(config=FullModelConfig(n_participants=16, n_trials=80, n_recovery=2)),
            args.out_dir / "CRT_STAGE0H_FULL_MODEL_RECOVERY.json",
        )
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
