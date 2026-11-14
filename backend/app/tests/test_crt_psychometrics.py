"""Tests for Stage 0E test-facet reliability."""
from __future__ import annotations

import pytest

from app.research.crt.psychometrics import (
    PsychometricConfig,
    compute_test_facet_reliability,
    run_psychometrics,
    simulate_facet_matrices,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_facet_matrices_have_the_expected_shape() -> None:
    config = PsychometricConfig(n_participants=10, n_tests=3, n_occasions=2, seed=7)
    matrices = simulate_facet_matrices(config)
    assert len(matrices) == 3
    assert all(len(matrix) == 10 for matrix in matrices)
    assert all(len(row) == 2 for matrix in matrices for row in matrix)


def test_facet_reliabilities_are_bounded() -> None:
    matrices = simulate_facet_matrices(PsychometricConfig(n_participants=20, n_tests=4, seed=7))
    reliabilities = compute_test_facet_reliability(matrices)
    assert all(0.0 <= value <= 1.0 for value in reliabilities)


def test_psychometric_gate_passes_for_the_simulated_menu() -> None:
    report = run_psychometrics(PsychometricConfig(n_participants=40, n_tests=6, seed=7))
    assert report["decision"] == "CRT_STAGE0E_PSYCHOMETRIC_PASS"
    assert report["summary"]["minimum"] >= 0.70
