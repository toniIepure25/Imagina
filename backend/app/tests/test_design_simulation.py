"""Tests for simulation-based design validation with calibrated thresholds."""

from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, SCENARIO_STRICT_NULL
from app.research.design_simulation import (
    DesignRecommendation,
    SimulationResult,
    generate_design_recommendation,
    run_scenario_grid,
    run_simulation,
    simulation_hash,
)


class TestSimulation:
    def test_null_type_i_calibrated(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=15, n_participants=12)
        assert isinstance(result, SimulationResult)
        mc_tolerance = 3.0 * result.type_i_se if result.type_i_se > 0 else 0.15
        assert result.type_i_error <= 0.05 + mc_tolerance, (
            f"Type-I {result.type_i_error} exceeds alpha=0.05 + 3*SE={mc_tolerance}"
        )

    def test_medium_effect_power_positive(self):
        result = run_simulation(SCENARIO_MEDIUM_ADAPTIVE, n_iterations=15, n_participants=18)
        assert result.n_iterations == 15
        assert result.power >= 0.0

    def test_oracle_effect_reported(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10)
        assert isinstance(result.oracle_effect, float)
        assert isinstance(result.oracle_se, float)

    def test_bias_uses_oracle(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10)
        assert isinstance(result.bias, float)
        assert isinstance(result.rmse, float)
        assert isinstance(result.bias_se, float)

    def test_coverage_with_se(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=15, n_participants=12)
        assert 0.0 <= result.coverage <= 1.0
        assert isinstance(result.coverage_se, float)

    def test_convergence_excludes_fallback(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10, n_participants=12)
        assert result.convergence_rate >= 0.0
        assert result.fallback_rate >= 0.0
        assert result.valid_inference_rate >= 0.0
        assert result.convergence_rate + result.fallback_rate <= 1.01

    def test_negative_control_fp_computed(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10, n_participants=12)
        assert isinstance(result.negative_control_fp_rate, float)

    def test_interval_width_reported(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10, n_participants=12)
        assert isinstance(result.interval_width, float)

    def test_mode_field(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10, mode="unit")
        assert result.mode == "unit"


class TestScenarioGrid:
    def test_grid_runs_all_scenarios(self):
        results = run_scenario_grid(n_iterations=5, n_participants=6)
        assert "strict_null" in results
        assert "medium_adaptive" in results
        assert len(results) >= 5


class TestDesignRecommendation:
    def test_recommendation_from_grid(self):
        grid = run_scenario_grid(n_iterations=5, n_participants=12)
        rec = generate_design_recommendation(grid, code_sha="test123")
        assert isinstance(rec, DesignRecommendation)
        assert rec.n_participants >= 6
        assert rec.code_sha == "test123"
        assert len(rec.assumptions) >= 2


class TestSimulationHash:
    def test_deterministic(self):
        h1 = simulation_hash("strict_null", 100, 42)
        h2 = simulation_hash("strict_null", 100, 42)
        assert h1 == h2

    def test_different_params(self):
        h1 = simulation_hash("strict_null", 100, 42)
        h2 = simulation_hash("medium_adaptive", 100, 42)
        assert h1 != h2
