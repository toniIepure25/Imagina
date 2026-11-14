"""Test-selection policy models for the CRT Stage 0I program.

This module is a policy-identification layer, not a source-model replacement. It simulates a small
POMDP over four latent sources and compares fixed, random, meta-EIG, outcome-EIG, positive-testing,
and cost-only test-selection rules. The source-model comparison remains in ``full_model.py``.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from .full_model import TEST_LIKELIHOODS

SCOPE = "policy_choice_simulation_not_human_evidence"
POLICIES: tuple[str, ...] = (
    "fixed",
    "random",
    "meta_eig",
    "outcome_eig",
    "positive_testing",
    "cost_only",
)
POLICY_COSTS = np.array([1.5, 1.0, 1.0, 2.0, 1.0, 0.5], dtype=float)
POLICY_COMPLEXITY = np.array([2, 1, 1, 3, 1, 1], dtype=float)
POLICY_AGENCY = np.array([0.30, 0.40, 0.30, 0.70, 0.30, 0.30], dtype=float)


@dataclass(frozen=True)
class PolicyConfig:
    n_participants: int = 16
    n_trials: int = 40
    n_simulations: int = 3
    seed: int = 20261031
    temperature: float = 1.0
    cost_weight: float = 0.25
    complexity_weight: float = 0.10
    agency_weight: float = 0.10
    positive_bias: float = 0.75
    lapse: float = 0.02
    recovery_threshold: float = 0.85
    n_parameter_sbc: int = 10
    n_parameter_draws: int = 50
    parameter_sbc_low: float = 0.90
    parameter_sbc_high: float = 0.99

    def __post_init__(self) -> None:
        if self.n_participants < 2 or self.n_trials < 6:
            raise ValueError("policy simulation requires at least 2 participants and 6 trials")
        if self.n_simulations <= 0 or not 0 < self.recovery_threshold <= 1:
            raise ValueError("simulation count and threshold must be positive")
        if self.n_parameter_sbc <= 0 or self.n_parameter_draws < 20:
            raise ValueError("parameter SBC counts must be positive and draws at least 20")
        if not 0 <= self.lapse < 1 or self.temperature <= 0:
            raise ValueError("lapse must be in [0, 1) and temperature must be positive")
        if not 0 < self.parameter_sbc_low < self.parameter_sbc_high < 1:
            raise ValueError("parameter SBC coverage bounds must be ordered")


@dataclass(frozen=True)
class PolicyData:
    participant: np.ndarray
    trial: np.ndarray
    test: np.ndarray
    outcome: np.ndarray


def _entropy(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-12, 1.0)
    return -np.sum(clipped * np.log(clipped), axis=-1)


def _posterior(belief: np.ndarray, test: int, outcome: int) -> np.ndarray:
    likelihood = TEST_LIKELIHOODS[test]
    unnormalized = belief * (likelihood if outcome == 1 else (1.0 - likelihood))
    total = unnormalized.sum(axis=-1, keepdims=True)
    return np.where(total > 1e-12, unnormalized / np.maximum(total, 1e-12), belief)


def _expected_information_gain(belief: np.ndarray, test: int) -> np.ndarray:
    likelihood = TEST_LIKELIHOODS[test]
    p_outcome = np.sum(belief * likelihood, axis=-1)
    prior_entropy = _entropy(belief)
    posterior_one = _posterior(belief, test, 1)
    posterior_zero = _posterior(belief, test, 0)
    expected_entropy = p_outcome * _entropy(posterior_one) + (1.0 - p_outcome) * _entropy(posterior_zero)
    return prior_entropy - expected_entropy


def _utility(policy: str, belief: np.ndarray, test: int, trial_index: int, config: PolicyConfig) -> np.ndarray:
    cost = config.cost_weight * POLICY_COSTS[test]
    complexity = config.complexity_weight * POLICY_COMPLEXITY[test]
    agency = config.agency_weight * POLICY_AGENCY[test]
    if policy == "meta_eig":
        return _expected_information_gain(belief, test) + agency - cost - complexity
    if policy == "outcome_eig":
        p_outcome = np.sum(belief * TEST_LIKELIHOODS[test], axis=-1)
        entropy = _entropy(np.stack([1.0 - p_outcome, p_outcome], axis=-1))
        return entropy + agency - cost - complexity
    if policy == "positive_testing":
        p_outcome = np.sum(belief * TEST_LIKELIHOODS[test], axis=-1)
        return config.positive_bias * p_outcome + agency - cost - complexity
    if policy == "cost_only":
        return -np.full(belief.shape[0], cost + complexity)
    if policy == "fixed":
        chosen = trial_index % len(TEST_LIKELIHOODS)
        return np.full(belief.shape[0], 1.0 if chosen == test else 0.0)
    return np.zeros(belief.shape[0])


def _choice_probabilities(
    policy: str, belief: np.ndarray, trial_index: int, config: PolicyConfig
) -> np.ndarray:
    utilities = np.stack(
        [_utility(policy, belief, test, trial_index, config) for test in range(len(TEST_LIKELIHOODS))],
        axis=0,
    ).T
    if policy == "random":
        probabilities = np.full_like(utilities, 1.0 / utilities.shape[1])
    elif policy == "fixed":
        chosen = trial_index % len(TEST_LIKELIHOODS)
        probabilities = np.full_like(utilities, 1e-6)
        probabilities[:, chosen] = 1.0
        probabilities /= probabilities.sum(axis=1, keepdims=True)
    else:
        scaled = utilities / config.temperature
        scaled -= scaled.max(axis=1, keepdims=True)
        probabilities = np.exp(scaled)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
    probabilities = (1.0 - config.lapse) * probabilities + config.lapse / probabilities.shape[1]
    return probabilities


def simulate_policy_data(policy: str, config: PolicyConfig | None = None) -> tuple[PolicyData, dict[str, Any]]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    cfg = config or PolicyConfig()
    rng = np.random.default_rng(cfg.seed)
    n_rows = cfg.n_participants * cfg.n_trials
    participant = np.repeat(np.arange(cfg.n_participants), cfg.n_trials)
    trial = np.tile(np.arange(cfg.n_trials), cfg.n_participants)
    source = rng.integers(0, 4, size=n_rows)
    belief = np.full((cfg.n_participants, 4), 0.25)
    tests: list[int] = []
    outcomes: list[int] = []

    for index in range(n_rows):
        participant_index = int(participant[index])
        trial_index = int(trial[index])
        current = belief[participant_index : participant_index + 1]
        probabilities = _choice_probabilities(policy, current, trial_index, cfg)[0]
        test = int(rng.choice(len(TEST_LIKELIHOODS), p=probabilities))
        outcome = int(rng.binomial(1, TEST_LIKELIHOODS[test, source[index]]))
        tests.append(test)
        outcomes.append(outcome)
        belief[participant_index] = _posterior(current, test, outcome)[0]

    return (
        PolicyData(
            participant=participant,
            trial=trial,
            test=np.asarray(tests, dtype=int),
            outcome=np.asarray(outcomes, dtype=int),
        ),
        {"policy": policy, "config": asdict(cfg)},
    )


def policy_log_likelihood(data: PolicyData, policy: str, config: PolicyConfig | None = None) -> float:
    cfg = config or PolicyConfig()
    belief = np.full((int(data.participant.max()) + 1, 4), 0.25)
    log_likelihood = 0.0
    for index in range(len(data.test)):
        participant_index = int(data.participant[index])
        trial_index = int(data.trial[index])
        probabilities = _choice_probabilities(
            policy, belief[participant_index : participant_index + 1], trial_index, cfg
        )[0]
        log_likelihood += float(np.log(max(probabilities[int(data.test[index])], 1e-12)))
        belief[participant_index] = _posterior(
            belief[participant_index : participant_index + 1],
            int(data.test[index]),
            int(data.outcome[index]),
        )[0]
    return log_likelihood


def fit_policy_choice(data: PolicyData, config: PolicyConfig | None = None) -> dict[str, Any]:
    cfg = config or PolicyConfig()
    scores = {policy: policy_log_likelihood(data, policy, cfg) for policy in POLICIES}
    best = max(scores, key=scores.get)
    n = len(data.test)
    bic = {policy: -2.0 * score + (0 if policy in {"random", "fixed"} else 1) * math.log(n) for policy, score in scores.items()}
    return {
        "selected_policy": best,
        "scores": scores,
        "bic": bic,
        "selected_by_bic": min(bic, key=bic.get),
    }


def _parameter_vector(config: PolicyConfig) -> np.ndarray:
    return np.array(
        [
            math.log(config.temperature),
            math.log(config.cost_weight / max(1e-6, 1.0 - config.cost_weight)),
            math.log(config.positive_bias / max(1e-6, 1.0 - config.positive_bias)),
        ],
        dtype=float,
    )


def _config_from_parameters(base: PolicyConfig, theta: np.ndarray) -> PolicyConfig:
    return replace(
        base,
        temperature=float(np.clip(math.exp(float(theta[0])), 0.05, 20.0)),
        cost_weight=float(np.clip(expit(float(theta[1])), 0.001, 0.999)),
        positive_bias=float(np.clip(expit(float(theta[2])), 0.001, 0.999)),
    )


def policy_parameter_log_likelihood(
    data: PolicyData,
    policy: str,
    theta: np.ndarray,
    base: PolicyConfig | None = None,
) -> float:
    config = _config_from_parameters(base or PolicyConfig(), theta)
    return policy_log_likelihood(data, policy, config)


def fit_policy_parameters(
    data: PolicyData,
    policy: str,
    base: PolicyConfig | None = None,
) -> dict[str, Any]:
    cfg = base or PolicyConfig()
    if policy in {"fixed", "random"}:
        raise ValueError("fixed and random policies have no free parameters")
    initial = _parameter_vector(cfg)
    bounds = [(-3.0, 3.0), (-5.0, 5.0), (-5.0, 5.0)]
    result = minimize(
        lambda theta: -policy_parameter_log_likelihood(data, policy, theta, cfg),
        initial,
        method="L-BFGS-B",
        bounds=bounds,
    )
    theta = np.asarray(result.x, dtype=float)
    n = len(data.test)
    log_likelihood = -float(result.fun)
    return {
        "policy": policy,
        "theta": theta,
        "temperature": float(np.clip(math.exp(theta[0]), 0.05, 20.0)),
        "cost_weight": float(np.clip(expit(theta[1]), 0.001, 0.999)),
        "positive_bias": float(np.clip(expit(theta[2]), 0.001, 0.999)),
        "log_likelihood": log_likelihood,
        "bic": -2.0 * log_likelihood + 3 * math.log(n),
        "converged": bool(result.success),
    }


def _laplace_policy_draws(
    data: PolicyData,
    policy: str,
    fit: Mapping[str, Any],
    cfg: PolicyConfig,
    rng: np.random.Generator,
) -> np.ndarray:
    theta = np.asarray(fit["theta"], dtype=float)
    dimension = len(theta)
    step = 0.05
    hessian = np.zeros((dimension, dimension))
    for i in range(dimension):
        for j in range(dimension):
            delta_i = np.zeros(dimension)
            delta_j = np.zeros(dimension)
            delta_i[i] = step
            delta_j[j] = step
            hessian[i, j] = (
                -policy_parameter_log_likelihood(data, policy, theta + delta_i + delta_j, cfg)
                + policy_parameter_log_likelihood(data, policy, theta + delta_i - delta_j, cfg)
                + policy_parameter_log_likelihood(data, policy, theta - delta_i + delta_j, cfg)
                - policy_parameter_log_likelihood(data, policy, theta - delta_i - delta_j, cfg)
            ) / (4.0 * step * step)
    hessian = 0.5 * (hessian + hessian.T)
    eigenvalues, eigenvectors = np.linalg.eigh(hessian)
    eigenvalues = np.clip(eigenvalues, 1e-8, None)
    covariance = (eigenvectors / eigenvalues) @ eigenvectors.T
    return theta + rng.normal(size=(cfg.n_parameter_draws, dimension)) @ np.linalg.cholesky(covariance).T


def run_policy_parameter_sbc(config: PolicyConfig | None = None) -> dict[str, Any]:
    """Laplace SBC for the meta-EIG policy's softmax parameters.

    The policy is a POMDP test-selection rule, but the parameter posterior is a local Laplace
    approximation; this artifact is not a NUTS posterior or a human result.
    """
    cfg = config or PolicyConfig()
    rng = np.random.default_rng(cfg.seed + 313)
    parameter_names = ("temperature", "cost_weight", "positive_bias")
    ranks = {name: [] for name in parameter_names}
    coverage = {name: [] for name in parameter_names}
    convergence = 0
    for _ in range(cfg.n_parameter_sbc):
        true_cfg = replace(
            cfg,
            temperature=float(np.exp(rng.uniform(math.log(0.3), math.log(3.0)))),
            cost_weight=float(rng.uniform(0.02, 0.80)),
            positive_bias=float(rng.uniform(0.05, 0.95)),
            seed=int(rng.integers(0, 2**31 - 1)),
        )
        data, _ = simulate_policy_data("meta_eig", true_cfg)
        fit = fit_policy_parameters(data, "meta_eig", cfg)
        convergence += int(fit["converged"])
        draws = _laplace_policy_draws(data, "meta_eig", fit, cfg, rng)
        for index, name in enumerate(parameter_names):
            true_value = float(getattr(true_cfg, name))
            column = draws[:, index]
            if name == "temperature":
                column = np.clip(np.exp(column), 0.05, 20.0)
            else:
                column = np.clip(expit(column), 0.001, 0.999)
            ranks[name].append(float((column < true_value).mean()))
            low, high = np.quantile(column, [0.025, 0.975])
            coverage[name].append(float(low <= true_value <= high))
    metrics = {name: _rank_metrics(np.asarray(ranks[name]), np.asarray(coverage[name])) for name in parameter_names}
    passed = all(
        cfg.parameter_sbc_low <= metrics[name]["coverage"] <= cfg.parameter_sbc_high
        and metrics[name]["chi_square"] <= 21.666
        for name in parameter_names
    )
    return {
        "analysis": "stage0i_policy_parameter_sbc",
        "scope": SCOPE,
        "sbc_type": "laplace_approximate_continuous_parameter_sbc",
        "policy": "meta_eig",
        "parameter_names": list(parameter_names),
        "config": asdict(cfg),
        "metrics": metrics,
        "convergence_rate": convergence / cfg.n_parameter_sbc,
        "decision": (
            "CRT_STAGE0I_POLICY_PARAMETER_SBC_PASS"
            if passed
            else "CRT_STAGE0I_POLICY_PARAMETER_SBC_REVIEW"
        ),
        "note": (
            "Local Laplace SBC for the meta-EIG policy parameters; not NUTS and not human evidence."
        ),
    }


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


def run_policy_recovery(config: PolicyConfig | None = None) -> dict[str, Any]:
    cfg = config or PolicyConfig()
    confusion = np.zeros((len(POLICIES), len(POLICIES)), dtype=int)
    for true_index, policy in enumerate(POLICIES):
        for simulation in range(cfg.n_simulations):
            local = PolicyConfig(**{**asdict(cfg), "seed": cfg.seed + 1000 * true_index + simulation})
            data, _ = simulate_policy_data(policy, local)
            fit = fit_policy_choice(data, local)
            selected = POLICIES.index(fit["selected_by_bic"])
            confusion[true_index, selected] += 1
    rows = confusion.sum(axis=1)
    per_policy = {
        policy: float(confusion[index, index] / max(rows[index], 1))
        for index, policy in enumerate(POLICIES)
    }
    minimum = min(per_policy.values())
    return {
        "analysis": "stage0i_policy_recovery",
        "scope": SCOPE,
        "policies": list(POLICIES),
        "config": asdict(cfg),
        "confusion": confusion.tolist(),
        "per_policy_accuracy": per_policy,
        "minimum_accuracy": float(minimum),
        "decision": (
            "CRT_STAGE0I_POLICY_RECOVERY_PASS"
            if minimum >= cfg.recovery_threshold
            else "CRT_STAGE0I_POLICY_RECOVERY_REVIEW"
        ),
        "note": "Policy-choice recovery in simulation; it does not show that participants use a policy.",
    }


def run_policy_sbc(config: PolicyConfig | None = None) -> dict[str, Any]:
    """Discrete policy-model calibration.

    This is a rank calibration for a six-way discrete model, not continuous-parameter SBC. It is
    labelled accordingly so it cannot be mistaken for posterior calibration.
    """
    cfg = config or PolicyConfig()
    ranks: list[int] = []
    correct = 0
    for true_index, policy in enumerate(POLICIES):
        for simulation in range(cfg.n_simulations):
            local = PolicyConfig(**{**asdict(cfg), "seed": cfg.seed + 5000 * true_index + simulation})
            data, _ = simulate_policy_data(policy, local)
            fit = fit_policy_choice(data, local)
            ordered = sorted(POLICIES, key=lambda name: fit["scores"][name], reverse=True)
            rank = ordered.index(policy)
            ranks.append(rank)
            correct += int(rank == 0)
    return {
        "analysis": "stage0i_policy_sbc",
        "scope": SCOPE,
        "sbc_type": "discrete_policy_model_rank_not_continuous_parameter_sbc",
        "config": asdict(cfg),
        "mean_rank": float(np.mean(ranks)),
        "top1_accuracy": float(correct / len(ranks)),
        "n": len(ranks),
        "decision": (
            "CRT_STAGE0I_POLICY_SBC_PASS"
            if correct / len(ranks) >= cfg.recovery_threshold
            else "CRT_STAGE0I_POLICY_SBC_REVIEW"
        ),
        "note": "Discrete policy-choice calibration; not a substitute for continuous-parameter SBC.",
    }


def write_artifact(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value)!r}")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("results/crt/CRT_STAGE0I_POLICY_RECOVERY.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    cfg = PolicyConfig(n_participants=4, n_trials=12, n_simulations=1)
    payload = run_policy_recovery(cfg)
    if args.write:
        write_artifact(payload, args.out)
    print(json.dumps({"decision": payload["decision"], "minimum": payload["minimum_accuracy"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
