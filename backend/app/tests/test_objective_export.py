"""Tests for objective scientific evidence package export and validation."""
from app.research.objective_endpoints import registry_hash
from app.research.objective_export import ExportPackage, export_hash, validate_export_package


def _make_valid_package():
    return ExportPackage(
        study_id="test-study",
        endpoint_registry_hash=registry_hash(),
        scoring_hash="test",
        schedule_hash="test",
        analysis_spec_hash="test",
        oracle_spec_hash="test",
        objective_targets=[{"t": 1}],
        responses=[{"r": 1}],
        composite_scores=[{"s": 1}],
        seal_evidence=[{"seal": True}],
        replay_results=[{"replay": True}],
        manifest_evidence=[{"manifest": True}],
    )


class TestExportValidation:
    def test_valid_package_passes(self):
        pkg = _make_valid_package()
        result = validate_export_package(pkg)
        assert result.valid

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
