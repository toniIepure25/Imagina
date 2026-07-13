"""Tests for session manifest creation and completion sealing."""
import os
import tempfile
from datetime import datetime, timezone

import aiosqlite
import pytest

from app.research.manifest import (
    create_session_manifest,
    get_manifest,
    seal_session_completion,
    validate_manifest,
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


class TestManifestSealing:
    async def test_seal_session(self, manifest_db):
        await _create_manifest(manifest_db)
        await manifest_db.commit()
        seal_hash = await seal_session_completion(
            manifest_db, "rs1",
            terminal_status="completed",
            terminal_reason="all_trials_done",
            content_hash="content123",
            sealed_at=datetime.now(timezone.utc),
        )
        await manifest_db.commit()
        assert len(seal_hash) == 64

        result = await get_manifest(manifest_db, "rs1")
        assert result["sealed_at"] is not None

    async def test_seal_validates_manifest_exists(self, manifest_db):
        with pytest.raises(ValueError, match="No manifest found"):
            await seal_session_completion(
                manifest_db, "nonexistent",
                terminal_status="completed",
                terminal_reason="done",
                content_hash="abc",
                sealed_at=datetime.now(timezone.utc),
            )
