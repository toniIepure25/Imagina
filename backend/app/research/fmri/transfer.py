"""Zero-shot perception-to-imagery transfer evaluation for C3-H2.

Applies a frozen perception-trained decoder to imagery betas and evaluates
retrieval performance against the candidate stimulus pool.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from app.research.fmri.decoder import (
    TrainedDecoder,
    _batch_cosine_similarity,
    evaluate_retrieval,
)


def zero_shot_transfer(
    decoder: TrainedDecoder,
    imagery_betas: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
    target_embeddings: NDArray[np.float64],
) -> dict[str, Any]:
    """Apply frozen perception decoder to imagery betas, evaluate retrieval.

    decoder: trained on perception data (frozen, no imagery data seen)
    imagery_betas: [n_trials, n_voxels] imagery fMRI betas
    candidate_pool: [n_candidates, embedding_dim] target embeddings
    target_indices: [n_trials] index of correct target per trial
    target_embeddings: [n_trials, embedding_dim] ground truth per trial
    """
    predictions = decoder.predict(imagery_betas)
    retrieval = evaluate_retrieval(predictions, target_embeddings, candidate_pool, target_indices)

    cosine_per_trial = _batch_cosine_similarity(predictions, target_embeddings)

    return {
        "method": "zero_shot_frozen_perception_decoder",
        "n_trials": int(imagery_betas.shape[0]),
        "n_candidates": int(candidate_pool.shape[0]),
        "retrieval": retrieval,
        "cosine_per_trial": cosine_per_trial.tolist(),
        "mean_cosine": float(np.mean(cosine_per_trial)),
    }


def per_stimulus_analysis(
    decoder: TrainedDecoder,
    imagery_betas: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
    stimulus_ids: NDArray[np.int64],
) -> dict[str, Any]:
    """Compute per-stimulus MRR by averaging trial-level RR within stimulus."""
    predictions = decoder.predict(imagery_betas)

    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    sims = pred_norm @ pool_norm.T

    n_trials = predictions.shape[0]
    rr_per_trial = np.zeros(n_trials)
    for i in range(n_trials):
        sorted_idx = np.argsort(-sims[i])
        rank = int(np.where(sorted_idx == target_indices[i])[0][0]) + 1
        rr_per_trial[i] = 1.0 / rank

    unique_stims = np.unique(stimulus_ids)
    per_stim_mrr = {}
    for stim in unique_stims:
        mask = stimulus_ids == stim
        per_stim_mrr[int(stim)] = float(np.mean(rr_per_trial[mask]))

    return {
        "per_stimulus_mrr": per_stim_mrr,
        "overall_mrr": float(np.mean(rr_per_trial)),
        "n_stimuli": len(unique_stims),
    }


def participant_level_inference(
    participant_mrrs: list[float],
    null_mrr: float,
) -> dict[str, Any]:
    """Perform participant-level sign-flip permutation test.

    With n=4 participants, there are 2^4 = 16 possible sign-flips.
    """
    n = len(participant_mrrs)
    deltas = [mrr - null_mrr for mrr in participant_mrrs]
    observed_mean = float(np.mean(deltas))

    n_perms = 2**n
    null_means = []
    for perm_idx in range(n_perms):
        signs = [(1 if (perm_idx >> i) & 1 == 0 else -1) for i in range(n)]
        flipped = [d * s for d, s in zip(deltas, signs)]
        null_means.append(float(np.mean(flipped)))

    null_means_arr = np.array(null_means)
    p_value = float(np.mean(null_means_arr >= observed_mean))

    return {
        "n_participants": n,
        "participant_mrrs": participant_mrrs,
        "null_mrr": null_mrr,
        "participant_deltas": deltas,
        "observed_mean_delta": observed_mean,
        "sign_flip_p_value": p_value,
        "n_permutations": n_perms,
        "null_distribution_mean": float(np.mean(null_means_arr)),
        "null_distribution_std": float(np.std(null_means_arr)),
        "significant_at_alpha_05": p_value < 0.05,
        "minimum_achievable_p": 1.0 / n_perms,
    }
