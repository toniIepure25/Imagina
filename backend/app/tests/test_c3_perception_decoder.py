"""Smoke tests for C3 perception decoder and retrieval evaluation.

Uses synthetic data to verify:
- Ridge decoder trains and predicts
- Voxel selection works
- Retrieval evaluation produces valid metrics
- Shuffled null is near expected chance
- Decoder generalizes on structured synthetic data
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.decoder import (
    DecoderConfig,
    _batch_cosine_similarity,
    compute_shuffled_null,
    evaluate_retrieval,
    select_voxels,
    train_ridge_decoder,
)


class TestVoxelSelection:
    def test_nsdgeneral_selects_nonzero(self):
        roi = np.array([0, 1, 1, 0, 1], dtype=np.int32)
        ncsnr = np.array([0.5, 0.3, 0.8, 0.1, 0.6], dtype=np.float32)
        mask = select_voxels(roi, ncsnr, roi_id="nsdgeneral", ncsnr_threshold=0.0)
        assert mask.sum() == 3
        assert np.array_equal(mask, [False, True, True, False, True])

    def test_ncsnr_threshold_filters(self):
        roi = np.ones(5, dtype=np.int32)
        ncsnr = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)
        mask = select_voxels(roi, ncsnr, roi_id="nsdgeneral", ncsnr_threshold=0.4)
        assert mask.sum() == 3

    def test_specific_roi_labels(self):
        roi = np.array([0, 1, 2, 3, 4, 1, 2], dtype=np.int32)
        ncsnr = np.ones(7, dtype=np.float32)
        v1_mask = select_voxels(roi, ncsnr, roi_id="V1")
        assert v1_mask.sum() == 2
        v2_mask = select_voxels(roi, ncsnr, roi_id="V2")
        assert v2_mask.sum() == 2

    def test_streams_roi(self):
        streams = np.array([0, 1, 2, 3, 1, 2, 3], dtype=np.int32)
        ncsnr = np.ones(7, dtype=np.float32)
        ventral = select_voxels(streams, ncsnr, roi_id="ventral")
        assert ventral.sum() == 2


class TestRidgeDecoder:
    def test_trains_on_synthetic_data(self):
        rng = np.random.default_rng(42)
        n_images, n_voxels, emb_dim = 100, 50, 10
        X = rng.standard_normal((n_images, n_voxels))
        W_true = rng.standard_normal((n_voxels, emb_dim)) * 0.1
        Y = X @ W_true + rng.standard_normal((n_images, emb_dim)) * 0.01

        config = DecoderConfig(inner_cv_folds=3, alpha_candidates=(1.0, 10.0, 100.0))
        decoder = train_ridge_decoder(X, Y, config)

        assert decoder.weights.shape == (n_voxels, emb_dim)
        assert decoder.n_train_images == n_images
        assert decoder.n_voxels == n_voxels
        assert decoder.alpha in config.alpha_candidates

    def test_prediction_shape(self):
        rng = np.random.default_rng(123)
        n_images, n_voxels, emb_dim = 50, 30, 8
        X = rng.standard_normal((n_images, n_voxels))
        Y = rng.standard_normal((n_images, emb_dim))

        config = DecoderConfig(inner_cv_folds=3, alpha_candidates=(10.0,))
        decoder = train_ridge_decoder(X, Y, config)

        X_test = rng.standard_normal((10, n_voxels))
        preds = decoder.predict(X_test)
        assert preds.shape == (10, emb_dim)

    def test_decoder_generalizes_on_structured_signal(self):
        rng = np.random.default_rng(99)
        n_images, n_voxels, emb_dim = 200, 100, 16
        W_true = rng.standard_normal((n_voxels, emb_dim)) * 0.5
        X_train = rng.standard_normal((n_images, n_voxels))
        Y_train = X_train @ W_true

        config = DecoderConfig(inner_cv_folds=5, alpha_candidates=(0.1, 1.0, 10.0))
        decoder = train_ridge_decoder(X_train, Y_train, config)

        X_test = rng.standard_normal((50, n_voxels))
        Y_test = X_test @ W_true
        preds = decoder.predict(X_test)

        cos_sims = _batch_cosine_similarity(preds, Y_test)
        assert np.mean(cos_sims) > 0.9

    def test_config_spec_hash_deterministic(self):
        c1 = DecoderConfig()
        c2 = DecoderConfig()
        assert c1.spec_hash() == c2.spec_hash()

        c3 = DecoderConfig(alpha_candidates=(1.0, 10.0))
        assert c3.spec_hash() != c1.spec_hash()


class TestRetrievalEvaluation:
    def test_perfect_retrieval(self):
        n_candidates = 12
        emb_dim = 8
        rng = np.random.default_rng(42)
        pool = rng.standard_normal((n_candidates, emb_dim))
        pool = pool / np.linalg.norm(pool, axis=1, keepdims=True)

        n_trials = 24
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        predictions = pool[target_indices]
        targets = pool[target_indices]

        result = evaluate_retrieval(predictions, targets, pool, target_indices)
        assert result["mrr"] == 1.0
        assert result["top1_accuracy"] == 1.0
        assert result["median_rank"] == 1.0
        assert result["n_candidates"] == 12

    def test_random_retrieval_near_chance(self):
        n_candidates = 12
        emb_dim = 768
        rng = np.random.default_rng(42)
        pool = rng.standard_normal((n_candidates, emb_dim))

        n_trials = 1000
        predictions = rng.standard_normal((n_trials, emb_dim))
        target_indices = rng.integers(0, n_candidates, size=n_trials).astype(np.int64)
        targets = pool[target_indices]

        result = evaluate_retrieval(predictions, targets, pool, target_indices)
        expected_chance_mrr = sum(1.0 / k for k in range(1, n_candidates + 1)) / n_candidates
        assert abs(result["mrr"] - expected_chance_mrr) < 0.05

    def test_shuffled_null_near_chance(self):
        n_candidates = 12
        emb_dim = 32
        rng = np.random.default_rng(42)
        pool = rng.standard_normal((n_candidates, emb_dim))
        pool = pool / np.linalg.norm(pool, axis=1, keepdims=True)

        n_trials = 48
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        predictions = pool[target_indices]

        null_result = compute_shuffled_null(predictions, pool, target_indices, n_permutations=500, seed=42)
        expected_chance = sum(1.0 / k for k in range(1, n_candidates + 1)) / n_candidates
        assert abs(null_result["null_mean"] - expected_chance) < 0.1


class TestCosineSimilarity:
    def test_identical_vectors(self):
        A = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        B = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        sims = _batch_cosine_similarity(A, B)
        np.testing.assert_allclose(sims, [1.0, 1.0], atol=1e-7)

    def test_orthogonal_vectors(self):
        A = np.array([[1.0, 0.0]])
        B = np.array([[0.0, 1.0]])
        sims = _batch_cosine_similarity(A, B)
        np.testing.assert_allclose(sims, [0.0], atol=1e-7)
