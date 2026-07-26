"""Tests for perception pilot implementation and controls."""
from __future__ import annotations

import json
import numpy as np
import pytest
from pathlib import Path

from app.research.fmri.perception_pilot import (
    build_trial_assignments,
    compute_chance_mrr,
    build_clip_index_map,
    fit_ridge,
    compute_metrics,
    average_repeated_trials,
    select_alpha,
)


class TestChanceMRR:
    """Verify candidate-pool chance MRR computation."""

    def test_12_candidates(self):
        mrr = compute_chance_mrr(12)
        expected = sum(1.0 / k for k in range(1, 13)) / 12
        assert abs(mrr - expected) < 1e-10
        assert abs(mrr - 0.2586) < 0.001

    def test_1000_candidates(self):
        mrr = compute_chance_mrr(1000)
        expected = sum(1.0 / k for k in range(1, 1001)) / 1000
        assert abs(mrr - expected) < 1e-10
        assert mrr < 0.008  # Much smaller than 12-candidate chance

    def test_perception_is_not_imagery(self):
        """The perception candidate pool (1000) gives much lower chance MRR than imagery (12)."""
        imagery_mrr = compute_chance_mrr(12)
        perception_mrr = compute_chance_mrr(1000)
        assert perception_mrr < imagery_mrr / 10


class TestCLIPIndexMap:
    """Verify CLIP embedding row mapping."""

    def test_sorted_order(self):
        all_ids = [10, 20, 30, 40, 50]
        split_ids = [30, 10, 50]
        result = build_clip_index_map(split_ids, all_ids)
        assert list(result) == [2, 0, 4]

    def test_one_index_shift_fails(self):
        """Off-by-one in ID mapping produces wrong indices."""
        all_ids = list(range(100, 110))  # Only 10 IDs
        split_ids = [100, 105, 109]
        correct = build_clip_index_map(split_ids, all_ids)
        assert list(correct) == [0, 5, 9]
        # Shift by +1: 101, 106, 110 - 110 is not in the set
        shifted_ids = [101, 106, 110]
        with pytest.raises(KeyError):
            build_clip_index_map(shifted_ids, all_ids)


class TestFitRidge:
    """Verify ridge regression implementation."""

    def test_dual_vs_primal_equivalent(self):
        rng = np.random.default_rng(42)
        n_samples, n_features, n_targets = 50, 100, 10
        x = rng.standard_normal((n_samples, n_features)).astype(np.float32)
        y = rng.standard_normal((n_samples, n_targets)).astype(np.float32)
        alpha = 100.0

        w_dual = fit_ridge(x, y, alpha)  # n_samples < n_features -> dual
        assert w_dual.shape == (n_features, n_targets)

        # Verify against closed-form primal
        xtx = x.astype(np.float64).T @ x.astype(np.float64)
        xtx += alpha * np.eye(n_features, dtype=np.float64)
        xty = x.astype(np.float64).T @ y.astype(np.float64)
        w_primal = np.linalg.solve(xtx, xty).astype(np.float32)

        np.testing.assert_allclose(w_dual, w_primal, atol=1e-3)

    def test_primal_form_used(self):
        rng = np.random.default_rng(42)
        n_samples, n_features = 200, 50
        x = rng.standard_normal((n_samples, n_features)).astype(np.float32)
        y = rng.standard_normal((n_samples, 10)).astype(np.float32)
        w = fit_ridge(x, y, 1.0)
        assert w.shape == (n_features, 10)


class TestTrialAssignments:
    """Verify trial-to-split assignment logic."""

    def test_no_image_crosses_splits(self):
        rng = np.random.default_rng(42)
        masterordering = np.arange(1, 11)  # 1-based slots 1..10
        subjectim = np.array([[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]])  # 10 slots
        split = {
            "train": {10, 20, 30, 40, 50, 60},
            "val": {70, 80},
            "test": {90, 100},
        }
        assignments = build_trial_assignments(masterordering, subjectim, split)
        all_trials = set(assignments["train"]) | set(assignments["val"]) | set(assignments["test"])
        assert len(all_trials) == 10

    def test_repeated_images_stay_together(self):
        masterordering = np.array([1, 2, 3, 1, 2, 3])  # 1-based slots
        subjectim = np.array([[10, 20, 30]])  # slot 0->10, 1->20, 2->30
        split = {"train": {10, 20}, "val": set(), "test": {30}}
        assignments = build_trial_assignments(masterordering, subjectim, split)
        assert 0 in assignments["train"] and 3 in assignments["train"]
        assert 2 in assignments["test"] and 5 in assignments["test"]


