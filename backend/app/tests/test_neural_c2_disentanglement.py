"""Tests for the C2 disentanglement probe machinery (Commit 6). Synthetic
embedding matrices only.
"""
from __future__ import annotations

import numpy as np

from app.research.neural.c2_disentanglement import (
    quality_bin_labels,
    run_binary_probe,
    run_multiclass_probe,
    stratified_kfold_indices,
)


class TestStratifiedKFoldIndices:
    def test_every_sample_appears_in_exactly_one_test_fold(self):
        labels = np.array(["a", "b", "c"] * 20)
        splits = stratified_kfold_indices(labels, n_folds=5)
        all_test_idx = np.concatenate([test for _, test in splits])
        assert sorted(all_test_idx.tolist()) == list(range(len(labels)))

    def test_train_test_disjoint_within_each_fold(self):
        labels = np.array(["a", "b"] * 30)
        splits = stratified_kfold_indices(labels, n_folds=4)
        for train_idx, test_idx in splits:
            assert set(train_idx.tolist()).isdisjoint(set(test_idx.tolist()))

    def test_deterministic_for_same_seed(self):
        labels = np.array(["a", "b", "c"] * 10)
        s1 = stratified_kfold_indices(labels, n_folds=3, seed=42)
        s2 = stratified_kfold_indices(labels, n_folds=3, seed=42)
        for (tr1, te1), (tr2, te2) in zip(s1, s2):
            assert np.array_equal(tr1, tr2)
            assert np.array_equal(te1, te2)


class TestQualityBinLabels:
    def test_produces_requested_number_of_bins(self):
        rng = np.random.RandomState(0)
        values = rng.randn(300)
        bins = quality_bin_labels(values, n_bins=3)
        assert len(set(bins.tolist())) == 3

    def test_roughly_balanced_bin_sizes(self):
        rng = np.random.RandomState(0)
        values = rng.randn(300)
        bins = quality_bin_labels(values, n_bins=3)
        counts = [np.sum(bins == f"quality_bin_{i}") for i in range(3)]
        assert max(counts) - min(counts) < 20  # roughly equal-sized quantile bins


class TestRunMulticlassProbe:
    def test_recovers_informative_signal(self):
        rng = np.random.RandomState(0)
        n = 150
        labels = rng.choice(["p0", "p1", "p2"], size=n)
        emb = rng.randn(n, 6)
        for i, cls in enumerate(["p0", "p1", "p2"]):
            emb[labels == cls, 0] += i * 4.0
        result = run_multiclass_probe(emb, labels, "participant_identity", "stratified_5fold_within_sample")
        assert result.mean_metric < np.log(3)
        assert result.balanced_accuracy_mean > 0.6

    def test_single_class_is_reported_not_run_not_crashed(self):
        rng = np.random.RandomState(0)
        emb = rng.randn(50, 4)
        labels = np.array(["1"] * 50)
        result = run_multiclass_probe(emb, labels, "session_identity", "stratified_5fold_within_sample")
        assert result.n_folds == 0
        assert result.n_classes == 1
        assert "not meaningfully testable" in result.note

    def test_to_dict_is_json_serializable(self):
        import json
        rng = np.random.RandomState(0)
        emb = rng.randn(60, 4)
        labels = rng.choice(["a", "b", "c"], size=60)
        result = run_multiclass_probe(emb, labels, "content_category", "stratified_5fold_within_sample")
        json.dumps(result.to_dict())


class TestRunBinaryProbe:
    def test_recovers_informative_signal(self):
        rng = np.random.RandomState(0)
        n = 120
        labels = rng.choice(["perception", "imagery"], size=n)
        emb = rng.randn(n, 4)
        emb[labels == "imagery", 0] += 3.0
        result = run_binary_probe(emb, labels, "cognitive_state", "stratified_5fold_within_sample")
        assert result.mean_metric < np.log(2)

    def test_single_class_is_reported_not_run(self):
        rng = np.random.RandomState(0)
        emb = rng.randn(40, 4)
        labels = np.array(["perception"] * 40)
        result = run_binary_probe(emb, labels, "cognitive_state", "stratified_5fold_within_sample")
        assert result.n_folds == 0
