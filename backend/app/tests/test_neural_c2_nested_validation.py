"""Tests for the C2 LOSO nested-validation harness (Commit 3). Synthetic
multi-participant feature matrices only.
"""
from __future__ import annotations

import numpy as np

from app.research.neural.c2_nested_validation import (
    aggregate_metric_across_folds,
    run_loso_nested_validation_classification,
    run_single_loso_fold_classification,
)


def _make_content_data(n_participants=6, n_per=20, seed=0, informative=True):
    rng = np.random.RandomState(seed)
    participant_ids, x, y = [], [], []
    for p in range(n_participants):
        pid = f"p{p}"
        classes = ["visual_square", "visual_face_male", "visual_face_female"]
        labels = rng.choice(classes, size=n_per, p=[0.5, 0.25, 0.25])
        feats = rng.randn(n_per, 4)
        if informative:
            for i, cls in enumerate(classes):
                feats[labels == cls, 0] += i * 3.0
        participant_ids.extend([pid] * n_per)
        x.append(feats)
        y.extend(labels)
    return np.vstack(x), np.array(y), participant_ids


def _make_state_data(n_participants=6, n_per=20, seed=0, informative=True):
    rng = np.random.RandomState(seed)
    participant_ids, x, y = [], [], []
    for p in range(n_participants):
        pid = f"p{p}"
        labels = rng.choice(["perception", "imagery"], size=n_per)
        feats = rng.randn(n_per, 3)
        if informative:
            feats[labels == "imagery", 0] += 3.0
        participant_ids.extend([pid] * n_per)
        x.append(feats)
        y.extend(labels)
    return np.vstack(x), np.array(y), participant_ids


class TestRunSingleLosoFoldClassification:
    def test_content_fold_returns_valid_result(self):
        x, y, ids = _make_content_data()
        train_mask = np.array([i != "p0" for i in ids])
        test_mask = ~train_mask
        result = run_single_loso_fold_classification(
            x[train_mask], y[train_mask], [i for i in ids if i != "p0"],
            x[test_mask], y[test_mask], "p0", target_kind="content",
        )
        assert result is not None
        assert result.held_out_participant == "p0"
        assert "class_weighted_log_loss" in result.metrics
        assert result.chosen_l2 in (0.1, 1.0, 10.0)

    def test_state_fold_returns_valid_result(self):
        x, y, ids = _make_state_data()
        train_mask = np.array([i != "p0" for i in ids])
        test_mask = ~train_mask
        result = run_single_loso_fold_classification(
            x[train_mask], y[train_mask], [i for i in ids if i != "p0"],
            x[test_mask], y[test_mask], "p0", target_kind="state",
        )
        assert result is not None
        assert "binary_log_loss" in result.metrics

    def test_too_few_test_samples_returns_none(self):
        x, y, ids = _make_content_data()
        result = run_single_loso_fold_classification(x, y, ids, x[:1], y[:1], "p0", target_kind="content")
        assert result is None

    def test_unknown_target_kind_raises(self):
        x, y, ids = _make_content_data()
        try:
            run_single_loso_fold_classification(x, y, ids, x, y, "p0", target_kind="bogus")
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


class TestRunLosoNestedValidationClassification:
    def test_no_held_out_participant_appears_in_own_training_set(self):
        x, y, ids = _make_content_data(n_participants=5)
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        assert len(results) == 5
        assert {r.held_out_participant for r in results} == {f"p{i}" for i in range(5)}

    def test_informative_content_features_beat_chance(self):
        x, y, ids = _make_content_data(informative=True)
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        agg = aggregate_metric_across_folds(results, "class_weighted_log_loss")
        assert agg["mean"] < np.log(3)  # better than chance-level log loss

    def test_uninformative_content_features_near_chance(self):
        x, y, ids = _make_content_data(informative=False, seed=99)
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        agg = aggregate_metric_across_folds(results, "class_weighted_log_loss")
        assert agg["mean"] > np.log(3) * 0.7  # not dramatically better than chance

    def test_informative_state_features_beat_chance(self):
        x, y, ids = _make_state_data(informative=True)
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="state")
        agg = aggregate_metric_across_folds(results, "binary_log_loss")
        assert agg["mean"] < np.log(2)  # better than chance-level binary log loss


class TestAggregateMetricAcrossFolds:
    def test_participant_is_the_unit_one_value_per_fold(self):
        x, y, ids = _make_content_data(n_participants=4)
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        agg = aggregate_metric_across_folds(results, "balanced_accuracy")
        assert agg["n_participants"] == 4
        assert set(agg["per_participant"].keys()) == {"p0", "p1", "p2", "p3"}
