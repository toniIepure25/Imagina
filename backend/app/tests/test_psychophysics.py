"""Tests for the objective imagery precision battery."""
import pytest

from app.research.psychophysics.common import (
    ResponseSpec,
    StimulusSpec,
    TaskFamily,
    schedule_hash,
)
from app.research.psychophysics.delayed_imagery import generate_delayed_trials
from app.research.psychophysics.feature_reconstruction import generate_reconstruction_trials
from app.research.psychophysics.imagery_manipulation import (
    apply_transform,
    generate_manipulation_trials,
)
from app.research.psychophysics.perceptual_control import generate_perceptual_control_trials
from app.research.psychophysics.scoring import score_reconstruction


class TestTrialGeneration:
    def test_reconstruction_deterministic(self):
        t1 = generate_reconstruction_trials(10, seed=42)
        t2 = generate_reconstruction_trials(10, seed=42)
        assert schedule_hash(t1) == schedule_hash(t2)

    def test_reconstruction_different_seeds(self):
        t1 = generate_reconstruction_trials(10, seed=42)
        t2 = generate_reconstruction_trials(10, seed=99)
        assert schedule_hash(t1) != schedule_hash(t2)

    def test_reconstruction_count(self):
        trials = generate_reconstruction_trials(20, seed=1)
        assert len(trials) == 20
        assert all(t.task_family == TaskFamily.FEATURE_RECONSTRUCTION for t in trials)

    def test_manipulation_trials_have_transforms(self):
        trials = generate_manipulation_trials(10, seed=42)
        assert all(t.transform is not None for t in trials)
        assert all(t.task_family == TaskFamily.IMAGERY_MANIPULATION for t in trials)

    def test_manipulation_expected_differs_from_target(self):
        trials = generate_manipulation_trials(20, seed=42)
        for t in trials:
            target = t.target
            expected = t.expected_response
            same = (
                target.orientation_deg == expected.orientation_deg
                and target.hue_deg == expected.hue_deg
                and target.spatial_frequency_cpd == expected.spatial_frequency_cpd
                and target.position_x == expected.position_x
                and target.size == expected.size
            )
            assert not same, f"Trial {t.trial_id}: transform should change the target"

    def test_delayed_trials_multiple_delays(self):
        trials = generate_delayed_trials(5, seed=42, delays_s=[0.0, 2.0, 5.0])
        assert len(trials) == 15
        delays = {t.delay_s for t in trials}
        assert delays == {0.0, 2.0, 5.0}
        assert all(t.task_family == TaskFamily.DELAYED_IMAGERY for t in trials)

    def test_perceptual_control_no_mask(self):
        trials = generate_perceptual_control_trials(10, seed=42)
        assert all(t.mask_strength == 0.0 for t in trials)
        assert all(t.task_family == TaskFamily.PERCEPTUAL_CONTROL for t in trials)

    def test_all_trials_hashable(self):
        r = generate_reconstruction_trials(5, seed=1)
        m = generate_manipulation_trials(5, seed=1)
        d = generate_delayed_trials(3, seed=1)
        p = generate_perceptual_control_trials(5, seed=1)
        combined = r + m + d + p
        h = schedule_hash(combined)
        assert isinstance(h, str) and len(h) == 64

    def test_feature_balance(self):
        trials = generate_reconstruction_trials(60, seed=42)
        orientations = [t.target.orientation_deg for t in trials]
        assert min(orientations) < 30
        assert max(orientations) > 150


class TestTransforms:
    def test_rotate(self):
        from app.research.psychophysics.imagery_manipulation import TransformSpec
        s = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        result = apply_transform(s, TransformSpec("rotate", 30.0))
        assert result.orientation_deg == pytest.approx(75.0)

    def test_rotate_wraparound(self):
        from app.research.psychophysics.imagery_manipulation import TransformSpec
        s = StimulusSpec(170, 0, 3.0, 500, 400, 50)
        result = apply_transform(s, TransformSpec("rotate", 20.0))
        assert result.orientation_deg == pytest.approx(10.0)

    def test_change_hue_wraparound(self):
        from app.research.psychophysics.imagery_manipulation import TransformSpec
        s = StimulusSpec(45, 350, 3.0, 500, 400, 50)
        result = apply_transform(s, TransformSpec("change_hue", 30.0))
        assert result.hue_deg == pytest.approx(20.0)

    def test_resize(self):
        import math

        from app.research.psychophysics.imagery_manipulation import TransformSpec
        s = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        result = apply_transform(s, TransformSpec("resize", math.log(2)))
        assert result.size == pytest.approx(100.0, abs=0.1)


class TestScoring:
    def test_exact_match(self):
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=3.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["composite_error"] == 0.0
        assert result["invalidity"] == "none"

    def test_orientation_wraparound(self):
        target = StimulusSpec(5, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=175, hue_deg=120,
            spatial_frequency_cpd=3.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["orientation_error"] == pytest.approx(10.0 / 90.0, abs=1e-6)

    def test_hue_wraparound(self):
        target = StimulusSpec(45, 10, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=350,
            spatial_frequency_cpd=3.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["hue_error"] == pytest.approx(20.0 / 180.0, abs=1e-6)

    def test_position_boundaries(self):
        target = StimulusSpec(45, 120, 3.0, 100, 100, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=3.0,
            position_x=900, position_y=100, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response, display_diagonal=1000)
        assert 0 < result["position_error"] <= 1.0

    def test_log_scale_frequency(self):
        import math
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=6.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["spatial_frequency_error"] == pytest.approx(math.log(2), abs=1e-6)

    def test_missing_response(self):
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec()
        result = score_reconstruction(target, response)
        assert result["composite_error"] == 1.0
        assert result["invalidity"] == "missing_response"

    def test_invalid_response_zero_frequency(self):
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=0.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["invalidity"] == "response_out_of_range"

    def test_too_fast_response(self):
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=3.0,
            position_x=500, position_y=400, size=50,
            latency_ms=50,
        )
        result = score_reconstruction(target, response)
        assert result["invalidity"] == "response_too_fast"

    def test_scoring_version_present(self):
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        response = ResponseSpec(
            orientation_deg=45, hue_deg=120,
            spatial_frequency_cpd=3.0,
            position_x=500, position_y=400, size=50,
            latency_ms=2000,
        )
        result = score_reconstruction(target, response)
        assert result["scoring_version"] == "1.0"
