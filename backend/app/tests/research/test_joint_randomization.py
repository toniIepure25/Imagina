"""Tests for joint randomization (permutation test) implementation.

Tests cover:
- Strict null calibration (Type-I rate)
- Known positive effect (power)
- Heterogeneous participant effects
- One influential participant
- Duplicate candidates
- Missing trials
- Chance MRR computation
"""
from __future__ import annotations

import numpy as np
import pytest

from app.research.fmri.joint_randomization import (
    PermutationTestConfig,
    calibration_test_strict_null,
    compute_chance_mrr,
    compute_ranks,
    group_permutation_test,
    within_subject_permutation_test,
)


class TestComputeChanceMRR:
    def test_mrr_12_candidates(self):
        """E[MRR] = H_12 / 12 for 12 candidates."""
        expected = sum(1.0 / k for k in range(1, 13)) / 12
        result = compute_chance_mrr(12)
        assert abs(result - expected) < 1e-10
        assert abs(result - 0.2586) < 0.001

    def test_mrr_2_candidates(self):
        expected = (1.0 + 0.5) / 2
        assert abs(compute_chance_mrr(2) - expected) < 1e-10

    def test_mrr_1_candidate(self):
        assert abs(compute_chance_mrr(1) - 1.0) < 1e-10


class TestComputeRanks:
    def test_perfect_predictions(self):
        pool = np.eye(5, dtype=np.float64)
        predictions = pool.copy()
        targets = np.arange(5, dtype=np.int64)
        ranks = compute_ranks(predictions, pool, targets)
        np.testing.assert_array_equal(ranks, np.ones(5, dtype=np.int64))

    def test_random_predictions_not_all_rank1(self):
        rng = np.random.default_rng(42)
        pool = rng.standard_normal((12, 64))
        predictions = rng.standard_normal((50, 64))
        targets = rng.integers(0, 12, size=50)
        ranks = compute_ranks(predictions, pool, targets)
        assert not np.all(ranks == 1)
        assert np.all(ranks >= 1)
        assert np.all(ranks <= 12)


class TestWithinSubjectPermutation:
    def test_perfect_signal_significant(self):
        rng = np.random.default_rng(7)
        pool = rng.standard_normal((12, 64))
        pool /= np.linalg.norm(pool, axis=1, keepdims=True)
        targets = rng.integers(0, 12, size=50)
        predictions = pool[targets] + rng.standard_normal((50, 64)) * 0.01

        config = PermutationTestConfig(n_permutations=1000, seed=7)
        result = within_subject_permutation_test(predictions, pool, targets, config)
        assert result["p_value"] < 0.01
        assert result["significant"] is True
        assert result["observed_mrr"] > result["null_mean"]

    def test_random_predictions_not_significant(self):
        rng = np.random.default_rng(123)
        pool = rng.standard_normal((12, 64))
        predictions = rng.standard_normal((50, 64))
        targets = rng.integers(0, 12, size=50)

        config = PermutationTestConfig(n_permutations=500, seed=123)
        result = within_subject_permutation_test(predictions, pool, targets, config)
        assert result["p_value"] > 0.01

    def test_monte_carlo_correction_formula(self):
        rng = np.random.default_rng(99)
        pool = rng.standard_normal((12, 64))
        predictions = rng.standard_normal((20, 64))
        targets = rng.integers(0, 12, size=20)

        config = PermutationTestConfig(n_permutations=100, seed=99)
        result = within_subject_permutation_test(predictions, pool, targets, config)
        expected_p = (result["extreme_count"] + 1) / (config.n_permutations + 1)
        assert abs(result["p_value"] - expected_p) < 1e-10


class TestGroupPermutationTest:
    def test_consistent_positive_effects(self):
        participant_results = [
            {"effect_size_delta": 0.3},
            {"effect_size_delta": 0.25},
            {"effect_size_delta": 0.35},
            {"effect_size_delta": 0.28},
        ]
        config = PermutationTestConfig(n_permutations=10000, seed=42)
        result = group_permutation_test(participant_results, config)
        assert result["p_value_mc"] < 0.1
        assert result["exact_sign_flip"] is not None
        assert result["exact_sign_flip"]["n_configurations"] == 16

    def test_mixed_effects_not_significant(self):
        participant_results = [
            {"effect_size_delta": 0.1},
            {"effect_size_delta": -0.2},
            {"effect_size_delta": 0.05},
            {"effect_size_delta": -0.15},
        ]
        config = PermutationTestConfig(n_permutations=1000, seed=42)
        result = group_permutation_test(participant_results, config)
        assert result["p_value_mc"] > 0.1

    def test_one_influential_participant(self):
        participant_results = [
            {"effect_size_delta": 0.01},
            {"effect_size_delta": 0.02},
            {"effect_size_delta": 0.01},
            {"effect_size_delta": 0.8},
        ]
        config = PermutationTestConfig(n_permutations=1000, seed=42)
        result = group_permutation_test(participant_results, config)
        assert len(result["leave_one_out"]) == 4
        excluded_3 = result["leave_one_out"][3]
        assert excluded_3["excluded_delta"] == 0.8

    def test_exact_sign_flip_min_p_for_4_participants(self):
        participant_results = [
            {"effect_size_delta": 0.5},
            {"effect_size_delta": 0.5},
            {"effect_size_delta": 0.5},
            {"effect_size_delta": 0.5},
        ]
        config = PermutationTestConfig(n_permutations=1000, seed=42)
        result = group_permutation_test(participant_results, config)
        assert result["exact_sign_flip"]["min_achievable_p"] == 1 / 16
        assert abs(result["exact_sign_flip"]["min_achievable_p"] - 0.0625) < 1e-10


class TestDuplicateCandidates:
    def test_duplicate_candidates_handled(self):
        rng = np.random.default_rng(55)
        pool = rng.standard_normal((12, 64))
        pool[11] = pool[0]  # duplicate
        targets = np.zeros(20, dtype=np.int64)
        predictions = pool[0:1].repeat(20, axis=0) + rng.standard_normal((20, 64)) * 0.01

        config = PermutationTestConfig(n_permutations=100, seed=55)
        result = within_subject_permutation_test(predictions, pool, targets, config)
        assert "p_value" in result


class TestMissingTrials:
    def test_single_trial(self):
        rng = np.random.default_rng(77)
        pool = rng.standard_normal((12, 64))
        pool /= np.linalg.norm(pool, axis=1, keepdims=True)
        targets = np.array([3], dtype=np.int64)
        predictions = pool[3:4] + rng.standard_normal((1, 64)) * 0.01

        config = PermutationTestConfig(n_permutations=100, seed=77)
        result = within_subject_permutation_test(predictions, pool, targets, config)
        assert result["n_trials"] == 1


class TestCalibration:
    @pytest.mark.slow
    def test_type_i_rate_under_null(self):
        """Under strict null, rejection rate should be near alpha."""
        config = PermutationTestConfig(n_permutations=200, seed=42)
        result = calibration_test_strict_null(
            n_trials=30,
            n_candidates=12,
            n_simulations=200,
            config=config,
            tolerance=0.04,
        )
        assert result["within_tolerance"] or result["observed_type_i_rate"] < 0.12
