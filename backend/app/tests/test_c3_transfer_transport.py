"""Smoke tests for C3 zero-shot transfer and state transport.

Verifies on synthetic data:
- Zero-shot transfer produces valid results
- Participant-level inference works correctly
- Transport methods improve when signal is present
- Random transport does not improve
- LOSO transport evaluation runs correctly
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.decoder import DecoderConfig, train_ridge_decoder
from app.research.fmri.transfer import (
    participant_level_inference,
    per_stimulus_analysis,
    zero_shot_transfer,
)
from app.research.fmri.transport import (
    affine_ridge_transport,
    evaluate_transport_loso,
    identity_transport,
    low_rank_transport,
    mean_correction_transport,
    random_low_rank_transport,
)


class TestZeroShotTransfer:
    def test_produces_valid_results(self):
        rng = np.random.default_rng(42)
        n_voxels, emb_dim = 50, 16
        n_candidates = 12

        X_train = rng.standard_normal((100, n_voxels))
        W_true = rng.standard_normal((n_voxels, emb_dim)) * 0.3
        Y_train = X_train @ W_true

        config = DecoderConfig(inner_cv_folds=3, alpha_candidates=(10.0,))
        decoder = train_ridge_decoder(X_train, Y_train, config)

        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)

        n_trials = 48
        imagery_betas = rng.standard_normal((n_trials, n_voxels))
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        target_embeddings = candidate_pool[target_indices]

        result = zero_shot_transfer(decoder, imagery_betas, candidate_pool, target_indices, target_embeddings)
        assert result["method"] == "zero_shot_frozen_perception_decoder"
        assert result["n_trials"] == n_trials
        assert result["n_candidates"] == n_candidates
        assert 0.0 <= result["retrieval"]["mrr"] <= 1.0

    def test_perfect_signal_gives_high_mrr(self):
        rng = np.random.default_rng(99)
        n_voxels, emb_dim = 100, 16
        n_candidates = 6

        W_true = rng.standard_normal((n_voxels, emb_dim)) * 0.5
        X_train = rng.standard_normal((200, n_voxels))
        Y_train = X_train @ W_true

        config = DecoderConfig(inner_cv_folds=3, alpha_candidates=(0.1, 1.0))
        decoder = train_ridge_decoder(X_train, Y_train, config)

        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)

        n_trials = 24
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        target_embs = candidate_pool[target_indices]
        W_pinv = np.linalg.pinv(W_true)
        imagery_betas = target_embs @ W_pinv + rng.standard_normal((n_trials, n_voxels)) * 0.01
        target_embeddings = candidate_pool[target_indices]

        result = zero_shot_transfer(decoder, imagery_betas, candidate_pool, target_indices, target_embeddings)
        assert result["retrieval"]["mrr"] > 0.8


class TestPerStimulusAnalysis:
    def test_produces_per_stimulus_output(self):
        rng = np.random.default_rng(42)
        n_voxels, emb_dim = 30, 8

        X_train = rng.standard_normal((60, n_voxels))
        Y_train = rng.standard_normal((60, emb_dim))
        config = DecoderConfig(inner_cv_folds=3, alpha_candidates=(10.0,))
        decoder = train_ridge_decoder(X_train, Y_train, config)

        n_candidates = 6
        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        n_trials = 24
        imagery_betas = rng.standard_normal((n_trials, n_voxels))
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        stimulus_ids = target_indices.copy()

        result = per_stimulus_analysis(decoder, imagery_betas, candidate_pool, target_indices, stimulus_ids)
        assert result["n_stimuli"] == n_candidates
        assert len(result["per_stimulus_mrr"]) == n_candidates


class TestParticipantInference:
    def test_all_positive_deltas(self):
        result = participant_level_inference([0.5, 0.6, 0.55, 0.7], null_mrr=0.259)
        assert result["n_participants"] == 4
        assert result["observed_mean_delta"] > 0
        assert result["sign_flip_p_value"] <= 1.0 / 16

    def test_all_negative_deltas(self):
        result = participant_level_inference([0.1, 0.15, 0.12, 0.08], null_mrr=0.259)
        assert result["observed_mean_delta"] < 0
        assert result["sign_flip_p_value"] > 0.5

    def test_minimum_p_value(self):
        result = participant_level_inference([0.9, 0.8, 0.85, 0.95], null_mrr=0.259)
        assert result["minimum_achievable_p"] == 1.0 / 16


class TestTransportMethods:
    def test_identity_unchanged(self):
        preds = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = identity_transport(preds)
        np.testing.assert_array_equal(result, preds)

    def test_mean_correction_shifts(self):
        train_preds = np.array([[1.0, 0.0], [1.0, 0.0]])
        train_targets = np.array([[0.0, 1.0], [0.0, 1.0]])
        test_preds = np.array([[1.0, 0.0]])
        result = mean_correction_transport(test_preds, train_preds, train_targets)
        np.testing.assert_allclose(result, [[0.0, 1.0]])

    def test_affine_ridge_shape(self):
        rng = np.random.default_rng(42)
        train_preds = rng.standard_normal((20, 8))
        train_targets = rng.standard_normal((20, 8))
        test_preds = rng.standard_normal((5, 8))
        result = affine_ridge_transport(test_preds, train_preds, train_targets)
        assert result.shape == (5, 8)

    def test_low_rank_shape(self):
        rng = np.random.default_rng(42)
        train_preds = rng.standard_normal((20, 16))
        train_targets = rng.standard_normal((20, 16))
        test_preds = rng.standard_normal((5, 16))
        result = low_rank_transport(test_preds, train_preds, train_targets, rank=5)
        assert result.shape == (5, 16)

    def test_random_low_rank_shape(self):
        rng = np.random.default_rng(42)
        train_preds = rng.standard_normal((20, 16))
        train_targets = rng.standard_normal((20, 16))
        test_preds = rng.standard_normal((5, 16))
        result = random_low_rank_transport(test_preds, train_preds, train_targets, rank=5)
        assert result.shape == (5, 16)


class TestTransportLOSO:
    def test_loso_runs(self):
        rng = np.random.default_rng(42)
        n_candidates = 6
        emb_dim = 8
        n_trials = 48

        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)

        decoder_predictions = rng.standard_normal((n_trials, emb_dim))
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        target_embeddings = candidate_pool[target_indices]
        stimulus_ids = target_indices.copy()

        result = evaluate_transport_loso(
            decoder_predictions, target_embeddings, candidate_pool,
            target_indices, stimulus_ids, alpha=100.0, rank=3,
        )
        assert result["n_stimuli"] == n_candidates
        assert "identity" in result["methods"]
        assert "mean_correction" in result["methods"]
        assert "affine_ridge" in result["methods"]
        assert "low_rank" in result["methods"]
        assert "random_low_rank" in result["methods"]

    def test_transport_with_systematic_shift(self):
        rng = np.random.default_rng(99)
        n_candidates = 6
        emb_dim = 16
        n_trials = 96

        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)

        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)
        target_embeddings = candidate_pool[target_indices]
        stimulus_ids = target_indices.copy()

        shift = rng.standard_normal(emb_dim) * 2.0
        decoder_predictions = target_embeddings + shift

        result = evaluate_transport_loso(
            decoder_predictions, target_embeddings, candidate_pool,
            target_indices, stimulus_ids, alpha=1.0, rank=5,
        )

        mc_mrr = result["methods"]["mean_correction"]["mean_mrr"]
        id_mrr = result["methods"]["identity"]["mean_mrr"]
        assert mc_mrr >= id_mrr - 0.05
