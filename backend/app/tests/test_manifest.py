"""Tests for session manifest creation, completion sealing, and tamper detection."""
import os
import tempfile
from datetime import datetime, timezone

import aiosqlite
import pytest

from app.research.manifest import (
    create_session_manifest,
    get_completion_seal,
    get_manifest,
    seal_session_completion,
    validate_manifest,
    verify_seal_integrity,
)
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def manifest_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_manifest.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await run_migrations(db)
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO studies (study_id, title, application_mode, data_classification, "
            "lifecycle_status, created_at, updated_at) "
            "VALUES ('s1', 'Test', 'research', 'synthetic', 'active', ?, ?)",
            (now, now),
        )
        await db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, "
            "status, created_at) VALUES ('pv1', 's1', 'v1', 'draft', ?)", (now,),
        )
        await db.execute(
            "INSERT INTO participants (participant_id, study_id, participant_kind, "
            "pseudonym, created_at) VALUES ('p1', 's1', 'synthetic', 'agent-1', ?)", (now,),
        )
        await db.execute(
            "INSERT INTO research_sessions (research_session_id, study_id, participant_id, "
            "protocol_version_id, allocation_id, session_index, condition, "
            "data_classification, signal_provider_id, policy_id, policy_version, "
            "runtime_seed, status, state_version, planned_at, software_version, git_sha) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'sim', 'adaptive', '1.0', 42, 'planned', 0, ?, '0.5.0', 'test')", (now,),
        )
        await db.commit()
        yield db
        await db.close()


async def _create_manifest(db):
    return await create_session_manifest(
        db, "rs1",
        study_id="s1",
        protocol_version_id="pv1",
        protocol_hash="abc123",
        participant_id="p1",
        allocation_id="a1",
        condition="adaptive",
        session_index=0,
        data_classification="synthetic",
        runtime_seed=42,
        signal_provider_id="synthetic.deterministic",
        policy_id="adaptive",
        policy_version="1.0",
    )


async def _seal(db):
    return await seal_session_completion(
        db, "rs1",
        terminal_status="completed",
        terminal_reason="all_trials_done",
        content_hash="content_hash_abc123",
        sealed_at=datetime.now(timezone.utc),
    )


