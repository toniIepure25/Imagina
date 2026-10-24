"""Tests for the objective endpoint registry."""
import math

import pytest

from app.research.objective_endpoints import (
    EndpointRole,
    ScoreDirection,
    circular_distance,
    composite_reconstruction_error,
    confidence_resolution_slope,
    get_endpoints_by_role,
    get_objective_endpoints,
    get_primary_endpoint,
    get_subjective_endpoints,
    hue_error,
    list_endpoints,
    orientation_error,
    position_error,
    registry_hash,
    size_error,
    spatial_frequency_error,
    stability_degradation,
    validate_registry,
)


class TestRegistryIntegrity:
    def test_registry_valid(self):
        errors = validate_registry()
        assert errors == [], f"Registry violations: {errors}"

    def test_exactly_one_primary(self):
        primary = get_endpoints_by_role(EndpointRole.PRIMARY)
        assert len(primary) == 1

    def test_primary_is_objective(self):
        primary = get_primary_endpoint()
        assert primary.is_objective is True

    def test_primary_is_lower_is_better(self):
        primary = get_primary_endpoint()
        assert primary.score_direction == ScoreDirection.LOWER_IS_BETTER

    def test_primary_has_frozen_weights(self):
        primary = get_primary_endpoint()
        assert len(primary.feature_weights) == 5
        assert abs(sum(primary.feature_weights.values()) - 1.0) < 1e-9

    def test_subjective_not_marked_objective(self):
        for ep in list_endpoints():
            if ep.endpoint_id in ("subjective_vividness", "subjective_effort", "fatigue_rating"):
                assert ep.is_objective is False, f"{ep.endpoint_id} incorrectly marked objective"

    def test_negative_controls_are_objective(self):
        for ep in get_endpoints_by_role(EndpointRole.NEGATIVE_CONTROL):
            assert ep.is_objective is True, f"Negative control {ep.endpoint_id} must be objective"

    def test_all_endpoints_have_score_direction(self):
        for ep in list_endpoints():
            assert ep.score_direction is not None, f"{ep.endpoint_id} missing score direction"

    def test_all_endpoints_have_valid_range(self):
        for ep in list_endpoints():
            lo, hi = ep.valid_range
            assert lo < hi, f"{ep.endpoint_id} invalid range ({lo}, {hi})"

    def test_registry_hash_deterministic(self):
        h1 = registry_hash()
        h2 = registry_hash()
        assert h1 == h2

    def test_endpoint_count(self):
        all_eps = list_endpoints()
        obj = get_objective_endpoints()
        subj = get_subjective_endpoints()
        assert len(all_eps) == len(obj) + len(subj)
        assert len(obj) >= 10
        assert len(subj) >= 2

    def test_primary_mutation_detection(self):
        h_before = registry_hash()
        primary = get_primary_endpoint()
        assert primary.version == "1.0"
        h_after = registry_hash()
        assert h_before == h_after


class TestScoringFunctions:
    def test_circular_distance_exact(self):
        assert circular_distance(0, 0, 180) == 0.0

    def test_circular_distance_halfway(self):
        assert circular_distance(0, 90, 180) == 90.0

    def test_circular_distance_wraparound(self):
        assert abs(circular_distance(170, 10, 180) - 20.0) < 1e-9

    def test_orientation_error_exact(self):
        assert orientation_error(45, 45) == 0.0

    def test_orientation_error_max(self):
        assert orientation_error(0, 90) == 1.0

    def test_orientation_error_wraparound(self):
        err = orientation_error(5, 175)
        assert err == pytest.approx(10.0 / 90.0, abs=1e-9)

    def test_hue_error_exact(self):
        assert hue_error(120, 120) == 0.0

    def test_hue_error_max(self):
        assert hue_error(0, 180) == 1.0

    def test_hue_error_wraparound(self):
        err = hue_error(350, 10)
        assert err == pytest.approx(20.0 / 180.0, abs=1e-9)

    def test_position_error_exact(self):
        assert position_error(100, 100, 100, 100, 500) == 0.0

    def test_position_error_clamped(self):
        err = position_error(0, 0, 1000, 1000, 10)
        assert err == 1.0

    def test_spatial_frequency_error_exact(self):
        assert spatial_frequency_error(3.0, 3.0) == 0.0

    def test_spatial_frequency_error_double(self):
        err = spatial_frequency_error(6.0, 3.0)
        assert err == pytest.approx(math.log(2), abs=1e-9)

    def test_spatial_frequency_error_zero_response(self):
        assert spatial_frequency_error(0.0, 3.0) == 1.0

    def test_size_error_exact(self):
        assert size_error(10, 10) == 0.0

    def test_size_error_double(self):
        err = size_error(20, 10)
        assert err == pytest.approx(math.log(2), abs=1e-9)

    def test_composite_exact_match(self):
        errors = {
            "orientation": 0.0,
            "hue": 0.0,
            "spatial_frequency": 0.0,
            "position": 0.0,
            "size": 0.0,
        }
        assert composite_reconstruction_error(errors) == 0.0

    def test_composite_maximum(self):
        errors = {
            "orientation": 1.0,
            "hue": 1.0,
            "spatial_frequency": 1.0,
            "position": 1.0,
            "size": 1.0,
        }
        assert composite_reconstruction_error(errors) == pytest.approx(1.0, abs=1e-9)

    def test_stability_degradation_positive(self):
        assert stability_degradation(0.2, 0.5) == 0.3

    def test_stability_degradation_no_change(self):
        assert stability_degradation(0.5, 0.5) == 0.0

    def test_stability_degradation_improvement(self):
        assert stability_degradation(0.5, 0.3) == 0.0

    def test_confidence_resolution_perfect(self):
        confs = [1, 2, 3, 4, 5]
        accs = [0.2, 0.4, 0.6, 0.8, 1.0]
        slope = confidence_resolution_slope(confs, accs)
        assert slope == pytest.approx(0.2, abs=1e-9)

    def test_confidence_resolution_flat(self):
        confs = [1, 2, 3, 4, 5]
        accs = [0.5, 0.5, 0.5, 0.5, 0.5]
        slope = confidence_resolution_slope(confs, accs)
        assert slope == pytest.approx(0.0, abs=1e-9)

    def test_confidence_resolution_too_few(self):
        slope = confidence_resolution_slope([1, 2], [0.3, 0.7])
        assert slope == 0.0


class TestAggregationCompatibility:
    def test_trial_level_endpoints_exist(self):
        from app.research.objective_endpoints import AggregationRule
        trial_eps = [ep for ep in list_endpoints() if ep.aggregation == AggregationRule.TRIAL_LEVEL]
        assert len(trial_eps) >= 8

    def test_participant_mean_endpoints_exist(self):
        from app.research.objective_endpoints import AggregationRule
        part_eps = [ep for ep in list_endpoints() if ep.aggregation == AggregationRule.PARTICIPANT_MEAN]
        assert len(part_eps) >= 2
