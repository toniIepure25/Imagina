"""Tests for objective scientific evidence package export and validation."""
import hashlib
import json

from app.research.objective_endpoints import registry_hash
from app.research.objective_export import ExportPackage, export_hash, validate_export_package


def _make_valid_package():
    manifest_data = {"scoring_version": "1.0", "design_hash": "test_design"}
    manifest_hash = hashlib.sha256(
        json.dumps(manifest_data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ExportPackage(
        study_id="test-study",
        endpoint_registry_hash=registry_hash(),
        scoring_hash="test",
        schedule_hash="test",
        design_hash="test_design",
        analysis_spec_hash="test",
        oracle_spec_hash="test",
        objective_targets=[{"t": 1}],
        responses=[{"r": 1}],
        composite_scores=[{"s": 1}],
        seal_evidence=[{"seal": True, "manifest_hash": manifest_hash}],
        replay_results=[{
            "exact_match": True,
            "manifest_verified": True,
            "seal_verified": True,
            "schedule_verified": True,
            "scoring_verified": True,
            "response_provider_verified": True,
            "content_hash_match": True,
        }],
        manifest_evidence=[manifest_data],
        leakage_audits=[{"audit": True}],
        trial_transitions=[{"transition": True}],
        outbox_events=[
            {"event_type": "objective_trial_presented"},
            {"event_type": "objective_response_recorded"},
            {"event_type": "objective_trial_scored"},
            {"event_type": "objective_trial_finalized"},
            {"event_type": "objective_session_completed"},
        ],
        inference_valid=True,
        campaign_valid=True,
        required_inference_count=1,
        valid_inference_count=1,
        required_campaign_count=1,
        valid_campaign_count=1,
    )


class TestExportValidation:
    def test_valid_package_passes(self):
        pkg = _make_valid_package()
        result = validate_export_package(pkg)
        assert result.valid, result.issues

    def test_missing_registry_hash_fails(self):
        pkg = _make_valid_package()
        pkg.endpoint_registry_hash = ""
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("endpoint_registry_hash" in i for i in result.issues)

    def test_wrong_registry_hash_fails(self):
        pkg = _make_valid_package()
        pkg.endpoint_registry_hash = "wrong"
        result = validate_export_package(pkg)
        assert not result.valid

    def test_missing_targets_fails(self):
        pkg = _make_valid_package()
        pkg.objective_targets = []
        result = validate_export_package(pkg)
        assert not result.valid

    def test_target_response_mismatch_fails(self):
        pkg = _make_valid_package()
        pkg.objective_targets = [{"t": 1}, {"t": 2}]
        result = validate_export_package(pkg)
        assert not result.valid

    def test_missing_schedule_hash_fails(self):
        pkg = _make_valid_package()
        pkg.schedule_hash = ""
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("schedule_hash" in i for i in result.issues)

    def test_missing_design_hash_fails(self):
        pkg = _make_valid_package()
        pkg.design_hash = ""
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("design_hash" in i for i in result.issues)

    def test_invalid_inference_fails(self):
        pkg = _make_valid_package()
        pkg.inference_valid = False
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("inference_valid" in i for i in result.issues)

    def test_failed_campaign_fails(self):
        pkg = _make_valid_package()
        pkg.campaign_valid = False
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("campaign" in i for i in result.issues)


    def test_replay_missing_verification_flag_fails(self):
        pkg = _make_valid_package()
        pkg.replay_results = [{
            "exact_match": True,
            "manifest_verified": True,
            "seal_verified": True,
            "schedule_verified": True,
            "scoring_verified": True,
            "response_provider_verified": False,
            "content_hash_match": True,
        }]
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("missing flags" in i for i in result.issues)

    def test_mixed_valid_invalid_inference_fails(self):
        pkg = _make_valid_package()
        pkg.inference_valid = False
        pkg.required_inference_count = 2
        pkg.valid_inference_count = 1
        pkg.invalid_inference_ids = ["id-2"]
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("inference_valid" in i for i in result.issues)

    def test_mixed_pass_fail_campaign_fails(self):
        pkg = _make_valid_package()
        pkg.campaign_valid = False
        pkg.required_campaign_count = 2
        pkg.valid_campaign_count = 1
        pkg.failed_campaign_ids = ["scenario-2"]
        result = validate_export_package(pkg)
        assert not result.valid
        assert any("campaign" in i for i in result.issues)


class TestExportHash:
    def test_deterministic(self):
        p1 = _make_valid_package()
        p2 = _make_valid_package()
        assert export_hash(p1) == export_hash(p2)

    def test_changes_on_modification(self):
        p1 = _make_valid_package()
        p2 = _make_valid_package()
        p2.study_id = "different"
        assert export_hash(p1) != export_hash(p2)
