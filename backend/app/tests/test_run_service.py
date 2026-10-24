"""Tests for persistent run service — lifecycle, idempotency, abort, recovery."""
import tempfile

import aiosqlite
import pytest

from app.research.run_service import (
    RunConflictError,
    RunTerminalError,
    check_abort_requested,
    create_run,
    get_run,
    list_runs,
    mark_interrupted_on_startup,
    request_abort,
    update_run_phase,
    update_run_progress,
)
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def run_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        db_path = os.path.join(tmpdir, "test_runs.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        now = "2026-01-01T00:00:00+00:00"
        await db.execute(
            "INSERT INTO studies (study_id, title, application_mode, data_classification, "
            "lifecycle_status, created_at, updated_at) "
            "VALUES ('s1', 'Test', 'research', 'synthetic', 'active', ?, ?)",
            (now, now),
        )
        await db.commit()
        yield db
        await db.close()


class TestRunLifecycle:
    async def test_create_run(self, run_db):
        row = await create_run(run_db, "s1", "key-1", {"a": 1}, 42, 18)
        assert row["run_id"]
        assert row["status"] == "accepted"
        assert row["total_sessions"] == 18

    async def test_idempotent_same_input(self, run_db):
        r1 = await create_run(run_db, "s1", "key-2", {"b": 2}, 42, 6)
        r2 = await create_run(run_db, "s1", "key-2", {"b": 2}, 42, 6)
        assert r1["run_id"] == r2["run_id"]

    async def test_conflict_different_input(self, run_db):
        await create_run(run_db, "s1", "key-3", {"c": 3}, 42, 6)
        with pytest.raises(RunConflictError):
            await create_run(run_db, "s1", "key-3", {"c": 999}, 42, 6)

    async def test_phase_progression(self, run_db):
        row = await create_run(run_db, "s1", "key-4", {"d": 4}, 42, 6)
        run_id = row["run_id"]
        await update_run_phase(run_db, run_id, "running", "running")
        r = await get_run(run_db, run_id)
        assert r["status"] == "running"
        assert r["current_phase"] == "running"

    async def test_progress_update(self, run_db):
        row = await create_run(run_db, "s1", "key-5", {"e": 5}, 42, 6)
        await update_run_progress(run_db, row["run_id"], 3, 1)
        r = await get_run(run_db, row["run_id"])
        assert r["completed_sessions"] == 3
        assert r["failed_sessions"] == 1

    async def test_abort_flow(self, run_db):
        row = await create_run(run_db, "s1", "key-6", {"f": 6}, 42, 6)
        run_id = row["run_id"]
        result = await request_abort(run_db, run_id)
        assert result["status"] == "abort_requested"
        assert await check_abort_requested(run_db, run_id)

    async def test_abort_terminal_raises(self, run_db):
        row = await create_run(run_db, "s1", "key-7", {"g": 7}, 42, 6)
        await update_run_phase(run_db, row["run_id"], "completed", "done")
        with pytest.raises(RunTerminalError):
            await request_abort(run_db, row["run_id"])

    async def test_restart_recovery(self, run_db):
        r1 = await create_run(run_db, "s1", "key-8", {"h": 8}, 42, 6)
        await update_run_phase(run_db, r1["run_id"], "running", "running")
        count = await mark_interrupted_on_startup(run_db)
        assert count == 1
        r = await get_run(run_db, r1["run_id"])
        assert r["status"] == "interrupted"

    async def test_list_runs(self, run_db):
        await create_run(run_db, "s1", "key-9a", {"i": 1}, 42, 6)
        await create_run(run_db, "s1", "key-9b", {"j": 2}, 43, 6)
        rows = await list_runs(run_db)
        assert len(rows) == 2

    async def test_completed_run_not_interrupted(self, run_db):
        row = await create_run(run_db, "s1", "key-10", {"k": 10}, 42, 6)
        await update_run_phase(run_db, row["run_id"], "completed", "done")
        count = await mark_interrupted_on_startup(run_db)
        assert count == 0
