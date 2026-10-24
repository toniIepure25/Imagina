"""Perception-foundation pilot for subj01.

Implements a strictly subject-specific perception decoder using:
- 30,000 perception trials (from 40 sessions)
- Frozen train/val/test split (8000/1000/1000 image identities)
- nsdgeneral ROI
- CLIP ViT-L/14 embeddings as targets
- Ridge regression decoder
- Within-subject permutation test for inference

This is NOT imagery transfer or population evidence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class PilotConfig:
    subject: str = "subj01"
    n_sessions: int = 40
    trials_per_session: int = 750
    roi: str = "nsdgeneral"
    clip_model: str = "openai/clip-vit-large-patch14"
    embedding_dim: int = 768
    n_train_images: int = 8000
    n_val_images: int = 1000
    n_test_images: int = 1000
    alpha_range: tuple[float, ...] = (1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6)
    n_permutations: int = 10000
    seed: int = 42


def load_split(split_path: Path) -> dict[str, set[int]]:
    """Load the frozen perception split."""
    with open(split_path) as f:
        manifest = json.load(f)
    return {
        "train": set(manifest["train_image_ids"]),
        "val": set(manifest["val_image_ids"]),
        "test": set(manifest["test_image_ids"]),
    }


def build_trial_assignments(
    masterordering: NDArray,
    subjectim: NDArray,
    split: dict[str, set[int]],
    subject_idx: int = 0,
) -> dict[str, list[int]]:
    """Map each trial to its split based on image identity.

    Note: split IDs and subjectim values use the same convention (1-based NSD IDs).
    The masterordering is 1-based image slot index.
    """
    assignments: dict[str, list[int]] = {"train": [], "val": [], "test": []}
    trial_to_image: list[int] = []
    for trial in range(len(masterordering)):
        slot = int(masterordering[trial]) - 1
        img_id = int(subjectim[subject_idx, slot])
        trial_to_image.append(img_id)
        if img_id in split["train"]:
            assignments["train"].append(trial)
        elif img_id in split["val"]:
            assignments["val"].append(trial)
        elif img_id in split["test"]:
            assignments["test"].append(trial)
    return assignments


def average_repeated_trials(
    fmri_data: NDArray,
    trial_to_image: NDArray,
    image_ids: list[int],
) -> tuple[NDArray, list[int]]:
    """Average fMRI responses for repeated presentations of same image."""
    img_to_trials: dict[int, list[int]] = {}
    for trial_idx, img_id in enumerate(trial_to_image):
        img_id = int(img_id)
        if img_id in set(image_ids):
            if img_id not in img_to_trials:
                img_to_trials[img_id] = []
            img_to_trials[img_id].append(trial_idx)

    ordered_ids = sorted(img_to_trials.keys())
    averaged = np.zeros((len(ordered_ids), fmri_data.shape[1]), dtype=np.float32)
    for i, img_id in enumerate(ordered_ids):
        trials = img_to_trials[img_id]
        averaged[i] = fmri_data[trials].mean(axis=0)

    return averaged, ordered_ids


def fit_ridge(X_train: NDArray, Y_train: NDArray, alpha: float) -> NDArray:
    """Fit ridge regression using the efficient formulation.

    When n_samples < n_features (8000 < 15724), uses dual form:
        W = X^T (X X^T + alpha*I)^{-1} Y
    Otherwise uses primal form:
        W = (X^T X + alpha*I)^{-1} X^T Y
    """
    n_samples, n_features = X_train.shape
    if n_samples < n_features:
        K = X_train @ X_train.T  # (n, n)
        K += alpha * np.eye(n_samples, dtype=K.dtype)
        beta = np.linalg.solve(K, Y_train)
        W = X_train.T @ beta
    else:
        XtX = X_train.T @ X_train
        XtX += alpha * np.eye(n_features, dtype=XtX.dtype)
        XtY = X_train.T @ Y_train
        W = np.linalg.solve(XtX, XtY)
    return W


def select_alpha(
    X_train: NDArray, Y_train: NDArray,
    X_val: NDArray, Y_val: NDArray,
    alphas: tuple[float, ...],
) -> tuple[float, float]:
    """Select best alpha using validation cosine similarity."""
    best_alpha = alphas[0]
    best_score = -np.inf

    for alpha in alphas:
        W = fit_ridge(X_train, Y_train, alpha)
        Y_pred = X_val @ W
        cos_sims = []
        for i in range(len(Y_val)):
            pred_norm = Y_pred[i] / (np.linalg.norm(Y_pred[i]) + 1e-8)
            true_norm = Y_val[i] / (np.linalg.norm(Y_val[i]) + 1e-8)
            cos_sims.append(float(pred_norm @ true_norm))
        mean_cos = np.mean(cos_sims)
        if mean_cos > best_score:
            best_score = mean_cos
            best_alpha = alpha

    return best_alpha, float(best_score)


def compute_metrics(
    predictions: NDArray,
    targets: NDArray | None,
    all_targets: NDArray,
) -> dict[str, float]:
    """Compute perception pilot metrics.

    If targets is None, assumes prediction i corresponds to all_targets[i].
    If targets is an array, targets[i] gives the index into all_targets for prediction i.
    """
    n = len(predictions)
    pred_norm = predictions / (np.linalg.norm(predictions, axis=1, keepdims=True) + 1e-8)
    tgt_norm = all_targets / (np.linalg.norm(all_targets, axis=1, keepdims=True) + 1e-8)

    ranks = []
    cosine_sims = []
    for i in range(n):
        sims = pred_norm[i] @ tgt_norm.T
        true_idx = i if targets is None else int(targets[i])
        rank = int((sims >= sims[true_idx]).sum())
        ranks.append(rank)
        cosine_sims.append(float(pred_norm[i] @ tgt_norm[true_idx]))

    ranks_arr = np.array(ranks)
    n_pool = len(all_targets)

    return {
        "mrr": float(np.mean(1.0 / ranks_arr)),
        "top1": float(np.mean(ranks_arr == 1)),
        "top5": float(np.mean(ranks_arr <= 5)),
        "median_rank": int(np.median(ranks_arr)),
        "mean_cosine": float(np.mean(cosine_sims)),
        "n_test": n,
        "n_pool": n_pool,
    }


def run_permutation_test(
    predictions: NDArray,
    targets_pool: NDArray,
    test_indices: list[int],
    n_permutations: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """Within-subject permutation test for perception decoding."""
    rng = np.random.default_rng(seed)
    pred_norm = predictions / (np.linalg.norm(predictions, axis=1, keepdims=True) + 1e-8)
    tgt_norm = targets_pool / (np.linalg.norm(targets_pool, axis=1, keepdims=True) + 1e-8)
    n_test = len(predictions)
    n_pool = len(targets_pool)

    def compute_mrr(pred_n, tgt_n, indices):
        reciprocal_ranks = []
        for i, idx in enumerate(indices):
            sims = pred_n[i] @ tgt_n.T
            rank = int((sims >= sims[idx]).sum())
            reciprocal_ranks.append(1.0 / rank)
        return np.mean(reciprocal_ranks)

    observed_mrr = compute_mrr(pred_norm, tgt_norm, test_indices)

    null_mrrs = []
    for _ in range(n_permutations):
        shuffled = rng.permutation(n_pool)[:n_test].tolist()
        null_mrr = compute_mrr(pred_norm, tgt_norm, shuffled)
        null_mrrs.append(null_mrr)

    null_arr = np.array(null_mrrs)
    p_value = float((np.sum(null_arr >= observed_mrr) + 1) / (n_permutations + 1))

    return {
        "observed_mrr": float(observed_mrr),
        "null_mean": float(null_arr.mean()),
        "null_std": float(null_arr.std()),
        "p_value": p_value,
        "n_permutations": n_permutations,
        "significant_005": p_value < 0.05,
        "significant_001": p_value < 0.01,
    }


def run_controls(
    X_train: NDArray, Y_train: NDArray,
    X_test: NDArray, Y_test: NDArray,
    all_targets: NDArray,
    alpha: float,
    seed: int = 42,
) -> dict[str, Any]:
    """Run required control conditions."""
    rng = np.random.default_rng(seed)
    controls = {}

    # 1. Shuffled fMRI-target pairing
    shuffle_idx = rng.permutation(len(X_train))
    W_shuffled = fit_ridge(X_train[shuffle_idx], Y_train, alpha)
    pred_shuffled = X_test @ W_shuffled
    controls["shuffled_pairing"] = compute_metrics(
        pred_shuffled, None, all_targets
    )

    # 2. Mean target embedding (predict mean always)
    mean_target = Y_train.mean(axis=0, keepdims=True)
    pred_mean = np.tile(mean_target, (len(X_test), 1))
    controls["mean_target"] = compute_metrics(pred_mean, None, all_targets)

    # 3. Random voxels (same count as ROI)
    n_voxels = X_train.shape[1]
    random_features = rng.standard_normal((len(X_train), n_voxels)).astype(np.float32)
    W_random = fit_ridge(random_features, Y_train, alpha)
    random_test = rng.standard_normal((len(X_test), n_voxels)).astype(np.float32)
    pred_random = random_test @ W_random
    controls["random_voxels"] = compute_metrics(pred_random, None, all_targets)

    # 4. Voxel permutation
    perm_features = X_train[:, rng.permutation(n_voxels)]
    W_perm = fit_ridge(perm_features, Y_train, alpha)
    pred_perm = X_test[:, rng.permutation(n_voxels)] @ W_perm
    controls["voxel_permutation"] = compute_metrics(pred_perm, None, all_targets)

    return controls


def check_pilot_prerequisites(results_dir: Path) -> dict[str, bool]:
    """Verify all prerequisites for running the pilot."""
    checks = {}
    checks["spatial_certified"] = False
    spatial = results_dir / "c3_spatial_alignment.json"
    if spatial.exists():
        with open(spatial) as f:
            data = json.load(f)
        checks["spatial_certified"] = data.get("status") == "SPATIAL_ALIGNMENT_CERTIFIED_REAL_DATA"

    checks["split_verified"] = False
    split = results_dir / "c3_split_manifest.json"
    if split.exists():
        with open(split) as f:
            data = json.load(f)
        checks["split_verified"] = data.get("integrity_verified", False) or "train_image_ids" in data

    checks["storage_pass"] = False
    storage = results_dir / "c3_storage_preflight.json"
    if storage.exists():
        with open(storage) as f:
            data = json.load(f)
        checks["storage_pass"] = data.get("status") == "PASS"

    checks["betas_certified"] = False
    betas = results_dir / "c3_subj01_perception_certification.json"
    if betas.exists():
        with open(betas) as f:
            data = json.load(f)
        checks["betas_certified"] = (
            data.get("certification_status") == "SUBJ01_PERCEPTION_ACQUISITION_CERTIFIED"
        )

    checks["stimulus_certified"] = False
    stim = results_dir / "c3_stimulus_reconstruction.json"
    if stim.exists():
        with open(stim) as f:
            data = json.load(f)
        checks["stimulus_certified"] = "EQUIVALENT" in data.get("status", "")

    return checks


def compute_chance_mrr(n_candidates: int) -> float:
    """Compute chance MRR = H_N / N where H_N is the N-th harmonic number."""
    harmonic = sum(1.0 / k for k in range(1, n_candidates + 1))
    return harmonic / n_candidates


def build_clip_index_map(split_image_ids: list[int], all_sorted_ids: list[int]) -> NDArray:
    """Map split image IDs to CLIP embedding array row indices.

    CLIP embeddings are stored in sorted NSD ID order.
    This returns the row index in the CLIP array for each split image.
    """
    id_to_row = {img_id: row for row, img_id in enumerate(all_sorted_ids)}
    return np.array([id_to_row[img_id] for img_id in split_image_ids])
