"""Tests for calibration and staircase procedures."""
import random

from app.research.psychophysics.calibration import (
    estimate_threshold,
    run_calibration,
    transformed_up_down_staircase,
)


class TestStaircase:
    def test_convergence_with_good_responder(self):
        def respond(level, idx, rng):
            return rng.random() < (0.85 - level * 0.5)

        result = run_calibration("P001", "reconstruction", respond, seed=42)
        assert result.converged
        assert 0.0 < result.threshold_estimate < 1.0
        assert result.n_reversals >= 4

    def test_non_convergence_with_random_responder(self):
        rng = random.Random(42)
        responses = [rng.random() < 0.5 for _ in range(20)]
        state, transitions = transformed_up_down_staircase(
            responses, max_reversals=20,
        )
        estimate = estimate_threshold(state)
        assert estimate.n_trials == 20

    def test_perfect_responder_converges_to_low(self):
        responses = [True] * 60
        state, _ = transformed_up_down_staircase(responses, start_level=0.5)
        estimate = estimate_threshold(state)
        assert estimate.threshold < 0.3

    def test_always_wrong_goes_high(self):
        responses = [False] * 30
        state, _ = transformed_up_down_staircase(responses, start_level=0.5)
        assert state.current_level > 0.7

    def test_extreme_high_performer(self):
        def respond(level, idx, rng):
            return True
        result = run_calibration("extreme", "reconstruction", respond, seed=1, n_trials=40)
        assert result.threshold_estimate < 0.2

    def test_extreme_low_performer(self):
        def respond(level, idx, rng):
            return False
        result = run_calibration("low", "reconstruction", respond, seed=1, n_trials=40)
        assert result.threshold_estimate > 0.7

    def test_missing_trials_handled(self):
        state, transitions = transformed_up_down_staircase([], start_level=0.5)
        estimate = estimate_threshold(state)
        assert estimate.converged is False
        assert estimate.threshold == 0.5


class TestCalibrationIntegrity:
    def test_deterministic_hash(self):
        def respond(level, idx, rng):
            return rng.random() < 0.7
        r1 = run_calibration("P001", "reconstruction", respond, seed=42)
        r2 = run_calibration("P001", "reconstruction", respond, seed=42)
        assert r1.calibration_hash == r2.calibration_hash

    def test_different_seed_different_hash(self):
        def respond(level, idx, rng):
            return rng.random() < 0.7
        r1 = run_calibration("P001", "reconstruction", respond, seed=42)
        r2 = run_calibration("P001", "reconstruction", respond, seed=99)
        assert r1.calibration_hash != r2.calibration_hash

    def test_frozen_difficulty_present(self):
        def respond(level, idx, rng):
            return rng.random() < 0.7
        result = run_calibration("P001", "reconstruction", respond, seed=42)
        assert "mask_strength" in result.frozen_difficulty
        assert "retention_delay_s" in result.frozen_difficulty
        assert "distractor_similarity" in result.frozen_difficulty
        assert "transform_magnitude" in result.frozen_difficulty

    def test_calibration_version(self):
        def respond(level, idx, rng):
            return rng.random() < 0.7
        result = run_calibration("P001", "reconstruction", respond, seed=42)
        assert result.protocol_version == "1.0"

    def test_convergence_diagnostics(self):
        def respond(level, idx, rng):
            return rng.random() < 0.75
        result = run_calibration("P001", "reconstruction", respond, seed=42, n_trials=60)
        diag = result.convergence_diagnostics
        assert "final_step_size" in diag
        assert "reversal_levels" in diag
        assert "accuracy" in diag

    def test_trial_records_complete(self):
        def respond(level, idx, rng):
            return rng.random() < 0.7
        result = run_calibration("P001", "reconstruction", respond, seed=42, n_trials=30)
        assert len(result.trials) > 0
        for trial in result.trials:
            assert "trial" in trial
            assert "level" in trial
            assert "correct" in trial
