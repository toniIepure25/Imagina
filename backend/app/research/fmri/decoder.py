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
    """Train ridge regression decoder with fold-safe inner CV for alpha selection.

    X_train: [n_images, n_voxels] — mean beta per image
    Y_train: [n_images, embedding_dim] — target CLIP embeddings

    No statistic derived from an inner-validation fold (or from the eventual
    outer test set, which this function never sees) may enter fitting:
    - Each inner fold fits its own voxel mean/std and target mean on the
      inner-train rows only, and applies those same statistics to transform
      the inner-validation rows.
    - After alpha selection, voxel normalization, target centering, and the
      final ridge fit are all refit on the complete outer training set
      passed in here. The returned voxel_mean/voxel_std/target_mean are
      exactly the statistics a caller must use to transform any held-out
      (val/test) data — TrainedDecoder.predict() does this automatically.
    """
    if config is None:
        config = DecoderConfig()

    rng = np.random.default_rng(config.random_seed)
    n_images, n_voxels = X_train.shape
    embedding_dim = Y_train.shape[1]

    fold_indices = np.arange(n_images)
    rng.shuffle(fold_indices)
    folds = np.array_split(fold_indices, config.inner_cv_folds)

    cv_scores: dict[float, float] = {}
    for alpha in config.alpha_candidates:
        fold_scores = []
        for fold_idx in range(config.inner_cv_folds):
            val_idx = folds[fold_idx]
            train_idx = np.concatenate([folds[j] for j in range(config.inner_cv_folds) if j != fold_idx])

            X_inner_train, X_inner_val = X_train[train_idx], X_train[val_idx]
            Y_inner_train, Y_inner_val = Y_train[train_idx], Y_train[val_idx]

            fold_voxel_mean = X_inner_train.mean(axis=0)
            fold_voxel_std = np.clip(X_inner_train.std(axis=0), 1e-8, None)
            X_tr = (X_inner_train - fold_voxel_mean) / fold_voxel_std
            X_val = (X_inner_val - fold_voxel_mean) / fold_voxel_std

            if config.normalize_targets:
                fold_target_mean = Y_inner_train.mean(axis=0)
                Y_tr = Y_inner_train - fold_target_mean
                Y_val = Y_inner_val - fold_target_mean
            else:
                Y_tr, Y_val = Y_inner_train, Y_inner_val

            W = _solve_ridge(X_tr, Y_tr, alpha)
            preds = X_val @ W
            cos_sim = _batch_cosine_similarity(preds, Y_val)
            fold_scores.append(float(np.mean(cos_sim)))

        cv_scores[alpha] = float(np.mean(fold_scores))

    best_alpha = max(cv_scores, key=lambda a: cv_scores[a])

    voxel_mean = X_train.mean(axis=0)
    voxel_std = np.clip(X_train.std(axis=0), 1e-8, None)
    X_z = (X_train - voxel_mean) / voxel_std

    target_mean = None
    Y_centered = Y_train
    if config.normalize_targets:
        target_mean = Y_train.mean(axis=0)
        Y_centered = Y_train - target_mean

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
    """Solve ridge regression, using whichever formulation is mathematically
    equivalent but computationally practical for the given shape.

    Primal: W = (X^T X + alpha I)^{-1} X^T Y                    — O(n_features^3)
    Dual:   W = X^T (X X^T + alpha I)^{-1} Y                     — O(n_samples^3)

    These give identical W (up to floating-point error) for any alpha > 0.
    The dual form is used whenever n_samples < n_features, which is the
    common case for ROI-level fMRI decoders (~9000 training images vs
    ~15,000+ voxels) — the primal form would otherwise need to allocate and
    factor an n_features x n_features matrix that may not fit in memory.
    """
    n_samples, n_features = X.shape
    if n_samples < n_features:
        K = X @ X.T + alpha * np.eye(n_samples)
        beta = np.linalg.solve(K, Y)
        W = X.T @ beta
    else:
        XtX = X.T @ X + alpha * np.eye(n_features)
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


def two_way_identification(
    predictions: NDArray[np.float64],
    targets: NDArray[np.float64],
    seed: int = 42,
) -> dict[str, Any]:
    """Conventional two-way (2AFC) identification accuracy.

    For every ordered pair (i, j) with i != j, the trial is scored correct
    when sim(pred_i, true_i) > sim(pred_i, true_j) — i.e. prediction i is
    closer to its own true target than to a foil drawn from another trial's
    true target. This is the standard 2AFC identification statistic used in
    the encoding/decoding literature; chance is 0.5. It is NOT the same
    statistic as requiring the true pair to be simultaneously the row-argmax
    and column-argmax of the similarity matrix (that mutual-nearest-neighbor
    quantity is reported separately as mutual_top1_rate).

    Ties (sim equal) are broken as incorrect, so the reported accuracy is
    conservative.
    """
    n = predictions.shape[0]
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    tgt_norm = targets / np.clip(np.linalg.norm(targets, axis=1, keepdims=True), 1e-8, None)

    sim_matrix = pred_norm @ tgt_norm.T  # [n, n], sim_matrix[i, j] = sim(pred_i, true_j)
    own_sim = np.diag(sim_matrix)  # sim(pred_i, true_i)

    n_correct = 0
    n_pairs = 0
    for i in range(n):
        foil_sims = np.delete(sim_matrix[i], i)
        n_correct += int(np.sum(own_sim[i] > foil_sims))
        n_pairs += foil_sims.shape[0]

    accuracy = float(n_correct / n_pairs) if n_pairs > 0 else float("nan")

    return {
        "two_way_identification_accuracy": accuracy,
        "pair_count": n_pairs,
        "chance": 0.5,
        "n_trials": n,
        "tie_handling": "ties_scored_as_incorrect",
        "seed": seed,
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
