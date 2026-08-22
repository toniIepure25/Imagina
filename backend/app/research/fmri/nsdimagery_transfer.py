"""Shared NSD-Imagery beta extraction and frozen-decoder retrieval for the
C3 vision cross-session validation and the sealed H2 zero-shot imagery
transfer. All preprocessing is the frozen H1 perception preprocessing; no
imagery-derived statistic is ever computed.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from numpy.typing import NDArray

from app.research.fmri.decoder import TrainedDecoder, evaluate_retrieval


def load_frozen_decoder(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return pickle.load(f)


def extract_imagery_rows(
    imagery_betas_path: Path, beta_coords: NDArray, row_indices: list[int]
) -> NDArray:
    """Extract [len(row_indices), n_voxels] float32 from betas_nsdimagery.hdf5
    at the frozen ROI voxel coordinates. Raw int16 -> float32, no scaling
    (matches the perception extraction the decoder was trained on).

    betas_nsdimagery.hdf5 is chunked (n_trials, 1, 1, 1) - i.e. optimized for
    reading all trials of a single voxel at once. Reading per-voxel
    (betas[:, i, j, k]) is therefore chunk-aligned and fast; reading per-row
    (betas[row]) touches every chunk and is pathologically slow / OOMs. This
    matches the per-voxel access pattern used by the perception extraction.
    """
    n_vox = len(beta_coords)
    row_arr = np.asarray(row_indices)
    out = np.zeros((len(row_indices), n_vox), dtype=np.float32)
    with h5py.File(str(imagery_betas_path), "r") as hf:
        betas = hf["betas"]
        for v_idx in range(n_vox):
            i, j, k = beta_coords[v_idx]
            col = betas[:, i, j, k]  # all trials for this voxel (one chunk)
            out[:, v_idx] = col[row_arr].astype(np.float32)
    return out


def retrieval_with_frozen_decoder(
    decoder: TrainedDecoder,
    betas: NDArray,
    candidate_pool: NDArray,
    target_pool_indices: NDArray,
) -> dict[str, Any]:
    """Apply the frozen perception decoder to imagery/vision betas and
    evaluate retrieval against the frozen 12-item candidate pool.
    target_pool_indices[i] is the correct pool index for trial i.
    """
    predictions = decoder.predict(betas.astype(np.float64))
    targets = candidate_pool[target_pool_indices]
    return evaluate_retrieval(predictions, targets, candidate_pool, target_pool_indices)


def two_way_from_predictions(
    decoder: TrainedDecoder, betas: NDArray, candidate_pool: NDArray, target_pool_indices: NDArray
) -> float:
    """2AFC accuracy against the candidate pool: for each trial, is the true
    candidate closer than each other candidate? Chance 0.5.
    """
    predictions = decoder.predict(betas.astype(np.float64))
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    sims = pred_norm @ pool_norm.T  # [n_trials, n_candidates]
    n_correct = 0
    n_pairs = 0
    for i in range(len(betas)):
        true_idx = int(target_pool_indices[i])
        true_sim = sims[i, true_idx]
        foils = np.delete(sims[i], true_idx)
        n_correct += int(np.sum(true_sim > foils))
        n_pairs += foils.shape[0]
    return float(n_correct / n_pairs) if n_pairs else float("nan")


def prediction_collapse_diagnostic(
    decoder: TrainedDecoder, betas: NDArray, candidate_pool: NDArray, set_pool_labels: list[int]
) -> dict[str, Any]:
    """Detect degenerate single-candidate prediction collapse.

    Cross-session distribution shift can make the frozen linear decoder emit
    near-constant predictions that land nearest ONE candidate for (almost)
    every trial, regardless of the true stimulus. The exact target-label
    permutation test cannot guard against this: if one physical stimulus
    happens to share the collapse target, its trials all rank #1 and inflate
    MRR, producing a spuriously "significant" p-value. This diagnostic flags
    that failure mode so a collapse-driven result is not reported as transfer.

    Returns the fraction of trials whose within-set argmax is the single most
    common candidate; `degenerate` is True when that fraction exceeds 0.5
    (chance for 6 candidates is ~0.167, so >0.5 is a gross concentration).
    """
    predictions = decoder.predict(betas.astype(np.float64))
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    set_cols = list(set_pool_labels)
    sims_set = pred_norm @ pool_norm[set_cols].T  # [n_trials, n_set]
    within_argmax = np.array(set_cols)[sims_set.argmax(axis=1)]
    counts = {int(c): int((within_argmax == c).sum()) for c in set_cols}
    n = len(betas)
    top_candidate = max(counts, key=counts.get)
    top_fraction = counts[top_candidate] / n
    return {
        "n_trials": n,
        "within_set_argmax_counts": counts,
        "dominant_candidate": top_candidate,
        "dominant_fraction": float(top_fraction),
        "uniform_fraction": 1.0 / len(set_cols),
        "degenerate": bool(top_fraction > 0.5),
        "interpretation": (
            "Predictions collapse onto a single candidate for a majority of trials -> "
            "no genuine stimulus-specific transfer; any permutation-test significance is an "
            "artifact of one true stimulus coinciding with the collapse target."
            if top_fraction > 0.5 else
            "Predictions are distributed across candidates (no gross single-candidate collapse)."
        ),
    }


def sha256_of_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
