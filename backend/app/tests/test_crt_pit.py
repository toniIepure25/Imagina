"""Tests for the Stage 0E posterior PIT calibration check."""
from __future__ import annotations

import random

import pytest

from app.research.crt.pit import PitConfig, posterior_pit, run_pit_calibration

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_posterior_pit_is_bounded() -> None:
    rng = random.Random(7)
    values = [posterior_pit(source, 2, rng) for source in [0, 1, 2, 3]]
    assert all(0.0 <= value <= 1.0 for value in values)


def test_pit_histogram_has_the_expected_mass() -> None:
    report = run_pit_calibration(PitConfig(n_simulations=200, bins=10, seed=7))
    assert sum(report["histogram"]) == 200


def test_pit_gate_passes_for_the_assumed_generative_model() -> None:
    report = run_pit_calibration(PitConfig(n_simulations=1000, bins=10, seed=20261030))
    assert report["decision"] == "CRT_STAGE0E_PIT_PASS"
    assert 0.45 <= report["summary"]["mean_pit"] <= 0.55
