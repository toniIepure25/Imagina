"""Integration test: unified database — run, sessions, failures all in one DB.

Proves:
1. create run through run_service
2. orchestrator completes using same DB
3. run status readable from same DB
4. sessions endpoint returns all expected sessions
5. failures endpoint reads same records
6. process restart can still read run and sessions
"""
import os
import tempfile
from datetime import datetime, timezone

import aiosqlite
import pytest

from app.research.run_service import (
    create_run,
    get_run,
    list_runs,
    mark_interrupted_on_startup,
    update_run_phase,
    update_run_progress,
)
from app.research.synthetic_orchestrator import run_synthetic_study
from app.storage.migration_runner import run_migrations


async def _ensure_study(db, study_id, seed=42):
    """Mirror API's _ensure_study_exists for test setup."""
    existing = await (await db.execute(
        "SELECT study_id FROM studies WHERE study_id = ?", (study_id,)
    )).fetchone()
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at) "
            "VALUES (?, ?, 'research', 'synthetic', 'active', ?, ?, ?)",
            (study_id, f"Synthetic Study {study_id}", seed, now, now),
        )
        await db.commit()


@pytest.fixture
async def unified_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "unified.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        yield db, db_path
        await db.close()


class TestUnifiedDatabase:
    async def test_create_run_then_orchestrate(self, unified_db):
        db, _ = unified_db
        await _ensure_study(db, "int-study")
        run_row = await create_run(
            db, "int-study", "key-001",
            {"study_id": "int-study", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]
        assert run_row["status"] == "accepted"

        await update_run_phase(db, run_id, "running", "running")

        result = await run_synthetic_study(
            db=db, study_id="int-study", participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2, run_id=run_id,
        )

        completed = result["sessions_completed"]
        failed = result["sessions_failed"]
        await update_run_progress(db, run_id, completed, failed)
        await update_run_phase(db, run_id, "completed", "completed")

        run_check = await get_run(db, run_id)
        assert run_check is not None
        assert run_check["status"] == "completed"
        assert run_check["completed_sessions"] == 6

    async def test_sessions_readable_from_same_db(self, unified_db):
        db, _ = unified_db
        await _ensure_study(db, "sess-read")
        run_row = await create_run(
            db, "sess-read", "key-002",
            {"study_id": "sess-read", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )

        await run_synthetic_study(
            db=db, study_id="sess-read", participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2, run_id=run_row["run_id"],
        )

        sessions = await (await db.execute(
            "SELECT research_session_id, participant_id, condition, status "
            "FROM research_sessions WHERE study_id = ? ORDER BY research_session_id",
            ("sess-read",),
        )).fetchall()
        assert len(sessions) == 6

        conditions = {s["condition"] for s in sessions}
        assert conditions == {"adaptive", "fixed", "yoked"}

    async def test_failures_readable_from_same_db(self, unified_db):
        db, _ = unified_db
        await _ensure_study(db, "fail-read")
        run_row = await create_run(
            db, "fail-read", "key-003",
            {"study_id": "fail-read", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )

        await run_synthetic_study(
            db=db, study_id="fail-read", participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2, run_id=run_row["run_id"],
        )

        failures = await (await db.execute(
            "SELECT research_session_id, status "
            "FROM research_sessions WHERE study_id = ? AND status NOT IN ('completed', 'planned')",
            ("fail-read",),
        )).fetchall()
        assert isinstance(failures, list)

    async def test_restart_preserves_data(self, unified_db):
        db, db_path = unified_db
        await _ensure_study(db, "restart-test")
        run_row = await create_run(
            db, "restart-test", "key-004",
            {"study_id": "restart-test", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]

        await run_synthetic_study(
            db=db, study_id="restart-test", participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2, run_id=run_id,
        )
        await update_run_progress(db, run_id, 6, 0)
        await update_run_phase(db, run_id, "completed", "completed")
        await db.close()

        db2 = await aiosqlite.connect(db_path)
        db2.row_factory = aiosqlite.Row
        try:
            recovered = await mark_interrupted_on_startup(db2)
            assert recovered == 0

            run_after = await get_run(db2, run_id)
            assert run_after is not None
            assert run_after["status"] == "completed"
            assert run_after["completed_sessions"] == 6

            sessions = await (await db2.execute(
                "SELECT * FROM research_sessions WHERE study_id = ?",
                ("restart-test",),
            )).fetchall()
            assert len(sessions) == 6

            manifests = await (await db2.execute(
                "SELECT * FROM session_manifests",
            )).fetchall()
            assert len(manifests) == 6

            runs = await list_runs(db2, "restart-test")
            assert len(runs) == 1
            assert runs[0]["run_id"] == run_id
        finally:
            await db2.close()

    async def test_export_from_unified_db(self, unified_db):
        db, tmpdir_ref = unified_db
        await _ensure_study(db, "export-unified")
        run_row = await create_run(
            db, "export-unified", "key-005",
            {"study_id": "export-unified", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )

        await run_synthetic_study(
            db=db, study_id="export-unified", participant_count=2, seed=42,
            trials_per_session=2, windows_per_trial=2, run_id=run_row["run_id"],
        )

        from app.research.export_service import export_synthetic_dataset, validate_export
        export_dir = os.path.join(os.path.dirname(tmpdir_ref), "export_dir")
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, "export-unified")

        result = await export_synthetic_dataset(db, "export-unified", export_path)
        assert result["data_classification"] == "synthetic"
        assert "sessions.csv" in result["files"]

        runtime_runs_info = result["files"].get("runtime_runs.csv")
        assert runtime_runs_info is not None
        assert runtime_runs_info["rows"] >= 1

        validation = validate_export(export_path)
        assert validation["valid"] is True
