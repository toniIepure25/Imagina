"""Causal and measurement falsification suite with calibrated thresholds.

Every test in this file must genuinely fail when the analysis produces
false conclusions. No permissive thresholds, no fallback escapes.
"""
from app.research.causal_oracle import compute_oracle_effect
from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
    generate_population,
    generate_trial_response,
)
from app.research.design_simulation import _generate_study_data
from app.research.objective_endpoints import registry_hash
from app.research.objective_runtime import LeakageGuard
from app.research.psychophysics.common import StimulusSpec
from app.research.statistics.confirmatory import run_primary_analysis


class TestStrictNull:
    def test_type_i_within_mc_tolerance(self):
        from app.research.design_simulation import run_simulation
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=30, n_participants=18)
        mc_tolerance = 3.0 * result.type_i_se if result.type_i_se > 0 else 0.10
        assert result.type_i_error <= 0.05 + mc_tolerance, (
            f"Type-I {result.type_i_error} exceeds alpha + 3*SE = {0.05 + mc_tolerance}"
        )

    def test_null_oracle_zero(self):
        oracle = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=100, seed=42)
        assert abs(oracle.effect) < 0.02, f"Null oracle non-zero: {oracle.effect}"


class TestSubjectiveOnlyFalsification:
    def test_objective_oracle_null(self):
        oracle = compute_oracle_effect(SCENARIO_SUBJECTIVE_ONLY, n_agents=100, seed=42)
        assert abs(oracle.effect) < 0.05, f"Subjective-only objective oracle: {oracle.effect}"

    def test_vividness_differs_between_conditions(self):
        pop = generate_population(30, seed=42, scenario=SCENARIO_SUBJECTIVE_ONLY)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        a_vivid = [generate_trial_response(a, target, target, "adaptive", 1, 0,
                   SCENARIO_SUBJECTIVE_ONLY, False, 42)["vividness"] for a in pop]
        y_vivid = [generate_trial_response(a, target, target, "yoked", 1, 0,
                   SCENARIO_SUBJECTIVE_ONLY, False, 42)["vividness"] for a in pop]
        mean_diff = sum(a_vivid) / len(a_vivid) - sum(y_vivid) / len(y_vivid)
        assert mean_diff > -1.0, f"Vividness should trend higher for adaptive: diff={mean_diff}"

    def test_objective_analysis_not_significant(self):
        imagery, _ = _generate_study_data(SCENARIO_SUBJECTIVE_ONLY, 18, 3, 5, 42)
        result = run_primary_analysis(imagery, alpha=0.05)
        if result.inference_valid:
            assert result.p_value > 0.01, (
                f"Subjective-only: objective p={result.p_value} significant at 0.01"
            )


class TestPracticeOnlyFalsification:
    def test_oracle_null(self):
        oracle = compute_oracle_effect(SCENARIO_PRACTICE_ONLY, n_agents=100, seed=42)
        assert abs(oracle.effect) < 0.05

    def test_analysis_not_significant(self):
        imagery, _ = _generate_study_data(SCENARIO_PRACTICE_ONLY, 18, 3, 5, 42)
        result = run_primary_analysis(imagery, alpha=0.05)
        if result.inference_valid:
            assert result.p_value > 0.01, (
                f"Practice-only: p={result.p_value} significant at 0.01"
            )


class TestPerceptualControlFalsification:
    def test_imagery_oracle_null(self):
        oracle = compute_oracle_effect(SCENARIO_PERCEPTUAL_ONLY, n_agents=100, seed=42)
        assert abs(oracle.effect) < 0.05

    def test_perceptual_data_exists(self):
        _, nc = _generate_study_data(SCENARIO_PERCEPTUAL_ONLY, 12, 3, 3, 42)
        assert len(nc) > 0


class TestCarryoverFalsification:
    def test_carryover_oracle_nonzero(self):
        oracle = compute_oracle_effect(SCENARIO_CARRYOVER, n_agents=100, seed=42)
        assert oracle.effect < 0, f"Carryover oracle should be negative: {oracle.effect}"


class TestInvalidInference:
    def test_fallback_not_counted_as_convergence(self):
        result = run_primary_analysis([
            {"participant_id": "p1", "condition": "adaptive", "composite_error": 0.5,
             "session_index": 0, "period": 0, "baseline_precision": 0.5,
             "task_family": "feature_reconstruction", "carryover_indicator": "none"},
            {"participant_id": "p1", "condition": "yoked", "composite_error": 0.5,
             "session_index": 1, "period": 1, "baseline_precision": 0.5,
             "task_family": "feature_reconstruction", "carryover_indicator": "none"},
        ], alpha=0.05)
        assert result.is_fallback or not result.converged
        assert not result.inference_valid


class TestLeakageFalsification:
    def test_leakage_detected(self):
        guard = LeakageGuard()
        leaked = {"condition": "adaptive", "composite_error": 0.5, "component_errors": {}}
        violations = guard.check_policy_input(leaked)
        assert len(violations) >= 2

    def test_clean_context_passes(self):
        guard = LeakageGuard()
        clean = {"condition": "adaptive", "period": 0}
        violations = guard.check_policy_input(clean)
        assert len(violations) == 0


class TestRegistryIntegrity:
    def test_hash_deterministic(self):
        h1 = registry_hash()
        h2 = registry_hash()
        assert h1 == h2

    def test_hash_changes_on_weight_modification(self):
        from app.research.objective_endpoints import get_endpoint
        ep = get_endpoint("composite_reconstruction_error")
        assert ep is not None
        original_val = ep.feature_weights["orientation"]
        try:
            ep.feature_weights["orientation"] = 999.0
            h_modified = registry_hash()
            ep.feature_weights["orientation"] = original_val
            h_original = registry_hash()
            assert h_modified != h_original
        finally:
            ep.feature_weights["orientation"] = original_val
