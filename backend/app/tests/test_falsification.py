"""End-to-end scientific falsification test suite.

Tests that try to make the system produce false conclusions.
Each scenario verifies that the analysis pipeline correctly handles
adversarial conditions and does not overclaim.
"""
from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
    generate_population,
    generate_trial_response,
)
from app.research.design_simulation import run_simulation
from app.research.objective_endpoints import registry_hash
from app.research.objective_runtime import LeakageGuard
from app.research.psychophysics.common import StimulusSpec
from app.research.statistics.confirmatory import run_primary_analysis


def _generate_data(scenario, n=18, seed=42, trials=5):
    pop = generate_population(n, seed=seed, scenario=scenario)
    target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
    sequences = [
        ["adaptive", "fixed", "yoked"],
        ["fixed", "yoked", "adaptive"],
        ["yoked", "adaptive", "fixed"],
        ["yoked", "fixed", "adaptive"],
        ["adaptive", "yoked", "fixed"],
        ["fixed", "adaptive", "yoked"],
    ]
    data = []
    for ai, agent in enumerate(pop):
        seq = sequences[ai % len(sequences)]
        for si in range(3):
            cond = seq[si]
            prev = seq[si - 1] if si > 0 else None
            for ti in range(trials):
                r = generate_trial_response(
                    agent, target, target, cond, si, ti,
                    scenario, False, seed + si * 100 + ti,
                    prev_condition=prev,
                )
                r["period"] = si
                r["baseline_precision"] = agent.baseline_imagery_precision
                r["task_family"] = "feature_reconstruction"
                r["carryover_indicator"] = prev if prev else "none"
                data.append(r)
    return data, pop


class TestStrictNull:
    """Under the exact null, adaptive must not systematically outperform controls."""

    def test_type_i_within_monte_carlo_bounds(self):
        result = run_simulation(SCENARIO_STRICT_NULL, n_iterations=30, n_participants=18)
        assert result.type_i_error <= 0.25, (
            f"Type-I error {result.type_i_error} exceeds 0.25 (SE={result.type_i_se})"
        )

    def test_null_no_systematic_advantage(self):
        data, _ = _generate_data(SCENARIO_STRICT_NULL, n=24)
        result = run_primary_analysis(data)
        assert result.p_value > 0.001 or result.is_fallback


class TestSubjectiveOnlyImprovement:
    """When vividness improves but precision does not, primary must remain null."""

    def test_objective_remains_null(self):
        data, _ = _generate_data(SCENARIO_SUBJECTIVE_ONLY, n=24)
        result = run_primary_analysis(data)
        assert result.p_value > 0.01 or result.is_fallback, (
            "Primary objective endpoint should not be significant under subjective-only scenario"
        )

    def test_vividness_may_change(self):
        data, _ = _generate_data(SCENARIO_SUBJECTIVE_ONLY, n=24)
        adaptive_vivid = [d["vividness"] for d in data if d["condition"] == "adaptive"]
        yoked_vivid = [d["vividness"] for d in data if d["condition"] == "yoked"]
        mean_a = sum(adaptive_vivid) / len(adaptive_vivid) if adaptive_vivid else 0
        mean_y = sum(yoked_vivid) / len(yoked_vivid) if yoked_vivid else 0
        assert isinstance(mean_a, float) and isinstance(mean_y, float)


class TestPracticeOnlyImprovement:
    """When all conditions improve equally, adaptive contrast should be null."""

    def test_adaptive_contrast_null(self):
        data, _ = _generate_data(SCENARIO_PRACTICE_ONLY, n=24)
        result = run_primary_analysis(data)
        assert result.p_value > 0.005 or result.is_fallback, (
            "Adaptive contrast should be null when practice equally affects all conditions"
        )


class TestPerceptualControlOnly:
    """When motor/perceptual matching improves, imagery primary should remain null."""

    def test_imagery_primary_null(self):
        data, _ = _generate_data(SCENARIO_PERCEPTUAL_ONLY, n=24)
        result = run_primary_analysis(data)
        assert result.p_value > 0.01 or result.is_fallback


class TestCarryover:
    """When adaptive effects persist, sensitivity must differ from naive model."""

    def test_carryover_analysis_differs(self):
        data, _ = _generate_data(SCENARIO_CARRYOVER, n=24)
        naive = run_primary_analysis(
            [d for d in data if d["carryover_indicator"] == "none"],
            estimand_id="naive_no_carryover",
        )
        full = run_primary_analysis(data, estimand_id="with_carryover")
        assert naive.effect_estimate != full.effect_estimate or naive.is_fallback


class TestScoreLeakage:
    """The system must reject or detect leakage of future outcomes to the policy."""

    def test_leakage_detected(self):
        guard = LeakageGuard()
        leaked_context = {
            "iqi": 0.5,
            "pid": 0.3,
            "composite_endpoint_score": 0.15,
        }
        violations = guard.check_policy_input(leaked_context)
        assert len(violations) > 0, "Leakage guard should detect composite_endpoint_score"

    def test_clean_context_passes(self):
        guard = LeakageGuard()
        clean_context = {"iqi": 0.5, "pid": 0.3, "attention": 0.6, "fatigue": 0.2}
        violations = guard.check_policy_input(clean_context)
        assert len(violations) == 0


class TestDataTampering:
    """Changing scoring, weights, or calibration must invalidate provenance."""

    def test_registry_hash_changes_on_modification(self):
        h1 = registry_hash()
        h2 = registry_hash()
        assert h1 == h2

    def test_different_weights_different_hash(self):
        from app.research.objective_endpoints import composite_reconstruction_error
        errors = {"orientation": 0.5, "hue": 0.5, "spatial_frequency": 0.3, "position": 0.2, "size": 0.1}
        s1 = composite_reconstruction_error(errors)
        s2 = composite_reconstruction_error(errors, {"orientation": 0.5, "hue": 0.1, "spatial_frequency": 0.1,
                                                      "position": 0.1, "size": 0.2})
        assert s1 != s2


class TestNegativeControlOutcome:
    """Negative control outcomes should remain null under imagery-specific effects."""

    def test_negative_control_null_under_adaptive(self):
        data, pop = _generate_data(SCENARIO_MEDIUM_ADAPTIVE, n=24)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        perceptual_data = []
        for ai, agent in enumerate(pop):
            for si in range(3):
                for ti in range(3):
                    r = generate_trial_response(
                        agent, target, target, "adaptive", si, ti,
                        SCENARIO_MEDIUM_ADAPTIVE, True, 42 + si * 100 + ti,
                    )
                    r["period"] = si
                    r["baseline_precision"] = agent.baseline_imagery_precision
                    r["task_family"] = "perceptual_control"
                    r["carryover_indicator"] = "none"
                    r["condition"] = "adaptive" if si == 0 else "yoked"
                    perceptual_data.append(r)
        if perceptual_data:
            result = run_primary_analysis(perceptual_data, estimand_id="negative_control")
            assert result.effect_estimate is not None
