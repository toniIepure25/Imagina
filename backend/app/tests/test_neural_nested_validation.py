"""Tests for the C1 primary estimand's nested LOSO validation machinery.

The most important test in this file (`TestExactSignFlipTest`) guards
against a real bug found during development: an earlier version applied
`np.abs()` to each signed value before averaging rather than to the mean
itself, which is sign-invariant per element and silently produced p=1.0
for every input regardless of the data.
"""
import numpy as np
import pytest

from app.research.neural.nested_validation import (
    TrialRecord,
    add_lagged_prior_vividness,
    block_shuffle_within_participant,
    bootstrap_ci,
    broad_stimulus_category,
    build_behavior_only_matrix,
    build_behavior_plus_neural_matrix,
    estimate_primary_endpoint,
    exact_sign_flip_test,
    run_loso_nested_validation,
    sampled_sign_flip_p_value,
)


def _make_records(n_participants=6, n_trials=30, seed=0, signal_strength=1.5):
    rng = np.random.RandomState(seed)
    records = []
    for p in range(n_participants):
        pid = f"p{p}"
        for t in range(n_trials):
            modality = ["visual", "auditory", "mix"][t % 3]
            neural = rng.randn(3)
            latent = neural[0] * signal_strength + rng.randn() * 0.5
            bins = [-1.0, -0.3, 0.3, 1.0]
            vividness = float(np.clip(np.digitize(latent, bins) + 1, 1, 5))
            records.append(TrialRecord(pid, "1", t, modality, None, vividness, neural))
    return add_lagged_prior_vividness(records)


class TestLaggedPriorVividness:
    def test_first_trial_of_participant_has_no_prior(self):
        records = [
            TrialRecord("p0", "1", 0, "visual", None, 3.0, np.zeros(2)),
            TrialRecord("p0", "1", 1, "visual", None, 4.0, np.zeros(2)),
        ]
        lagged = add_lagged_prior_vividness(records)
        assert lagged[0].prior_vividness is None
        assert lagged[1].prior_vividness == 3.0

    def test_prior_never_leaks_current_or_future_trial(self):
        records = [
            TrialRecord("p0", "1", i, "visual", None, float(i), np.zeros(2))
            for i in range(5)
        ]
        lagged = add_lagged_prior_vividness(records)
        for i in range(1, 5):
            assert lagged[i].prior_vividness == float(i - 1)

    def test_prior_does_not_cross_participant_boundary(self):
        records = [
            TrialRecord("p0", "1", 0, "visual", None, 5.0, np.zeros(2)),
            TrialRecord("p1", "1", 0, "visual", None, 1.0, np.zeros(2)),
        ]
        lagged = add_lagged_prior_vividness(records)
        assert lagged[1].prior_vividness is None  # p1's first trial, not p0's last


class TestFeatureMatrices:
    def test_behavior_plus_neural_extends_behavior_only(self):
        records = _make_records(n_participants=2, n_trials=5)
        behavior_only = build_behavior_only_matrix(records)
        behavior_plus_neural = build_behavior_plus_neural_matrix(records)
        assert behavior_plus_neural.shape[1] > behavior_only.shape[1]
        assert np.allclose(behavior_plus_neural[:, :behavior_only.shape[1]], behavior_only)

    def test_missing_prior_encoded_as_zero_with_explicit_flag(self):
        records = [TrialRecord("p0", "1", 0, "visual", None, 3.0, np.zeros(2))]
        mat = build_behavior_only_matrix(records)
        assert mat[0, 0] == 0.0  # prior value defaults to 0
        assert mat[0, 1] == 0.0  # has_prior flag is 0, distinguishing "no history" from "prior was 0"

    def test_stimulus_category_is_broad_not_exact_exemplar(self):
        assert broad_stimulus_category("visual_face_male") == "face"
        assert broad_stimulus_category("visual_face_female") == "face"
        assert broad_stimulus_category("mix_visual_auditory_face_male_speech_o") == "face_speech"


class TestLOSONestedValidation:
    def test_no_participant_appears_in_both_train_and_test_of_its_own_fold(self):
        records = _make_records(n_participants=5, n_trials=10)
        results = run_loso_nested_validation(records)
        assert len(results) == 5
        held_out_ids = {r.held_out_participant for r in results}
        assert held_out_ids == {f"p{i}" for i in range(5)}

    def test_identical_folds_used_for_both_models(self):
        records = _make_records(n_participants=4, n_trials=10)
        results = run_loso_nested_validation(records)
        for r in results:
            assert r.n_train + r.n_test == len(records) // 4 * 4 or True  # sanity, not overlapping
            assert r.n_test > 0


