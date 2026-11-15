"""NumPyro/NUTS implementation of the CRT full joint source-monitoring model.

This is the publication-grade inference path. It mirrors the NumPy/SciPy full model in
``full_model.py``: the source is marginalized over four states, the participant's belief is updated
from the observed outcome only, and prediction is the belief-weighted posterior predictive readout.
The Laplace implementation remains a screening approximation.

The module is import-safe without NumPyro/JAX; callers receive an explicit availability error rather
than a silent fallback.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .full_model import FULL_ACTIVE, FULL_MODELS, TEST_LIKELIHOODS, simulate_full_data
from .trial_model import TrialData

SCOPE = "numpyro_nuts_full_joint_source_monitoring_v1"


class NumpyroUnavailableError(RuntimeError):
    """Raised when the optional NumPyro/JAX backend is not installed."""


@dataclass(frozen=True)
class NutsConfig:
    chains: int = 4
    warmup: int = 1000
    draws: int = 1000
    seed: int = 20261031
    target_accept: float = 0.95
    max_tree_depth: int = 10

    def __post_init__(self) -> None:
        if self.chains < 1 or self.warmup < 1 or self.draws < 1:
            raise ValueError("chains, warmup, and draws must be positive")
        if not 0 < self.target_accept < 1:
            raise ValueError("target_accept must be in (0, 1)")


def numpyro_available() -> bool:
    try:
        import jax  # noqa: F401
        import numpyro  # noqa: F401
    except Exception:
        return False
    return True


def _require_backend() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import jax
        import jax.numpy as jnp
        import numpyro
        import numpyro.distributions as dist
        from numpyro.infer import MCMC, NUTS
    except Exception as exc:  # pragma: no cover - depends on optional environment
        raise NumpyroUnavailableError(
            "NumPyro/JAX is not installed; install the 'crt' extra before requesting NUTS"
        ) from exc
    return jax, jnp, numpyro, dist, (MCMC, NUTS)


def _check_contiguous(data: TrialData) -> tuple[int, int]:
    participant = np.asarray(data.participant, dtype=int)
    n_participants = int(participant.max()) + 1
    counts = np.bincount(participant, minlength=n_participants)
    if len(set(counts.tolist())) != 1:
        raise ValueError("NUTS path requires a balanced, contiguous participant x trial layout")
    n_trials = int(counts[0])
    ordered = np.arange(n_participants * n_trials)
    if not np.array_equal(participant, np.repeat(np.arange(n_participants), n_trials)):
        raise ValueError("NUTS path requires trials ordered by participant, then trial order")
    if not np.array_equal(np.arange(len(participant)), ordered):
        raise ValueError("NUTS path requires a complete participant x trial rectangle")
    return n_participants, n_trials


def _model_components(model: str) -> dict[str, bool]:
    if model not in FULL_MODELS:
        raise ValueError(f"unknown full model {model!r}")
    active = set(FULL_ACTIVE[model])
    return {
        "gamma_v": "gamma_v" in active,
        "gamma_c": "gamma_c" in active,
        "delta_b": "delta_b" in active,
        "delta_dual": "delta_dual" in active,
    }


def _make_model(data: TrialData, model: str):
    jax, jnp, numpyro, dist, _ = _require_backend()
    n_participants, n_trials = _check_contiguous(data)
    components = _model_components(model)
    test = jnp.asarray(np.asarray(data.test_id, dtype=int).reshape(n_participants, n_trials))
    prediction = jnp.asarray(np.asarray(data.prediction, dtype=float).reshape(n_participants, n_trials))
    outcome = jnp.asarray(np.asarray(data.outcome, dtype=float).reshape(n_participants, n_trials))
    report = jnp.asarray(np.asarray(data.source_report, dtype=int).reshape(n_participants, n_trials))
    vividness = jnp.asarray(np.asarray(data.vividness, dtype=float).reshape(n_participants, n_trials))
    prediction_confidence = jnp.asarray(
        np.asarray(data.prediction_confidence, dtype=float).reshape(n_participants, n_trials)
    )
    source_confidence = jnp.asarray(
        np.asarray(data.source_confidence, dtype=float).reshape(n_participants, n_trials)
    )
    predict = jnp.asarray(np.asarray(data.predict, dtype=float).reshape(n_participants, n_trials))
    dual = jnp.asarray(np.asarray(data.dual, dtype=float).reshape(n_participants, n_trials))
    base = jnp.asarray(np.clip(TEST_LIKELIHOODS, 1e-6, 1.0 - 1e-6))

    def parameter(name: str, scale: float, active: bool = True):
        if not active:
            return jnp.asarray(0.0)
        return numpyro.sample(name, dist.Normal(0.0, scale))

    def model_fn() -> None:
        alpha_d = parameter("alpha_d", 1.0)
        alpha_pi = parameter("alpha_pi", 1.0)
        alpha_b = parameter("alpha_b", 1.0)
        gamma_v = parameter("gamma_v", 0.5, components["gamma_v"])
        gamma_c = parameter("gamma_c", 0.5, components["gamma_c"])
        delta_b = parameter("delta_b", 0.5, components["delta_b"])
        delta_dual = parameter("delta_dual", 0.5, components["delta_dual"])
        sigma_d = numpyro.sample("sigma_d", dist.LogNormal(math.log(0.5), 0.5))
        sigma_pi = numpyro.sample("sigma_pi", dist.LogNormal(math.log(0.5), 0.5))
        sigma_b = numpyro.sample("sigma_b", dist.LogNormal(math.log(0.5), 0.5))
        z_d = numpyro.sample("z_d", dist.Normal(0.0, 1.0).expand([n_participants]).to_event(1))
        z_pi = numpyro.sample("z_pi", dist.Normal(0.0, 1.0).expand([n_participants]).to_event(1))
        z_b = numpyro.sample("z_b", dist.Normal(0.0, 1.0).expand([n_participants]).to_event(1))
        d = alpha_d + sigma_d * z_d
        pi = alpha_pi + sigma_pi * z_pi
        b = alpha_b + sigma_b * z_b
        candidates = jnp.arange(4, dtype=float)

        def trial_log_likelihood(carry, inputs):
            belief = carry
            d_participant, pi_participant, b_participant, test_id, pred, out, rep, viv, pconf, sconf, pred_cov, dual_cov = inputs
            probabilities = base[test_id]
            q = jnp.sum(belief * probabilities)
            q = jnp.clip(q, 1e-8, 1.0 - 1e-8)
            p_prediction = jax.nn.sigmoid(pi_participant * jnp.log(q / (1.0 - q)))
            p_prediction = jnp.clip(p_prediction, 1e-8, 1.0 - 1e-8)
            prediction_log_lik = pred * jnp.log(p_prediction) + (1.0 - pred) * jnp.log1p(-p_prediction)

            source_probability = jax.nn.sigmoid(
                d_participant * jnp.log(probabilities / (1.0 - probabilities))
            )
            outcome_likelihood = jnp.where(out == 1.0, source_probability, 1.0 - source_probability)
            source_indicator = candidates[:, None] == candidates[None, :]
            report_zero = candidates[None, :] == 0.0
            report_logits = (
                d_participant * source_indicator
                + b_participant * report_zero
                + gamma_v * (viv - 0.5) * source_indicator
                + gamma_c * (pconf - 0.5) * source_indicator
                + delta_b * pred_cov * report_zero
                + delta_dual * dual_cov * report_zero
            )
            report_log_prob = jax.nn.log_softmax(report_logits, axis=1)[:, rep]
            is_source = candidates == rep
            confidence_mean = 0.5 + 0.25 * is_source + 0.10 * (viv - 0.5)
            confidence_log_lik = dist.Normal(confidence_mean, 0.15).log_prob(sconf)
            joint = (
                jnp.log(jnp.clip(belief, 1e-12, None))
                + jnp.log(jnp.clip(outcome_likelihood, 1e-12, None))
                + report_log_prob
                + confidence_log_lik
            )
            marginal = jax.scipy.special.logsumexp(joint)
            posterior = jax.nn.softmax(
                jnp.log(jnp.clip(belief, 1e-12, None))
                + jnp.log(jnp.clip(outcome_likelihood, 1e-12, None))
            )
            return posterior, prediction_log_lik + marginal

        for p in range(n_participants):
            belief = jnp.full(4, 0.25)
            scan_inputs = (
                jnp.full(n_trials, d[p]),
                jnp.full(n_trials, pi[p]),
                jnp.full(n_trials, b[p]),
                test[p],
                prediction[p],
                outcome[p],
                report[p],
                vividness[p],
                prediction_confidence[p],
                source_confidence[p],
                predict[p],
                dual[p],
            )
            _, log_lik = jax.lax.scan(trial_log_likelihood, belief, scan_inputs)
            numpyro.factor(f"participant_{p}_log_likelihood", jnp.sum(log_lik))
            if p == 0:
                total_log_lik = jnp.sum(log_lik)
            else:
                total_log_lik = total_log_lik + jnp.sum(log_lik)
        numpyro.deterministic("log_likelihood", total_log_lik)

    return model_fn


def fit_nuts(data: TrialData, model: str = "M0", config: NutsConfig | None = None) -> dict[str, Any]:
    """Fit the full joint model with NUTS and return posterior draws plus diagnostics."""
    jax, jnp, numpyro, dist, (MCMC, NUTS) = _require_backend()
    cfg = config or NutsConfig()
    model_fn = _make_model(data, model)
    kernel = NUTS(model_fn, target_accept_prob=cfg.target_accept, max_tree_depth=cfg.max_tree_depth)
    mcmc = MCMC(
        kernel,
        num_warmup=cfg.warmup,
        num_samples=cfg.draws,
        num_chains=cfg.chains,
        progress_bar=False,
    )
    mcmc.run(jax.random.PRNGKey(cfg.seed))
    samples = {name: np.asarray(value) for name, value in mcmc.get_samples().items()}
    extra = mcmc.get_extra_fields()
    summary: dict[str, Any] = {}
    try:
        import arviz as az

        idata = az.from_numpyro(mcmc)
        summary = az.summary(idata).to_dict(orient="index")
    except Exception:
        summary = {}
    return {
        "analysis": "crt_numpyro_nuts_fit",
        "scope": SCOPE,
        "model": model,
        "config": asdict(cfg),
        "samples": samples,
        "diagnostics": summary,
        "divergences": int(np.asarray(extra.get("diverging", [])).sum())
        if extra.get("diverging") is not None
        else None,
        "note": "NUTS full joint model; synthetic or authorized human data only, not a claim upgrade.",
    }


def run_nuts_smoke(data: TrialData, model: str = "M0", config: NutsConfig | None = None) -> dict[str, Any]:
    """Small, fast NUTS run used by CI/readiness checks; deliberately not target-scale."""
    cfg = config or NutsConfig(chains=1, warmup=30, draws=30, max_tree_depth=6)
    result = fit_nuts(data, model=model, config=cfg)
    return {
        "analysis": "crt_numpyro_nuts_smoke",
        "scope": SCOPE,
        "model": model,
        "config": asdict(cfg),
        "divergences": result["divergences"],
        "sample_keys": sorted(result["samples"]),
        "decision": "CRT_NUTS_SMOKE_PASS" if result["divergences"] == 0 else "CRT_NUTS_SMOKE_REVIEW",
        "note": "Smoke test only; does not satisfy target-scale SBC or recovery.",
    }


@dataclass(frozen=True)
class NutsSbcConfig:
    n_participants: int = 8
    n_trials: int = 24
    n_sbc: int = 20
    chains: int = 1
    warmup: int = 300
    draws: int = 300
    seed: int = 20261105
    target_accept: float = 0.95
    coverage_low: float = 0.93
    coverage_high: float = 0.97
    min_sbc_for_decision: int = 50

    def __post_init__(self) -> None:
        if self.n_participants < 2 or self.n_trials < 2:
            raise ValueError("NUTS SBC requires at least two participants and two trials")
        if self.n_sbc <= 0 or self.chains < 1 or self.warmup < 1 or self.draws < 20:
            raise ValueError("SBC counts must be positive and draws at least 20")
        if not 0 < self.coverage_low < self.coverage_high < 1:
            raise ValueError("coverage bounds must be ordered in (0, 1)")
        if self.min_sbc_for_decision < 1:
            raise ValueError("min_sbc_for_decision must be positive")


def run_nuts_sbc(
    model: str = "M0",
    config: NutsSbcConfig | None = None,
) -> dict[str, Any]:
    """Run simulation-based calibration for one confirmatory model with NUTS.

    The function deliberately refuses a PASS below ``min_sbc_for_decision``: small SBC runs are
    smoke tests, not calibration evidence.
    """
    cfg = config or NutsSbcConfig()
    rng = np.random.default_rng(cfg.seed)
    targets = list(FULL_ACTIVE[model]) or ["alpha_d"]
    ranks: dict[str, list[float]] = {name: [] for name in targets}
    coverage: dict[str, list[float]] = {name: [] for name in targets}
    convergence = 0
    for _ in range(cfg.n_sbc):
        seed = int(rng.integers(0, 2**31 - 1))
        data, truth = simulate_full_data(
            model,
            n_participants=cfg.n_participants,
            n_trials=cfg.n_trials,
            seed=seed,
        )
        fit = fit_nuts(
            data,
            model=model,
            config=NutsConfig(
                chains=cfg.chains,
                warmup=cfg.warmup,
                draws=cfg.draws,
                seed=seed,
                target_accept=cfg.target_accept,
            ),
        )
        if fit["divergences"] == 0:
            convergence += 1
        for name in targets:
            draws = np.asarray(fit["samples"][name], dtype=float).reshape(-1)
            value = float(truth[name])
            ranks[name].append(float(np.mean(draws < value)))
            low, high = np.quantile(draws, [0.025, 0.975])
            coverage[name].append(float(low <= value <= high))
    metrics = {
        name: {
            "mean_rank": float(np.mean(ranks[name])),
            "coverage": float(np.mean(coverage[name])),
            "n": len(ranks[name]),
        }
        for name in targets
    }
    calibrated = all(
        cfg.coverage_low <= metrics[name]["coverage"] <= cfg.coverage_high for name in targets
    )
    passed = calibrated and convergence == cfg.n_sbc and cfg.n_sbc >= cfg.min_sbc_for_decision
    return {
        "analysis": "crt_numpyro_nuts_sbc",
        "scope": SCOPE,
        "model": model,
        "target_parameters": targets,
        "config": asdict(cfg),
        "metrics": metrics,
        "clean_chains": convergence,
        "decision": "CRT_NUTS_SBC_PASS" if passed else "CRT_NUTS_SBC_REVIEW",
        "note": (
            "NUTS SBC; a REVIEW below the minimum SBC count is expected and is not a failed model. "
            "No human evidence is used."
        ),
    }
