"""Tests for the fold-safe C1 EEG preprocessing pipeline.

Uses tiny synthetic MNE RawArray recordings, never the real ~114MB ds005815
recording (not committed to this repository). Exercises: channel validation
and the missing-channel policy, condition-specific (non-padded) epoch
extraction, baseline correction, fixed-threshold artifact rejection, and the
QC report's retained-fraction / class-balance / block-order-confound
diagnostics.
"""
import numpy as np
import pytest

mne = pytest.importorskip("mne")

from app.research.neural.manifests import NeuralTrialManifest  # noqa: E402
from app.research.neural.preprocessing import (  # noqa: E402
    PreprocessingConfig,
    build_qc_report,
    preprocess_recording,
    validate_channels,
)


def _make_trial(trial_id, condition, onset, stimulus_id="visual_square", target=4.0):
    return NeuralTrialManifest(
        dataset_id="ds005815", dataset_version="2.0.1",
        participant_id="sub-01", session_id="1", run_id="task",
        trial_id=trial_id, condition=condition, stimulus_id=stimulus_id,
        event_onset=onset, event_duration=2.0 if condition == "perception" else 4.0,
        behavioral_target=target, subjective_target=None,
        channel_names=("FP1", "FP2", "CZ"), sampling_rate=250.0,
        source_file_hash="a" * 64,
    )


def _make_raw(seed=0, n_seconds=30, sfreq=250.0, amplitude=1e-5, ch_names=("FP1", "FP2", "CZ")):
    info = mne.create_info(list(ch_names), sfreq, ch_types="eeg")
    n_samples = int(sfreq * n_seconds)
    data = np.random.RandomState(seed).randn(len(ch_names), n_samples) * amplitude
    return mne.io.RawArray(data, info, verbose="ERROR")


class TestChannelValidation:
    def test_all_expected_present(self):
        present, missing = validate_channels(["FP1", "FP2", "CZ"], expected=("FP1", "FP2", "CZ"))
        assert present == ["FP1", "FP2", "CZ"]
        assert missing == []

    def test_missing_channel_reported_not_fabricated(self):
        present, missing = validate_channels(["FP1", "CZ"], expected=("FP1", "FP2", "CZ"))
        assert present == ["FP1", "CZ"]
        assert missing == ["FP2"]

    def test_case_insensitive_match(self):
        present, missing = validate_channels(["fp1", "fp2"], expected=("FP1", "FP2"))
        assert present == ["FP1", "FP2"]
        assert missing == []