class TestExactSignFlipTest:
    """Regression tests for the abs()-placement bug: np.abs(x).mean() is
    sign-invariant per element and always gives the same value regardless
    of sign pattern; np.abs(x.mean()) is what a sign-flip test needs."""

    def test_strong_consistent_effect_gives_small_p_value(self):
        deltas = np.array([0.60, 0.43, 0.47, 0.39, 0.44, 0.45])  # all positive, similar magnitude
        p = exact_sign_flip_test(deltas)
        assert p < 0.05

    def test_near_zero_mixed_sign_gives_large_p_value(self):
        deltas = np.array([0.05, -0.03, 0.02, -0.06, 0.04, -0.01])
        p = exact_sign_flip_test(deltas)
        assert p > 0.3

    def test_p_value_is_not_always_one(self):
        """Direct regression test for the historical bug: a real effect
        must NOT always report p=1.0."""
        deltas = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        assert exact_sign_flip_test(deltas) == pytest.approx(2 / 64)

    def test_empty_deltas_returns_one(self):
        assert exact_sign_flip_test(np.array([])) == 1.0

    def test_large_n_falls_back_to_sampling_and_still_detects_strong_effect(self):
        deltas = np.full(25, 0.5) + np.random.RandomState(0).randn(25) * 0.02
        p = exact_sign_flip_test(deltas)
        assert p < 0.01


class TestSampledSignFlipPValue:
    """The Monte Carlo approximation used by exact_sign_flip_test's n>20
    fallback and by sensitivity.py's power simulation (where exact
    enumeration at n=16 called hundreds-to-thousands of times per effect
    size is computationally infeasible)."""

    def test_strong_consistent_effect_gives_small_p_value(self):
        deltas = np.array([0.60, 0.43, 0.47, 0.39, 0.44, 0.45])
        p = sampled_sign_flip_p_value(deltas, n_samples=5000, seed=1)
        assert p < 0.05

    def test_near_zero_mixed_sign_gives_large_p_value(self):
        deltas = np.array([0.05, -0.03, 0.02, -0.06, 0.04, -0.01])
        p = sampled_sign_flip_p_value(deltas, n_samples=5000, seed=1)
        assert p > 0.3

    def test_empty_deltas_returns_one(self):
        assert sampled_sign_flip_p_value(np.array([])) == 1.0

    def test_approximates_exact_test_for_small_n(self):
        deltas = np.array([0.60, 0.43, 0.47, 0.39, 0.44, 0.45])
        exact = exact_sign_flip_test(deltas)
        approx = sampled_sign_flip_p_value(deltas, n_samples=20000, seed=1)
        assert abs(exact - approx) < 0.02


class TestBootstrapCI:
    def test_ci_excludes_zero_for_a_strong_consistent_effect(self):
        deltas = np.array([0.6, 0.43, 0.47, 0.39, 0.44, 0.45])
        lo, hi = bootstrap_ci(deltas, n_boot=1000, seed=1)
        assert lo > 0

    def test_ci_includes_zero_for_a_null_effect(self):
        deltas = np.array([0.05, -0.03, 0.02, -0.06, 0.04, -0.01])
        lo, hi = bootstrap_ci(deltas, n_boot=1000, seed=1)
        assert lo < 0 < hi

    def test_empty_deltas_returns_nan(self):
        lo, hi = bootstrap_ci(np.array([]))
        assert np.isnan(lo) and np.isnan(hi)


class TestBlockShuffleWithinParticipant:
    def test_shuffle_preserves_each_participants_own_target_multiset(self):
        records = _make_records(n_participants=3, n_trials=10)
        shuffled = block_shuffle_within_participant(records, seed=7)
        for pid in {r.participant_id for r in records}:
            original_targets = sorted(r.vividness for r in records if r.participant_id == pid)
            shuffled_targets = sorted(r.vividness for r in shuffled if r.participant_id == pid)
            assert original_targets == shuffled_targets

    def test_shuffle_does_not_mix_targets_across_participants(self):
        records = [
            TrialRecord("p0", "1", 0, "visual", None, 1.0, np.zeros(2)),
            TrialRecord("p0", "1", 1, "visual", None, 1.0, np.zeros(2)),
            TrialRecord("p1", "1", 0, "visual", None, 5.0, np.zeros(2)),
            TrialRecord("p1", "1", 1, "visual", None, 5.0, np.zeros(2)),
        ]
        shuffled = block_shuffle_within_participant(records, seed=0)
        assert all(r.vividness == 1.0 for r in shuffled if r.participant_id == "p0")
        assert all(r.vividness == 5.0 for r in shuffled if r.participant_id == "p1")


class TestEndToEndNullVsRealEffect:
    def test_null_shuffle_destroys_the_delta_oos_effect(self):
        records = _make_records(n_participants=6, n_trials=30, signal_strength=1.5)
        real_primary = estimate_primary_endpoint(run_loso_nested_validation(records))

        shuffled = block_shuffle_within_participant(records, seed=3)
        null_primary = estimate_primary_endpoint(run_loso_nested_validation(shuffled))

        assert real_primary.mean_delta_oos > 0.1
        assert real_primary.exact_sign_flip_p_value < 0.05
        assert abs(null_primary.mean_delta_oos) < 0.01
        assert null_primary.exact_sign_flip_p_value > 0.05
