"""Tests for C3 uncertainty calibration and negative controls."""
from __future__ import annotations

import numpy as np

from app.research.fmri.negative_controls import (
    mean_target_control,
    run_all_fixture_controls,
    shuffled_pairing_control,
    trial_order_control,
    verify_generator_free,
    verify_no_target_leakage,
    verify_perception_imagery_separation,
)
from app.research.fmri.uncertainty import (
    compute_distribution_distance,
    compute_repeat_variance,
    compute_roi_disagreement,
    risk_coverage_curve,
)


class TestUncertainty:
    def test_repeat_variance(self):
        rng = np.random.default_rng(42)
        preds = rng.standard_normal((6, 16, 8))
        var_scores = compute_repeat_variance(preds)
        assert var_scores.shape == (6,)
        assert np.all(var_scores >= 0)

    def test_distribution_distance(self):
        rng = np.random.default_rng(42)
        train_preds = rng.standard_normal((50, 8))
        imagery_preds = rng.standard_normal((10, 8)) + 5.0
        distances = compute_distribution_distance(imagery_preds, train_preds)
        assert distances.shape == (10,)
        assert np.all(distances > 0)

    def test_roi_disagreement(self):
        rng = np.random.default_rng(42)
        n_trials, emb_dim = 20, 8
        predictions_by_roi = {
            "V1": rng.standard_normal((n_trials, emb_dim)),
            "V2": rng.standard_normal((n_trials, emb_dim)) + 1.0,
            "hV4": rng.standard_normal((n_trials, emb_dim)) - 1.0,
        }
        disagreement = compute_roi_disagreement(predictions_by_roi)
        assert disagreement.shape == (n_trials,)
        assert np.all(disagreement >= 0)

    def test_risk_coverage_curve(self):
        rng = np.random.default_rng(42)
        n_trials = 48
        uncertainty = rng.uniform(0, 1, n_trials)
        rr = rng.uniform(0, 1, n_trials)

        result = risk_coverage_curve(uncertainty, rr, thresholds=5)
        assert len(result["coverages"]) == 5
        assert len(result["selective_mrrs"]) == 5
        assert result["coverages"][-1] == 1.0


class TestNegativeControls:
    def test_shuffled_pairing(self):
        rng = np.random.default_rng(42)
        n_candidates, emb_dim = 12, 16
        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)

        n_trials = 48
        predictions = rng.standard_normal((n_trials, emb_dim))
        target_indices = np.array([i % n_candidates for i in range(n_trials)], dtype=np.int64)

        result = shuffled_pairing_control(predictions, candidate_pool, target_indices, n_permutations=50)
        assert result["status"] == "PASS"
        assert result["null_mean_mrr"] > 0

    def test_mean_target(self):
        rng = np.random.default_rng(42)
        n_candidates, emb_dim = 12, 16
        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)
        target_indices = np.array([i % n_candidates for i in range(48)], dtype=np.int64)

        result = mean_target_control(candidate_pool, target_indices, 48)
        assert result["status"] == "PASS"
        assert 0 <= result["mrr"] <= 1.0

    def test_trial_order(self):
        rng = np.random.default_rng(42)
        n_candidates, emb_dim = 12, 16
        candidate_pool = rng.standard_normal((n_candidates, emb_dim))
        candidate_pool /= np.linalg.norm(candidate_pool, axis=1, keepdims=True)
        target_indices = np.array([i % n_candidates for i in range(48)], dtype=np.int64)

        result = trial_order_control(48, candidate_pool, target_indices, emb_dim)
        assert result["status"] == "PASS"

    def test_no_leakage_clean(self):
        result = verify_no_target_leakage({"fmri_betas": "data", "roi_mask": "nsdgeneral"})
        assert result["status"] == "PASS"
        assert result["leaked_keys"] == []

    def test_leakage_detected(self):
        result = verify_no_target_leakage({"fmri_betas": "data", "target_embedding": "leaked!"})
        assert result["status"] == "FAIL"

    def test_perception_imagery_separation(self):
        result = verify_perception_imagery_separation(
            {"nsd_img_001", "nsd_img_002"},
            {"stim_A", "stim_B"},
        )
        assert result["status"] == "PASS"
        assert result["overlap"] == []

    def test_separation_overlap_detected(self):
        result = verify_perception_imagery_separation(
            {"shared_001", "nsd_img_002"},
            {"shared_001", "stim_B"},
        )
        assert result["status"] == "FAIL"

    def test_generator_free_clean(self):
        result = verify_generator_free({"method": "ridge", "metric": "mrr"})
        assert result["status"] == "PASS"

    def test_generator_detected(self):
        result = verify_generator_free({"method": "stable_diffusion_reconstruction"})
        assert result["status"] == "FAIL"

    def test_run_all_fixture_controls(self):
        result = run_all_fixture_controls()
        assert result["all_pass"] is True
        assert result["total"] >= 6
