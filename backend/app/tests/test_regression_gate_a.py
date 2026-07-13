"""Regression tests — verify Gate A behavior remains intact after Gate B changes."""
import tempfile

import aiosqlite
import pytest

from app.research.governance import evaluate_synthetic_readiness, get_system_capabilities
from app.research.sequence_allocator import WILLIAMS_SEQUENCES, allocate_sequence
from app.storage.migration_runner import current_version, run_migrations


@pytest.fixture
async def reg_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    yield db
    await db.close()


class TestGateARegression:
    async def test_migrations_run_on_fresh_db(self, reg_db):
        version = await current_version(reg_db)
        assert version >= 5

    async def test_williams_sequences_exist(self):
        assert len(WILLIAMS_SEQUENCES) == 6
        labels = {label for label, _ in WILLIAMS_SEQUENCES}
        assert len(labels) == 6

    async def test_capabilities_returns_dict(self):
        caps = await get_system_capabilities()
        assert isinstance(caps, dict)
        assert "protocol_freeze" in caps

    async def test_synthetic_readiness_checks_structure(self, reg_db, monkeypatch):
        now_iso = "2026-01-01T00:00:00+00:00"
        await reg_db.execute(
            "INSERT INTO studies (study_id, title, application_mode, data_classification, "
            "lifecycle_status, created_at, updated_at) VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?)",
            ("reg-test", "Regression", now_iso, now_iso),
        )
        await reg_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, participant_kind, "
            "eligibility_confirmed, created_at) VALUES (?, ?, 'REG-001', 'synthetic', 1, ?)",
            ("reg-p1", "reg-test", now_iso),
        )
        await reg_db.commit()

        async def mock_get_db():
            return reg_db

        monkeypatch.setattr("app.research.governance.get_db", mock_get_db)
        result = await evaluate_synthetic_readiness("reg-test", "reg-p1")
        check_names = {c.check for c in result.checks}
        assert "study_exists" in check_names
        assert "data_classification" in check_names
        assert "participant_kind" in check_names
        study_check = next(c for c in result.checks if c.check == "study_exists")
        assert study_check.status == "passed"

    async def test_allocation_balanced(self, reg_db):
        now_iso = "2026-01-01T00:00:00+00:00"
        await reg_db.execute(
            "INSERT INTO studies (study_id, title, application_mode, data_classification, "
            "lifecycle_status, created_at, updated_at) VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?)",
            ("bal-test", "Balance", now_iso, now_iso),
        )
        await reg_db.commit()
        labels = set()
        for i in range(6):
            pid = f"bal-p{i}"
            await reg_db.execute(
                "INSERT OR IGNORE INTO participants (participant_id, study_id, pseudonym, participant_kind, "
                "eligibility_confirmed, created_at) VALUES (?, ?, ?, 'synthetic', 1, ?)",
                (pid, "bal-test", f"BAL-{i:03d}", now_iso),
            )
            await reg_db.commit()
            label, _ = await allocate_sequence("bal-test", pid, 42, db=reg_db)
            labels.add(label)
        assert len(labels) == 6
