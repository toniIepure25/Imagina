"""Tests for prespecified classical EEG features and reliability analysis."""
import numpy as np
import pytest

from app.research.neural.features import (
    ClassicalFeatureVector,
    build_precue_trials,
    extract_classical_features,
    precue_postcue_discrimination,
    session_reliability,
    signal_quality_target_correlation,
    split_half_reliability,
)
from app.research.neural.manifests import NeuralTrialManifest
from app.research.neural.preprocessing import FRONTAL_PROXY_CHANNELS, POSTERIOR_CHANNELS

CHANNELS = list(dict.fromkeys(FRONTAL_PROXY_CHANNELS + POSTERIOR_CHANNELS))
SFREQ = 250.0


def _sine_epoch(freq_hz, n_channels=len(CHANNELS), n_seconds=2.0, amplitude=1e-5, seed=0):
    n_samples = int(SFREQ * n_seconds)
    t = np.arange(n_samples) / SFREQ
    rng = np.random.RandomState(seed)
    base = amplitude * np.sin(2 * np.pi * freq_hz * t)
    noise = rng.randn(n_channels, n_samples) * amplitude * 0.05
    return np.tile(base, (n_channels, 1)) + noise


def _extract(epoch, channels=CHANNELS, trial_id="t0", condition="perception", stimulus_id="visual_square"):
    return extract_classical_features(
        epoch, SFREQ, channels, trial_id=trial_id, condition=condition, stimulus_id=stimulus_id,
    )


class TestExtractClassicalFeatures:
    def test_alpha_dominant_signal_has_higher_alpha_than_beta_power(self):
        epoch = _sine_epoch(freq_hz=10.0)  # squarely in the alpha band (8-13Hz)
        fv = _extract(epoch)
        assert fv.features["band_power__posterior__alpha"] > fv.features["band_power__posterior__beta"]

    def test_beta_dominant_signal_has_higher_beta_than_alpha_power(self):
        epoch = _sine_epoch(freq_hz=20.0)  # squarely in the beta band (13-30Hz)
        fv = _extract(epoch)
        assert fv.features["band_power__posterior__beta"] > fv.features["band_power__posterior__alpha"]

    def test_feature_vector_carries_trial_identity(self):
        epoch = _sine_epoch(freq_hz=10.0)
        fv = _extract(epoch, trial_id="t7", condition="imagery", stimulus_id="auditory_speech_a")
        assert fv.trial_id == "t7"
        assert fv.condition == "imagery"
        assert fv.stimulus_id == "auditory_speech_a"

    def test_missing_channel_group_is_skipped_not_fabricated(self):
        epoch = _sine_epoch(freq_hz=10.0, n_channels=1)
        fv = _extract(epoch, channels=["FP1"])
        # only the frontal group can be resolved from a single FP1 channel
        assert any(k.startswith("band_power__frontal__") for k in fv.features)
        assert not any(k.startswith("band_power__posterior__") for k in fv.features)

    def test_to_dict_is_json_serializable(self):
        import json
        epoch = _sine_epoch(freq_hz=10.0)
        fv = _extract(epoch)
        json.dumps(fv.to_dict())


def _make_vectors(n, feature_name, values, condition="perception", stimulus_id="visual_square"):
    return [
        ClassicalFeatureVector(
            trial_id=f"t{i}", condition=condition, stimulus_id=stimulus_id, features={feature_name: v},
        )
        for i, v in enumerate(values)
    ]


class TestSplitHalfReliability:
    def test_returns_none_with_too_few_trials(self):
        vecs = _make_vectors(3, "f", [1.0, 2.0, 3.0])
        assert split_half_reliability(vecs, "f") is None

    def test_returns_a_correlation_with_enough_trials(self):
        rng = np.random.RandomState(0)
        vecs = _make_vectors(20, "f", rng.randn(20).tolist())
        r = split_half_reliability(vecs, "f")
        assert r is not None
        assert -1.0 <= r <= 1.0


