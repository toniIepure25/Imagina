"""Tests for objective provenance — manifests and completion seals."""
from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, generate_population
from app.research.objective_provenance import (
    create_completion_seal,
    create_objective_manifest,
    verify_seal,
)
from app.research.objective_runtime import LeakageGuard, execute_objective_session
from app.research.response_provider import SyntheticCognitiveResponseProvider


def _run_test_session():
    pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
    provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
    specs = [{"trial_index": i, "task_family": "feature_reconstruction",
              "target_orientation": 45, "target_hue": 120,
              "target_sf": 3.0, "target_pos_x": 500, "target_pos_y": 400,
              "target_size": 50, "is_perceptual_control": False, "delay_s": 0.0}
             for i in range(3)]
    result = execute_objective_session(
        "prov-s1", pop[0].participant_id, "adaptive", 0,
        specs, provider, LeakageGuard(), 42,
    )
    return result


class TestManifest:
    def test_create_manifest(self):
        m = create_objective_manifest(
            schedule_hash="abc", response_provider_id="synthetic",
        )
        assert m.endpoint_registry_hash != ""
        assert m.rng_version_hash != ""

    def test_manifest_validation(self):
        m = create_objective_manifest()
        issues = m.validate()
        assert "missing response_provider_id" in issues

    def test_manifest_hash_deterministic(self):
        m1 = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        m2 = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        assert m1.hash() == m2.hash()

    def test_manifest_hash_changes(self):
        m1 = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        m2 = create_objective_manifest(response_provider_id="synthetic", schedule_hash="y")
        assert m1.hash() != m2.hash()


class TestCompletionSeal:
    def test_seal_creation(self):
        result = _run_test_session()
        manifest = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        seal = create_completion_seal(result, manifest)
        assert seal.trial_count == 3
        assert seal.content_hash == result.content_hash
        assert seal.seal_hash() != ""

    def test_seal_verification(self):
        result = _run_test_session()
        manifest = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        seal = create_completion_seal(result, manifest)
        issues = verify_seal(seal, result)
        assert len(issues) == 0

    def test_seal_detects_tamper(self):
        result = _run_test_session()
        manifest = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        seal = create_completion_seal(result, manifest)
        result.content_hash = "tampered"
        issues = verify_seal(seal, result)
        assert any("content_hash" in i for i in issues)

    def test_score_change_invalidates_seal(self):
        result = _run_test_session()
        manifest = create_objective_manifest(response_provider_id="synthetic", schedule_hash="x")
        seal1 = create_completion_seal(result, manifest)
        result.trials[0].composite_error = 999.0
        result.content_hash = "modified"
        seal2 = create_completion_seal(result, manifest)
        assert seal1.score_hash != seal2.score_hash
