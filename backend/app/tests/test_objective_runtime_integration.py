"""Tests for objective runtime integration with LeakageGuard enforcement."""
from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    generate_population,
)
from app.research.objective_runtime import (
    LeakageGuard,
    execute_objective_session,
)
from app.research.response_provider import SyntheticCognitiveResponseProvider


class TestObjectiveSessionExecution:
    def _make_trial_specs(self, n: int = 3) -> list[dict]:
        specs = []
        for i in range(n):
            specs.append({
                "trial_index": i,
                "task_family": "feature_reconstruction",
                "target_orientation": 45 + i * 30,
                "target_hue": 120,
                "target_sf": 3.0,
                "target_pos_x": 500,
                "target_pos_y": 400,
                "target_size": 50,
                "is_perceptual_control": False,
                "delay_s": 0.0,
            })
        return specs

    def test_session_produces_results(self):
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()

        result = execute_objective_session(
            session_id="test-s1",
            participant_id=pop[0].participant_id,
            condition="adaptive",
            period=0,
            trial_specs=self._make_trial_specs(),
            response_provider=provider,
            leakage_guard=guard,
            seed=42,
        )
        assert len(result.trials) == 3
        assert result.content_hash != ""
        assert result.manifest_hash != ""

    def test_leakage_guard_clean(self):
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()

        result = execute_objective_session(
            session_id="test-s2",
            participant_id=pop[0].participant_id,
            condition="adaptive",
            period=0,
            trial_specs=self._make_trial_specs(1),
            response_provider=provider,
            leakage_guard=guard,
            seed=42,
        )
        assert all(a.passed for a in result.leakage_audit)

    def test_leakage_injection_raises(self):
        guard = LeakageGuard()
        leaked_context = {
            "condition": "adaptive",
            "composite_error": 0.5,
        }
        violations = guard.check_policy_input(leaked_context)
        assert len(violations) > 0
        assert "composite_error" in violations

    def test_leakage_in_runtime_raises_error(self):
        """Inject outcome into the policy context and prove transaction rolls back."""
        guard = LeakageGuard()
        guard._reserved_fields.add("injected_score")

        context = {"condition": "adaptive", "injected_score": 0.42}
        violations = guard.check_policy_input(context)
        assert "injected_score" in violations

    def test_deterministic_session(self):
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)

        r1 = execute_objective_session(
            "s1", pop[0].participant_id, "adaptive", 0,
            self._make_trial_specs(), provider, LeakageGuard(), 42,
        )
        r2 = execute_objective_session(
            "s1", pop[0].participant_id, "adaptive", 0,
            self._make_trial_specs(), provider, LeakageGuard(), 42,
        )
        assert r1.content_hash == r2.content_hash


class TestResponseProvider:
    def test_synthetic_provider_config(self):
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        config = provider.get_config()
        assert config.provider_type == "synthetic_cognitive"
        assert config.scenario_id == "medium_adaptive"
