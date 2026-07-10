"""Tests for research governance gates — readiness evaluation."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.governance import evaluate_collection_readiness
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def gov_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "gov_test.db")
        monkeypatch.setattr("app.storage.database.DB_PATH", path)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        await db.close()
        yield path


async def _setup_study(db_path: str, lifecycle: str = "draft", with_protocol: bool = False,
                       with_ethics: bool = False, with_participant: bool = False,
                       participant_kind: str = "human_research", with_consent: bool = False,
                       with_allocation: bool = False, withdrawn: bool = False,
                       eligibility: bool = True):
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        pvid = "pv-1" if with_protocol else None
        await db.execute(
            "INSERT OR REPLACE INTO studies "
            "(study_id, title, lifecycle_status, active_protocol_version_id, created_at, updated_at) "
            "VALUES ('study-1', 'Test', ?, ?, '2026-01-01', '2026-01-01')",
            (lifecycle, pvid),
        )
        if with_protocol:
            await db.execute(
                "INSERT OR REPLACE INTO protocol_versions "
                "(protocol_version_id, study_id, version, status, created_at) "
                "VALUES ('pv-1', 'study-1', '1.0', 'frozen', '2026-01-01')"
            )
        if with_ethics:
            await db.execute(
                "INSERT OR REPLACE INTO ethics_reviews "
                "(ethics_review_id, study_id, protocol_version_id, status, recorded_at) "
                "VALUES ('er-1', 'study-1', 'pv-1', 'approved', '2026-01-01')"
            )
        if with_participant:
            withdrawn_at = "2026-06-01" if withdrawn else None
            await db.execute(
                "INSERT OR REPLACE INTO participants "
                "(participant_id, study_id, pseudonym, participant_kind, eligibility_confirmed, "
                "withdrawn_at, created_at) "
                "VALUES ('p-1', 'study-1', 'ALICE', ?, ?, ?, '2026-01-01')",
                (participant_kind, int(eligibility), withdrawn_at),
            )
        if with_consent and with_participant:
            await db.execute(
                "INSERT OR REPLACE INTO consents "
                "(consent_id, participant_id, study_id, consented_at) "
                "VALUES ('c-1', 'p-1', 'study-1', '2026-01-01')"
            )
        if with_allocation and with_participant:
            await db.execute(
                "INSERT OR REPLACE INTO sequence_allocations "
                "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
                "VALUES ('a-1', 'study-1', 'p-1', 'ABC', 'ABC', '2026-01-01')"
            )
        await db.commit()
    finally:
        await db.close()


class TestGovernanceGates:
    async def test_nonexistent_study_fails(self, gov_db):
        result = await evaluate_collection_readiness("no-study", "no-participant")
        assert result.allowed is False
        assert any(c.check == "study_exists" and c.status == "failed" for c in result.checks)

    async def test_draft_lifecycle_blocks(self, gov_db):
        await _setup_study(gov_db, lifecycle="draft", with_participant=True)
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "study_lifecycle" and c.status == "failed" for c in result.checks)

    async def test_no_protocol_blocks(self, gov_db):
        await _setup_study(gov_db, lifecycle="active", with_participant=True)
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "protocol_frozen" and c.status == "failed" for c in result.checks)

    async def test_no_ethics_blocks(self, gov_db):
        await _setup_study(gov_db, lifecycle="active", with_protocol=True, with_participant=True)
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "ethics_approved" and c.status == "failed" for c in result.checks)

    async def test_no_consent_blocks_human(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, participant_kind="human_research",
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "valid_consent" and c.status == "failed" for c in result.checks)

    async def test_withdrawn_blocks(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, withdrawn=True, with_consent=True, with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "not_withdrawn" and c.status == "failed" for c in result.checks)

    async def test_synthetic_skips_consent(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, participant_kind="synthetic", with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert any(c.check == "valid_consent" and c.status == "skipped" for c in result.checks)

    async def test_full_readiness_passes(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, participant_kind="human_research",
            with_consent=True, with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is True

    async def test_participant_study_mismatch(self, gov_db):
        await _setup_study(gov_db, lifecycle="active", with_protocol=True)
        result = await evaluate_collection_readiness("study-1", "nonexistent-participant")
        assert result.allowed is False
        assert any(c.check == "participant_belongs" and c.status == "failed" for c in result.checks)
