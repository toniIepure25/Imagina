"""Tests for synthetic study orchestration and export."""
import json
import os
import tempfile

import aiosqlite
import pytest

from app.research.synthetic_orchestrator import run_synthetic_study
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def orch_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = await aiosqlite.connect(db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        yield db, tmpdir
        await db.close()


class TestSyntheticOrchestration:
    async def test_full_workflow(self, orch_db):
        db, tmpdir = orch_db
        export_dir = os.path.join(tmpdir, "export")

        result = await run_synthetic_study(
            db=db,
            study_id="test-synth-001",
            participant_count=6,
            seed=42,
            trials_per_session=3,
            windows_per_trial=2,
            export_dir=export_dir,
        )

        assert result["study_id"] == "test-synth-001"
        assert result["participants"] == 6
        assert result["sessions_completed"] == 18
        assert result["sessions_failed"] == 0

    async def test_export_files_created(self, orch_db):
        db, tmpdir = orch_db
        export_dir = os.path.join(tmpdir, "export")

        await run_synthetic_study(
            db=db,
            study_id="test-export-001",
            participant_count=3,
            seed=123,
            trials_per_session=2,
            windows_per_trial=2,
            export_dir=export_dir,
        )

        expected_files = [
            "metadata.json", "sessions.csv",
            "trials.csv", "trial_responses.csv", "feedback_records.csv",
        ]
        for fname in expected_files:
            assert os.path.exists(os.path.join(export_dir, fname)), f"Missing: {fname}"

    async def test_export_metadata_synthetic(self, orch_db):
        db, tmpdir = orch_db
        export_dir = os.path.join(tmpdir, "export")

        await run_synthetic_study(
            db=db,
            study_id="test-meta-001",
            participant_count=3,
            seed=7,
            trials_per_session=2,
            windows_per_trial=2,
            export_dir=export_dir,
        )

        with open(os.path.join(export_dir, "metadata.json")) as f:
            meta = json.load(f)
        assert meta["data_classification"] == "synthetic"

    async def test_balanced_conditions(self, orch_db):
        db, _ = orch_db

        await run_synthetic_study(
            db=db,
            study_id="test-balance",
            participant_count=6,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
        )

        cursor = await db.execute(
            "SELECT condition, COUNT(*) as cnt FROM research_sessions "
            "WHERE study_id='test-balance' GROUP BY condition"
        )
        rows = await cursor.fetchall()

        condition_counts = {r["condition"]: r["cnt"] for r in rows}
        assert condition_counts.get("adaptive", 0) == 6
        assert condition_counts.get("fixed", 0) == 6
        assert condition_counts.get("yoked", 0) == 6

    async def test_deterministic_rerun(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1_path = os.path.join(tmpdir, "s1.db")
            db2_path = os.path.join(tmpdir, "s2.db")

            db1 = await aiosqlite.connect(db1_path)
            db1.row_factory = aiosqlite.Row
            await db1.execute("PRAGMA foreign_keys = ON")
            await run_migrations(db1)

            db2 = await aiosqlite.connect(db2_path)
            db2.row_factory = aiosqlite.Row
            await db2.execute("PRAGMA foreign_keys = ON")
            await run_migrations(db2)

            try:
                r1 = await run_synthetic_study(
                    db=db1, study_id="det-test", participant_count=3,
                    seed=99, trials_per_session=2, windows_per_trial=2,
                )
                r2 = await run_synthetic_study(
                    db=db2, study_id="det-test", participant_count=3,
                    seed=99, trials_per_session=2, windows_per_trial=2,
                )
                assert r1["sessions_completed"] == r2["sessions_completed"]
            finally:
                await db1.close()
                await db2.close()

    async def test_manifests_created(self, orch_db):
        db, _ = orch_db

        await run_synthetic_study(
            db=db,
            study_id="mfst-test",
            participant_count=2,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
        )

        cursor = await db.execute("SELECT COUNT(*) as cnt FROM session_manifests")
        row = await cursor.fetchone()
        assert row["cnt"] == 6

    async def test_typed_errors_reported(self, orch_db):
        db, _ = orch_db

        result = await run_synthetic_study(
            db=db,
            study_id="err-test",
            participant_count=2,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
        )

        assert isinstance(result.get("errors"), list)

    async def test_run_id_passed_through(self, orch_db):
        db, _ = orch_db

        result = await run_synthetic_study(
            db=db,
            study_id="run-id-test",
            participant_count=2,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
            run_id="explicit-run-001",
        )

        assert result["run_id"] == "explicit-run-001"
        row = await (await db.execute(
            "SELECT * FROM research_sessions WHERE study_id = ?",
            ("run-id-test",),
        )).fetchall()
        assert len(row) == 6

    async def test_runtime_runs_in_same_db_when_no_run_id(self, orch_db):
        db, _ = orch_db

        result = await run_synthetic_study(
            db=db,
            study_id="same-db-test",
            participant_count=2,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
        )

        run_row = await (await db.execute(
            "SELECT * FROM runtime_runs WHERE run_id = ?",
            (result["run_id"],),
        )).fetchone()
        assert run_row is not None
        assert run_row["study_id"] == "same-db-test"

        sessions = await (await db.execute(
            "SELECT * FROM research_sessions WHERE study_id = ?",
            ("same-db-test",),
        )).fetchall()
        assert len(sessions) == 6

    async def test_unified_db_sessions_and_runs_coexist(self, orch_db):
        """Integration: run with run_id, verify sessions + run metadata in same DB."""
        db, _ = orch_db
        from datetime import datetime, timezone

        from app.research.run_service import create_run

        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO studies "
            "(study_id, title, application_mode, data_classification, lifecycle_status, "
            "study_seed, created_at, updated_at) "
            "VALUES (?, ?, 'research', 'synthetic', 'active', 42, ?, ?)",
            ("unified-test", "Synthetic Study unified-test", now, now),
        )
        await db.commit()

        run_row = await create_run(
            db, "unified-test", "idem-001",
            {"study_id": "unified-test", "participant_count": 2, "seed": 42,
             "trials_per_session": 2, "windows_per_trial": 2},
            seed=42, total_sessions=6,
        )
        run_id = run_row["run_id"]

        result = await run_synthetic_study(
            db=db,
            study_id="unified-test",
            participant_count=2,
            seed=42,
            trials_per_session=2,
            windows_per_trial=2,
            run_id=run_id,
        )

        assert result["sessions_completed"] == 6

        run_check = await (await db.execute(
            "SELECT * FROM runtime_runs WHERE run_id = ?", (run_id,)
        )).fetchone()
        assert run_check is not None

        sessions = await (await db.execute(
            "SELECT research_session_id, status FROM research_sessions WHERE study_id = ?",
            ("unified-test",),
        )).fetchall()
        assert len(sessions) == 6
        for s in sessions:
            assert s["status"] in ("completed", "safety_stopped")
