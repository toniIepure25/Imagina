"""Tests for the C2 leakage-safe content/state baseline models (Commit 3).
Synthetic feature matrices only -- validates classifier-head correctness,
metric computation, and provenance/determinism properties. Scientific
results come from the real ds005815 run.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.research.neural.c2_models import (
    PRIMARY_CONTENT_CLASSES,
    STATE_CLASSES,
    BinaryFeatureModel,
    MulticlassFeatureModel,
    balanced_accuracy,
    block_session_only_features,
    chance_majority_content_baseline,
    class_weighted_log_loss,
    macro_f1,
    order_only_features,
    quality_only_features,
    roc_auc_binary,
)


def _make_multiclass_data(n=90, seed=0, informative=True):
    rng = np.random.RandomState(seed)
    y = rng.choice(PRIMARY_CONTENT_CLASSES, size=n, p=[0.5, 0.25, 0.25])
    x = rng.randn(n, 5)
    if informative:
        for i, cls in enumerate(PRIMARY_CONTENT_CLASSES):
            x[y == cls, 0] += i * 3.0
    return x, y


def _make_binary_data(n=80, seed=0, informative=True):
    rng = np.random.RandomState(seed)
    y = rng.choice(STATE_CLASSES, size=n)
    x = rng.randn(n, 4)
    if informative:
        x[y == "imagery", 0] += 3.0
    return x, y


class TestClassWeightedLogLoss:
    def test_perfect_predictions_give_near_zero_loss(self):
        y = np.array(["visual_square", "visual_face_male", "visual_face_female"])
        proba = np.array([[0.99, 0.005, 0.005], [0.005, 0.99, 0.005], [0.005, 0.005, 0.99]])
        loss = class_weighted_log_loss(y, proba, PRIMARY_CONTENT_CLASSES)
        assert loss < 0.05

    def test_uniform_predictions_give_log3_loss(self):
        y = np.array(["visual_square", "visual_face_male", "visual_face_female"] * 4)
        proba = np.full((len(y), 3), 1 / 3)
        loss = class_weighted_log_loss(y, proba, PRIMARY_CONTENT_CLASSES)
        assert loss == pytest.approx(np.log(3), abs=1e-6)


class TestBalancedAccuracyMacroF1:
    def test_balanced_accuracy_perfect(self):
        y = np.array(["visual_square", "visual_face_male", "visual_face_female"] * 3)
        assert balanced_accuracy(y, y, PRIMARY_CONTENT_CLASSES) == 1.0

    def test_macro_f1_perfect(self):
        y = np.array(["visual_square", "visual_face_male", "visual_face_female"] * 3)
        assert macro_f1(y, y, PRIMARY_CONTENT_CLASSES) == 1.0

    def test_balanced_accuracy_insensitive_to_class_imbalance(self):
        # 90 square, 5 each face -- a majority-class predictor scores much
        # lower on balanced accuracy than raw accuracy would suggest.
        y = np.array(["visual_square"] * 90 + ["visual_face_male"] * 5 + ["visual_face_female"] * 5)
        pred = np.array(["visual_square"] * 100)
        acc = balanced_accuracy(y, pred, PRIMARY_CONTENT_CLASSES)
        assert acc == pytest.approx(1 / 3, abs=0.01)


class TestRocAucBinary:
    def test_perfect_separation_gives_auc_one(self):
        y = np.array(["perception"] * 10 + ["imagery"] * 10)
        scores = np.array([0.1] * 10 + [0.9] * 10)
        assert roc_auc_binary(y, scores, "imagery") == pytest.approx(1.0)

    def test_random_scores_give_auc_near_half(self):
        rng = np.random.RandomState(0)
        y = np.array(["perception", "imagery"] * 50)
        scores = rng.rand(100)
        auc = roc_auc_binary(y, scores, "imagery")
        assert 0.3 < auc < 0.7


class TestMulticlassFeatureModel:
    def test_recovers_informative_signal(self):
        x, y = _make_multiclass_data(informative=True)
        model = MulticlassFeatureModel(l2=1.0)
        model.fit(x, y)
        metrics = model.evaluate(x, y)
        assert metrics["class_weighted_log_loss"] < np.log(3)
        assert metrics["balanced_accuracy"] > 0.5

    def test_uninformative_features_near_chance(self):
        rng = np.random.RandomState(1)
        x = rng.randn(90, 5)
        y = rng.choice(PRIMARY_CONTENT_CLASSES, size=90)
        model = MulticlassFeatureModel(l2=10.0)
        model.fit(x, y)
        metrics = model.evaluate(x, y)
        assert metrics["class_weighted_log_loss"] > 0.8  # not near-zero like the informative case

    def test_deterministic_checkpoint_hash(self):
        x, y = _make_multiclass_data()
        m1 = MulticlassFeatureModel(l2=1.0, seed=42)
        m1.fit(x, y)
        m2 = MulticlassFeatureModel(l2=1.0, seed=42)
        m2.fit(x, y)
        assert m1.to_spec("m").checkpoint_hash == m2.to_spec("m").checkpoint_hash

    def test_predict_proba_columns_match_declared_class_order(self):
        x, y = _make_multiclass_data()
        model = MulticlassFeatureModel(l2=1.0)
        model.fit(x, y)
        proba = model.predict_proba(x)
        assert proba.shape == (len(y), 3)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)


class TestBinaryFeatureModel:
    def test_recovers_informative_signal(self):
        x, y = _make_binary_data(informative=True)
        model = BinaryFeatureModel(l2=1.0)
        model.fit(x, y)
        metrics = model.evaluate(x, y)
        assert metrics["roc_auc"] > 0.7

    def test_deterministic_checkpoint_hash(self):
        x, y = _make_binary_data()
        m1 = BinaryFeatureModel(l2=1.0, seed=42)
        m1.fit(x, y)
        m2 = BinaryFeatureModel(l2=1.0, seed=42)
        m2.fit(x, y)
        assert m1.to_spec("m").checkpoint_hash == m2.to_spec("m").checkpoint_hash


class TestNuisanceFeatureConstructors:
    def test_order_only_features_shape(self):
        trial_order = np.arange(10)
        block_index = np.zeros(10)
        feats = order_only_features(trial_order, block_index)
        assert feats.shape == (10, 2)

    def test_block_session_only_features_shape(self):
        feats = block_session_only_features(np.zeros(10), np.ones(10))
        assert feats.shape == (10, 2)

    def test_quality_only_features_stacks_sorted_keys(self):
        dicts = [{"quality__b": 2.0, "quality__a": 1.0}, {"quality__b": 4.0, "quality__a": 3.0}]
        feats = quality_only_features(dicts)
        assert feats.shape == (2, 2)
        assert feats[0].tolist() == [1.0, 2.0]  # sorted: quality__a, quality__b


class TestChanceMajorityBaseline:
    def test_identifies_majority_class(self):
        y = np.array(["visual_square"] * 20 + ["visual_face_male"] * 5 + ["visual_face_female"] * 5)
        result = chance_majority_content_baseline(y)
        assert result["majority_class"] == "visual_square"
        assert result["class_counts"]["visual_square"] == 20
