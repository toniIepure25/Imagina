"""Minimal proportional-odds (cumulative-logit) ordinal regression.

The C1 analysis spec (`docs/research/C1_ANALYSIS_SPEC.md` Section 1) freezes
a proper ordinal log score as the primary metric for the vividness target
(1-5). No maintained, dependency-free ordinal regression ships with
scikit-learn, so a minimal, from-scratch cumulative-logit model is
implemented here — reused by both the "regularized ordinal model" baseline
(Commit 5) and the primary estimand's log-score computation (Commit 7).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


@dataclass
class OrdinalLogisticModel:
    """Proportional-odds model: P(y <= k | x) = sigmoid(theta_k - x @ beta).

    Fit by maximizing the multinomial log-likelihood directly (a compact,
    dependency-free alternative to iteratively-reweighted least squares).
    """
    n_classes: int
    beta: np.ndarray  # (n_features,)
    thresholds: np.ndarray  # (n_classes - 1,) strictly increasing

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        """x: (n_samples, n_features) -> (n_samples, n_classes) probabilities."""
        eta = x @ self.beta  # (n_samples,)
        cum = expit(self.thresholds[None, :] - eta[:, None])  # (n_samples, n_classes-1)
        cum = np.concatenate([cum, np.ones((len(eta), 1))], axis=1)
        cum = np.concatenate([np.zeros((len(eta), 1)), cum], axis=1)
        probs = np.diff(cum, axis=1)
        return np.clip(probs, 1e-9, 1.0)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(x), axis=1) + 1  # classes are 1-indexed (vividness 1-5)

    def log_score(self, x: np.ndarray, y: np.ndarray) -> float:
        """Mean negative log-likelihood of the true ordinal class (the
        frozen primary metric for an ordinal target, per
        C1_ANALYSIS_SPEC.md Section 1) — lower is better."""
        probs = self.predict_proba(x)
        y_idx = (y.astype(int) - 1)
        p_true = probs[np.arange(len(y)), y_idx]
        return float(-np.mean(np.log(p_true)))


def fit_ordinal_logistic(
    x: np.ndarray, y: np.ndarray, n_classes: int = 5, l2: float = 1.0, seed: int = 42,
) -> OrdinalLogisticModel:
    """Fit a proportional-odds model by direct likelihood maximization.

    `seed` only affects the deterministic initial guess (all-zeros beta plus
    evenly spaced thresholds is already deterministic; the seed is accepted
    for interface consistency with the other baselines and is not itself a
    source of stochasticity here).
    """
    n_features = x.shape[1]
    y_idx = y.astype(int) - 1

    def unpack(params):
        beta = params[:n_features]
        raw_thresholds = params[n_features:]
        # Enforce strictly increasing thresholds via cumulative softplus-like
        # transform: thresholds[0] free, subsequent are cumulative positive steps.
        thresholds = np.cumsum(np.concatenate([[raw_thresholds[0]], np.exp(raw_thresholds[1:])]))
        return beta, thresholds

    def neg_log_likelihood(params):
        beta, thresholds = unpack(params)
        eta = x @ beta
        cum = expit(thresholds[None, :] - eta[:, None])
        cum = np.concatenate([np.zeros((len(eta), 1)), cum, np.ones((len(eta), 1))], axis=1)
        probs = np.clip(np.diff(cum, axis=1), 1e-9, 1.0)
        nll = -np.mean(np.log(probs[np.arange(len(y_idx)), y_idx]))
        reg = l2 * np.sum(beta ** 2)
        return nll + reg

    init_beta = np.zeros(n_features)
    init_thresholds_raw = np.zeros(n_classes - 1)
    init_thresholds_raw[0] = -2.0
    x0 = np.concatenate([init_beta, init_thresholds_raw])

    result = minimize(neg_log_likelihood, x0, method="L-BFGS-B")
    beta, thresholds = unpack(result.x)
    return OrdinalLogisticModel(n_classes=n_classes, beta=beta, thresholds=thresholds)