class TestPreprocessRecording:
    def test_perception_and_imagery_epochs_have_different_correct_lengths(self):
        raw = _make_raw(n_seconds=30)
        trials = [_make_trial("t0", "perception", onset=5.0), _make_trial("t0", "imagery", onset=7.0)]
        config = PreprocessingConfig(run_ica=False, resample_to_hz=250.0, reject_peak_to_peak_v=1.0)
        epochs, kept, manifest = preprocess_recording(raw, trials, raw_hash="h" * 64, config=config)

        assert "perception" in epochs and "imagery" in epochs
        assert epochs["perception"].shape == (1, 3, 500)  # 2s @ 250Hz
        assert epochs["imagery"].shape == (1, 3, 1000)  # 4s @ 250Hz
        assert len(kept) == 2
        assert manifest.excluded_trials == ()

    def test_missing_channel_excluded_and_recorded_not_interpolated(self):
        raw = _make_raw(n_seconds=10, ch_names=("FP1", "CZ"))
        trials = [_make_trial("t0", "perception", onset=1.0)]
        config = PreprocessingConfig(run_ica=False, reject_peak_to_peak_v=1.0)
        _epochs, _kept, manifest = preprocess_recording(raw, trials, raw_hash="h" * 64, config=config)
        assert "FP2" in manifest.excluded_channels
        assert any("FP2" in k for k in manifest.exclusion_reasons)

    def test_artifact_rejection_excludes_high_amplitude_trial(self):
        raw = _make_raw(n_seconds=10, amplitude=1e-3)  # deliberately huge amplitude
        trials = [_make_trial("t0", "perception", onset=1.0)]
        config = PreprocessingConfig(run_ica=False, reject_peak_to_peak_v=150e-6)
        epochs, kept, manifest = preprocess_recording(raw, trials, raw_hash="h" * 64, config=config)
        assert kept == []
        assert epochs == {}
        assert len(manifest.excluded_trials) == 1
        trial_reason = manifest.exclusion_reasons["trial:t0:perception"]
        assert "artifact_rejection" in trial_reason

    def test_clean_trial_survives_reasonable_threshold(self):
        raw = _make_raw(n_seconds=10, amplitude=1e-6)  # tiny, clean amplitude
        trials = [_make_trial("t0", "perception", onset=1.0)]
        config = PreprocessingConfig(run_ica=False, reject_peak_to_peak_v=150e-6)
        epochs, kept, manifest = preprocess_recording(raw, trials, raw_hash="h" * 64, config=config)
        assert len(kept) == 1
        assert manifest.excluded_trials == ()

    def test_baseline_correction_shifts_epoch_toward_zero_mean(self):
        # Constant-offset signal: baseline correction should remove the DC
        # offset from the perception epoch, not merely leave it in place.
        sfreq = 250.0
        info = mne.create_info(["FP1"], sfreq, ch_types="eeg")
        n_samples = int(sfreq * 10)
        data = np.full((1, n_samples), 5e-6)  # constant 5 microvolt offset
        raw = mne.io.RawArray(data, info, verbose="ERROR")
        trials = [_make_trial("t0", "perception", onset=2.0)]
        config = PreprocessingConfig(
            run_ica=False, reject_peak_to_peak_v=1.0, baseline_window_s=(-0.5, 0.0),
        )
        epochs, kept, _manifest = preprocess_recording(raw, trials, raw_hash="h" * 64, config=config)
        assert len(kept) == 1
        # A perfectly constant signal minus its own baseline mean is ~0.
        assert np.allclose(epochs["perception"], 0.0, atol=1e-9)

    def test_output_hash_is_deterministic_for_identical_input(self):
        raw1 = _make_raw(seed=7, n_seconds=10)
        raw2 = _make_raw(seed=7, n_seconds=10)
        trials = [_make_trial("t0", "perception", onset=1.0)]
        config = PreprocessingConfig(run_ica=False, reject_peak_to_peak_v=1.0)
        _e1, _k1, m1 = preprocess_recording(raw1, trials, raw_hash="h" * 64, config=config)
        _e2, _k2, m2 = preprocess_recording(raw2, trials, raw_hash="h" * 64, config=config)
        assert m1.output_hash == m2.output_hash


class TestQCReport:
    def test_retained_fraction_and_class_balance(self):
        all_trials = [
            _make_trial("t0", "perception", onset=1.0, stimulus_id="visual_square"),
            _make_trial("t1", "perception", onset=5.0, stimulus_id="visual_square"),
            _make_trial("t2", "perception", onset=9.0, stimulus_id="visual_face_male"),
        ]
        kept = all_trials[:2]  # simulate one exclusion
        manifest_stub = type("M", (), {"excluded_channels": ()})()
        report = build_qc_report("ds005815", "sub-01", "1", all_trials, kept, manifest_stub)
        assert report.n_trials_total == 3
        assert report.n_trials_retained == 2
        assert report.retained_fraction == pytest.approx(2 / 3)
        assert report.class_balance["visual_square"] == 2

    def test_block_order_confound_flag_true_when_stimulus_clustered_in_time(self):
        # "visual_square" only ever occurs early (onsets 0-1 of a 0-4 span);
        # "visual_face_male" fills the rest — a genuine block/order confound.
        clustered = [
            _make_trial(f"sq{i}", "perception", onset=float(i), stimulus_id="visual_square")
            for i in range(2)
        ]
        rest = [
            _make_trial(f"fc{i}", "perception", onset=float(i + 2), stimulus_id="visual_face_male")
            for i in range(3)
        ]
        all_trials = clustered + rest
        manifest_stub = type("M", (), {"excluded_channels": ()})()
        report = build_qc_report("ds005815", "sub-01", "1", all_trials, all_trials, manifest_stub)
        assert report.block_order_confound_flag is True

    def test_block_order_confound_flag_false_when_stimulus_spread_across_recording(self):
        square_trials = [
            _make_trial(f"sq{i}", "perception", onset=float(i * 20), stimulus_id="visual_square")
            for i in range(5)
        ]
        face_trials = [
            _make_trial(f"fc{i}", "perception", onset=float(i * 20) + 10, stimulus_id="visual_face_male")
            for i in range(5)
        ]
        all_trials = square_trials + face_trials
        manifest_stub = type("M", (), {"excluded_channels": ()})()
        report = build_qc_report("ds005815", "sub-01", "1", all_trials, all_trials, manifest_stub)
        assert report.block_order_confound_flag is False
