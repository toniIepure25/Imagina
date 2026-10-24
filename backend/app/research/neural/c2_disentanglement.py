"""Content-state-nuisance disentanglement probes for Scientific Gate C2
(Commit 6).

Trains separate frozen-representation probes for content category, state,
participant identity, session identity, and signal-quality bin -- reported
as separate metrics (C2-H5), never combined into one opaque "disentanglement
score" per the task specification.

Content and state probing reuse the SAME held-out-participant LOSO
structure as Commits 3-5 (a cross-subject generalization question).
Participant-identity and quality-bin probing use a DIFFERENT, deliberately
different validation scheme: stratified K-fold over trials from the SAME
known set of participants, because "can this representation recover WHICH
of these 14 known people this trial came from" is a within-sample leakage
question, not a cross-subject generalization claim -- a held-out-participant
split cannot even ask this question, since a genuinely new participant's
identity was never in the label space the probe was fit on.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.c2_models import BinaryFeatureModel, MulticlassFeatureModel, balanced_accuracy, macro_f1


@dataclass
class ProbeResult:
    target_name: str
    validation_scheme: str
    n_classes: int
    n_folds: int
    metric_name: str
    mean_metric: float
    std_metric: float
    balanced_accuracy_mean: float
    per_fold: list[dict[str, Any]]
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def quality_bin_labels(quality_scalar: np.ndarray, n_bins: int = 3) -> np.ndarray:
    """Discretize a continuous signal-quality scalar (e.g. broadband
    variance or mean peak-to-peak amplitude) into `n_bins` labeled classes
    by within-sample quantile -- a frozen, data-driven-but-not-outcome-
    driven binning (quantiles of the quality scalar itself, never of the
    content/state target)."""
    quantiles = np.quantile(quality_scalar, np.linspace(0, 1, n_bins + 1)[1:-1])
    bin_idx = np.searchsorted(quantiles, quality_scalar)
    return np.array([f"quality_bin_{i}" for i in bin_idx])


def stratified_kfold_indices(labels: np.ndarray, n_folds: int, seed: int = 42) -> list[tuple[np.ndarray, np.ndarray]]:
    """A minimal stratified K-fold splitter (no sklearn dependency): each
    class's samples are shuffled and distributed round-robin across folds,
    so every fold gets a roughly proportional share of every class."""
    rng = np.random.RandomState(seed)
    fold_assignment = np.full(len(labels), -1, dtype=int)
    for cls in sorted(set(labels.tolist())):
        idx = np.where(labels == cls)[0]
        rng.shuffle(idx)
        for i, sample_idx in enumerate(idx):
            fold_assignment[sample_idx] = i % n_folds
    return [
        (np.where(fold_assignment != f)[0], np.where(fold_assignment == f)[0])
        for f in range(n_folds)
    ]


def run_multiclass_probe(
    embeddings: np.ndarray, labels: np.ndarray, target_name: str, validation_scheme: str,
    n_folds: int = 5, l2: float = 1.0, seed: int = 42, note: str = "",
) -> ProbeResult:
    classes = tuple(sorted(set(labels.tolist())))
    if len(classes) < 2:
        return ProbeResult(
            target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
            n_folds=0, metric_name="class_weighted_log_loss", mean_metric=float("nan"), std_metric=float("nan"),
            balanced_accuracy_mean=float("nan"), per_fold=[],
            note=note or f"Only {len(classes)} distinct class(es) present -- probe is not meaningfully testable.",
        )

    splits = stratified_kfold_indices(labels, n_folds, seed)
    per_fold = []
    for train_idx, test_idx in splits:
        if len(test_idx) < 2 or len(train_idx) < 2:
            continue
        model = MulticlassFeatureModel(l2=l2, classes=classes, seed=seed)
        model.fit(embeddings[train_idx], labels[train_idx])
        metrics = model.evaluate(embeddings[test_idx], labels[test_idx])
        per_fold.append(metrics)

    if not per_fold:
        return ProbeResult(
            target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
            n_folds=0, metric_name="class_weighted_log_loss", mean_metric=float("nan"), std_metric=float("nan"),
            balanced_accuracy_mean=float("nan"), per_fold=[], note="No fold had enough samples to fit/evaluate.",
        )
    log_losses = [f["class_weighted_log_loss"] for f in per_fold]
    bal_accs = [f["balanced_accuracy"] for f in per_fold]
    return ProbeResult(
        target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
        n_folds=len(per_fold), metric_name="class_weighted_log_loss",
        mean_metric=float(np.mean(log_losses)), std_metric=float(np.std(log_losses)),
        balanced_accuracy_mean=float(np.mean(bal_accs)), per_fold=per_fold, note=note,
    )


def run_binary_probe(
    embeddings: np.ndarray, labels: np.ndarray, target_name: str, validation_scheme: str,
    n_folds: int = 5, l2: float = 1.0, seed: int = 42, note: str = "",
) -> ProbeResult:
    classes = tuple(sorted(set(labels.tolist())))
    if len(classes) < 2:
        return ProbeResult(
            target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
            n_folds=0, metric_name="binary_log_loss", mean_metric=float("nan"), std_metric=float("nan"),
            balanced_accuracy_mean=float("nan"), per_fold=[],
            note=note or f"Only {len(classes)} distinct class(es) present -- probe is not meaningfully testable.",
        )
    splits = stratified_kfold_indices(labels, n_folds, seed)
    per_fold = []
    for train_idx, test_idx in splits:
        if len(test_idx) < 2 or len(train_idx) < 2:
            continue
        model = BinaryFeatureModel(l2=l2, classes=classes, seed=seed)
        model.fit(embeddings[train_idx], labels[train_idx])
        metrics = model.evaluate(embeddings[test_idx], labels[test_idx])
        per_fold.append(metrics)

    if not per_fold:
        return ProbeResult(
            target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
            n_folds=0, metric_name="binary_log_loss", mean_metric=float("nan"), std_metric=float("nan"),
            balanced_accuracy_mean=float("nan"), per_fold=[], note="No fold had enough samples to fit/evaluate.",
        )
    log_losses = [f["binary_log_loss"] for f in per_fold]
    bal_accs = [f["balanced_accuracy"] for f in per_fold]
    return ProbeResult(
        target_name=target_name, validation_scheme=validation_scheme, n_classes=len(classes),
        n_folds=len(per_fold), metric_name="binary_log_loss",
        mean_metric=float(np.mean(log_losses)), std_metric=float(np.std(log_losses)),
        balanced_accuracy_mean=float(np.mean(bal_accs)), per_fold=per_fold, note=note,
    )


__all__ = [
    "ProbeResult", "quality_bin_labels", "stratified_kfold_indices",
    "run_multiclass_probe", "run_binary_probe", "balanced_accuracy", "macro_f1",
]
