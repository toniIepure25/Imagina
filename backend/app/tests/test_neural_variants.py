"""Tests for the C1 real-data falsification-closure feature-variant system
(tests 2, 4, 5, 7). Uses small synthetic epoch arrays -- these validate
construction/provenance/determinism properties, not scientific results,
which come from the real ds005815 run persisted in results/c1_negative_controls.json.
"""
from __future__ import annotations

import numpy as np

from app.research.neural.preprocessing import EXPECTED_YOTO_CHANNELS, FRONTAL_PROXY_CHANNELS
from app.research.neural.variants import (
    CHANNEL_PERMUTATION_SEEDS,
    LATE_SHIFT_OFFSET_S,
    build_aligned_full_variant,
    build_channel_permuted_variant,
    build_frontal_proxy_variant,
    build_late_shift_trials,
    build_quality_only_variant,
    extract_quality_only_features,
    neighboring_trial_rejection_rate,
    permute_channel_labels,
)

SFREQ = 250.0
N_CHANNELS = len(EXPECTED_YOTO_CHANNELS)
N_SAMPLES = int(SFREQ * 4.0)  # imagery-phase-length epoch


def _synthetic_epoch(seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return rng.randn(N_CHANNELS, N_SAMPLES) * 1e-5


class TestPermuteChannelLabels:
    def test_permutation_is_a_rearrangement_not_a_new_set(self):
        names = list(EXPECTED_YOTO_CHANNELS)
        permuted = permute_channel_labels(names, seed=101)
        assert sorted(permuted) == sorted(names)
        assert permuted != names  # a real shuffle, not a no-op

    def test_deterministic_for_same_seed(self):
        names = list(EXPECTED_YOTO_CHANNELS)
        a = permute_channel_labels(names, seed=101)
        b = permute_channel_labels(names, seed=101)
        assert a == b

    def test_different_seeds_give_different_permutations(self):
        names = list(EXPECTED_YOTO_CHANNELS)
        results = {tuple(permute_channel_labels(names, seed=s)) for s in CHANNEL_PERMUTATION_SEEDS}
        assert len(results) == len(CHANNEL_PERMUTATION_SEEDS)

    def test_seed_registry_is_fixed_and_nonempty(self):
        assert len(CHANNEL_PERMUTATION_SEEDS) >= 3
        assert len(set(CHANNEL_PERMUTATION_SEEDS)) == len(CHANNEL_PERMUTATION_SEEDS)


class TestAlignedFullVariant:
    def test_provenance_fields_populated(self):
        epoch = _synthetic_epoch()
        record = build_aligned_full_variant(
            epoch, SFREQ, list(EXPECTED_YOTO_CHANNELS),
            participant_id="p0", session_id="1", trial_id="p0_ses-1_task_t0000_code37", code_sha="deadbeef",
        )
        assert record.variant_id == "aligned_full"
        assert record.participant_id == "p0"
        assert record.trial_id == "p0_ses-1_task_t0000_code37"
        assert record.code_sha == "deadbeef"
        assert len(record.feature_names) > 0
        assert record.channel_selection == tuple(EXPECTED_YOTO_CHANNELS)

    def test_source_epoch_hash_changes_with_epoch_content(self):
        names = list(EXPECTED_YOTO_CHANNELS)
        r1 = build_aligned_full_variant(_synthetic_epoch(0), SFREQ, names, "p0", "1", "t0", "sha")
        r2 = build_aligned_full_variant(_synthetic_epoch(1), SFREQ, names, "p0", "1", "t0", "sha")
        assert r1.source_epoch_hash != r2.source_epoch_hash

    def test_feature_hash_deterministic_for_identical_epoch(self):
        epoch = _synthetic_epoch()
        r1 = build_aligned_full_variant(epoch, SFREQ, list(EXPECTED_YOTO_CHANNELS), "p0", "1", "t0", "sha")
        r2 = build_aligned_full_variant(epoch, SFREQ, list(EXPECTED_YOTO_CHANNELS), "p0", "1", "t0", "sha")
        assert r1.feature_hash == r2.feature_hash
        assert r1.source_epoch_hash == r2.source_epoch_hash


class TestChannelPermutedVariant:
    def test_permuted_features_differ_from_aligned_full(self):
        epoch = _synthetic_epoch()
        names = list(EXPECTED_YOTO_CHANNELS)
        aligned = build_aligned_full_variant(epoch, SFREQ, names, "p0", "1", "t0", "sha")
        permuted = build_channel_permuted_variant(
            epoch, SFREQ, names, seed=101, participant_id="p0", session_id="1", trial_id="t0", code_sha="sha",
        )
        # Same epoch data, different anatomical-group assignment -> the
        # feature VALUES (band power per group etc.) should differ, since
        # each group now averages over the wrong physical channels.
        assert permuted.feature_hash != aligned.feature_hash
        assert permuted.variant_id == "channel_group_permuted_seed101"

    def test_deterministic_across_repeated_calls(self):
        epoch = _synthetic_epoch()
        names = list(EXPECTED_YOTO_CHANNELS)
        r1 = build_channel_permuted_variant(epoch, SFREQ, names, 101, "p0", "1", "t0", "sha")
        r2 = build_channel_permuted_variant(epoch, SFREQ, names, 101, "p0", "1", "t0", "sha")
        assert r1.feature_hash == r2.feature_hash
        assert r1.channel_selection == r2.channel_selection


class TestFrontalProxyVariant:
    def test_channel_selection_restricted_to_frontal_group(self):
        epoch = _synthetic_epoch()
        names = list(EXPECTED_YOTO_CHANNELS)
        record = build_frontal_proxy_variant(epoch, SFREQ, names, "p0", "1", "t0", "sha")
        assert set(record.channel_selection) <= set(FRONTAL_PROXY_CHANNELS)
        assert len(record.channel_selection) == len(FRONTAL_PROXY_CHANNELS)

    def test_epoch_restricted_to_fewer_channels_than_full(self):
        epoch = _synthetic_epoch()
        names = list(EXPECTED_YOTO_CHANNELS)
        record = build_frontal_proxy_variant(epoch, SFREQ, names, "p0", "1", "t0", "sha")
        assert len(record.channel_selection) < len(EXPECTED_YOTO_CHANNELS)


class TestQualityOnlyFeatures:
    def test_excludes_content_and_anatomical_features(self):
        epoch = _synthetic_epoch()
        features = extract_quality_only_features(
            epoch, SFREQ, rejection_threshold_v=150e-6,
            n_missing_channels=0, neighboring_trial_rejection_rate=0.1,
            recording_retained_fraction=0.9,
        )
        forbidden_substrings = ["erp_", "band_power", "frontal", "posterior", "central", "spectral_entropy"]
        for name in features:
            assert not any(bad in name for bad in forbidden_substrings), name

    def test_all_values_are_finite_floats(self):
        epoch = _synthetic_epoch()
        features = extract_quality_only_features(
            epoch, SFREQ, rejection_threshold_v=150e-6,
            n_missing_channels=2, neighboring_trial_rejection_rate=0.2,
            recording_retained_fraction=0.8,
        )
        for value in features.values():
            assert np.isfinite(value)

    def test_variant_record_uses_quality_only_feature_names(self):
        epoch = _synthetic_epoch()
        names = list(EXPECTED_YOTO_CHANNELS)
        record = build_quality_only_variant(
            epoch, SFREQ, names, rejection_threshold_v=150e-6,
            n_missing_channels=0, neighboring_trial_rejection_rate=0.0,
            recording_retained_fraction=1.0,
            participant_id="p0", session_id="1", trial_id="t0", code_sha="sha",
        )
        assert all(name.startswith("quality__") for name in record.feature_names)
        assert record.variant_id == "signal_quality_only"


class TestNeighboringTrialRejectionRate:
    def test_zero_when_all_neighbors_kept(self):
        rate = neighboring_trial_rejection_rate(10, list(range(5, 16)), set(range(5, 16)))
        assert rate == 0.0

    def test_reflects_fraction_rejected(self):
        all_idx = list(range(5, 16))
        kept = set(all_idx) - {8, 9}
        rate = neighboring_trial_rejection_rate(10, all_idx, kept, window=5)
        assert rate == 2 / 10  # neighbors within +-5 of 10, excluding 10 itself = 10 trials

    def test_no_neighbors_returns_zero(self):
        assert neighboring_trial_rejection_rate(0, [0], {0}, window=5) == 0.0


class TestLateShiftTrials:
    def test_onset_shifted_forward_by_fixed_offset(self):
        class _FakeTrial:
            dataset_id = "ds005815"
            dataset_version = "2.0.1"
            participant_id = "sub-01"
            session_id = "1"
            run_id = "task"
            trial_id = "sub-01_ses-1_task_t0000_code37"
            stimulus_id = "visual_square"
            event_onset = 12.0
            event_duration = 4.0
            channel_names = tuple(EXPECTED_YOTO_CHANNELS)
            sampling_rate = 250.0
            source_file_hash = "abc123"

        trials = build_late_shift_trials([_FakeTrial()])
        assert len(trials) == 1
        assert trials[0].event_onset == 12.0 + LATE_SHIFT_OFFSET_S
        assert trials[0].event_duration == 4.0
        assert trials[0].condition == "late_shift"
        assert trials[0].behavioral_target is None  # never a self-reported target of its own
