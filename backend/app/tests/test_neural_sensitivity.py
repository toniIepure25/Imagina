"""Tests for the C1 fixed-sample sensitivity analysis."""
from app.research.neural.sensitivity import (
    MINIMUM_EFFECT_OF_INTEREST,
    estimate_power_at_effect,
    run_sensitivity_analysis,
)


class TestEstimatePowerAtEffect:
    def test_power_is_near_alpha_at_zero_true_effect(self):
        # At true effect 0, the test should reject at approximately the
        # nominal alpha rate (it's testing a true null).
        power = estimate_power_at_effect(
            true_mean_delta=0.0, observed_std=0.05, n_participants=16,
            alpha=0.05, n_simulations=500, seed=1,
        )
        assert power < 0.15  # generous margin around the nominal 5%

    def test_power_increases_with_effect_size(self):
        small = estimate_power_at_effect(0.01, observed_std=0.05, n_participants=16, n_simulations=500, seed=1)
        large = estimate_power_at_effect(0.20, observed_std=0.05, n_participants=16, n_simulations=500, seed=1)
        assert large > small

    def test_power_increases_with_sample_size(self):
        small_n = estimate_power_at_effect(0.08, observed_std=0.05, n_participants=8, n_simulations=500, seed=1)
        large_n = estimate_power_at_effect(0.08, observed_std=0.05, n_participants=30, n_simulations=500, seed=1)
        assert large_n >= small_n

    def test_power_decreases_with_higher_variance(self):
        low_var = estimate_power_at_effect(0.08, observed_std=0.02, n_participants=16, n_simulations=500, seed=1)
        high_var = estimate_power_at_effect(0.08, observed_std=0.20, n_participants=16, n_simulations=500, seed=1)
        assert low_var >= high_var


class TestRunSensitivityAnalysis:
    def test_result_contains_power_curve_and_minimum_effect_check(self):
        result = run_sensitivity_analysis(
            n_participants=16, observed_std_delta_oos=0.05, n_simulations=300,
        )
        assert result.n_participants == 16
        assert result.minimum_effect_of_interest == MINIMUM_EFFECT_OF_INTEREST
        assert "0.000" in result.power_curve
        assert 0.0 <= result.power_at_minimum_effect_of_interest <= 1.0

    def test_adequately_powered_flag_reflects_80_percent_threshold(self):
        # Very low variance + large sample -> should be adequately powered
        # to detect the minimum effect of interest.
        well_powered = run_sensitivity_analysis(
            n_participants=16, observed_std_delta_oos=0.01, n_simulations=500,
        )
        assert well_powered.adequately_powered is (well_powered.power_at_minimum_effect_of_interest >= 0.8)

    def test_to_dict_is_json_serializable(self):
        import json
        result = run_sensitivity_analysis(n_participants=10, observed_std_delta_oos=0.05, n_simulations=200)
        json.dumps(result.to_dict())

    def test_high_variance_small_n_is_not_adequately_powered(self):
        underpowered = run_sensitivity_analysis(
            n_participants=6, observed_std_delta_oos=0.30, n_simulations=300,
        )
        assert underpowered.adequately_powered is False
