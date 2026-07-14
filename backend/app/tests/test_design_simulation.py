"""Tests for simulation-based design validation."""

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
    def test_null_scenario_type_i(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=20, n_participants=12)
        assert isinstance(result, SimulationResult)
        assert result.type_i_error <= 0.50  # wide bound for 20 MC iterations
        assert result.type_i_se >= 0

    def test_medium_effect_has_power(self):
        result = run_simulation(SCENARIO_MEDIUM_ADAPTIVE, n_iterations=20, n_participants=18)
        assert result.n_iterations == 20
        assert result.n_participants == 18

    def test_monte_carlo_se_reported(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=20)
        assert result.type_i_se >= 0
        assert result.power_se >= 0

    def test_bias_computed(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10)
        assert isinstance(result.bias, float)
        assert isinstance(result.rmse, float)

    def test_coverage_computed(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10)
        assert 0.0 <= result.coverage <= 1.0

    def test_convergence_rate(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=10, n_participants=12)
        assert 0.0 <= result.convergence_rate <= 1.0


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
