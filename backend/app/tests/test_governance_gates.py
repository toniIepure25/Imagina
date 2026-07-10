"""Tests for research governance gates — readiness evaluation."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.governance import (
    evaluate_collection_readiness,
    evaluate_synthetic_readiness,
    get_system_capabilities,
)
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


async def _setup_study(
    db_path: str,
    lifecycle: str = "draft",
    with_protocol: bool = False,
    with_ethics: bool = False,
    with_participant: bool = False,
    participant_kind: str = "human_research",
    with_consent: bool = False,
    with_consent_doc: bool = False,
    consent_protocol_id: str | None = "pv-1",
    consent_doc_id: str | None = "cdv-1",
    consent_doc_status: str = "active",
    with_allocation: bool = False,
    withdrawn: bool = False,
    eligibility: bool = True,
    data_classification: str = "synthetic",
):
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        pvid = "pv-1" if with_protocol else None
        await db.execute(
            "INSERT OR REPLACE INTO studies "
            "(study_id, title, lifecycle_status, data_classification, "
            "active_protocol_version_id, created_at, updated_at) "
            "VALUES ('study-1', 'Test', ?, ?, ?, '2026-01-01', '2026-01-01')",
            (lifecycle, data_classification, pvid),
        )
        if with_protocol:
            await db.execute(
                "INSERT OR REPLACE INTO protocol_versions "
                "(protocol_version_id, study_id, version, status, created_at) "
                "VALUES ('pv-1', 'study-1', '1.0', 'frozen', '2026-01-01')"
            )
        if with_consent_doc and with_protocol:
            await db.execute(
                "INSERT OR REPLACE INTO consent_document_versions "
                "(consent_document_version_id, study_id, protocol_version_id, "
                "version, status, created_at) "
                "VALUES (?, 'study-1', 'pv-1', '1.0', ?, '2026-01-01')",
                (consent_doc_id or "cdv-1", consent_doc_status),
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
                "(consent_id, participant_id, study_id, protocol_version_id, "
                "consent_document_version_id, consented_at) "
                "VALUES ('c-1', 'p-1', 'study-1', ?, ?, '2026-01-01')",
                (consent_protocol_id, consent_doc_id),
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
            with_participant=True, withdrawn=True, with_consent=True,
            with_consent_doc=True, with_allocation=True,
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
            with_consent=True, with_consent_doc=True, with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is True

    async def test_participant_study_mismatch(self, gov_db):
        await _setup_study(gov_db, lifecycle="active", with_protocol=True)
        result = await evaluate_collection_readiness("study-1", "nonexistent-participant")
        assert result.allowed is False
        assert any(c.check == "participant_belongs" and c.status == "failed" for c in result.checks)


class TestConsentVersionEnforcement:
    async def test_null_protocol_reference_blocks(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent=True, with_consent_doc=True,
            consent_protocol_id=None, with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(
            c.check == "valid_consent" and c.status == "failed" and "null protocol" in c.reason
            for c in result.checks
        )

    async def test_null_consent_doc_reference_blocks(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent=True, with_consent_doc=True,
            consent_doc_id=None, with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(
            c.check == "valid_consent" and c.status == "failed" and "null consent_document" in c.reason
            for c in result.checks
        )

    async def test_wrong_protocol_blocks(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent=True, with_consent_doc=True,
            consent_protocol_id="pv-wrong", with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(
            c.check == "valid_consent" and c.status == "failed" and "pv-wrong" in c.reason
            for c in result.checks
        )

    async def test_superseded_document_blocks(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent=True, with_consent_doc=True,
            consent_doc_status="superseded", with_allocation=True,
        )
        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(
            c.check == "valid_consent" and c.status == "failed" and "superseded" in c.reason
            for c in result.checks
        )

    async def test_reconsent_after_document_update(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent_doc=True, with_allocation=True,
        )
        db = await aiosqlite.connect(gov_db)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "INSERT INTO consent_document_versions "
            "(consent_document_version_id, study_id, protocol_version_id, version, status, created_at) "
            "VALUES ('cdv-2', 'study-1', 'pv-1', '2.0', 'active', '2026-02-01')"
        )
        await db.execute(
            "UPDATE consent_document_versions SET status='superseded', superseded_at='2026-02-01' "
            "WHERE consent_document_version_id='cdv-1'"
        )
        await db.execute(
            "INSERT INTO consents "
            "(consent_id, participant_id, study_id, protocol_version_id, "
            "consent_document_version_id, consented_at) "
            "VALUES ('c-new', 'p-1', 'study-1', 'pv-1', 'cdv-2', '2026-02-01')"
        )
        await db.commit()
        await db.close()

        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is True

    async def test_withdrawal_after_reconsent(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent=True, with_consent_doc=True,
            with_allocation=True,
        )
        db = await aiosqlite.connect(gov_db)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "UPDATE consents SET withdrawn_at='2026-03-01' WHERE consent_id='c-1'"
        )
        await db.commit()
        await db.close()

        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "valid_consent" and c.status == "failed" for c in result.checks)

    async def test_multiple_historical_consents(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True, with_ethics=True,
            with_participant=True, with_consent_doc=True, with_allocation=True,
        )
        db = await aiosqlite.connect(gov_db)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "INSERT INTO consents (consent_id, participant_id, study_id, "
            "protocol_version_id, consent_document_version_id, consented_at, withdrawn_at) "
            "VALUES ('c-old', 'p-1', 'study-1', 'pv-1', 'cdv-1', '2025-01-01', '2025-06-01')"
        )
        await db.execute(
            "INSERT INTO consents (consent_id, participant_id, study_id, "
            "protocol_version_id, consent_document_version_id, consented_at) "
            "VALUES ('c-latest', 'p-1', 'study-1', 'pv-1', 'cdv-1', '2026-06-01')"
        )
        await db.commit()
        await db.close()

        result = await evaluate_collection_readiness("study-1", "p-1")
        assert result.allowed is True


class TestSyntheticReadiness:
    async def test_synthetic_study_passes(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True,
            with_participant=True, participant_kind="synthetic",
            with_allocation=True, data_classification="synthetic",
        )
        result = await evaluate_synthetic_readiness("study-1", "p-1")
        assert result.allowed is True

    async def test_human_classification_blocks_synthetic(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True,
            with_participant=True, participant_kind="synthetic",
            with_allocation=True, data_classification="human_research",
        )
        result = await evaluate_synthetic_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "data_classification" and c.status == "failed" for c in result.checks)

    async def test_human_participant_blocks_synthetic(self, gov_db):
        await _setup_study(
            gov_db, lifecycle="active", with_protocol=True,
            with_participant=True, participant_kind="human_research",
            with_allocation=True, data_classification="synthetic",
        )
        result = await evaluate_synthetic_readiness("study-1", "p-1")
        assert result.allowed is False
        assert any(c.check == "participant_kind" and c.status == "failed" for c in result.checks)


class TestCapabilitiesStructure:
    async def test_capabilities_have_structured_fields(self, gov_db):
        caps = await get_system_capabilities()
        assert isinstance(caps["protocol_freeze"], dict)
        assert "schema_available" in caps["protocol_freeze"]
        assert "service_available" in caps["protocol_freeze"]
        assert "runtime_gate_active" in caps["protocol_freeze"]
        assert "status" in caps["protocol_freeze"]
        assert "detail" in caps["protocol_freeze"]
        assert caps["human_collection_allowed"] is False

    async def test_capabilities_report_governance_schema(self, gov_db):
        caps = await get_system_capabilities()
        assert caps["protocol_freeze"]["schema_available"] is True
        assert caps["protocol_freeze"]["service_available"] is True
        assert caps["protocol_freeze"]["runtime_gate_active"] is False
        assert caps["protocol_freeze"]["status"] == "implemented"
