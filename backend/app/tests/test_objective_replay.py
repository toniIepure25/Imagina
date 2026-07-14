"""Tests for exact objective replay and rescoring."""
from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, generate_population
from app.research.objective_provenance import create_completion_seal, create_objective_manifest
from app.research.objective_replay import replay_hash, replay_objective_session
from app.research.objective_runtime import LeakageGuard, execute_objective_session
from app.research.response_provider import SyntheticCognitiveResponseProvider

TRIAL_SPECS = [
    {"trial_index": i, "task_family": "feature_reconstruction",
     "target_orientation": 45, "target_hue": 120, "target_sf": 3.0,
     "target_pos_x": 500, "target_pos_y": 400, "target_size": 50,
     "is_perceptual_control": False, "delay_s": 0.0}
    for i in range(5)
]


def _run_and_seal():
    pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
    provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
    result = execute_objective_session(
        "replay-s1", pop[0].participant_id, "adaptive", 0,
        TRIAL_SPECS, provider, LeakageGuard(), 42,
    )
    manifest = create_objective_manifest(
        response_provider_id="synthetic", schedule_hash="test",
    )
    seal = create_completion_seal(result, manifest)
    return result, manifest, seal


class TestExactReplay:
    def test_exact_match(self):
        original, manifest, seal = _run_and_seal()
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=42,
        )
        assert replay.exact_match
        assert len(replay.divergences) == 0

    def test_content_hash_matches(self):
        original, manifest, seal = _run_and_seal()
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=42,
        )
        assert replay.original_content_hash == replay.replayed_content_hash

    def test_replay_hash_deterministic(self):
        original, manifest, seal = _run_and_seal()
        r1 = replay_objective_session(original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE, TRIAL_SPECS, 42)
        r2 = replay_objective_session(original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE, TRIAL_SPECS, 42)
        assert replay_hash(r1) == replay_hash(r2)


class TestCorruptionDetection:
    def test_target_corruption(self):
        original, manifest, seal = _run_and_seal()
        original.trials[0].target["orientation_deg"] = 999.0
        original.content_hash = "corrupted"
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=42,
        )
        assert not replay.exact_match

    def test_response_corruption(self):
        original, manifest, seal = _run_and_seal()
        original.trials[0].response["hue_deg"] = 999.0
        original.content_hash = "corrupted"
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=42,
        )
        assert not replay.exact_match

    def test_score_corruption(self):
        original, manifest, seal = _run_and_seal()
        original.trials[0].composite_error = 999.0
        original.content_hash = "corrupted"
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=42,
        )
        assert not replay.exact_match
        assert any(d.field == "composite_error" for d in replay.divergences)

    def test_different_seed_diverges(self):
        original, manifest, seal = _run_and_seal()
        replay = replay_objective_session(
            original, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE,
            TRIAL_SPECS, seed=99,
        )
        assert not replay.exact_match
