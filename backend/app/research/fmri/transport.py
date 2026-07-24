"""Low-capacity imagery state transport for C3-H4.

Tests whether a minimal calibration layer (mean correction, affine ridge,
low-rank linear) can improve the frozen perception decoder's output for
imagery. All transport models are fitted only inside imagery-training folds.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def identity_transport(predictions: NDArray[np.float64]) -> NDArray[np.float64]:
    """No transformation — baseline."""
    return predictions.copy()


def mean_correction_transport(
    predictions: NDArray[np.float64],
    train_predictions: NDArray[np.float64],
    train_targets: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Apply additive mean correction: shift predicted mean to target mean."""
    pred_mean = train_predictions.mean(axis=0)
    target_mean = train_targets.mean(axis=0)
    correction = target_mean - pred_mean
    return predictions + correction


def affine_ridge_transport(
    predictions: NDArray[np.float64],
    train_predictions: NDArray[np.float64],
    train_targets: NDArray[np.float64],
    alpha: float = 100.0,
) -> NDArray[np.float64]:
    """Fit affine ridge: y_cal = A @ y_pred + b."""
    n_train = train_predictions.shape[0]
    emb_dim = train_predictions.shape[1]

    X_aug = np.hstack([train_predictions, np.ones((n_train, 1))])
    XtX = X_aug.T @ X_aug + alpha * np.eye(emb_dim + 1)
    XtY = X_aug.T @ train_targets
    W = np.linalg.solve(XtX, XtY)

    X_test_aug = np.hstack([predictions, np.ones((predictions.shape[0], 1))])
    return X_test_aug @ W


def low_rank_transport(
    predictions: NDArray[np.float64],
    train_predictions: NDArray[np.float64],
    train_targets: NDArray[np.float64],
    rank: int = 10,
    alpha: float = 100.0,
) -> NDArray[np.float64]:
    """Low-rank linear transport: y_cal = U @ V^T @ y_pred + mean_correction."""
    emb_dim = train_predictions.shape[1]
    effective_rank = min(rank, emb_dim, train_predictions.shape[0])

    residual_targets = train_targets - train_predictions.mean(axis=0)
    residual_preds = train_predictions - train_predictions.mean(axis=0)

    XtX = residual_preds.T @ residual_preds + alpha * np.eye(emb_dim)
    XtY = residual_preds.T @ residual_targets
    W_full = np.linalg.solve(XtX, XtY)

    U, S, Vt = np.linalg.svd(W_full, full_matrices=False)
    W_lowrank = U[:, :effective_rank] @ np.diag(S[:effective_rank]) @ Vt[:effective_rank, :]

    pred_centered = predictions - train_predictions.mean(axis=0)
    calibrated = pred_centered @ W_lowrank + train_targets.mean(axis=0)
    return calibrated


def random_low_rank_transport(
    predictions: NDArray[np.float64],
    train_predictions: NDArray[np.float64],
    train_targets: NDArray[np.float64],
    rank: int = 10,
    seed: int = 42,
) -> NDArray[np.float64]:
    """Random low-rank transform (control for transport)."""
    rng = np.random.default_rng(seed)
    emb_dim = predictions.shape[1]
    effective_rank = min(rank, emb_dim)

    W_random = rng.standard_normal((emb_dim, effective_rank)) * 0.01
    V_random = rng.standard_normal((effective_rank, emb_dim)) * 0.01
    W_full = W_random @ V_random

    pred_centered = predictions - train_predictions.mean(axis=0)
    calibrated = pred_centered @ W_full + train_targets.mean(axis=0)
    return calibrated


def evaluate_transport_loso(
    decoder_predictions: NDArray[np.float64],
    target_embeddings: NDArray[np.float64],
    candidate_pool: NDArray[np.float64],
    target_indices: NDArray[np.int64],
    stimulus_ids: NDArray[np.int64],
    alpha: float = 100.0,
    rank: int = 10,
) -> dict[str, Any]:
    """Leave-one-stimulus-out evaluation of all transport methods.

    For each stimulus held out:
    - Train transport on remaining stimuli's trials
    - Evaluate on held-out stimulus trials
    """
    from app.research.fmri.decoder import evaluate_retrieval

    unique_stims = np.unique(stimulus_ids)
    n_stims = len(unique_stims)

    results_by_method: dict[str, list[float]] = {
        "identity": [],
        "mean_correction": [],
        "affine_ridge": [],
        "low_rank": [],
        "random_low_rank": [],
    }

    for held_out_stim in unique_stims:
        test_mask = stimulus_ids == held_out_stim
        train_mask = ~test_mask

        train_preds = decoder_predictions[train_mask]
        train_targets = target_embeddings[train_mask]
        test_preds = decoder_predictions[test_mask]
        test_targets = target_embeddings[test_mask]
        test_target_idx = target_indices[test_mask]

        id_out = identity_transport(test_preds)
        mc_out = mean_correction_transport(test_preds, train_preds, train_targets)
        ar_out = affine_ridge_transport(test_preds, train_preds, train_targets, alpha=alpha)
        lr_out = low_rank_transport(test_preds, train_preds, train_targets, rank=rank, alpha=alpha)
        rl_out = random_low_rank_transport(test_preds, train_preds, train_targets, rank=rank)

        for method_name, calibrated in [
            ("identity", id_out),
            ("mean_correction", mc_out),
            ("affine_ridge", ar_out),
            ("low_rank", lr_out),
            ("random_low_rank", rl_out),
        ]:
            eval_result = evaluate_retrieval(calibrated, test_targets, candidate_pool, test_target_idx)
            results_by_method[method_name].append(eval_result["mrr"])

    summary: dict[str, Any] = {}
    for method, mrrs in results_by_method.items():
        summary[method] = {
            "per_stimulus_mrr": mrrs,
            "mean_mrr": float(np.mean(mrrs)),
            "std_mrr": float(np.std(mrrs)),
        }

    identity_mean = summary["identity"]["mean_mrr"]
    for method in ["mean_correction", "affine_ridge", "low_rank"]:
        delta = summary[method]["mean_mrr"] - identity_mean
        summary[method]["delta_vs_identity"] = delta

    return {
        "evaluation": "leave_one_stimulus_out",
        "n_stimuli": int(n_stims),
        "transport_alpha": alpha,
        "transport_rank": rank,
        "methods": summary,
    }
