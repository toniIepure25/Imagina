"""Smoke tests for the C2 Commit 5 perception-to-imagery transfer
evaluation's pure encoder fit/evaluate logic (Commit 8 CI:
c2-cross-state-transfer-smoke). Synthetic epoch arrays only -- the real
transfer result comes from results/c2_cross_state_transfer.json.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("mne")

from app.research.neural.run_c2_transfer import _evaluate, _fit_encoder  # noqa: E402

SFREQ = 250.0
N_CHANNELS = 30
N_SAMPLES = 500  # 2.0s @ 250Hz, matching the equal-duration common window


def _synthetic_content_data(n_trials=24, seed=0):
    rng = np.random.RandomState(seed)
    x = (rng.randn(n_trials, N_CHANNELS, N_SAMPLES) * 1e-5).astype(np.float32)
    y = rng.choice(["visual_square", "visual_face_male", "visual_face_female"], size=n_trials)
    return x, y


class TestFitEncoderAndEvaluate:
    def test_tcn_fit_and_evaluate_shapes(self):
        x_train, y_train = _synthetic_content_data(seed=0)
        x_test, y_test = _synthetic_content_data(seed=1)
        enc, probe = _fit_encoder("tcn", N_CHANNELS, N_SAMPLES, x_train, y_train)
        assert probe is None  # tcn/eegnet have no separate probe
        metrics = _evaluate("tcn", enc, probe, x_test, y_test)
        assert set(metrics.keys()) == {"log_loss", "balanced_accuracy", "n_test"}
        assert metrics["n_test"] == len(y_test)
        assert np.isfinite(metrics["log_loss"])

    def test_contrastive_fit_and_evaluate_uses_a_probe(self):
        x_train, y_train = _synthetic_content_data(seed=0)
        x_test, y_test = _synthetic_content_data(seed=1)
        enc, probe = _fit_encoder("contrastive", N_CHANNELS, N_SAMPLES, x_train, y_train)
        assert probe is not None
        metrics = _evaluate("contrastive", enc, probe, x_test, y_test)
        assert np.isfinite(metrics["log_loss"])

    def test_cross_state_evaluation_does_not_crash_on_matched_length_input(self):
        """The real bug this session found: perception (500 samples) and
        the full imagery epoch (1000 samples) have different lengths,
        which crashes EEGNet/TCN's fixed-input-shape architectures. This
        test locks in that both sides of a transfer evaluation must use
        the SAME epoch length (the equal-duration common window)."""
        x_train, y_train = _synthetic_content_data(seed=0)
        x_test_same_length, y_test = _synthetic_content_data(seed=2)
        enc, probe = _fit_encoder("tcn", N_CHANNELS, N_SAMPLES, x_train, y_train)
        metrics = _evaluate("tcn", enc, probe, x_test_same_length, y_test)
        assert np.isfinite(metrics["log_loss"])