class TestManifestCreation:
    async def test_creates_manifest(self, manifest_db):
        mid = await _create_manifest(manifest_db)
        await manifest_db.commit()
        assert mid

    async def test_manifest_retrievable(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        result = await get_manifest(manifest_db, "rs1")
        assert result is not None
        assert result["manifest"]["study_id"] == "s1"
        assert result["manifest"]["condition"] == "adaptive"
        assert result["manifest_hash"]

    async def test_manifest_validation_passes(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        result = await validate_manifest(manifest_db, "rs1")
        assert result["valid"] is True

    async def test_missing_manifest_invalid(self, manifest_db):
        result = await validate_manifest(manifest_db, "nonexistent")
        assert result["valid"] is False

    async def test_manifest_hash_deterministic(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        r1 = await get_manifest(manifest_db, "rs1")
        assert len(r1["manifest_hash"]) == 64


class TestCompletionSeals:
    async def test_seal_persisted(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        seal_hash = await _seal(manifest_db)
        await manifest_db.commit()

        assert len(seal_hash) == 64
        seal = await get_completion_seal(manifest_db, "rs1")
        assert seal is not None
        assert seal["terminal_status"] == "completed"
        assert seal["scientific_content_hash"] == "content_hash_abc123"
        assert seal["seal_hash"] == seal_hash

    async def test_seal_immutable(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        with pytest.raises(ValueError, match="Seal already exists"):
            await _seal(manifest_db)

    async def test_seal_integrity_valid(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        result = await verify_seal_integrity(manifest_db, "rs1")
        assert result["valid"] is True

    async def test_seal_requires_manifest(self, manifest_db):
        with pytest.raises(ValueError, match="No manifest found"):
            await seal_session_completion(
                manifest_db, "nonexistent",
                terminal_status="completed",
                terminal_reason="done",
                content_hash="abc",
                sealed_at=datetime.now(timezone.utc),
            )

    async def test_manifest_sealed_at_updated(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        result = await get_manifest(manifest_db, "rs1")
        assert result["sealed_at"] is not None


class TestTamperDetection:
    async def test_tampered_seal_hash_detected(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        await manifest_db.execute(
            "UPDATE session_completion_seals "
            "SET seal_hash = 'tampered_hash' "
            "WHERE research_session_id = 'rs1'"
        )
        await manifest_db.commit()

        result = await verify_seal_integrity(manifest_db, "rs1")
        assert result["valid"] is False
        assert "tampering" in result["error"].lower()

    async def test_tampered_content_hash_detected(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        await manifest_db.execute(
            "UPDATE session_completion_seals "
            "SET scientific_content_hash = 'tampered_content' "
            "WHERE research_session_id = 'rs1'"
        )
        await manifest_db.commit()

        result = await verify_seal_integrity(manifest_db, "rs1")
        assert result["valid"] is False

    async def test_tampered_manifest_hash_detected(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        await _seal(manifest_db)
        await manifest_db.commit()

        await manifest_db.execute(
            "UPDATE session_manifests "
            "SET manifest_hash = 'tampered_manifest_hash' "
            "WHERE research_session_id = 'rs1'"
        )
        await manifest_db.commit()

        result = await verify_seal_integrity(manifest_db, "rs1")
        assert result["valid"] is False
        assert "manifest" in result["error"].lower()

    async def test_missing_seal_detected(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()

        result = await verify_seal_integrity(manifest_db, "rs1")
        assert result["valid"] is False
        assert "no completion seal" in result["error"].lower()


class TestManifestDependencyFields:
    async def test_round_trip_all_fields(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        result = await get_manifest(manifest_db, "rs1")
        m = result["manifest"]
        assert m["signal_provider"]["id"] == "synthetic.deterministic"
        assert m["feature_processor"]["id"] == "passthrough"
        assert m["state_estimator"]["id"] == "rule_based"
        assert m["metric_processor"]["id"] == "composite"
        assert m["curriculum_processor"]["id"] == "fixed_level"
        assert m["feedback_policy"]["id"] == "adaptive"
        assert m["safety_monitor"]["id"] == "synthetic"
        assert m["id_generator"]["id"] == "deterministic"
        assert m["clock"]["id"] == "deterministic"
        assert m["canonicalization_version"] == "2.0"
        assert m["db_schema_version"] == 6
        assert m["manifest_schema_version"] == 2

    async def test_unknown_version_replay_fails(self, manifest_db):
        from app.research.replay_validator import _verify_manifest_dependencies
        m = {
            "signal_provider": {"id": "synthetic.deterministic", "version": "1.0"},
            "feature_processor": {"id": "UNKNOWN_PROCESSOR", "version": "9.9"},
            "state_estimator": {"id": "rule_based", "version": "1.0"},
            "metric_processor": {"id": "composite", "version": "1.0"},
            "curriculum_processor": {"id": "fixed_level", "version": "1.0"},
            "feedback_policy": {"id": "adaptive", "version": "1.0"},
            "safety_monitor": {"id": "synthetic", "version": "1.0"},
        }
        err = _verify_manifest_dependencies(m)
        assert err is not None
        assert "Unknown" in err

    async def test_missing_field_replay_fails(self, manifest_db):
        from app.research.replay_validator import _verify_manifest_dependencies
        m = {
            "signal_provider": {"id": "synthetic.deterministic"},
            "feature_processor": {"id": "passthrough", "version": "1.0"},
            "state_estimator": {"id": "rule_based", "version": "1.0"},
            "metric_processor": {"id": "composite", "version": "1.0"},
            "curriculum_processor": {"id": "fixed_level", "version": "1.0"},
            "feedback_policy": {"id": "adaptive", "version": "1.0"},
            "safety_monitor": {"id": "synthetic", "version": "1.0"},
        }
        err = _verify_manifest_dependencies(m)
        assert err is not None
        assert "Missing" in err

    async def test_canonicalization_version_mismatch_fails(self, manifest_db):
        from app.research.replay_validator import _verify_manifest_dependencies
        m = {
            "signal_provider": {"id": "synthetic.deterministic", "version": "1.0"},
            "feature_processor": {"id": "passthrough", "version": "1.0"},
            "state_estimator": {"id": "rule_based", "version": "1.0"},
            "metric_processor": {"id": "composite", "version": "1.0"},
            "curriculum_processor": {"id": "fixed_level", "version": "1.0"},
            "feedback_policy": {"id": "adaptive", "version": "1.0"},
            "safety_monitor": {"id": "synthetic", "version": "1.0"},
            "canonicalization_version": "0.9",
        }
        err = _verify_manifest_dependencies(m)
        assert err is not None
        assert "Canonicalization" in err

    async def test_valid_dependencies_pass(self, manifest_db):
        from app.research.replay_validator import _verify_manifest_dependencies
        m = {
            "signal_provider": {"id": "synthetic.deterministic", "version": "1.0"},
            "feature_processor": {"id": "passthrough", "version": "1.0"},
            "state_estimator": {"id": "rule_based", "version": "1.0"},
            "metric_processor": {"id": "composite", "version": "1.0"},
            "curriculum_processor": {"id": "fixed_level", "version": "1.0"},
            "feedback_policy": {"id": "adaptive", "version": "1.0"},
            "safety_monitor": {"id": "synthetic", "version": "1.0"},
            "canonicalization_version": "2.0",
        }
        err = _verify_manifest_dependencies(m)
        assert err is None
