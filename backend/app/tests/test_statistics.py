"""Tests for the confirmatory analysis package."""


from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    generate_population,
    generate_trial_response,
)
from app.research.psychophysics.common import StimulusSpec
from app.research.statistics.confirmatory import AnalysisResult, run_primary_analysis
from app.research.statistics.design_matrix import build_design_matrix, design_matrix_hash
from app.research.statistics.multiplicity import classify_endpoints, holm_correction


def _generate_study_data(n_participants: int, scenario, seed: int) -> list[dict]:
    pop = generate_population(n_participants, seed=seed, scenario=scenario)
    target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
    data: list[dict] = []
    conditions = ["adaptive", "fixed", "yoked"]
    for agent in pop:
        for si, cond in enumerate(conditions):
            for ti in range(5):
                r = generate_trial_response(
                    agent, target, target, cond, si, ti,
                    scenario, False, seed + si * 100 + ti,
                )
                r["period"] = si
                r["baseline_precision"] = agent.baseline_imagery_precision
                r["task_family"] = "feature_reconstruction"
                r["carryover_indicator"] = "none"
                data.append(r)
    return data


class TestDesignMatrix:
    def test_build_from_trial_data(self):
        data = _generate_study_data(6, SCENARIO_STRICT_NULL, 42)
        dm = build_design_matrix(data)
        assert dm["n_rows"] == len(data)
        assert dm["n_participants"] == 6
        assert dm["n_conditions"] == 3

    def test_hash_deterministic(self):
        data = _generate_study_data(6, SCENARIO_STRICT_NULL, 42)
        dm = build_design_matrix(data)
        h1 = design_matrix_hash(dm)
        h2 = design_matrix_hash(dm)
        assert h1 == h2


class TestConfirmatoryAnalysis:
    def test_analysis_returns_result(self):
        data = _generate_study_data(12, SCENARIO_STRICT_NULL, 42)
        result = run_primary_analysis(data)
        assert isinstance(result, AnalysisResult)
        assert result.n_participants >= 12
        assert result.n_trials > 0

    def test_null_scenario_no_significant_effect(self):
        data = _generate_study_data(24, SCENARIO_STRICT_NULL, 42)
        result = run_primary_analysis(data)
        assert result.p_value > 0.001 or result.is_fallback

    def test_medium_effect_detectable(self):
        data = _generate_study_data(30, SCENARIO_MEDIUM_ADAPTIVE, 42)
        result = run_primary_analysis(data)
        assert result.effect_estimate != 0.0
        assert result.standard_error > 0

    def test_result_has_diagnostics(self):
        data = _generate_study_data(12, SCENARIO_STRICT_NULL, 42)
        result = run_primary_analysis(data)
        assert result.model_spec_hash is not None
        assert result.analysis_population == "intention_to_treat"

    def test_too_few_participants_uses_fallback(self):
        data = _generate_study_data(2, SCENARIO_STRICT_NULL, 42)
        result = run_primary_analysis(data)
        assert result.is_fallback is True

    def test_empty_data(self):
        result = run_primary_analysis([])
        assert result.is_fallback is True
        assert result.converged is False


class TestMultiplicity:
    def test_holm_all_significant(self):
        p_values = [("a", 0.001), ("b", 0.005), ("c", 0.01)]
        results = holm_correction(p_values, alpha=0.05)
        assert all(r["significant"] for r in results)

    def test_holm_none_significant(self):
        p_values = [("a", 0.50), ("b", 0.60), ("c", 0.70)]
        results = holm_correction(p_values, alpha=0.05)
        assert not any(r["significant"] for r in results)

    def test_holm_partial(self):
        p_values = [("a", 0.01), ("b", 0.04), ("c", 0.60)]
        results = holm_correction(p_values, alpha=0.05)
        sig_count = sum(1 for r in results if r["significant"])
        assert 0 < sig_count < 3

    def test_hierarchical_classification(self):
        result = classify_endpoints(
            primary_p=0.03,
            secondary_p_values=[("sec1", 0.01), ("sec2", 0.04)],
        )
        assert result["primary"]["significant"] is True
        assert result["procedure"] == "hierarchical_holm"

    def test_hierarchical_primary_ns_blocks_secondary(self):
        result = classify_endpoints(
            primary_p=0.10,
            secondary_p_values=[("sec1", 0.001)],
        )
        assert result["primary"]["significant"] is False
        for sec in result["secondary"]:
            assert sec["significant"] is False
