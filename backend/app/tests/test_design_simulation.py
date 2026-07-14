"""Tests for simulation-based design validation with calibrated thresholds.

These tests require valid inference — not merely non-failing code.
A 100% fallback campaign must fail. Metrics from zero-valid-replicate
campaigns must be None, not 0.0.
"""
import math
import warnings

from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_SMALL_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
)
from app.research.design_simulation import (
    DesignRecommendation,
    SimulationResult,
    generate_design_recommendation,
    run_scenario_grid,
    run_simulation,
    simulation_hash,
)

N_CI_ITERS = 50
N_PARTICIPANTS = 18


class TestStrictNullStructural:
    """Potential outcomes must be identical under strict null."""

    def test_campaign_valid(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=N_CI_ITERS,
                               n_participants=N_PARTICIPANTS)
        assert r.campaign_valid, f"Strict null campaign invalid: {r.invalid_reason}"
        assert r.n_valid_replicates > 0

    def test_valid_inference_rate_high(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=N_CI_ITERS,
                               n_participants=N_PARTICIPANTS)
        assert r.valid_inference_rate >= 0.80, (
            f"Valid inference {r.valid_inference_rate} too low"
        )

    def test_type_i_calibrated(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=N_CI_ITERS,
                               n_participants=N_PARTICIPANTS)
        assert r.type_i_error is not None
        mc_tol = 2.576 * math.sqrt(0.05 * 0.95 / r.n_valid_replicates) if r.n_valid_replicates > 5 else 0.2
        assert r.type_i_error <= 0.05 + mc_tol, (
            f"Type-I {r.type_i_error} > 0.05 + {mc_tol:.4f}"
        )

    def test_coverage_calibrated(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=N_CI_ITERS,
                               n_participants=N_PARTICIPANTS)
        assert r.coverage is not None
        mc_tol = 2.576 * math.sqrt(0.95 * 0.05 / r.n_valid_replicates) if r.n_valid_replicates > 5 else 0.2
        assert r.coverage >= 0.95 - mc_tol, (
            f"Coverage {r.coverage} < 0.95 - {mc_tol:.4f}"
        )


class TestOrderedPower:
    """Power must increase with effect size."""

    def test_power_ordering(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r_null = run_simulation(SCENARIO_STRICT_NULL, n_iterations=N_CI_ITERS,
                                    n_participants=N_PARTICIPANTS)
            r_small = run_simulation(SCENARIO_SMALL_ADAPTIVE, n_iterations=N_CI_ITERS,
                                     n_participants=N_PARTICIPANTS)
            r_med = run_simulation(SCENARIO_MEDIUM_ADAPTIVE, n_iterations=N_CI_ITERS,
                                   n_participants=N_PARTICIPANTS)

        null_reject = r_null.type_i_error if r_null.type_i_error is not None else 0.0
        small_power = r_small.power if r_small.power is not None else 0.0
        med_power = r_med.power if r_med.power is not None else 0.0

        assert null_reject <= small_power + 0.15, (
            f"null reject {null_reject} > small power {small_power}"
        )
        assert small_power <= med_power + 0.10, (
            f"small power {small_power} > med power {med_power}"
        )


class TestFallbackRejection:
    """100% fallback campaigns must be flagged."""

    def test_zero_valid_returns_none_metrics(self):
        r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=5, n_participants=2)
        if r.n_valid_replicates == 0:
            assert r.power is None
            assert r.type_i_error is None
            assert r.coverage is None
            assert not r.campaign_valid


class TestSubjectiveOnly:
    def test_objective_oracle_zero(self):
        from app.research.causal_oracle import compute_oracle_effect
        r = compute_oracle_effect(SCENARIO_SUBJECTIVE_ONLY, n_agents=200, seed=42)
        assert abs(r.effect) <= 1e-10


class TestPracticeOnly:
    def test_oracle_treatment_zero(self):
        from app.research.causal_oracle import compute_oracle_effect
        r = compute_oracle_effect(SCENARIO_PRACTICE_ONLY, n_agents=200, seed=42)
        assert abs(r.effect) <= 1e-10


class TestScenarioGrid:
    def test_grid_runs_all_scenarios(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results = run_scenario_grid(n_iterations=5, n_participants=12)
        assert "strict_null" in results
        assert "medium_adaptive" in results
        assert len(results) >= 5


class TestDesignRecommendation:
    def test_recommendation_from_grid(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            grid = run_scenario_grid(n_iterations=5, n_participants=12)
        rec = generate_design_recommendation(grid, code_sha="test123")
        assert isinstance(rec, DesignRecommendation)
        assert rec.n_participants >= 6


class TestSimulationHash:
    def test_deterministic(self):
        h1 = simulation_hash("strict_null", 100, 42)
        h2 = simulation_hash("strict_null", 100, 42)
        assert h1 == h2

    def test_different_params(self):
        h1 = simulation_hash("strict_null", 100, 42)
        h2 = simulation_hash("medium_adaptive", 100, 42)
        assert h1 != h2
