"""Tests for persistent session and trial state machines."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.state_machines import (
    ConcurrencyConflictError,
    InvalidTransitionError,
    TerminalStateError,
    transition_session,
    transition_trial,
)
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def sm_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sm_test.db")
        monkeypatch.setattr("app.storage.database.DB_PATH", path)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        await db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
            "VALUES ('p1', 's1', 'A', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO sequence_allocations "
            "(allocation_id, study_id, participant_id, sequence_id, sequence_label, allocated_at) "
            "VALUES ('a1', 's1', 'p1', 'ABC', 'ABC', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO research_sessions "
            "(research_session_id, study_id, participant_id, protocol_version_id, "
            "allocation_id, session_index, condition, data_classification, "
            "signal_provider_id, policy_id, policy_version, runtime_seed, "
            "status, state_version, planned_at, software_version) "
            "VALUES ('rs1', 's1', 'p1', 'pv1', 'a1', 0, 'adaptive', 'synthetic', "
            "'simulated.default', 'adaptive', '1.0', 42, 'planned', 0, '2026-01-01', '0.5.0')"
        )
        await db.execute(
            "INSERT INTO trials (trial_id, research_session_id, trial_index, "
            "stimulus_id, status, state_version, planned_at) "
            "VALUES ('t1', 'rs1', 0, 'corridor_default', 'planned', 0, '2026-01-01')"
        )
        await db.commit()
        yield db
        await db.close()


class TestSessionTransitions:
    async def test_planned_to_ready(self, sm_db):
        v = await transition_session(sm_db, "rs1", "planned", 0, "ready")
        await sm_db.commit()
        assert v == 1
        row = await (await sm_db.execute(
            "SELECT status, state_version FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "ready"
        assert row["state_version"] == 1

    async def test_planned_to_running_invalid(self, sm_db):
        with pytest.raises(InvalidTransitionError):
            await transition_session(sm_db, "rs1", "planned", 0, "running")

    async def test_full_lifecycle(self, sm_db):
        v = await transition_session(sm_db, "rs1", "planned", 0, "ready")
        v = await transition_session(sm_db, "rs1", "ready", v, "running")
        v = await transition_session(sm_db, "rs1", "running", v, "completed")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT status, state_version, ended_at FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "completed"
        assert row["state_version"] == 3
        assert row["ended_at"] is not None

    async def test_terminal_state_immutable(self, sm_db):
        await transition_session(sm_db, "rs1", "planned", 0, "ready")
        await transition_session(sm_db, "rs1", "ready", 1, "running")
        await transition_session(sm_db, "rs1", "running", 2, "completed")
        await sm_db.commit()
        with pytest.raises(TerminalStateError):
            await transition_session(sm_db, "rs1", "completed", 3, "running")

    async def test_stale_version_raises(self, sm_db):
        await transition_session(sm_db, "rs1", "planned", 0, "ready")
        await sm_db.commit()
        with pytest.raises(ConcurrencyConflictError):
            await transition_session(sm_db, "rs1", "planned", 0, "aborted")

    async def test_abort_from_planned(self, sm_db):
        await transition_session(sm_db, "rs1", "planned", 0, "aborted", reason_code="operator_cancel")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT status, terminal_reason FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "aborted"
        assert row["terminal_reason"] == "operator_cancel"

    async def test_safety_stop(self, sm_db):
        await transition_session(sm_db, "rs1", "planned", 0, "ready")
        await transition_session(sm_db, "rs1", "ready", 1, "running")
        await transition_session(sm_db, "rs1", "running", 2, "safety_stopped", reason_code="fatigue_high")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT status, terminal_reason FROM research_sessions WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["status"] == "safety_stopped"
        assert row["terminal_reason"] == "fatigue_high"

    async def test_idempotency(self, sm_db):
        v1 = await transition_session(
            sm_db, "rs1", "planned", 0, "ready", idempotency_key="key-1"
        )
        await sm_db.commit()
        v2 = await transition_session(
            sm_db, "rs1", "planned", 0, "ready", idempotency_key="key-1"
        )
        assert v1 == v2

    async def test_transition_persisted(self, sm_db):
        await transition_session(sm_db, "rs1", "planned", 0, "ready", actor="test")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT from_status, to_status, actor FROM research_session_transitions "
            "WHERE research_session_id='rs1'"
        )).fetchone()
        assert row["from_status"] == "planned"
        assert row["to_status"] == "ready"
        assert row["actor"] == "test"


class TestTrialTransitions:
    async def test_planned_to_ready(self, sm_db):
        v = await transition_trial(sm_db, "t1", "planned", 0, "ready")
        await sm_db.commit()
        assert v == 1

    async def test_full_lifecycle(self, sm_db):
        await transition_trial(sm_db, "t1", "planned", 0, "ready")
        await transition_trial(sm_db, "t1", "ready", 1, "running")
        await transition_trial(sm_db, "t1", "running", 2, "completed")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT status, state_version FROM trials WHERE trial_id='t1'"
        )).fetchone()
        assert row["status"] == "completed"
        assert row["state_version"] == 3

    async def test_terminal_immutable(self, sm_db):
        await transition_trial(sm_db, "t1", "planned", 0, "ready")
        await transition_trial(sm_db, "t1", "ready", 1, "running")
        await transition_trial(sm_db, "t1", "running", 2, "completed")
        await sm_db.commit()
        with pytest.raises(TerminalStateError):
            await transition_trial(sm_db, "t1", "completed", 3, "running")

    async def test_invalid_transition(self, sm_db):
        with pytest.raises(InvalidTransitionError):
            await transition_trial(sm_db, "t1", "planned", 0, "running")

    async def test_safety_stop_trial(self, sm_db):
        await transition_trial(sm_db, "t1", "planned", 0, "ready")
        await transition_trial(sm_db, "t1", "ready", 1, "running")
        await transition_trial(sm_db, "t1", "running", 2, "safety_stopped", reason_code="fatigue")
        await sm_db.commit()
        row = await (await sm_db.execute(
            "SELECT status, terminal_reason FROM trials WHERE trial_id='t1'"
        )).fetchone()
        assert row["status"] == "safety_stopped"
        assert row["terminal_reason"] == "fatigue"