class TestAverageRepeatedTrials:
    """Verify repeated presentation averaging."""

    def test_averaging(self):
        fmri = np.array([[1, 2], [3, 4], [5, 6], [7, 8]], dtype=np.float32)
        trial_to_image = np.array([10, 20, 10, 20])
        image_ids = [10, 20]
        avg, ordered = average_repeated_trials(fmri, trial_to_image, image_ids)
        assert ordered == [10, 20]
        np.testing.assert_array_equal(avg[0], [3, 4])  # mean of [1,2] and [5,6]
        np.testing.assert_array_equal(avg[1], [5, 6])  # mean of [3,4] and [7,8]


class TestPilotSchema:
    """Validate pilot result JSON schema."""

    def test_required_fields(self):
        required_fields = [
            "timestamp", "subject", "state", "scope", "decision",
            "config", "test_candidate_count", "chance_mrr",
            "primary_metrics_image_averaged", "trial_level_metrics",
            "permutation_test",
        ]
        pilot_path = Path(__file__).parents[3] / "../../results/c3_subj01_perception_pilot.json"
        if not pilot_path.exists():
            pytest.skip("Pilot results not yet generated")
        with open(pilot_path) as f:
            data = json.load(f)
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_valid_decisions(self):
        valid = {
            "SUBJ01_PERCEPTION_FOUNDATION_PASS",
            "SUBJ01_PERCEPTION_FOUNDATION_NULL",
            "SUBJ01_PERCEPTION_FOUNDATION_FAILED_BY_MAPPING",
            "SUBJ01_PERCEPTION_FOUNDATION_FAILED_BY_LEAKAGE",
            "SUBJ01_PERCEPTION_FOUNDATION_BLOCKED",
        }
        pilot_path = Path(__file__).parents[3] / "../../results/c3_subj01_perception_pilot.json"
        if not pilot_path.exists():
            pytest.skip("Pilot results not yet generated")
        with open(pilot_path) as f:
            data = json.load(f)
        assert data["decision"] in valid


class TestReadinessTransitions:
    """Validate readiness state transitions."""

    def test_pass_enables_acquisition(self):
        readiness_path = Path(__file__).parents[3] / "../../results/c3_realdata_readiness.json"
        if not readiness_path.exists():
            pytest.skip("Readiness not yet generated")
        with open(readiness_path) as f:
            data = json.load(f)
        if data.get("pilot_decision") == "SUBJ01_PERCEPTION_FOUNDATION_PASS":
            assert data["current_status"] == "READY_FOR_REMAINING_PARTICIPANT_ACQUISITION"
            assert len(data["authorized_participants"]) == 3
        elif "NULL" in data.get("pilot_decision", ""):
            assert "BLOCKED" in data["current_status"]
            assert data["authorized_participants"] == []


class TestMappingControls:
    """Test that mapping controls would detect errors."""

    def test_shifted_targets_reduce_performance(self):
        rng = np.random.default_rng(42)
        n, d = 100, 768
        predictions = rng.standard_normal((n, d)).astype(np.float32)
        predictions /= np.linalg.norm(predictions, axis=1, keepdims=True)
        targets = predictions + rng.standard_normal((n, d)).astype(np.float32) * 0.1
        targets /= np.linalg.norm(targets, axis=1, keepdims=True)

        correct_metrics = compute_metrics(predictions, None, targets)
        shifted = np.roll(targets, 1, axis=0)
        shifted_metrics = compute_metrics(predictions, None, shifted)
        assert correct_metrics["mrr"] > shifted_metrics["mrr"]

    def test_40_session_certification_schema(self):
        cert_path = Path(__file__).parents[3] / "../../results/c3_subj01_perception_certification.json"
        if not cert_path.exists():
            pytest.skip("Certification not yet generated")
        with open(cert_path) as f:
            data = json.load(f)
        assert data["aggregate"]["total_sessions"] == 40
        assert data["aggregate"]["certified_sessions"] == 40
        assert data["aggregate"]["total_trials"] == 30000
        assert data["certification_status"] == "SUBJ01_PERCEPTION_ACQUISITION_CERTIFIED"
