"""Tests for observed-scale causal oracle."""
from app.research.causal_oracle import compute_full_oracle, compute_oracle_effect, oracle_spec_hash
from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
)


class TestOracleNull:
    def test_null_oracle_exactly_zero(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=100, seed=42)
        assert abs(r.effect) <= 1e-10, f"Null oracle effect {r.effect} not zero"

    def test_null_oracle_se_zero(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=100, seed=42)
        assert abs(r.effect_se) <= 1e-10, f"Null SE {r.effect_se} not zero"

    def test_null_participant_contrasts_all_zero(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=50, seed=42)
        for i, c in enumerate(r.participant_contrasts):
            assert abs(c) <= 1e-10, f"Participant {i} contrast {c} not zero"


class TestOracleEffectDirection:
    def test_medium_adaptive_negative(self):
        r = compute_oracle_effect(SCENARIO_MEDIUM_ADAPTIVE, n_agents=100, seed=42)
        assert r.effect < 0, f"Medium adaptive effect {r.effect} should be negative (lower error)"

    def test_subjective_only_objective_zero(self):
        r = compute_oracle_effect(SCENARIO_SUBJECTIVE_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) <= 1e-10, f"Subjective-only objective effect {r.effect} not zero"

    def test_practice_only_zero(self):
        r = compute_oracle_effect(SCENARIO_PRACTICE_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) <= 1e-10, f"Practice-only effect {r.effect} not zero"

    def test_perceptual_only_imagery_zero(self):
        r = compute_oracle_effect(SCENARIO_PERCEPTUAL_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) <= 1e-10, f"Perceptual-only imagery effect {r.effect} not zero"


class TestOracleContrasts:
    def test_full_oracle_has_three_contrasts(self):
        spec = compute_full_oracle(SCENARIO_MEDIUM_ADAPTIVE, n_agents=50, seed=42)
        assert "adaptive_vs_yoked" in spec.contrasts
        assert "adaptive_vs_fixed" in spec.contrasts
        assert "fixed_vs_yoked" in spec.contrasts

    def test_oracle_hash_deterministic(self):
        s1 = compute_full_oracle(SCENARIO_STRICT_NULL, n_agents=50, seed=42)
        s2 = compute_full_oracle(SCENARIO_STRICT_NULL, n_agents=50, seed=42)
        assert oracle_spec_hash(s1) == oracle_spec_hash(s2)


class TestOracleMetadata:
    def test_endpoint_id(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=50, seed=42)
        assert r.endpoint_id == "composite_reconstruction_error"

    def test_version(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=50, seed=42)
        assert r.oracle_version == "2.0"
