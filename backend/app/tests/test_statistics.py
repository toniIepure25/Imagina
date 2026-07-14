"""Tests for the confirmatory analysis package."""
import warnings

from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    generate_population,
    generate_trial_response,
)
from app.research.design_simulation import WILLIAMS_SEQUENCES
from app.research.psychophysics.common import StimulusSpec
from app.research.statistics.confirmatory import (
    AnalysisResult,
    run_bootstrap_ci,
    run_full_analysis,
    run_hierarchical_analysis,
    run_primary_analysis,
    run_randomization_test,
)
from app.research.statistics.design_matrix import build_design_matrix, design_matrix_hash
from app.research.statistics.multiplicity import classify_endpoints, holm_correction


def _generate_study_data(n_participants: int, scenario, seed: int) -> list[dict]:
    pop = generate_population(n_participants, seed=seed, scenario=scenario)
    target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
    data: list[dict] = []
    for ai, agent in enumerate(pop):
        seq_idx = ai % len(WILLIAMS_SEQUENCES)
        seq = WILLIAMS_SEQUENCES[seq_idx]
        for si, cond in enumerate(seq):
            for ti in range(5):
                r = generate_trial_response(
                    agent, target, target, cond, si, ti,
                    scenario, False, seed + si * 100 + ti,
                )
                r["period"] = si
                r["sequence"] = seq_idx
                r["baseline_precision"] = agent.baseline_imagery_precision
                r["task_family"] = "feature_reconstruction"
                r["carryover_indicator"] = seq[si - 1] if si > 0 else "none"
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


class TestGEEPrimaryEstimator:
    def test_model_type_is_gee(self):
        data = _generate_study_data(12, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_primary_analysis(data)
        assert result.model_type == "statsmodels.GEE"
        assert not result.is_fallback
        assert result.inference_valid

    def test_returns_cluster_diagnostics(self):
        data = _generate_study_data(12, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_primary_analysis(data)
        assert result.n_clusters >= 12
        assert result.cluster_size_min > 0
        assert result.covariance_type == "robust_sandwich"

    def test_null_no_significant_effect(self):
        data = _generate_study_data(24, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_primary_analysis(data)
        assert result.inference_valid
        assert result.p_value > 0.01

    def test_medium_effect_detectable(self):
        data = _generate_study_data(24, SCENARIO_MEDIUM_ADAPTIVE, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_primary_analysis(data)
        assert result.inference_valid
        assert result.effect_estimate < 0

    def test_too_few_clusters_rejected(self):
        data = _generate_study_data(4, SCENARIO_STRICT_NULL, 42)
        result = run_primary_analysis(data)
        assert not result.inference_valid

    def test_empty_data(self):
        result = run_primary_analysis([])
        assert result.is_fallback
        assert not result.inference_valid


class TestHierarchicalSensitivity:
    def test_model_type_correctly_named(self):
        data = _generate_study_data(18, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = run_hierarchical_analysis(data)
        if result.inference_valid:
            assert result.model_type == "random_intercept_sensitivity"

    def test_agrees_with_primary_direction(self):
        data = _generate_study_data(18, SCENARIO_MEDIUM_ADAPTIVE, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            primary = run_primary_analysis(data)
            hier = run_hierarchical_analysis(data)
        if primary.inference_valid and hier.inference_valid:
            assert (primary.effect_estimate < 0) == (hier.effect_estimate < 0)


class TestBootstrapAlignment:
    def test_bootstrap_resamples_participants_and_refits_gee(self):
        data = _generate_study_data(18, SCENARIO_MEDIUM_ADAPTIVE, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            boot = run_bootstrap_ci(data, n_bootstrap=30, seed=42)
        assert boot["valid"]
        assert boot["n_success"] > 0
        assert boot["ci"] is not None
        lo, hi = boot["ci"]
        assert lo < hi

    def test_null_bootstrap_covers_zero(self):
        data = _generate_study_data(18, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            boot = run_bootstrap_ci(data, n_bootstrap=30, seed=42)
        if boot["valid"] and boot["ci"] is not None:
            lo, hi = boot["ci"]
            assert lo <= 0 <= hi, f"Null bootstrap CI [{lo}, {hi}] does not cover 0"


class TestRandomizationInference:
    def test_model_type_is_sign_flip(self):
        data = _generate_study_data(12, SCENARIO_STRICT_NULL, 42)
        result = run_randomization_test(data, n_permutations=100, seed=42)
        assert result.model_type == "paired_sign_flip"
        assert result.inference_valid

    def test_null_high_p_value(self):
        data = _generate_study_data(18, SCENARIO_STRICT_NULL, 42)
        result = run_randomization_test(data, n_permutations=200, seed=42)
        assert result.p_value > 0.05


class TestFullAnalysis:
    def test_all_estimators_present(self):
        data = _generate_study_data(18, SCENARIO_STRICT_NULL, 42)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            multi = run_full_analysis(data, n_bootstrap=20, seed=42)
        assert multi.primary is not None
        assert multi.randomization is not None


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