class TestSessionReliability:
    def test_returns_none_with_too_few_shared_groups(self):
        a = _make_vectors(2, "f", [1.0, 2.0], stimulus_id="visual_square")
        b = _make_vectors(2, "f", [1.5, 2.5], stimulus_id="visual_square")
        assert session_reliability(a, b, "f", min_shared_groups=6) is None

    def test_two_category_grouping_would_be_trivial_but_stimulus_grouping_is_not(self):
        # Same two participants' worth of (condition, stimulus) groups,
        # values deliberately NOT perfectly correlated across sessions.
        stimuli = [f"stim_{i}" for i in range(10)]
        rng = np.random.RandomState(1)
        session_a_vals = rng.randn(10)
        session_b_vals = session_a_vals * 0.3 + rng.randn(10) * 0.9  # weak, noisy relationship
        a = [
            ClassicalFeatureVector(trial_id=f"a{i}", condition="perception", stimulus_id=s, features={"f": v})
            for i, (s, v) in enumerate(zip(stimuli, session_a_vals))
        ]
        b = [
            ClassicalFeatureVector(trial_id=f"b{i}", condition="perception", stimulus_id=s, features={"f": v})
            for i, (s, v) in enumerate(zip(stimuli, session_b_vals))
        ]
        r = session_reliability(a, b, "f", min_shared_groups=6)
        assert r is not None
        assert abs(r) < 0.999, "a real (non-trivial) correlation must not be a spurious +-1"

    def test_perfect_agreement_gives_correlation_near_one(self):
        stimuli = [f"stim_{i}" for i in range(8)]
        rng = np.random.RandomState(2)
        vals = rng.randn(8)
        a = [
            ClassicalFeatureVector(trial_id=f"a{i}", condition="perception", stimulus_id=s, features={"f": v})
            for i, (s, v) in enumerate(zip(stimuli, vals))
        ]
        b = [
            ClassicalFeatureVector(trial_id=f"b{i}", condition="perception", stimulus_id=s, features={"f": v})
            for i, (s, v) in enumerate(zip(stimuli, vals))
        ]
        r = session_reliability(a, b, "f", min_shared_groups=6)
        assert r == pytest.approx(1.0, abs=1e-9)


class TestPrecuePostcueDiscrimination:
    def test_zero_when_distributions_identical(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        pre = _make_vectors(4, "f", vals)
        post = _make_vectors(4, "f", vals)
        assert precue_postcue_discrimination(pre, post, "f") == pytest.approx(0.0, abs=1e-9)

    def test_nonzero_when_distributions_differ(self):
        pre = _make_vectors(6, "f", [1.0, 1.1, 0.9, 1.05, 0.95, 1.0])
        post = _make_vectors(6, "f", [5.0, 5.1, 4.9, 5.05, 4.95, 5.0])
        assert precue_postcue_discrimination(pre, post, "f") > 1.0

    def test_returns_zero_with_insufficient_data(self):
        pre = _make_vectors(1, "f", [1.0])
        post = _make_vectors(1, "f", [5.0])
        assert precue_postcue_discrimination(pre, post, "f") == 0.0


class TestBuildPrecueTrials:
    def test_precue_trial_shares_trial_id_and_uses_precue_condition(self):
        perception_trial = NeuralTrialManifest(
            dataset_id="ds005815", dataset_version="2.0.1", participant_id="sub-01",
            session_id="1", run_id="task", trial_id="t0", condition="perception",
            stimulus_id="visual_square", event_onset=10.0, event_duration=2.0,
            behavioral_target=4.0, subjective_target=None,
            channel_names=("FP1",), sampling_rate=250.0, source_file_hash="a" * 64,
        )
        precue = build_precue_trials([perception_trial])
        assert len(precue) == 1
        assert precue[0].trial_id == "t0"
        assert precue[0].condition == "precue"
        assert precue[0].event_onset == pytest.approx(8.0)
        assert precue[0].event_duration == pytest.approx(2.0)
        assert precue[0].behavioral_target is None  # never carries the post-cue self-report

    def test_trial_too_early_in_recording_is_skipped(self):
        perception_trial = NeuralTrialManifest(
            dataset_id="ds005815", dataset_version="2.0.1", participant_id="sub-01",
            session_id="1", run_id="task", trial_id="t0", condition="perception",
            stimulus_id="visual_square", event_onset=1.0, event_duration=2.0,
            behavioral_target=4.0, subjective_target=None,
            channel_names=("FP1",), sampling_rate=250.0, source_file_hash="a" * 64,
        )
        assert build_precue_trials([perception_trial]) == []


class TestSignalQualityTargetCorrelation:
    def test_returns_none_with_too_few_paired_observations(self):
        vecs = _make_vectors(3, "quality", [1.0, 2.0, 3.0])
        assert signal_quality_target_correlation(vecs, "quality", [1.0, 2.0, 3.0]) is None

    def test_detects_a_real_correlation(self):
        rng = np.random.RandomState(3)
        quality = rng.randn(10)
        targets = quality * 2.0
        vecs = _make_vectors(10, "quality", quality.tolist())
        r = signal_quality_target_correlation(vecs, "quality", targets.tolist())
        assert r == pytest.approx(1.0, abs=1e-6)

    def test_none_targets_are_excluded_not_treated_as_zero(self):
        vecs = _make_vectors(8, "quality", [1, 2, 3, 4, 5, 6, 7, 8])
        targets = [1.0, None, 3.0, None, 5.0, 6.0, 7.0, 8.0]
        r = signal_quality_target_correlation(vecs, "quality", targets)
        assert r is not None
