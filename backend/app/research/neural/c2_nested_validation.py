"""Leave-one-subject-out nested validation for C2 classification targets
(content: 3-class; state: binary), mirroring C1's
`nested_validation.run_loso_nested_validation`/`run_single_loso_fold`
pattern -- inner participant-grouped CV selects the L2 hyperparameter using
ONLY the outer-training participants, then both models are refit on the
full outer-training set and evaluated once on the held-out participant.
Never inspects the outer-test participant's data at any point.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.c2_models import BinaryFeatureModel, MulticlassFeatureModel
from app.research.neural.models import participant_grouped_split


@dataclass
class ClassificationFoldResult:
    held_out_participant: str
    n_train: int
    n_test: int
    metrics: dict[str, float]
    chosen_l2: float
    checkpoint_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _fit_and_select_l2(
    model_cls, x_train: np.ndarray, y_train: np.ndarray, participant_ids_train: list[str],
    primary_metric: str, lower_is_better: bool, l2_grid: tuple[float, ...], inner_k: int, classes: tuple[str, ...],
):
    train_participants = sorted(set(participant_ids_train))
    best_l2 = l2_grid[0]
    best_score = float("inf") if lower_is_better else float("-inf")
    if len(train_participants) >= 3:
        n_inner_folds = max(2, min(inner_k, len(train_participants)))
        participant_folds = [
            set(fold.tolist()) for fold in np.array_split(np.array(train_participants), n_inner_folds)
        ]
        for l2 in l2_grid:
            inner_scores = []
            for val_participants in participant_folds:
                inner_train_mask = np.array([p not in val_participants for p in participant_ids_train])
                inner_val_mask = ~inner_train_mask
                if inner_val_mask.sum() < 2 or inner_train_mask.sum() < 2:
                    continue
                m = model_cls(l2=l2, classes=classes)
                m.fit(x_train[inner_train_mask], y_train[inner_train_mask])
                score = m.evaluate(x_train[inner_val_mask], y_train[inner_val_mask])[primary_metric]
                inner_scores.append(score)
            if not inner_scores:
                continue
            mean_score = float(np.mean(inner_scores))
            better = mean_score < best_score if lower_is_better else mean_score > best_score
            if better:
                best_score = mean_score
                best_l2 = l2
    return best_l2


def run_single_loso_fold_classification(
    x_train: np.ndarray, y_train: np.ndarray, participant_ids_train: list[str],
    x_test: np.ndarray, y_test: np.ndarray, held_out_label: str, target_kind: str,
    l2_grid: tuple[float, ...] = (0.1, 1.0, 10.0), inner_k: int = 5,
) -> ClassificationFoldResult | None:
    """`target_kind`: "content" (3-class, MulticlassFeatureModel, primary
    metric class_weighted_log_loss, lower better) or "state" (binary,
    BinaryFeatureModel, primary metric binary_log_loss, lower better)."""
    if len(x_test) < 2:
        return None

    if target_kind == "content":
        model_cls = MulticlassFeatureModel
        primary_metric = "class_weighted_log_loss"
        classes = MulticlassFeatureModel().classes
    elif target_kind == "state":
        model_cls = BinaryFeatureModel
        primary_metric = "binary_log_loss"
        classes = BinaryFeatureModel().classes
    else:
        raise ValueError(f"unknown target_kind: {target_kind!r}")

    best_l2 = _fit_and_select_l2(
        model_cls, x_train, y_train, participant_ids_train, primary_metric,
        lower_is_better=True, l2_grid=l2_grid, inner_k=inner_k, classes=classes,
    )

    model = model_cls(l2=best_l2, classes=classes)
    model.fit(x_train, y_train)
    metrics = model.evaluate(x_test, y_test)
    spec = model.to_spec("c2_fold_model")

    return ClassificationFoldResult(
        held_out_participant=held_out_label, n_train=len(x_train), n_test=len(x_test),
        metrics=metrics, chosen_l2=best_l2, checkpoint_hash=spec.checkpoint_hash,
    )


def run_loso_nested_validation_classification(
    x: np.ndarray, y: np.ndarray, participant_ids: list[str], target_kind: str,
    l2_grid: tuple[float, ...] = (0.1, 1.0, 10.0), inner_k: int = 5,
) -> list[ClassificationFoldResult]:
    participants = sorted(set(participant_ids))
    ids_arr = np.array(participant_ids)
    results: list[ClassificationFoldResult] = []
    for held_out in participants:
        train_mask, test_mask = participant_grouped_split(participant_ids, held_out=held_out)
        result = run_single_loso_fold_classification(
            x[train_mask], y[train_mask], list(ids_arr[train_mask]),
            x[test_mask], y[test_mask], held_out, target_kind, l2_grid, inner_k,
        )
        if result is not None:
            results.append(result)
    return results


def aggregate_metric_across_folds(fold_results: list[ClassificationFoldResult], metric_name: str) -> dict[str, Any]:
    """Participant-level aggregate for one metric: mean, SD, per-participant
    values -- the inferential unit is the participant (one value per fold/
    held-out participant), never the trial."""
    per_participant = {r.held_out_participant: r.metrics[metric_name] for r in fold_results}
    values = np.array(list(per_participant.values()))
    return {
        "n_participants": len(values),
        "mean": float(values.mean()) if len(values) else float("nan"),
        "std": float(values.std()) if len(values) else float("nan"),
        "per_participant": per_participant,
    }
