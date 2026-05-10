"""Tests for V2.4 eeg_dsp module — Welch/FFT/heuristic fallback chain."""

import math
import random

from app.services.eeg_dsp import (
    _heuristic_bandpowers,
    _numpy_fft_bandpowers,
    compute_artifact_scores,
    compute_bandpowers,
    compute_signal_quality,
    extract_eeg_features,
)


def _generate_synthetic_eeg(sfreq=256, duration=2, alpha_amp=0.8, noise=0.05, seed=42):
    rng = random.Random(seed)
    n = int(sfreq * duration)
    samples = []
    for i in range(n):
        t = i / sfreq
        alpha = alpha_amp * math.sin(2 * math.pi * 10 * t)
        samples.append([alpha + rng.gauss(0, noise)] * 4)
    return samples


def test_scipy_welch_bandpowers_valid():
    samples = _generate_synthetic_eeg(duration=4)
    bp = compute_bandpowers(samples, 256)
    assert 0 <= bp["alpha"] <= 1
    assert 0 <= bp["theta"] <= 1
    assert 0 <= bp["beta"] <= 1


def test_alpha_dominant_signal_has_higher_alpha():
    samples = _generate_synthetic_eeg(duration=4, alpha_amp=1.0, noise=0.02)
    bp = compute_bandpowers(samples, 256)
    assert bp["alpha"] > bp["beta"] * 0.5


def test_numpy_fft_bandpowers_valid():
    samples = _generate_synthetic_eeg(duration=4)
    bp = _numpy_fft_bandpowers(samples, 256, None)
    assert 0 <= bp["alpha"] <= 1


def test_heuristic_bandpowers_valid():
    samples = _generate_synthetic_eeg(duration=4)
    bp = _heuristic_bandpowers(samples, 256, None)
    assert 0 <= bp["alpha"] <= 1


def test_compute_artifact_scores_valid():
    samples = _generate_synthetic_eeg(duration=2, noise=0.01)
    art = compute_artifact_scores(samples)
    assert 0 <= art["missing_data_ratio"] <= 1
    assert 0 <= art["blink_score"] <= 1
    assert art["clipping_score"] < 0.3


def test_artifact_scores_empty_returns_defaults():
    art = compute_artifact_scores([])
    assert art["missing_data_ratio"] == 1.0


def test_signal_quality_from_alpha():
    art = {"missing_data_ratio": 0.05, "muscle_score": 0.1, "clipping_score": 0.0}
    bp = {"alpha": 0.8}
    sq = compute_signal_quality(art, bp)
    assert sq > 0.6


def test_extract_eeg_features_from_synthetic():
    from datetime import datetime, timezone

    from app.schemas.signals import EEGSampleWindow
    samples = _generate_synthetic_eeg(duration=4, alpha_amp=0.8, noise=0.03)
    t = datetime.now(timezone.utc)
    window = EEGSampleWindow(
        session_id="test", timestamp=t, window_index=0,
        sampling_rate_hz=256, channels=["ch0", "ch1", "ch2", "ch3"],
        samples=samples, simulated=False,
        generator_version="test_v2.4",
        provider_id="test", provider_type="lsl",
        channel_count=4,
    )
    feats = extract_eeg_features(window)
    assert 0 <= feats["alpha_power"] <= 1
    assert 0 <= feats["beta_power"] <= 1
    assert feats["dsp_method"] in ("welch", "fft", "heuristic")
    assert 0 <= feats["blink_score"] <= 1


def test_feature_engine_uses_dsp_for_eeg_window():
    from datetime import datetime, timezone

    from app.schemas.signals import EEGSampleWindow
    from app.services.feature_engine import FeatureEngine
    samples = _generate_synthetic_eeg(duration=2)
    t = datetime.now(timezone.utc)
    window = EEGSampleWindow(
        session_id="test", timestamp=t, window_index=0,
        sampling_rate_hz=256, channels=["ch0", "ch1"],
        samples=samples, simulated=False,
        generator_version="dsp_test",
        provider_id="test", provider_type="lsl",
        channel_count=2,
    )
    engine = FeatureEngine()
    fv = engine.process_eeg_window(window)
    assert 0 <= fv.alpha_power <= 1
    assert 0 <= fv.signal_quality <= 1
    assert fv.feature_version == "v2.4"


def test_clipping_detected_with_large_values():
    import random
    rng = random.Random(42)
    big = []
    for i in range(200):
        if i % 10 == 0:
            big.append([rng.uniform(-50, 50)] * 4)
        else:
            big.append([rng.uniform(-0.5, 0.5)] * 4)
    art = compute_artifact_scores(big)
    assert art["clipping_score"] > 0


def test_bandpowers_all_in_range():
    for i in range(5):
        samples = _generate_synthetic_eeg(duration=2, seed=i * 10)
        bp = compute_bandpowers(samples, 256)
        for k, v in bp.items():
            assert 0 <= v <= 1, f"{k} = {v} out of range"


def test_dsp_fallback_on_bad_data():
    from datetime import datetime, timezone

    from app.schemas.signals import EEGSampleWindow
    t = datetime.now(timezone.utc)
    window = EEGSampleWindow(
        session_id="test", timestamp=t, window_index=0,
        samples=None, simulated=False, generator_version="bad",
        provider_id="test", provider_type="lsl",
    )
    feats = extract_eeg_features(window)
    assert feats["dsp_method"] == "dsp_fallback_no_samples"
    assert feats["alpha_power"] == 0.45


def test_all_artifact_scores_in_range():
    for i in range(3):
        samples = _generate_synthetic_eeg(duration=2, noise=0.02, seed=i * 7 + 1)
        art = compute_artifact_scores(samples)
        for k in ("blink_score", "muscle_score", "drift_score", "clipping_score", "missing_data_ratio"):
            assert 0 <= art[k] <= 1, f"{k} = {art[k]}"


def test_dsp_integration_through_feature_engine():
    from app.datasets.fixture import generate_synthetic_eeg
    from app.services.feature_engine import FeatureEngine
    windows = generate_synthetic_eeg(duration_seconds=4.0)
    engine = FeatureEngine()
    fv = engine.process_eeg_window(windows[0])
    assert 0 <= fv.alpha_power <= 1
    assert fv.feature_version == "v2.4"

def test_dataset_eval_dsp_and_compare(tmp_path):
    from app.cli.dataset_eval import main as eval_main
    out = str(tmp_path / "dsp.json")
    eval_main([
        "--dataset", "fixture", "--max-windows", "5",
        "--compute-pid-iqi", "--compare", "fixture",
        "--distribution-report", "--output", out,
    ])
    import json
    with open(out) as f:
        r = json.load(f)
    assert "pid_iqi" in r
    assert 0 <= r["pid_iqi"]["pid_mean"] <= 1
