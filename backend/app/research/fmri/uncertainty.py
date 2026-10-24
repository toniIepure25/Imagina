"""Uncertainty calibration and selective transfer for C3-H5.

Evaluates whether decoder uncertainty predicts trial-level errors.
Uses repeat-level variance, bootstrap decoder variance, and ROI disagreement.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def compute_repeat_variance(
    predictions_per_repeat: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Variance of predicted embeddings across repetitions of the same stimulus.

    predictions_per_repeat: [n_stimuli, n_repeats, embedding_dim]
    Returns: [n_stimuli] uncertainty scores
    """
    var_per_dim = np.var(predictions_per_repeat, axis=1)
    return np.mean(var_per_dim, axis=1)


def compute_distribution_distance(
    imagery_predictions: NDArray[np.float64],
    perception_train_predictions: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Mahalanobis-like distance from perception training distribution.

    Returns per-trial distance scores.
    """
    train_mean = perception_train_predictions.mean(axis=0)
    train_cov = np.cov(perception_train_predictions.T)

    reg = 1e-4 * np.eye(train_cov.shape[0])
    train_cov_inv = np.linalg.inv(train_cov + reg)

    n_trials = imagery_predictions.shape[0]
    distances = np.zeros(n_trials)
    for i in range(n_trials):
        diff = imagery_predictions[i] - train_mean
        distances[i] = float(np.sqrt(diff @ train_cov_inv @ diff))
    return distances


def compute_roi_disagreement(
    predictions_by_roi: dict[str, NDArray[np.float64]],
) -> NDArray[np.float64]:
    """Variance of predictions across ROI-specific decoders.

    predictions_by_roi: {roi_name: [n_trials, embedding_dim]}
    Returns: [n_trials] disagreement scores
    """
    pred_stack = np.stack(list(predictions_by_roi.values()), axis=0)
    var_across_rois = np.var(pred_stack, axis=0)
    return np.mean(var_across_rois, axis=1)


def evaluate_calibration(
    uncertainty_scores: NDArray[np.float64],
    errors: NDArray[np.float64],
    n_bins: int = 5,
) -> dict[str, Any]:
    """Evaluate uncertainty calibration via reliability diagram.

    uncertainty_scores: [n_trials] predicted uncertainty
    errors: [n_trials] actual error magnitude
    """
    from scipy.stats import spearmanr

    rho, p_value = spearmanr(uncertainty_scores, errors)

    sorted_idx = np.argsort(uncertainty_scores)
    bins = np.array_split(sorted_idx, n_bins)

    reliability = []
    for bin_idx in bins:
        mean_uncertainty = float(np.mean(uncertainty_scores[bin_idx]))
        mean_error = float(np.mean(errors[bin_idx]))
        reliability.append({"mean_uncertainty": mean_uncertainty, "mean_error": mean_error})

    return {
        "spearman_rho": float(rho),
        "spearman_p": float(p_value),
        "error_correlation_significant": p_value < 0.05,
        "reliability_diagram": reliability,
        "n_bins": n_bins,
    }


def risk_coverage_curve(
    uncertainty_scores: NDArray[np.float64],
    reciprocal_ranks: NDArray[np.float64],
    thresholds: int = 10,
) -> dict[str, Any]:
    """Compute selective MRR at various abstention thresholds.

    Abstain on the most uncertain trials and report MRR on remaining.
    """
    n_trials = len(uncertainty_scores)
    sorted_idx = np.argsort(uncertainty_scores)

    coverages = []
    selective_mrrs = []

    for k in range(1, thresholds + 1):
        coverage = k / thresholds
        n_keep = max(1, int(coverage * n_trials))
        kept_idx = sorted_idx[:n_keep]
        selective_mrr = float(np.mean(reciprocal_ranks[kept_idx]))
        coverages.append(coverage)
        selective_mrrs.append(selective_mrr)

    overall_mrr = float(np.mean(reciprocal_ranks))
    auc = float(np.trapezoid(selective_mrrs, coverages))

    return {
        "coverages": coverages,
        "selective_mrrs": selective_mrrs,
        "overall_mrr": overall_mrr,
        "auc_risk_coverage": auc,
        "abstention_utility": selective_mrrs[0] - overall_mrr if selective_mrrs else 0.0,
    }
