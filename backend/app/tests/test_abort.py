"""Tests for abort propagation through the runtime stack."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.run_service import (
    RunTerminalError,
    check_abort_requested,
    create_run,
    finalize_abort,
    get_run,
    request_abort,
    update_run_phase,
)
from app.research.synthetic_orchestrator import run_synthetic_study
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def abort_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "abort.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        yield db
        await db.close()


async def _ensure_study(db, study_id, seed=42):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    existing = await (await db.execute(
        "SELECT study_id FROM studies WHERE study_id = ?", (study_id,)
    )).fetchone()
    if not existing:
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at) "
            "VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?, ?)",
            (study_id, f"Test {study_id}", seed, now, now),
        )
        await db.commit()


class TestAbortBeforeFirstSession:
    async def test_abort_before_any_session(self, abort_db):
        abort_flag = False

        async def abort_checker():
            return abort_flag

        abort_flag = True
        result = await run_synthetic_study(
            db=abort_db, study_id="abort-before",
            participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2,
            abort_check=abort_checker,
        )

        assert result["aborted"] is True
        assert result["sessions_completed"] == 0
        assert result["sessions_aborted"] == 0


class TestAbortBetweenSessions:
    async def test_abort_after_some_sessions(self, abort_db):
        call_count = 0

        async def abort_checker():
            nonlocal call_count
            call_count += 1
            return call_count > 25

        result = await run_synthetic_study(
            db=abort_db, study_id="abort-between",
            participant_count=6, seed=42,
            trials_per_session=2, windows_per_trial=2,
            abort_check=abort_checker,
        )

        assert result["aborted"] is True
        assert result["sessions_completed"] > 0
        assert result["sessions_completed"] < 18


class TestAbortDuringTrial:
    async def test_abort_mid_trial(self, abort_db):
        window_count = 0

        async def abort_checker():
            nonlocal window_count
            window_count += 1
            return window_count > 3

        result = await run_synthetic_study(
            db=abort_db, study_id="abort-trial",
            participant_count=2, seed=42,
            trials_per_session=3, windows_per_trial=3,
            abort_check=abort_checker,
        )

        assert result["aborted"] is True
        aborted_sessions = await (await abort_db.execute(
            "SELECT COUNT(*) as cnt FROM research_sessions "
            "WHERE study_id = 'abort-trial' AND status = 'aborted'"
        )).fetchone()
        assert aborted_sessions["cnt"] >= 1


class TestAbortDuringWindowLoop:
    async def test_abort_mid_window(self, abort_db):
        check_count = 0

        async def abort_checker():
            nonlocal check_count
            check_count += 1
            return check_count > 5

        result = await run_synthetic_study(
            db=abort_db, study_id="abort-window",
            participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=4,
            abort_check=abort_checker,
        )

        assert result["aborted"] is True


class TestDuplicateAbortRequest:
    async def test_duplicate_abort_idempotent(self, abort_db):
        await _ensure_study(abort_db, "dup-abort")
        run_row = await create_run(
            abort_db, "dup-abort", "dup-key",
            {"study_id": "dup-abort"}, seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]
        await update_run_phase(abort_db, run_id, "running", "running")

        r1 = await request_abort(abort_db, run_id)
        assert r1["status"] == "abort_requested"

        r2 = await request_abort(abort_db, run_id)
        assert r2["status"] == "abort_requested"


class TestAbortTerminalRun:
    async def test_abort_completed_run_fails(self, abort_db):
        await _ensure_study(abort_db, "term-abort")
        run_row = await create_run(
            abort_db, "term-abort", "term-key",
            {"study_id": "term-abort"}, seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]
        await update_run_phase(abort_db, run_id, "completed", "completed")

        with pytest.raises(RunTerminalError):
            await request_abort(abort_db, run_id)


class TestRestartAfterAbort:
    async def test_restart_reads_aborted_state(self, abort_db):
        await _ensure_study(abort_db, "restart-abort")
        run_row = await create_run(
            abort_db, "restart-abort", "restart-key",
            {"study_id": "restart-abort"}, seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]
        await update_run_phase(abort_db, run_id, "running", "running")
        await request_abort(abort_db, run_id)

        assert await check_abort_requested(abort_db, run_id) is True

        await finalize_abort(abort_db, run_id, 3, "abort_requested")
        run_after = await get_run(abort_db, run_id)
        assert run_after["status"] == "aborted"
        assert run_after["completed_sessions"] == 3


class TestAbortIntegration:
    async def test_full_abort_flow_with_run_service(self, abort_db):
        """Integration: create run, start orchestrator with abort, verify final state."""
        await _ensure_study(abort_db, "full-abort")
        run_row = await create_run(
            abort_db, "full-abort", "full-key",
            {"study_id": "full-abort", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]
        await update_run_phase(abort_db, run_id, "running", "running")

        call_count = 0

        async def abort_checker():
            nonlocal call_count
            call_count += 1
            return call_count > 8

        result = await run_synthetic_study(
            db=abort_db, study_id="full-abort",
            participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2,
            run_id=run_id,
            abort_check=abort_checker,
        )

        assert result["aborted"] is True
        assert result["sessions_completed"] > 0
        assert result["sessions_completed"] < 6

        await finalize_abort(abort_db, run_id, result["sessions_completed"], "abort_requested")
        final_run = await get_run(abort_db, run_id)
        assert final_run["status"] == "aborted"
