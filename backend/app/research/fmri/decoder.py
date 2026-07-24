"""Ridge-based perception decoder for Scientific Gate C3.

Trains a subject-specific ridge regression mapping from voxel betas
to frozen CLIP image embeddings. Includes:
- Voxel selection (ROI mask + ncsnr threshold)
- Z-score normalization (fit on training data only)
- Ridge alpha selection via inner cross-validation
- Evaluation via cosine similarity and MRR
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class DecoderConfig:
    roi_id: str = "nsdgeneral"
    ncsnr_threshold: float = 0.0
    alpha_candidates: tuple[float, ...] = (0.1, 1.0, 10.0, 100.0, 1000.0, 10000.0, 100000.0)
    inner_cv_folds: int = 5
    normalize_targets: bool = True
    random_seed: int = 42

    def spec_hash(self) -> str:
        blob = json.dumps(self.__dict__, sort_keys=True, default=str).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


@dataclass
class TrainedDecoder:
    weights: NDArray[np.float64]
    bias: NDArray[np.float64]
    alpha: float
    voxel_mean: NDArray[np.float64]
    voxel_std: NDArray[np.float64]
    target_mean: NDArray[np.float64] | None
    config: DecoderConfig
    n_train_images: int = 0
    n_voxels: int = 0
    inner_cv_scores: dict[float, float] = field(default_factory=dict)

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        X_z = (X - self.voxel_mean) / np.clip(self.voxel_std, 1e-8, None)
        preds = X_z @ self.weights + self.bias
        if self.target_mean is not None and self.config.normalize_targets:
            preds = preds + self.target_mean
        return preds


def select_voxels(
    roi_mask: NDArray[np.int32],
    ncsnr: NDArray[np.float32],
    roi_id: str = "nsdgeneral",
    ncsnr_threshold: float = 0.0,
) -> NDArray[np.bool_]:
    """Select voxels based on ROI membership and ncsnr quality."""
    if roi_id == "nsdgeneral":
        in_roi = roi_mask > 0
    elif roi_id in ("V1", "V2", "V3", "hV4"):
        label_map = {"V1": 1, "V2": 2, "V3": 3, "hV4": 4}
        in_roi = roi_mask == label_map[roi_id]
    elif roi_id in ("ventral", "lateral", "parietal"):
        label_map = {"ventral": 1, "lateral": 2, "parietal": 3}
        in_roi = roi_mask == label_map[roi_id]
    else:
        in_roi = roi_mask > 0

    quality_ok = ncsnr > ncsnr_threshold
    return in_roi & quality_ok


def train_ridge_decoder(
    X_train: NDArray[np.float64],
    Y_train: NDArray[np.float64],
    config: DecoderConfig | None = None,
) -> TrainedDecoder:
    """Train ridge regression decoder with inner CV for alpha selection.

    X_train: [n_images, n_voxels] — mean beta per image
    Y_train: [n_images, embedding_dim] — target CLIP embeddings
    """
    if config is None:
        config = DecoderConfig()

    rng = np.random.default_rng(config.random_seed)
    n_images, n_voxels = X_train.shape
    embedding_dim = Y_train.shape[1]

    voxel_mean = X_train.mean(axis=0)
    voxel_std = X_train.std(axis=0)
    voxel_std = np.clip(voxel_std, 1e-8, None)
    X_z = (X_train - voxel_mean) / voxel_std

    target_mean = None
    Y_centered = Y_train
    if config.normalize_targets:
        target_mean = Y_train.mean(axis=0)
        Y_centered = Y_train - target_mean

    fold_indices = np.arange(n_images)
    rng.shuffle(fold_indices)
    folds = np.array_split(fold_indices, config.inner_cv_folds)

    cv_scores: dict[float, float] = {}
    for alpha in config.alpha_candidates:
        fold_scores = []
        for fold_idx in range(config.inner_cv_folds):
            val_idx = folds[fold_idx]
            train_idx = np.concatenate([folds[j] for j in range(config.inner_cv_folds) if j != fold_idx])

            X_tr, X_val = X_z[train_idx], X_z[val_idx]
            Y_tr, Y_val = Y_centered[train_idx], Y_centered[val_idx]

            W = _solve_ridge(X_tr, Y_tr, alpha)
            preds = X_val @ W
            cos_sim = _batch_cosine_similarity(preds, Y_val)
            fold_scores.append(float(np.mean(cos_sim)))

        cv_scores[alpha] = float(np.mean(fold_scores))

    best_alpha = max(cv_scores, key=lambda a: cv_scores[a])
    W_final = _solve_ridge(X_z, Y_centered, best_alpha)
    bias = np.zeros(embedding_dim)

    return TrainedDecoder(
        weights=W_final,
        bias=bias,
        alpha=best_alpha,
        voxel_mean=voxel_mean,
        voxel_std=voxel_std,
        target_mean=target_mean,
        config=config,
        n_train_images=n_images,
        n_voxels=n_voxels,
        inner_cv_scores=cv_scores,
    )


def _solve_ridge(X: NDArray[np.float64], Y: NDArray[np.float64], alpha: float) -> NDArray[np.float64]:
    """Solve ridge regression: W = (X^T X + alpha I)^{-1} X^T Y."""
    n_voxels = X.shape[1]
    XtX = X.T @ X + alpha * np.eye(n_voxels)
    XtY = X.T @ Y
    W = np.linalg.solve(XtX, XtY)
    return W


def _batch_cosine_similarity(A: NDArray[np.float64], B: NDArray[np.float64]) -> NDArray[np.float64]:
    """Row-wise cosine similarity between A and B."""
    A_norm = A / np.clip(np.linalg.norm(A, axis=1, keepdims=True), 1e-8, None)
    B_norm = B / np.clip(np.linalg.norm(B, axis=1, keepdims=True), 1e-8, None)
    return np.sum(A_norm * B_norm, axis=1)


def evaluate_retrieval(
    predictions: NDArray[np.float64],
    targets: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
) -> dict[str, Any]:
    """Evaluate retrieval performance (MRR, top-k, median rank).

    predictions: [n_trials, embedding_dim]
    targets: [n_trials, embedding_dim] (ground truth per trial)
    candidate_pool: [n_candidates, embedding_dim]
    target_indices: [n_trials] — index into candidate_pool for each trial
    """
    n_trials = predictions.shape[0]
    n_candidates = candidate_pool.shape[0]

    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)

    similarities = pred_norm @ pool_norm.T  # [n_trials, n_candidates]

    ranks = np.zeros(n_trials, dtype=np.int64)
    for i in range(n_trials):
        sim_row = similarities[i]
        sorted_idx = np.argsort(-sim_row)
        rank = int(np.where(sorted_idx == target_indices[i])[0][0]) + 1
        ranks[i] = rank

    reciprocal_ranks = 1.0 / ranks.astype(np.float64)
    mrr = float(np.mean(reciprocal_ranks))
    top1 = float(np.mean(ranks == 1))
    top3 = float(np.mean(ranks <= 3))
    top5 = float(np.mean(ranks <= 5))
    median_rank = float(np.median(ranks))

    cos_sims = _batch_cosine_similarity(predictions, targets)

    return {
        "mrr": mrr,
        "top1_accuracy": top1,
        "top3_accuracy": top3,
        "top5_accuracy": top5,
        "median_rank": median_rank,
        "mean_cosine_similarity": float(np.mean(cos_sims)),
        "n_trials": n_trials,
        "n_candidates": n_candidates,
        "ranks": ranks.tolist(),
        "reciprocal_ranks": reciprocal_ranks.tolist(),
    }


def compute_shuffled_null(
    predictions: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
    n_permutations: int = 10000,
    seed: int = 42,
) -> dict[str, Any]:
    """Compute null distribution of MRR under shuffled pairings."""
    rng = np.random.default_rng(seed)
    n_trials = predictions.shape[0]

    null_mrrs = []
    for _ in range(n_permutations):
        shuffled_targets = rng.permutation(target_indices)
        pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
        pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
        sims = pred_norm @ pool_norm.T

        rrs = []
        for i in range(n_trials):
            sorted_idx = np.argsort(-sims[i])
            rank = int(np.where(sorted_idx == shuffled_targets[i])[0][0]) + 1
            rrs.append(1.0 / rank)
        null_mrrs.append(float(np.mean(rrs)))

    null_mrrs_arr = np.array(null_mrrs)
    return {
        "null_mean": float(np.mean(null_mrrs_arr)),
        "null_std": float(np.std(null_mrrs_arr)),
        "null_percentiles": {
            "5": float(np.percentile(null_mrrs_arr, 5)),
            "50": float(np.percentile(null_mrrs_arr, 50)),
            "95": float(np.percentile(null_mrrs_arr, 95)),
            "99": float(np.percentile(null_mrrs_arr, 99)),
        },
        "n_permutations": n_permutations,
    }
