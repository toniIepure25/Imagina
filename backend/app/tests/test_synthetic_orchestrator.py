"""Tests for synthetic study orchestration and export."""
import os
import tempfile

from app.research.synthetic_orchestrator import run_synthetic_study


class TestSyntheticOrchestration:
    async def test_full_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "synth.db")
            export_dir = os.path.join(tmpdir, "export")

            result = await run_synthetic_study(
                db_path=db_path,
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

    async def test_export_files_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "synth.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path,
                study_id="test-export-001",
                participant_count=3,
                seed=123,
                trials_per_session=2,
                windows_per_trial=2,
                export_dir=export_dir,
            )

            expected_files = [
                "metadata.json", "study.json", "protocol.json",
                "participants.csv", "allocations.csv", "sessions.csv",
                "trials.csv", "trial_responses.csv", "feedback_records.csv",
                "checksums.sha256",
            ]
            for fname in expected_files:
                assert os.path.exists(os.path.join(export_dir, fname)), f"Missing: {fname}"

    async def test_export_metadata_synthetic(self):
        import json
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "synth.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path,
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
            assert "not human-subject" in meta["disclaimer"]

    async def test_balanced_conditions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "synth.db")

            await run_synthetic_study(
                db_path=db_path,
                study_id="test-balance",
                participant_count=6,
                seed=42,
                trials_per_session=2,
                windows_per_trial=2,
            )

            import aiosqlite
            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT condition, COUNT(*) as cnt FROM research_sessions "
                "WHERE study_id='test-balance' GROUP BY condition"
            )
            rows = await cursor.fetchall()
            await db.close()

            condition_counts = {r["condition"]: r["cnt"] for r in rows}
            assert condition_counts.get("adaptive", 0) == 6
            assert condition_counts.get("fixed", 0) == 6
            assert condition_counts.get("yoked", 0) == 6

    async def test_deterministic_rerun(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = os.path.join(tmpdir, "s1.db")
            db2 = os.path.join(tmpdir, "s2.db")

            r1 = await run_synthetic_study(
                db_path=db1, study_id="det-test", participant_count=3,
                seed=99, trials_per_session=2, windows_per_trial=2,
            )
            r2 = await run_synthetic_study(
                db_path=db2, study_id="det-test", participant_count=3,
                seed=99, trials_per_session=2, windows_per_trial=2,
            )

            assert r1["sessions_completed"] == r2["sessions_completed"]
