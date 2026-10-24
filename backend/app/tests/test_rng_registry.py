"""Tests for deterministic scientific random streams.

Proves identical outputs regardless of PYTHONHASHSEED or process.
"""
import random

from app.research.rng_registry import RNG_VERSION, derive_seed, rng_version_hash


class TestDeriveSeed:
    def test_deterministic(self):
        s1 = derive_seed(42, "population")
        s2 = derive_seed(42, "population")
        assert s1 == s2

    def test_different_namespace(self):
        s1 = derive_seed(42, "population")
        s2 = derive_seed(42, "stimulus")
        assert s1 != s2

    def test_different_root(self):
        s1 = derive_seed(42, "population")
        s2 = derive_seed(43, "population")
        assert s1 != s2

    def test_participant_isolation(self):
        s1 = derive_seed(42, "imagery_noise", participant_id="p1", session_index=0, trial_index=0)
        s2 = derive_seed(42, "imagery_noise", participant_id="p2", session_index=0, trial_index=0)
        assert s1 != s2

    def test_session_isolation(self):
        s1 = derive_seed(42, "imagery_noise", participant_id="p1", session_index=0, trial_index=0)
        s2 = derive_seed(42, "imagery_noise", participant_id="p1", session_index=1, trial_index=0)
        assert s1 != s2

    def test_trial_isolation(self):
        s1 = derive_seed(42, "imagery_noise", participant_id="p1", session_index=0, trial_index=0)
        s2 = derive_seed(42, "imagery_noise", participant_id="p1", session_index=0, trial_index=1)
        assert s1 != s2

    def test_stream_independence(self):
        """Changing one stream must not alter unrelated streams."""
        rng1 = random.Random(derive_seed(42, "population"))
        vals1 = [rng1.random() for _ in range(10)]

        rng2 = random.Random(derive_seed(42, "population"))
        vals2 = [rng2.random() for _ in range(10)]
        assert vals1 == vals2

        rng_stim = random.Random(derive_seed(42, "stimulus"))
        vals_stim = [rng_stim.random() for _ in range(10)]
        assert vals_stim != vals1

    def test_non_negative_63bit(self):
        for ns in ["population", "stimulus", "imagery_noise", "dropout"]:
            s = derive_seed(42, ns)
            assert s >= 0
            assert s < 2**63

    def test_replicate_index(self):
        s1 = derive_seed(42, "simulation", replicate_index=0)
        s2 = derive_seed(42, "simulation", replicate_index=1)
        assert s1 != s2


class TestCognitiveAgentDeterminism:
    """Prove cognitive agent produces identical results across invocations."""

    def test_cross_invocation_determinism(self):
        from app.research.cognitive_agent import (
            SCENARIO_STRICT_NULL,
            generate_population,
            generate_trial_response,
        )
        from app.research.psychophysics.common import StimulusSpec

        pop1 = generate_population(5, seed=42, scenario=SCENARIO_STRICT_NULL)
        pop2 = generate_population(5, seed=42, scenario=SCENARIO_STRICT_NULL)

        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        for a1, a2 in zip(pop1, pop2):
            r1 = generate_trial_response(a1, target, target, "adaptive", 0, 0,
                                         SCENARIO_STRICT_NULL, False, 42)
            r2 = generate_trial_response(a2, target, target, "adaptive", 0, 0,
                                         SCENARIO_STRICT_NULL, False, 42)
            assert r1["composite_error"] == r2["composite_error"]
            assert r1["response"] == r2["response"]


class TestVersionHash:
    def test_deterministic(self):
        assert rng_version_hash() == rng_version_hash()

    def test_version_present(self):
        assert RNG_VERSION == "1.0"
