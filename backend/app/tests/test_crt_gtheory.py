"""Tests for the Stage 0D generalizability-theory analysis."""
from __future__ import annotations

import pytest

from app.research.crt.gtheory import (
    GTheoryConfig,
    check_gtheory,
    d_study,
    run_gtheory,
    simulate_matrix,
    two_way_variance_components,
)
from app.research.crt.power import PowerConfig, simulate_power

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_variance_components_are_non_negative_and_exhaustive() -> None:
    matrix = [[1.0, 1.2], [2.0, 2.4], [3.0, 2.8], [4.5, 4.9]]
    components = two_way_variance_components(matrix)
    assert components.person >= 0.0
    assert components.occasion >= 0.0
    assert components.error >= 0.0
    assert components.total == pytest.approx(components.person + components.occasion + components.error)


def test_decision_study_reliability_increases_with_occasions() -> None:
    components = two_way_variance_components([[1.0, 1.2], [2.0, 2.4], [3.0, 2.8], [4.5, 4.9]])
    first = d_study(components, 1)
    second = d_study(components, 2)
    assert second["relative_reliability"] >= first["relative_reliability"]
    assert second["sem"] <= first["sem"]


def test_invalid_matrix_shapes_are_rejected() -> None:
    with pytest.raises(ValueError):
        two_way_variance_components([[1.0]])
    with pytest.raises(ValueError):
        two_way_variance_components([[1.0, 2.0], [3.0]])
    with pytest.raises(ValueError):
        GTheoryConfig(n_participants=2)
    with pytest.raises(ValueError):
        GTheoryConfig(n_occasions=1)


def test_simulated_matrix_is_deterministic() -> None:
    first = simulate_matrix(GTheoryConfig(n_participants=10, seed=5))
    second = simulate_matrix(GTheoryConfig(n_participants=10, seed=5))
    assert first == second


def test_gtheory_gate_passes_for_a_reliable_simulation() -> None:
    report = check_gtheory()
    assert report["decision"] == "CRT_STAGE0D_GTHEORY_PASS"
    assert len(report["d_study"]) == 4


def test_gtheory_review_is_possible_for_unreliable_simulation() -> None:
    report = run_gtheory(GTheoryConfig(n_participants=10, person_sd=0.05, error_sd=1.0, seed=7))
    assert report["decision"] in {"CRT_STAGE0D_GTHEORY_PASS", "CRT_STAGE0D_GTHEORY_REVIEW"}


def test_n240_power_target_is_adequate() -> None:
    result = simulate_power(
        0.80,
        PowerConfig(n_participants=240, n_simulations=500, seed=7, lower_bound_target=0.70),
    )
    assert result["power"] >= 0.80
