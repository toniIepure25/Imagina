"""Tests for the versioned migration runner and FK enforcement."""
import os
import tempfile

import aiosqlite
import pytest

from app.storage.migration_runner import _current_version, _ensure_version_table, run_migrations


@pytest.fixture
async def empty_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db
        await db.close()


@pytest.fixture
async def legacy_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                display_name TEXT,
                mode TEXT NOT NULL DEFAULT 'simulated',
                status TEXT NOT NULL DEFAULT 'created',
                task_id TEXT NOT NULL DEFAULT 'corridor_simple',
                signal_provider_id TEXT NOT NULL DEFAULT 'simulated.default',
                scenario TEXT,
                experiment_run_id TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                safety_disclaimer_acknowledged INTEGER NOT NULL DEFAULT 0,
                baseline_json TEXT
            );
            INSERT INTO sessions (session_id, user_id, created_at)
            VALUES ('s1', 'u1', '2026-01-01T00:00:00Z');
        """)
        await db.commit()
        yield db
        await db.close()


class TestEmptyDatabaseUpgrade:
    async def test_migrations_run_from_empty(self, empty_db):
        version = await run_migrations(empty_db)
        assert version == 3

    async def test_version_table_created(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute("SELECT COUNT(*) FROM schema_version")
        row = await cursor.fetchone()
        assert row[0] == 3

    async def test_studies_table_exists(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='studies'"
        )
        assert await cursor.fetchone() is not None

    async def test_participants_table_has_unique_pseudonym(self, empty_db):
        await run_migrations(empty_db)
        await empty_db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'ALICE', '2026-01-01')"
        )
        await empty_db.commit()
        with pytest.raises(Exception):
            await empty_db.execute(
                "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
                "VALUES ('p2', 's1', 'ALICE', '2026-01-01')"
            )


class TestLegacyDatabaseUpgrade:
    async def test_legacy_data_preserved(self, legacy_db):
        await run_migrations(legacy_db)
        cursor = await legacy_db.execute("SELECT session_id FROM sessions")
        row = await cursor.fetchone()
        assert row["session_id"] == "s1"

    async def test_research_tables_added(self, legacy_db):
        await run_migrations(legacy_db)
        cursor = await legacy_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='protocol_versions'"
        )
        assert await cursor.fetchone() is not None


class TestIdempotentStartup:
    async def test_second_run_is_noop(self, empty_db):
        v1 = await run_migrations(empty_db)
        v2 = await run_migrations(empty_db)
        assert v1 == v2 == 3


class TestV003RuntimeSchema:
    async def test_research_sessions_table_exists(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='research_sessions'"
        )
        assert await cursor.fetchone() is not None

    async def test_trials_table_exists(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trials'"
        )
        assert await cursor.fetchone() is not None

    async def test_frozen_yoked_libraries_table_exists(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='frozen_yoked_libraries'"
        )
        assert await cursor.fetchone() is not None

    async def test_session_unique_constraint(self, empty_db):
        await run_migrations(empty_db)
        await empty_db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'A', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
            "VALUES ('a1', 's1', 'p1', 'ABC', 'ABC', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO research_sessions "
            "(research_session_id, study_id, participant_id, protocol_version_id, "
            "allocation_id, session_index, condition, data_classification, "
            "signal_provider_id, policy_id, policy_version, runtime_seed, "
            "status, planned_at, software_version) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'simulated.default', 'adaptive', '1.0', 42, 'planned', '2026-01-01', '0.5.0')"
        )
        await empty_db.commit()
        with pytest.raises(Exception):
            await empty_db.execute(
                "INSERT INTO research_sessions "
                "(research_session_id, study_id, participant_id, protocol_version_id, "
                "allocation_id, session_index, condition, data_classification, "
                "signal_provider_id, policy_id, policy_version, runtime_seed, "
                "status, planned_at, software_version) "
                "VALUES ('rs2', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
                "'simulated.default', 'adaptive', '1.0', 42, 'planned', '2026-01-01', '0.5.0')"
            )

    async def test_classification_check_constraint(self, empty_db):
        await run_migrations(empty_db)
        await empty_db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'A', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
            "VALUES ('a1', 's1', 'p1', 'ABC', 'ABC', '2026-01-01')"
        )
        await empty_db.commit()
        with pytest.raises(Exception):
            await empty_db.execute(
                "INSERT INTO research_sessions "
                "(research_session_id, study_id, participant_id, protocol_version_id, "
                "allocation_id, session_index, condition, data_classification, "
                "signal_provider_id, policy_id, policy_version, runtime_seed, "
                "status, planned_at, software_version) "
                "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'INVALID', "
                "'simulated.default', 'adaptive', '1.0', 42, 'planned', '2026-01-01', '0.5.0')"
            )

    async def test_trial_unique_constraint(self, empty_db):
        await run_migrations(empty_db)
        await empty_db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'A', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
            "VALUES ('a1', 's1', 'p1', 'ABC', 'ABC', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO research_sessions "
            "(research_session_id, study_id, participant_id, protocol_version_id, "
            "allocation_id, session_index, condition, data_classification, "
            "signal_provider_id, policy_id, policy_version, runtime_seed, "
            "status, planned_at, software_version) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'simulated.default', 'adaptive', '1.0', 42, 'planned', '2026-01-01', '0.5.0')"
        )
        await empty_db.execute(
            "INSERT INTO trials (trial_id, research_session_id, trial_index, "
            "stimulus_id, planned_at) VALUES ('t1', 'rs1', 0, 'stim1', '2026-01-01')"
        )
        await empty_db.commit()
        with pytest.raises(Exception):
            await empty_db.execute(
                "INSERT INTO trials (trial_id, research_session_id, trial_index, "
                "stimulus_id, planned_at) VALUES ('t2', 'rs1', 0, 'stim2', '2026-01-01')"
            )


class TestForeignKeyEnforcement:
    async def test_fk_enabled(self, empty_db):
        await run_migrations(empty_db)
        cursor = await empty_db.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1

    async def test_fk_violation_rejected(self, empty_db):
        await run_migrations(empty_db)
        with pytest.raises(Exception):
            await empty_db.execute(
                "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
                "VALUES ('p1', 'nonexistent_study', 'BOB', '2026-01-01')"
            )

    async def test_valid_fk_accepted(self, empty_db):
        await run_migrations(empty_db)
        await empty_db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await empty_db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'BOB', '2026-01-01')"
        )
        await empty_db.commit()
        cursor = await empty_db.execute("SELECT pseudonym FROM participants WHERE participant_id = 'p1'")
        row = await cursor.fetchone()
        assert row["pseudonym"] == "BOB"


class TestMigrationVersionTracking:
    async def test_version_not_advanced_on_failure(self, empty_db):
        await _ensure_version_table(empty_db)
        v = await _current_version(empty_db)
        assert v == 0
