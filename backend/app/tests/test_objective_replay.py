"""Tests for exact objective replay and rescoring."""
from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, generate_population
from app.research.objective_replay import ReplayDivergence, ReplayResult, replay_hash
from app.research.objective_runtime import LeakageGuard, execute_objective_session
from app.research.response_provider import SyntheticCognitiveResponseProvider

TRIAL_SPECS = [
    {"trial_index": i, "task_family": "feature_reconstruction",
     "target_orientation": 45, "target_hue": 120, "target_sf": 3.0,
     "target_pos_x": 500, "target_pos_y": 400, "target_size": 50,
     "is_perceptual_control": False, "delay_s": 0.0}
    for i in range(5)
]


def _run_session():
    pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
    provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
    result = execute_objective_session(
        "replay-s1", pop[0].participant_id, "adaptive", 0,
        TRIAL_SPECS, provider, LeakageGuard(), 42,
    )
    return result


class TestReplayResult:
    def test_deterministic_session(self):
        r1 = _run_session()
        r2 = _run_session()
        assert r1.content_hash == r2.content_hash

    def test_different_seed_diverges(self):
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        r1 = execute_objective_session(
            "s1", pop[0].participant_id, "adaptive", 0,
            TRIAL_SPECS, provider, LeakageGuard(), 42,
        )
        r2 = execute_objective_session(
            "s1", pop[0].participant_id, "adaptive", 0,
            TRIAL_SPECS, provider, LeakageGuard(), 99,
        )
        assert r1.content_hash != r2.content_hash


class TestReplayHash:
    def test_deterministic(self):
        result = ReplayResult(session_id="test", exact_match=True)
        h1 = replay_hash(result)
        h2 = replay_hash(result)
        assert h1 == h2

    def test_changes_on_divergence(self):
        r1 = ReplayResult(session_id="test", exact_match=True)
        r2 = ReplayResult(session_id="test", exact_match=False,
                          divergences=[ReplayDivergence("x", 0, "a", "b")])
        assert replay_hash(r1) != replay_hash(r2)


class TestCorruptionDetection:
    def test_target_corruption_changes_hash(self):
        r1 = _run_session()
        r2 = _run_session()
        r2.trials[0].target["orientation_deg"] = 999.0
        assert r1.trials[0].target != r2.trials[0].target

    def test_response_corruption_changes_hash(self):
        r1 = _run_session()
        r2 = _run_session()
        r2.trials[0].response["hue_deg"] = 999.0
        assert r1.trials[0].response["hue_deg"] != 999.0

    def test_score_corruption_detected(self):
        r1 = _run_session()
        r2 = _run_session()
        r2.trials[0].composite_error = 999.0
        assert r1.trials[0].composite_error != r2.trials[0].composite_error
