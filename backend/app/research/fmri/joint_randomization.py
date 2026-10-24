"""Joint randomization (permutation test) implementation for C3 inference.

Implements:
- Within-participant target shuffling
- Frozen prediction vectors
- Candidate-pool-preserving rescoring
- 100,000 joint randomizations (configurable)
- Deterministic seed registry
- Group mean participant Delta (n=4 case)
- Monte Carlo p-value with finite-sample correction: p = (extreme + 1) / (n + 1)
- Supplementary exact sign-flip test
- Leave-one-participant-out aggregation
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PermutationTestConfig:
    n_permutations: int = 100_000
    seed: int = 20260724
    n_candidates: int = 12
    metric: str = "mrr"
    correction: str = "monte_carlo_finite_sample"
    alpha: float = 0.05

    def spec_hash(self) -> str:
        blob = json.dumps(self.__dict__, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


def compute_mrr(ranks: NDArray[np.int64]) -> float:
    """Compute Mean Reciprocal Rank from 1-indexed ranks."""
    return float(np.mean(1.0 / ranks.astype(np.float64)))


def compute_ranks(
    predictions: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
) -> NDArray[np.int64]:
    """Compute retrieval ranks for each trial."""
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    sims = pred_norm @ pool_norm.T

    n_trials = predictions.shape[0]
    ranks = np.zeros(n_trials, dtype=np.int64)
    for i in range(n_trials):
        sorted_idx = np.argsort(-sims[i])
        rank_pos = np.where(sorted_idx == target_indices[i])[0]
        ranks[i] = int(rank_pos[0]) + 1 if len(rank_pos) > 0 else candidate_pool.shape[0]
    return ranks


def within_subject_permutation_test(
    predictions: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
    config: PermutationTestConfig | None = None,
) -> dict[str, Any]:
    """Run within-subject permutation test for a single participant.

    Shuffles target assignments while preserving the candidate pool.
    Uses Monte Carlo p-value: p = (extreme_count + 1) / (n_permutations + 1)
    """
    if config is None:
        config = PermutationTestConfig()

    observed_ranks = compute_ranks(predictions, candidate_pool, target_indices)
    observed_mrr = compute_mrr(observed_ranks)

    rng = np.random.default_rng(config.seed)
    n_trials = len(target_indices)
    null_mrrs = np.zeros(config.n_permutations, dtype=np.float64)

    unique_targets = np.unique(target_indices)  # noqa: F841 — kept for potential future use

    for perm_idx in range(config.n_permutations):
        shuffled = rng.permutation(target_indices)
        perm_ranks = compute_ranks(predictions, candidate_pool, shuffled)
        null_mrrs[perm_idx] = compute_mrr(perm_ranks)

    extreme_count = int(np.sum(null_mrrs >= observed_mrr))
    p_value = (extreme_count + 1) / (config.n_permutations + 1)

    return {
        "observed_mrr": observed_mrr,
        "null_mean": float(np.mean(null_mrrs)),
        "null_std": float(np.std(null_mrrs)),
        "null_percentiles": {
            "2.5": float(np.percentile(null_mrrs, 2.5)),
            "5": float(np.percentile(null_mrrs, 5)),
            "50": float(np.percentile(null_mrrs, 50)),
            "95": float(np.percentile(null_mrrs, 95)),
            "97.5": float(np.percentile(null_mrrs, 97.5)),
            "99": float(np.percentile(null_mrrs, 99)),
        },
        "p_value": p_value,
        "extreme_count": extreme_count,
        "n_permutations": config.n_permutations,
        "significant": p_value < config.alpha,
        "effect_size_delta": observed_mrr - float(np.mean(null_mrrs)),
        "config_hash": config.spec_hash(),
        "n_trials": n_trials,
        "n_candidates": candidate_pool.shape[0],
        "correction": config.correction,
    }


def group_permutation_test(
    participant_results: list[dict[str, Any]],
    config: PermutationTestConfig | None = None,
) -> dict[str, Any]:
    """Run group-level test across participants.

    Uses mean participant delta as the test statistic.
    Supplementary exact sign-flip test for n=4.
    """
    if config is None:
        config = PermutationTestConfig()

    deltas = np.array([r["effect_size_delta"] for r in participant_results])
    observed_group_delta = float(np.mean(deltas))

    n_participants = len(participant_results)

    rng = np.random.default_rng(config.seed + 1)
    null_deltas = np.zeros(config.n_permutations, dtype=np.float64)
    for i in range(config.n_permutations):
        signs = rng.choice([-1, 1], size=n_participants)
        null_deltas[i] = float(np.mean(deltas * signs))

    extreme_count = int(np.sum(null_deltas >= observed_group_delta))
    p_value = (extreme_count + 1) / (config.n_permutations + 1)

    exact_sign_flip = None
    if n_participants <= 8:
        n_exact = 2 ** n_participants
        exact_nulls = np.zeros(n_exact, dtype=np.float64)
        for code in range(n_exact):
            signs = np.array([(1 if (code >> bit) & 1 else -1) for bit in range(n_participants)])
            exact_nulls[code] = float(np.mean(deltas * signs))
        exact_extreme = int(np.sum(exact_nulls >= observed_group_delta))
        exact_sign_flip = {
            "n_configurations": n_exact,
            "extreme_count": exact_extreme,
            "p_value": exact_extreme / n_exact,
            "min_achievable_p": 1 / n_exact,
        }

    loo_results = []
    for i in range(n_participants):
        remaining = np.delete(deltas, i)
        loo_results.append({
            "excluded_participant": i,
            "remaining_mean_delta": float(np.mean(remaining)),
            "excluded_delta": float(deltas[i]),
        })

    return {
        "observed_group_delta": observed_group_delta,
        "participant_deltas": deltas.tolist(),
        "n_participants": n_participants,
        "p_value_mc": p_value,
        "extreme_count_mc": extreme_count,
        "n_permutations": config.n_permutations,
        "significant_mc": p_value < config.alpha,
        "exact_sign_flip": exact_sign_flip,
        "leave_one_out": loo_results,
        "config_hash": config.spec_hash(),
    }


def compute_chance_mrr(n_candidates: int) -> float:
    """Compute expected MRR under uniform random ranking.

    For a uniformly random ranking over K candidates:
    E[MRR] = H_K / K where H_K = sum(1/k for k=1..K)
    """
    harmonic = sum(1.0 / k for k in range(1, n_candidates + 1))
    return harmonic / n_candidates


def calibration_test_strict_null(
    n_trials: int = 100,
    n_candidates: int = 12,
    n_simulations: int = 1000,
    config: PermutationTestConfig | None = None,
    target_type_i_rate: float = 0.05,
    tolerance: float = 0.02,
) -> dict[str, Any]:
    """Calibration: under strict null, Type-I rate should match alpha.

    Generates random predictions and runs permutation test to verify
    that p < alpha occurs at approximately the expected rate.
    """
    if config is None:
        config = PermutationTestConfig(n_permutations=1000)

    rng = np.random.default_rng(config.seed + 100)
    rejections = 0

    for sim in range(n_simulations):
        predictions = rng.standard_normal((n_trials, 768))
        candidate_pool = rng.standard_normal((n_candidates, 768))
        target_indices = rng.integers(0, n_candidates, size=n_trials)

        sim_config = PermutationTestConfig(
            n_permutations=config.n_permutations,
            seed=config.seed + sim,
            n_candidates=n_candidates,
        )
        result = within_subject_permutation_test(predictions, candidate_pool, target_indices, sim_config)
        if result["significant"]:
            rejections += 1

    observed_rate = rejections / n_simulations
    return {
        "n_simulations": n_simulations,
        "n_rejections": rejections,
        "observed_type_i_rate": observed_rate,
        "expected_rate": target_type_i_rate,
        "within_tolerance": abs(observed_rate - target_type_i_rate) < tolerance,
        "tolerance": tolerance,
    }


def calibration_test_known_positive(
    effect_strength: float = 2.0,
    n_trials: int = 100,
    n_candidates: int = 12,
    n_simulations: int = 100,
    config: PermutationTestConfig | None = None,
) -> dict[str, Any]:
    """Calibration: with known positive effect, test should reject null frequently."""
    if config is None:
        config = PermutationTestConfig(n_permutations=1000)

    rng = np.random.default_rng(config.seed + 200)
    rejections = 0

    for sim in range(n_simulations):
        candidate_pool = rng.standard_normal((n_candidates, 768)).astype(np.float64)
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)
        target_indices = rng.integers(0, n_candidates, size=n_trials)
        predictions = candidate_pool[target_indices] * effect_strength + rng.standard_normal((n_trials, 768)) * 0.1

        sim_config = PermutationTestConfig(
            n_permutations=config.n_permutations,
            seed=config.seed + 200 + sim,
            n_candidates=n_candidates,
        )
        result = within_subject_permutation_test(predictions, candidate_pool, target_indices, sim_config)
        if result["significant"]:
            rejections += 1

    return {
        "n_simulations": n_simulations,
        "n_rejections": rejections,
        "power": rejections / n_simulations,
        "effect_strength": effect_strength,
        "expected_high_power": True,
    }
