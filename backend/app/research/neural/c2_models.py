"""Leakage-safe content and state baselines for Scientific Gate C2 (Commit 3).

Mirrors C1's `models.py` provenance convention (`ModelSpec`: seed, param
count, train/inference time, checkpoint hash) and its "no model sees a
test-participant's data during fitting" boundary (enforced by the caller via
`participant_grouped_split`, reused unchanged from C1).

Two feature-set-agnostic classifier wrappers (`MulticlassFeatureModel` for
the 3-class content target, `BinaryFeatureModel` for the 2-class state
target) are reused across every nuisance/classical baseline in the model
hierarchy (`C2_ANALYSIS_SPEC.md` Section 6) -- only the FEATURE
CONSTRUCTION differs per baseline (order-only, block/session-only,
quality-only, raw-linear, classical-feature), never the classifier head.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.research.neural.c2_data import PRIMARY_CONTENT_CLASSES  # noqa: F401 (re-exported)
from app.research.neural.models import ModelSpec, participant_grouped_split  # noqa: F401 (re-exported)

C2_MODELS_VERSION = "1.0.0"

STATE_CLASSES = ("perception", "imagery")


def class_weighted_log_loss(
    y_true: np.ndarray, y_proba: np.ndarray, classes: tuple[str, ...], class_weights: dict[str, float] | None = None,
) -> float:
    """Mean class-weighted negative log-likelihood of the true class --
    the frozen primary content metric (C2_ANALYSIS_SPEC.md Section 1),
    accounting for the fixed 2:1:1 manifest class imbalance documented in
    C2_PROTOCOL.md Section 4. class_weights defaults to inverse-frequency
    weights over `classes` if not given."""
    class_index = {c: i for i, c in enumerate(classes)}
    if class_weights is None:
        counts = np.array([max(1, np.sum(y_true == c)) for c in classes], dtype=float)
        inv = 1.0 / counts
        weights_by_class = {c: float(w) for c, w in zip(classes, inv / inv.sum() * len(classes))}
    else:
        weights_by_class = class_weights

    eps = 1e-12
    total_weight = 0.0
    total_loss = 0.0
    for i, label in enumerate(y_true):
        idx = class_index[label]
        p = max(eps, min(1 - eps, y_proba[i, idx]))
        w = weights_by_class[label]
        total_loss += -w * np.log(p)
        total_weight += w
    return float(total_loss / total_weight) if total_weight > 0 else float("nan")


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray, classes: tuple[str, ...]) -> float:
    per_class_acc = []
    for c in classes:
        mask = y_true == c
        if mask.sum() == 0:
            continue
        per_class_acc.append(float(np.mean(y_pred[mask] == c)))
    return float(np.mean(per_class_acc)) if per_class_acc else float("nan")


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray, classes: tuple[str, ...]) -> float:
    scores = []
    for c in classes:
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        scores.append(f1)
    return float(np.mean(scores))


def roc_auc_binary(y_true: np.ndarray, y_score: np.ndarray, positive_class: str) -> float:
    """Rank-based AUC (Mann-Whitney U), no sklearn dependency needed for
    this one metric so callers without the neural extras can still compute
    it in tests."""
    y_bin = (y_true == positive_class).astype(int)
    n_pos, n_neg = int(y_bin.sum()), int((1 - y_bin).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(y_score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)
    sum_ranks_pos = ranks[y_bin == 1].sum()
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


@dataclass
class MulticlassFeatureModel:
    """Multinomial logistic regression on an arbitrary feature matrix --
    reused for every content baseline in the C2 model hierarchy; only the
    feature construction passed to `fit`/`predict_proba` changes."""
    classes: tuple[str, ...] = PRIMARY_CONTENT_CLASSES
    l2: float = 1.0
    seed: int = 42
    _model: Any = field(default=None, repr=False)
    _mean: np.ndarray | None = field(default=None, repr=False)
    _std: np.ndarray | None = field(default=None, repr=False)
    _train_time_s: float = field(default=0.0, repr=False)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "MulticlassFeatureModel":
        from sklearn.linear_model import LogisticRegression

        t0 = time.perf_counter()
        self._mean = x.mean(axis=0)
        self._std = x.std(axis=0) + 1e-9
        x_std = (x - self._mean) / self._std
        self._model = LogisticRegression(
            C=1.0 / max(self.l2, 1e-9), max_iter=2000, random_state=self.seed,
        )
        self._model.classes_ = np.array(self.classes)
        self._model.fit(x_std, y)
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        x_std = (x - self._mean) / self._std
        proba = self._model.predict_proba(x_std)
        # Re-order columns to match self.classes (sklearn sorts classes_ alphabetically internally).
        order = [list(self._model.classes_).index(c) for c in self.classes]
        return proba[:, order]

    def predict(self, x: np.ndarray) -> np.ndarray:
        proba = self.predict_proba(x)
        idx = proba.argmax(axis=1)
        return np.array([self.classes[i] for i in idx])

    def evaluate(self, x: np.ndarray, y: np.ndarray) -> dict[str, float]:
        proba = self.predict_proba(x)
        pred = self.predict(x)
        return {
            "class_weighted_log_loss": class_weighted_log_loss(y, proba, self.classes),
            "balanced_accuracy": balanced_accuracy(y, pred, self.classes),
            "macro_f1": macro_f1(y, pred, self.classes),
        }

    def to_spec(self, model_id: str, architecture: str = "multinomial_logistic") -> ModelSpec:
        t0 = time.perf_counter()
        n_features = len(self._mean) if self._mean is not None else 0
        if n_features:
            _ = self.predict_proba(np.zeros((1, n_features)))
        inference_time_s = time.perf_counter() - t0
        checkpoint_bytes = (
            np.concatenate([self._model.coef_.ravel(), self._model.intercept_.ravel()]).tobytes()
            if self._model is not None else b""
        )
        return ModelSpec(
            model_id=model_id, model_version=C2_MODELS_VERSION, architecture=architecture,
            hyperparameters={"l2": self.l2, "classes": list(self.classes)}, random_seed=self.seed,
            param_count=(n_features + 1) * len(self.classes), train_time_s=self._train_time_s,
            inference_time_s=inference_time_s, checkpoint_hash=hashlib.sha256(checkpoint_bytes).hexdigest(),
        )


@dataclass
class BinaryFeatureModel:
    """Logistic regression on an arbitrary feature matrix for the 2-class
    state target (perception vs. imagery) -- same feature-agnostic reuse
    pattern as MulticlassFeatureModel."""
    classes: tuple[str, ...] = STATE_CLASSES
    l2: float = 1.0
    seed: int = 42
    _model: Any = field(default=None, repr=False)
    _mean: np.ndarray | None = field(default=None, repr=False)
    _std: np.ndarray | None = field(default=None, repr=False)
    _train_time_s: float = field(default=0.0, repr=False)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "BinaryFeatureModel":
        from sklearn.linear_model import LogisticRegression

        t0 = time.perf_counter()
        self._mean = x.mean(axis=0)
        self._std = x.std(axis=0) + 1e-9
        x_std = (x - self._mean) / self._std
        self._model = LogisticRegression(C=1.0 / max(self.l2, 1e-9), max_iter=2000, random_state=self.seed)
        self._model.fit(x_std, y)
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict_proba_positive(self, x: np.ndarray) -> np.ndarray:
        """P(y == classes[1]) -- imagery, by STATE_CLASSES convention."""
        x_std = (x - self._mean) / self._std
        positive_idx = list(self._model.classes_).index(self.classes[1])
        return self._model.predict_proba(x_std)[:, positive_idx]

    def predict(self, x: np.ndarray) -> np.ndarray:
        p = self.predict_proba_positive(x)
        return np.where(p >= 0.5, self.classes[1], self.classes[0])

    def evaluate(self, x: np.ndarray, y: np.ndarray) -> dict[str, float]:
        p_pos = self.predict_proba_positive(x)
        pred = self.predict(x)
        eps = 1e-12
        y_bin = (y == self.classes[1]).astype(float)
        log_terms = y_bin * np.log(np.clip(p_pos, eps, 1)) + (1 - y_bin) * np.log(np.clip(1 - p_pos, eps, 1))
        log_loss = float(-np.mean(log_terms))
        return {
            "binary_log_loss": log_loss,
            "balanced_accuracy": balanced_accuracy(y, pred, self.classes),
            "roc_auc": roc_auc_binary(y, p_pos, self.classes[1]),
        }

    def to_spec(self, model_id: str, architecture: str = "binary_logistic") -> ModelSpec:
        t0 = time.perf_counter()
        n_features = len(self._mean) if self._mean is not None else 0
        if n_features:
            _ = self.predict_proba_positive(np.zeros((1, n_features)))
        inference_time_s = time.perf_counter() - t0
        checkpoint_bytes = (
            np.concatenate([self._model.coef_.ravel(), self._model.intercept_.ravel()]).tobytes()
            if self._model is not None else b""
        )
        return ModelSpec(
            model_id=model_id, model_version=C2_MODELS_VERSION, architecture=architecture,
            hyperparameters={"l2": self.l2, "classes": list(self.classes)}, random_seed=self.seed,
            param_count=n_features + 1, train_time_s=self._train_time_s, inference_time_s=inference_time_s,
            checkpoint_hash=hashlib.sha256(checkpoint_bytes).hexdigest(),
        )


def chance_majority_content_baseline(
    y_train: np.ndarray, classes: tuple[str, ...] = PRIMARY_CONTENT_CLASSES,
) -> dict[str, float]:
    """Fixed baseline: predicts the training set's majority class with
    probability 1, uniform chance otherwise -- no fitting, no leakage risk."""
    counts = {c: int(np.sum(y_train == c)) for c in classes}
    majority = max(counts, key=counts.get)
    return {"majority_class": majority, "class_counts": counts, "uniform_chance_log_loss": float(np.log(len(classes)))}


def order_only_features(trial_order: np.ndarray, block_index: np.ndarray) -> np.ndarray:
    return np.column_stack([trial_order.astype(float), block_index.astype(float)])


def block_session_only_features(block_index: np.ndarray, session_index: np.ndarray) -> np.ndarray:
    return np.column_stack([block_index.astype(float), session_index.astype(float)])


def quality_only_features(quality_dicts: list[dict[str, float]]) -> np.ndarray:
    names = sorted(quality_dicts[0].keys()) if quality_dicts else []
    return np.array([[d[name] for name in names] for d in quality_dicts])
