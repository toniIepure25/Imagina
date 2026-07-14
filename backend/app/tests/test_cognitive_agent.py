"""Tests for the hierarchical cognitive agent model."""

from app.research.cognitive_agent import (
    MODEL_VERSION,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    SCENARIOS,
    generate_population,
    generate_trial_response,
    model_hash,
)
from app.research.psychophysics.common import StimulusSpec


class TestPopulationGeneration:
    def test_deterministic(self):
        p1 = generate_population(10, seed=42)
        p2 = generate_population(10, seed=42)
        assert [a.participant_id for a in p1] == [a.participant_id for a in p2]
        assert p1[0].baseline_imagery_precision == p2[0].baseline_imagery_precision

    def test_count(self):
        pop = generate_population(24, seed=1)
        assert len(pop) == 24

    def test_traits_in_range(self):
        pop = generate_population(100, seed=42)
        for a in pop:
            assert 0.0 <= a.baseline_imagery_precision <= 1.0
            assert 0.0 <= a.imagery_control <= 1.0
            assert 0.0 <= a.imagery_stability <= 1.0
            assert 0.0 <= a.perceptual_matching_skill <= 1.0

    def test_correlated_constructs(self):
        pop = generate_population(200, seed=42)
        precisions = [a.baseline_imagery_precision for a in pop]
        controls = [a.imagery_control for a in pop]
        r = _pearson_r(precisions, controls)
        assert r > 0.3, f"Expected positive correlation between precision and control, got {r}"


class TestTrialResponse:
    def test_response_has_required_fields(self):
        agent = generate_population(1, seed=42)[0]
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        result = generate_trial_response(
            agent, target, target, "adaptive", 0, 0,
            SCENARIO_STRICT_NULL, False, 42,
        )
        assert "composite_error" in result
        assert "component_errors" in result
        assert "confidence" in result
        assert "vividness" in result

    def test_composite_error_bounded(self):
        pop = generate_population(10, seed=42)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        for agent in pop:
            result = generate_trial_response(
                agent, target, target, "adaptive", 0, 0,
                SCENARIO_STRICT_NULL, False, 42,
            )
            assert 0.0 <= result["composite_error"] <= 2.0

    def test_perceptual_control_differs(self):
        agent = generate_population(1, seed=42, scenario=SCENARIO_STRICT_NULL)[0]
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        imagery_result = generate_trial_response(
            agent, target, target, "adaptive", 0, 0,
            SCENARIO_STRICT_NULL, False, 42,
        )
        perceptual_result = generate_trial_response(
            agent, target, target, "adaptive", 0, 0,
            SCENARIO_STRICT_NULL, True, 42,
        )
        assert imagery_result["is_perceptual_control"] is False
        assert perceptual_result["is_perceptual_control"] is True

    def test_deterministic_response(self):
        agent = generate_population(1, seed=42)[0]
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        r1 = generate_trial_response(agent, target, target, "adaptive", 0, 0, SCENARIO_STRICT_NULL, False, 42)
        r2 = generate_trial_response(agent, target, target, "adaptive", 0, 0, SCENARIO_STRICT_NULL, False, 42)
        assert r1["composite_error"] == r2["composite_error"]


class TestNullScenario:
    def test_null_conditions_equivalent(self):
        pop = generate_population(50, seed=42)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        errors_by_cond: dict[str, list[float]] = {"adaptive": [], "fixed": [], "yoked": []}
        for agent in pop:
            for cond in errors_by_cond:
                r = generate_trial_response(
                    agent, target, target, cond, 0, 0,
                    SCENARIO_STRICT_NULL, False, 42,
                )
                errors_by_cond[cond].append(r["composite_error"])
        means = {c: sum(v) / len(v) for c, v in errors_by_cond.items()}
        assert abs(means["adaptive"] - means["yoked"]) < 0.1


class TestScenarios:
    def test_all_scenarios_versioned(self):
        for sid, s in SCENARIOS.items():
            assert s.version == MODEL_VERSION

    def test_model_hash_deterministic(self):
        h1 = model_hash(SCENARIO_STRICT_NULL, 42)
        h2 = model_hash(SCENARIO_STRICT_NULL, 42)
        assert h1 == h2

    def test_different_scenario_different_hash(self):
        h1 = model_hash(SCENARIO_STRICT_NULL, 42)
        h2 = model_hash(SCENARIO_MEDIUM_ADAPTIVE, 42)
        assert h1 != h2

    def test_required_scenarios_exist(self):
        required = [
            "strict_null", "small_adaptive", "medium_adaptive",
            "subjective_only", "practice_only", "placebo_expectancy",
            "carryover", "differential_dropout", "perceptual_control_only",
        ]
        for s in required:
            assert s in SCENARIOS, f"Missing scenario: {s}"


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0
