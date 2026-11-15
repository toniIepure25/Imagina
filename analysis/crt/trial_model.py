"""Trial-level hierarchical readout model for the CRT prediction/source task.

Scope: this module fits trial-level prediction and source-correctness outcomes with participant-level
random effects and condition effects. It is a *readout* model, not a full reimplementation of the CRT
source-monitoring policy or the meta-EIG test-selection model. The scope string is recorded in every
SBC/recovery artifact.

The implementation is NumPy/SciPy only so it can run without the FastAPI backend or a probabilistic
programming runtime. Posterior draws use a Laplace approximation at the MAP; that approximation is
adequate for SBC screening, not for a final publication-grade posterior.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import norm

MODELS: tuple[str, ...] = ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7")
ACTIVE_DELTAS: Mapping[str, tuple[str, ...]] = {
    "M0": (),
    "M1": ("delta_pi",),
    "M2": ("delta_d",),
    "M3": ("delta_d", "delta_dual_d"),
    "M4": ("delta_d", "delta_b", "delta_dual_b"),
    "M5": ("delta_b",),
    "M6": (),
    "M7": (),
}
ACCOUNT_PARAMS: Mapping[str, tuple[str, ...]] = {
    "M0": (),
    "M1": (),
    "M2": (),
    "M3": (),
    "M4": (),
    "M5": (),
    "M6": ("gamma_v",),
    "M7": ("gamma_c",),
}
CONFIRMATORY_MODELS: tuple[str, ...] = ("M0", "M2", "M4", "M6", "M7")
EXPLORATORY_MODELS: tuple[str, ...] = ("M1", "M3", "M5")
GROUP_NAMES: tuple[str, ...] = (
    "alpha_d",
    "alpha_b",
    "alpha_pi",
    "alpha_a",
    "delta_d",
    "delta_b",
    "delta_pi",
    "delta_dual_d",
    "delta_dual_b",
    "gamma_v",
    "gamma_c",
)
SIGMA_NAMES: tuple[str, ...] = ("sigma_d", "sigma_b", "sigma_pi", "sigma_a")
SCOPE = "trial_level_hierarchical_readout_not_full_crt_pomdp"


class MissingModelInputError(ValueError):
    """Raised when a model requires trial-level covariates that were not supplied."""


def active_parameters(model: str) -> tuple[str, ...]:
    """Return the condition/account effects that are free in ``model``."""
    return (*ACTIVE_DELTAS[model], *ACCOUNT_PARAMS[model])


@dataclass(frozen=True)
class TrialModelConfig:
    n_participants: int = 20
    n_trials: int = 60
    n_sbc: int = 1000
    n_posterior_draws: int = 200
    n_recovery: int = 20
    seed: int = 20261031
    max_iter: int = 1000
    laplace: bool = True
    coverage_low: float = 0.93
    coverage_high: float = 0.97
    recovery_threshold: float = 0.85

    def __post_init__(self) -> None:
        if self.n_participants < 6:
            raise ValueError("n_participants must be at least 6")
        if self.n_trials < 20:
            raise ValueError("n_trials must be at least 20")
        if self.n_sbc <= 0 or self.n_posterior_draws < 20 or self.n_recovery <= 0:
            raise ValueError("simulation counts must be positive")
        if not 0 < self.coverage_low < self.coverage_high < 1:
            raise ValueError("coverage bounds must be ordered in (0, 1)")


@dataclass(frozen=True)
class TrialData:
    participant: np.ndarray
    predict: np.ndarray
    dual: np.ndarray
    diagnosticity: np.ndarray
    imagined: np.ndarray
    prediction: np.ndarray
    outcome: np.ndarray
    source_correct: np.ndarray
    vividness: np.ndarray | None = None
    prediction_confidence: np.ndarray | None = None
    source_confidence: np.ndarray | None = None
    counterfactual_discrepancy: np.ndarray | None = None
    test_id: np.ndarray | None = None
    source: np.ndarray | None = None
    source_report: np.ndarray | None = None
    # Optional pre-computed belief over the four sources at the start of each trial. The full CRT
    # model uses this when supplied; otherwise it reconstructs the belief from observed history.
    source_belief: np.ndarray | None = None

    def __post_init__(self) -> None:
        arrays = (
            self.participant,
            self.predict,
            self.dual,
            self.diagnosticity,
            self.imagined,
            self.prediction,
            self.outcome,
            self.source_correct,
        )
        optional = (
            self.vividness,
            self.prediction_confidence,
            self.source_confidence,
            self.counterfactual_discrepancy,
            self.test_id,
            self.source,
            self.source_report,
            self.source_belief,
        )
        lengths = {len(array) for array in arrays}
        if len(lengths) != 1:
            raise ValueError("all trial arrays must have the same length")
        for array in optional:
            if array is not None and len(array) != len(self.participant):
                raise ValueError("optional trial arrays must match the required trial arrays")
        if self.source_belief is not None:
            belief = np.asarray(self.source_belief, dtype=float)
            if belief.shape != (len(self.participant), 4):
                raise ValueError("source_belief must have shape (n_trials, 4)")
            if np.any(belief < 0) or not np.allclose(belief.sum(axis=1), 1.0, atol=1e-8):
                raise ValueError("source_belief rows must be non-negative and sum to one")
        if np.any(self.diagnosticity < 0) or np.any(self.diagnosticity > 1):
            raise ValueError("diagnosticity must be in [0, 1]")
        for name, array in (
            ("vividness", self.vividness),
            ("prediction_confidence", self.prediction_confidence),
            ("source_confidence", self.source_confidence),
        ):
            if array is not None and (np.any(array < 0) or np.any(array > 1)):
                raise ValueError(f"{name} must be in [0, 1]")
        for name, array, upper in (
            ("source", self.source, 3),
            ("source_report", self.source_report, 3),
            ("test_id", self.test_id, 5),
        ):
            if array is not None and (np.any(array < 0) or np.any(array > upper)):
                raise ValueError(f"{name} must be in [0, {upper}]")

    def require(self, field_name: str, model: str) -> np.ndarray:
        value = getattr(self, field_name)
        if value is None:
            raise MissingModelInputError(f"{model} requires trial-level {field_name!r}")
        return np.asarray(value, dtype=float)

    @property
    def n_participants(self) -> int:
        return int(self.participant.max()) + 1 if len(self.participant) else 0

    @property
    def consistency(self) -> np.ndarray:
        return (self.prediction == self.outcome).astype(float)


@dataclass(frozen=True)
class TrialFit:
    model: str
    map_params: np.ndarray
    posterior_draws: np.ndarray
    log_likelihood: float
    n_parameters: int
    bic: float
    converged: bool

    def draw(self, name: str) -> np.ndarray:
        index = GROUP_NAMES.index(name)
        return self.posterior_draws[:, index]

    def truth_rank(self, name: str, truth: float) -> float:
        draws = self.draw(name)
        return float((draws < truth).mean())


def _prior_logpdf_group(values: Mapping[str, float]) -> float:
    total = 0.0
    for name in GROUP_NAMES:
        value = values[name]
        if name.startswith("delta_"):
            total += float(norm.logpdf(value, loc=0.0, scale=0.5))
        else:
            total += float(norm.logpdf(value, loc=0.0, scale=1.0))
    return total


def _objective_prior_grad_group(name: str, value: float) -> float:
    scale = 0.5 if name.startswith("delta_") else 1.0
    return value / (scale * scale)


def _unpack(
    model: str, x: np.ndarray, n_participants: int
) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    group_values = dict(zip(GROUP_NAMES, x[: len(GROUP_NAMES)]))
    free = set(active_parameters(model))
    for name in GROUP_NAMES:
        if (name.startswith("delta_") or name.startswith("gamma_")) and name not in free:
            group_values[name] = 0.0
    sigma = np.exp(x[len(GROUP_NAMES) : len(GROUP_NAMES) + len(SIGMA_NAMES)])
    effects = x[len(GROUP_NAMES) + len(SIGMA_NAMES) :].reshape(n_participants, len(SIGMA_NAMES))
    return group_values, sigma, effects


def _pack(model: str, group_values: Mapping[str, float], log_sigma: np.ndarray, effects: np.ndarray) -> np.ndarray:
    return np.concatenate(
        [
            np.array([group_values[name] for name in GROUP_NAMES], dtype=float),
            log_sigma,
            effects.ravel(),
        ]
    )


def _trial_arrays(
    model: str,
    data: TrialData,
    group_values: Mapping[str, float],
    sigma: np.ndarray,
    effects: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    idx = data.participant.astype(int)
    x = 2.0 * data.diagnosticity - 1.0
    prediction = data.prediction.astype(float)
    consistency = data.consistency
    imagined = data.imagined.astype(float)

    d = group_values["alpha_d"] + group_values["delta_d"] * data.predict + group_values["delta_dual_d"] * data.dual
    d = d + effects[idx, 0]
    b = group_values["alpha_b"] + group_values["delta_b"] * data.predict + group_values["delta_dual_b"] * data.dual
    b = b + effects[idx, 1]
    pi = group_values["alpha_pi"] + group_values["delta_pi"] * data.predict + effects[idx, 2]
    a = group_values["alpha_a"] + effects[idx, 3]

    eta_pred = a + pi * x
    eta_source = d * x + b * consistency + 0.2 * imagined
    if model in {"M6", "M7"}:
        if model == "M6":
            vividness = data.require("vividness", model)
            eta_source = eta_source + group_values["gamma_v"] * (vividness - 0.5)
        else:
            confidence = data.require("prediction_confidence", model)
            eta_source = eta_source + group_values["gamma_c"] * (confidence - 0.5)
    return eta_pred, eta_source, prediction, data.source_correct.astype(float), x


def _log_likelihood(
    model: str,
    data: TrialData,
    group_values: Mapping[str, float],
    sigma: np.ndarray,
    effects: np.ndarray,
) -> float:
    eta_pred, eta_source, prediction, source_correct, _ = _trial_arrays(
        model, data, group_values, sigma, effects
    )
    p = expit(eta_pred)
    q = expit(eta_source)
    eps = 1e-12
    return float(
        np.sum(prediction * np.log(p + eps) + (1.0 - prediction) * np.log(1.0 - p + eps))
        + np.sum(source_correct * np.log(q + eps) + (1.0 - source_correct) * np.log(1.0 - q + eps))
    )


def _log_prior(model: str, group_values: Mapping[str, float], sigma: np.ndarray, effects: np.ndarray) -> float:
    total = _prior_logpdf_group(group_values)
    for name, value in zip(SIGMA_NAMES, sigma):
        total += float(norm.logpdf(math.log(value), loc=math.log(0.5), scale=0.5))
    for column, value in enumerate(sigma):
        total += float(norm.logpdf(effects[:, column], loc=0.0, scale=value).sum())
    return total


def _objective_and_grad(model: str, data: TrialData, x: np.ndarray, n_participants: int) -> tuple[float, np.ndarray]:
    group_values, sigma, effects = _unpack(model, x, n_participants)
    eta_pred, eta_source, prediction, source_correct, x_trial = _trial_arrays(
        model, data, group_values, sigma, effects
    )
    p = expit(eta_pred)
    q = expit(eta_source)
    eps = 1e-12
    log_likelihood = float(
        np.sum(prediction * np.log(p + eps) + (1.0 - prediction) * np.log(1.0 - p + eps))
        + np.sum(source_correct * np.log(q + eps) + (1.0 - source_correct) * np.log(1.0 - q + eps))
    )
    prior = _log_prior(model, group_values, sigma, effects)
    objective = -(log_likelihood + prior)

    grad_group = np.zeros(len(GROUP_NAMES))
    grad_log_sigma = np.zeros(len(SIGMA_NAMES))
    grad_effects = np.zeros_like(effects)

    g_pred = p - prediction
    g_source = q - source_correct
    grad_group[GROUP_NAMES.index("alpha_a")] = g_pred.sum()
    grad_group[GROUP_NAMES.index("alpha_pi")] = np.sum(g_pred * x_trial)
    grad_group[GROUP_NAMES.index("delta_pi")] = np.sum(g_pred * x_trial * data.predict)
    grad_group[GROUP_NAMES.index("alpha_d")] = np.sum(g_source * x_trial)
    grad_group[GROUP_NAMES.index("delta_d")] = np.sum(g_source * x_trial * data.predict)
    grad_group[GROUP_NAMES.index("delta_dual_d")] = np.sum(g_source * x_trial * data.dual)
    grad_group[GROUP_NAMES.index("alpha_b")] = np.sum(g_source * data.consistency)
    grad_group[GROUP_NAMES.index("delta_b")] = np.sum(g_source * data.consistency * data.predict)
    grad_group[GROUP_NAMES.index("delta_dual_b")] = np.sum(g_source * data.consistency * data.dual)

    if "gamma_v" in active_parameters(model):
        vividness = data.require("vividness", model)
        grad_group[GROUP_NAMES.index("gamma_v")] = np.sum(g_source * (vividness - 0.5))
    if "gamma_c" in active_parameters(model):
        confidence = data.require("prediction_confidence", model)
        grad_group[GROUP_NAMES.index("gamma_c")] = np.sum(g_source * (confidence - 0.5))

    idx = data.participant.astype(int)
    contributions = np.column_stack(
        [
            g_source * x_trial,
            g_source * data.consistency,
            g_pred * x_trial,
            g_pred,
        ]
    )
    for column in range(4):
        grad_effects[:, column] = np.bincount(idx, weights=contributions[:, column], minlength=n_participants)

    free = set(active_parameters(model))
    for name in GROUP_NAMES:
        if (name.startswith("delta_") or name.startswith("gamma_")) and name not in free:
            grad_group[GROUP_NAMES.index(name)] = 0.0
        else:
            grad_group[GROUP_NAMES.index(name)] += _objective_prior_grad_group(name, group_values[name])

    for column, (name, value) in enumerate(zip(SIGMA_NAMES, sigma)):
        log_value = math.log(value)
        grad_log_sigma[column] = (log_value - math.log(0.5)) / (0.5 * 0.5)
        grad_log_sigma[column] += len(effects) - np.sum(effects[:, column] ** 2) / (value * value)
        grad_effects[:, column] += effects[:, column] / (value * value)

    grad = np.concatenate([grad_group, grad_log_sigma, grad_effects.ravel()])
    return objective, grad


def _fit_bounds(n_group: int, n_sigma: int, n_participants: int) -> list[tuple[float, float]]:
    bounds = [(-20.0, 20.0)] * n_group
    bounds += [(-8.0, 4.0)] * n_sigma
    bounds += [(-20.0, 20.0)] * (n_participants * n_sigma)
    return bounds


def fit_trial_model(data: TrialData, model: str = "M0", config: TrialModelConfig | None = None) -> TrialFit:
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}")
    cfg = config or TrialModelConfig(n_participants=data.n_participants)
    n_participants = data.n_participants
    group_values = {name: 0.0 for name in GROUP_NAMES}
    log_sigma = np.full(len(SIGMA_NAMES), math.log(0.5))
    effects = np.zeros((n_participants, len(SIGMA_NAMES)))
    x0 = _pack(model, group_values, log_sigma, effects)
    result = minimize(
        lambda x: _objective_and_grad(model, data, x, n_participants),
        x0,
        jac=True,
        method="L-BFGS-B",
        bounds=_fit_bounds(len(GROUP_NAMES), len(SIGMA_NAMES), n_participants),
        options={"maxiter": cfg.max_iter, "ftol": 1e-9},
    )
    map_params = np.asarray(result.x, dtype=float)
    group_map, sigma_map, effects_map = _unpack(model, map_params, n_participants)
    log_likelihood = _log_likelihood(model, data, group_map, sigma_map, effects_map)
    n_parameters = len(active_parameters(model)) + len(GROUP_NAMES) + len(SIGMA_NAMES) + 4 * n_participants
    bic = -2.0 * log_likelihood + n_parameters * math.log(len(data.participant))
    draws = (
        _laplace_draws(model, data, map_params, result, cfg, n_participants)
        if cfg.laplace
        else np.zeros((0, len(map_params)), dtype=float)
    )
    return TrialFit(
        model=model,
        map_params=map_params,
        posterior_draws=draws,
        log_likelihood=log_likelihood,
        n_parameters=n_parameters,
        bic=float(bic),
        converged=bool(result.success),
    )


def _numerical_hessian(model: str, data: TrialData, x: np.ndarray, n_participants: int) -> np.ndarray:
    """Central-difference Hessian of the negative log posterior at the MAP."""
    dimension = len(x)
    hessian = np.zeros((dimension, dimension))
    base = np.asarray(x, dtype=float)
    for column in range(dimension):
        step = 1e-4 * max(1.0, abs(base[column]))
        plus = base.copy()
        minus = base.copy()
        plus[column] += step
        minus[column] -= step
        _, grad_plus = _objective_and_grad(model, data, plus, n_participants)
        _, grad_minus = _objective_and_grad(model, data, minus, n_participants)
        hessian[:, column] = (grad_plus - grad_minus) / (2.0 * step)
    return (hessian + hessian.T) / 2.0


def _positive_definite(matrix: np.ndarray) -> np.ndarray:
    matrix = (matrix + matrix.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    floor = max(1e-6, float(eigenvalues.max()) * 1e-8)
    eigenvalues = np.maximum(eigenvalues, floor)
    return (eigenvectors * eigenvalues) @ eigenvectors.T


def _laplace_draws(
    model: str,
    data: TrialData,
    map_params: np.ndarray,
    result: Any,
    config: TrialModelConfig,
    n_participants: int,
) -> np.ndarray:
    del result
    hessian = _numerical_hessian(model, data, map_params, n_participants)
    n_group = len(GROUP_NAMES)
    h_gg = hessian[:n_group, :n_group]
    h_gu = hessian[:n_group, n_group:]
    h_uu = hessian[n_group:, n_group:]
    if h_uu.size:
        h_uu_inv = np.linalg.pinv(_positive_definite(h_uu))
        covariance = np.linalg.pinv(_positive_definite(h_gg - h_gu @ h_uu_inv @ h_gu.T))
    else:
        covariance = np.linalg.pinv(_positive_definite(h_gg))
    rng = np.random.default_rng(config.seed + 17)
    draws = rng.multivariate_normal(
        map_params[:n_group], _positive_definite(covariance), size=config.n_posterior_draws
    )
    free = set(active_parameters(model))
    for name in GROUP_NAMES:
        if (name.startswith("delta_") or name.startswith("gamma_")) and name not in free:
            draws[:, GROUP_NAMES.index(name)] = 0.0
    return draws


def _draw_group(
    rng: np.random.Generator,
    model: str,
    effect_scale: float = 0.5,
    min_abs_effect: float = 0.0,
) -> dict[str, float]:
    active = set(active_parameters(model))
    for _ in range(1000):
        values = {
            name: float(
                rng.normal(0.0, effect_scale if name in active else (0.5 if name.startswith("delta_") else 1.0))
            )
            for name in GROUP_NAMES
        }
        for name in GROUP_NAMES:
            if (name.startswith("delta_") or name.startswith("gamma_")) and name not in active:
                values[name] = 0.0
        if not active or all(abs(values[name]) >= min_abs_effect for name in active):
            return values
    raise RuntimeError("could not draw an effect-conditioned parameter set")


def _draw_effects(rng: np.random.Generator, n_participants: int) -> np.ndarray:
    sigma = np.exp(rng.normal(math.log(0.5), 0.5, size=len(SIGMA_NAMES)))
    return rng.normal(0.0, sigma, size=(n_participants, len(SIGMA_NAMES)))


def simulate_trial_data(
    model: str = "M0",
    n_participants: int = 40,
    n_trials: int = 120,
    seed: int = 20261031,
    effect_scale: float = 0.5,
    min_abs_effect: float = 0.0,
    predict_probability: float = 0.5,
    dual_probability: float = 0.5,
    diagnosticity_range: tuple[float, float] = (0.0, 1.0),
    vividness_spread: float = 0.0,
    confidence_spread: float = 0.0,
) -> tuple[TrialData, dict[str, float]]:
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}")
    if effect_scale <= 0 or min_abs_effect < 0:
        raise ValueError("effect_scale must be positive and min_abs_effect non-negative")
    if not 0.0 <= predict_probability <= 1.0 or not 0.0 <= dual_probability <= 1.0:
        raise ValueError("predict_probability and dual_probability must be in [0, 1]")
    low, high = diagnosticity_range
    if not 0.0 <= low < high <= 1.0:
        raise ValueError("diagnosticity_range must be ordered within [0, 1]")
    if vividness_spread < 0 or confidence_spread < 0:
        raise ValueError("vividness_spread and confidence_spread must be non-negative")
    rng = np.random.default_rng(seed)
    group = _draw_group(rng, model, effect_scale=effect_scale, min_abs_effect=min_abs_effect)
    effects = _draw_effects(rng, n_participants)
    idx = np.repeat(np.arange(n_participants), n_trials)
    predict = (rng.random(len(idx)) < predict_probability).astype(float)
    dual = (rng.random(len(idx)) < dual_probability).astype(float)
    diagnosticity = rng.uniform(low, high, size=len(idx))
    imagined = rng.integers(0, 2, size=len(idx)).astype(float)
    x = 2.0 * diagnosticity - 1.0

    d = group["alpha_d"] + group["delta_d"] * predict + group["delta_dual_d"] * dual + effects[idx, 0]
    b = group["alpha_b"] + group["delta_b"] * predict + group["delta_dual_b"] * dual + effects[idx, 1]
    pi = group["alpha_pi"] + group["delta_pi"] * predict + effects[idx, 2]
    a = group["alpha_a"] + effects[idx, 3]

    p_pred = expit(a + pi * x)
    prediction = rng.binomial(1, p_pred).astype(float)
    p_outcome = expit(d * x + 0.2 * imagined)
    outcome = rng.binomial(1, p_outcome).astype(float)
    consistency = (prediction == outcome).astype(float)
    vividness = np.clip(
        0.5
        + 0.12 * predict
        + 0.10 * imagined
        + 0.08 * dual
        + rng.normal(0.0, 0.12 + vividness_spread, size=len(idx)),
        0.01,
        0.99,
    )
    prediction_confidence = np.clip(
        0.5 + 0.15 * predict + rng.normal(0.0, 0.12 + confidence_spread, size=len(idx)),
        0.01,
        0.99,
    )

    eta_source = d * x + b * consistency + 0.2 * imagined
    if model == "M6":
        eta_source = eta_source + group["gamma_v"] * (vividness - 0.5)
    if model == "M7":
        eta_source = eta_source + group["gamma_c"] * (prediction_confidence - 0.5)
    p_source = expit(eta_source)
    source_correct = rng.binomial(1, p_source).astype(float)
    source_confidence = np.clip(
        0.5 + 0.22 * source_correct + 0.12 * (vividness - 0.5) + rng.normal(0.0, 0.12, size=len(idx)),
        0.01,
        0.99,
    )

    return (
        TrialData(
            participant=idx,
            predict=predict,
            dual=dual,
            diagnosticity=diagnosticity,
            imagined=imagined,
            prediction=prediction,
            outcome=outcome,
            source_correct=source_correct,
            vividness=vividness,
            prediction_confidence=prediction_confidence,
            source_confidence=source_confidence,
        ),
        group,
    )


def _rank_metrics(ranks: np.ndarray, coverage: np.ndarray) -> dict[str, float]:
    bins = np.linspace(0.0, 1.0, 11)
    counts, _ = np.histogram(ranks, bins=bins)
    expected = len(ranks) / 10.0
    chi_square = float(np.sum((counts - expected) ** 2 / expected)) if expected > 0 else float("nan")
    return {
        "mean_rank": float(np.mean(ranks)),
        "coverage": float(np.mean(coverage)),
        "chi_square": chi_square,
        "min_bin": int(counts.min()),
        "max_bin": int(counts.max()),
    }


def run_trial_sbc(config: TrialModelConfig | None = None, model: str = "M4") -> dict[str, Any]:
    cfg = config or TrialModelConfig()
    rng = np.random.default_rng(cfg.seed)
    active = list(active_parameters(model))
    rank_names = ["alpha_d", *active] if active else ["alpha_d"]
    ranks: dict[str, list[float]] = {name: [] for name in rank_names}
    coverage: dict[str, list[float]] = {name: [] for name in ranks}
    convergence = 0
    for draw_index in range(cfg.n_sbc):
        seed = int(rng.integers(0, 2**31 - 1))
        data, truth = simulate_trial_data(
            model=model,
            n_participants=cfg.n_participants,
            n_trials=cfg.n_trials,
            seed=seed,
        )
        fit = fit_trial_model(data, model=model, config=cfg)
        convergence += int(fit.converged)
        for name in ranks:
            draws = fit.draw(name)
            ranks[name].append(float((draws < truth[name]).mean()))
            low, high = np.quantile(draws, [0.025, 0.975])
            coverage[name].append(float(low <= truth[name] <= high))
    metrics = {name: _rank_metrics(np.array(ranks[name]), np.array(coverage[name])) for name in ranks}
    target_names = active or ["alpha_d"]
    passed = all(
        cfg.coverage_low <= metrics[name]["coverage"] <= cfg.coverage_high
        and metrics[name]["chi_square"] <= 21.666
        for name in target_names
    )
    return {
        "scope": SCOPE,
        "model": model,
        "target_parameters": target_names,
        "config": cfg.__dict__,
        "metrics": metrics,
        "convergence_rate": convergence / cfg.n_sbc,
        "decision": "CRT_STAGE0G_TRIAL_SBC_PASS" if passed else "CRT_STAGE0G_TRIAL_SBC_REVIEW",
        "note": (
            "Laplace-approximate trial-level readout model; not a full CRT POMDP posterior. "
            "The decision uses the active condition-effect parameters; alpha_d is diagnostic."
        ),
    }


def run_trial_recovery(
    config: TrialModelConfig | None = None,
    effect_scale: float = 0.8,
    min_abs_effect: float = 0.25,
    model_set: Iterable[str] = MODELS,
    selection_status: str = "pre_specified",
) -> dict[str, Any]:
    cfg = config or TrialModelConfig()
    candidates = tuple(model_set)
    if not candidates or any(model not in MODELS for model in candidates):
        raise ValueError("model_set must be a non-empty subset of MODELS")
    rng = np.random.default_rng(cfg.seed + 101)
    confusion = np.zeros((len(candidates), len(candidates)), dtype=int)
    for true_index, true_model in enumerate(candidates):
        for _ in range(cfg.n_recovery):
            seed = int(rng.integers(0, 2**31 - 1))
            data, _ = simulate_trial_data(
                model=true_model,
                n_participants=cfg.n_participants,
                n_trials=cfg.n_trials,
                seed=seed,
                effect_scale=effect_scale,
                min_abs_effect=min_abs_effect,
            )
            fits = [fit_trial_model(data, model=model, config=cfg) for model in candidates]
            best = int(np.argmin([fit.bic for fit in fits]))
            confusion[true_index, best] += 1
    row_sums = confusion.sum(axis=1)
    balanced_accuracy = float(np.mean(np.diag(confusion) / np.maximum(row_sums, 1)))
    return {
        "scope": SCOPE,
        "models": list(candidates),
        "selection_status": selection_status,
        "config": asdict(cfg),
        "recovery_conditions": {
            "effect_scale": effect_scale,
            "min_abs_effect": min_abs_effect,
            "conditioning": "each active condition effect has |delta| >= min_abs_effect",
        },
        "confusion": confusion.tolist(),
        "balanced_accuracy": balanced_accuracy,
        "decision": (
            "CRT_STAGE0G_TRIAL_RECOVERY_PASS"
            if balanced_accuracy >= cfg.recovery_threshold and selection_status == "pre_specified"
            else (
                "CRT_STAGE0G_TRIAL_RECOVERY_CONDITIONAL_PASS"
                if balanced_accuracy >= cfg.recovery_threshold
                else "CRT_STAGE0G_TRIAL_RECOVERY_REVIEW"
            )
        ),
        "note": (
            "BIC-based recovery among effect-conditioned trial-level readout models; not a full CRT "
            "POMDP comparison. The conditioning is necessary because the models are nested and a "
            "prior-averaged draw would often generate a null effect that M0 should win. A conditional "
            "pass after reducing the model set is not equivalent to a pre-specified full-set pass."
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


def write_artifact(payload: Mapping[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run a small SBC/recovery smoke test")
    parser.add_argument("--sbc", action="store_true", help="run trial-level SBC")
    parser.add_argument("--recovery", action="store_true", help="run trial-level model recovery")
    parser.add_argument(
        "--confirmatory-set",
        action="store_true",
        help="restrict recovery to the pre-specified M0/M2/M4 confirmatory set",
    )
    parser.add_argument("--model", default="M2", choices=MODELS, help="model for SBC")
    parser.add_argument("--out-dir", type=Path, default=Path("results/crt"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.check:
        cfg = TrialModelConfig(n_sbc=20, n_recovery=6, n_participants=12, n_trials=40, n_posterior_draws=40)
        print(json.dumps(_json_ready(run_trial_sbc(cfg)), indent=2))
        return 0
    if args.sbc:
        write_artifact(run_trial_sbc(model=args.model), args.out_dir / "CRT_STAGE0G_TRIAL_SBC.json")
        return 0
    if args.recovery:
        cfg = TrialModelConfig(
            n_participants=32,
            n_trials=160,
            n_recovery=10,
            n_posterior_draws=100,
            seed=20261031,
        )
        model_set = ("M0", "M2", "M4") if args.confirmatory_set else MODELS
        write_artifact(
            run_trial_recovery(
                cfg,
                model_set=model_set,
                selection_status=(
                    "post_hoc_after_full_set_review" if args.confirmatory_set else "pre_specified"
                ),
            ),
            args.out_dir / "CRT_STAGE0G_TRIAL_RECOVERY.json",
        )
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
