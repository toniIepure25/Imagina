"""Tests for the Stage 0D test-likelihood calibration design."""
from __future__ import annotations

import pytest

from app.research.crt.calibration import (
    CalibrationConfig,
    check_calibration,
    fit_likelihoods,
    likelihood_ratio,
    run_calibration,
    simulate_calibration_counts,
)
from app.research.crt.model import FLUENCY, TEST_IDS, VIEWPOINT

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_calibration_counts_have_one_cell_per_test_and_source() -> None:
    counts = simulate_calibration_counts(CalibrationConfig(n_participants=4, trials_per_cell=5, seed=7))
    assert len(counts) == len(TEST_IDS)
    assert all(len(row) == 4 for row in counts)
    assert all(successes + failures == 20 for row in counts for successes, failures in row)


def test_fitted_likelihoods_are_probabilities() -> None:
    counts = simulate_calibration_counts(CalibrationConfig(n_participants=4, trials_per_cell=5, seed=7))
    fitted = fit_likelihoods(counts)
    assert all(0.0 < value < 1.0 for row in fitted for value in row)


def test_viewpoint_is_more_diagnostic_than_fluency() -> None:
    counts = simulate_calibration_counts(
        CalibrationConfig(n_participants=20, trials_per_cell=20, seed=7, noise_sd=0.01)
    )
    fitted = fit_likelihoods(counts)
    assert likelihood_ratio(fitted, VIEWPOINT) > 1.5
    assert likelihood_ratio(fitted, FLUENCY) == pytest.approx(1.0, abs=0.1)


def test_invalid_calibration_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        CalibrationConfig(n_participants=0)
    with pytest.raises(ValueError):
        CalibrationConfig(trials_per_cell=0)
    with pytest.raises(ValueError):
        CalibrationConfig(prior_alpha=0.0)
    with pytest.raises(ValueError):
        likelihood_ratio([[0.5] * 4], 99)


def test_calibration_gate_retains_four_strong_tests() -> None:
    report = check_calibration()
    assert report["decision"] == "CRT_STAGE0D_CALIBRATION_PASS"
    assert len(report["strong_tests"]) >= 4
    assert report["fluency_lr"] == pytest.approx(1.0, abs=0.2)


def test_calibration_report_is_deterministic() -> None:
    config = CalibrationConfig(n_participants=10, trials_per_cell=10, seed=13)
    assert run_calibration(config) == run_calibration(config)
