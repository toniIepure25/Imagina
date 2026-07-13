"""Tests for atomic export service and validator."""
import json
import os
import tempfile

import aiosqlite

from app.research.export_service import (
    export_synthetic_dataset,
    validate_export,
)
from app.research.synthetic_orchestrator import run_synthetic_study


class TestAtomicExport:
    async def test_export_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "study.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path, study_id="export-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
                export_dir=None,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row

            result = await export_synthetic_dataset(db, "export-test", export_dir)
            await db.close()

            assert os.path.isdir(export_dir)
            assert "sessions.csv" in result["files"]
            assert "feedback_records.csv" in result["files"]
            assert result["data_classification"] == "synthetic"

    async def test_export_metadata_has_checksums(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "study.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path, study_id="cksum-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            await export_synthetic_dataset(db, "cksum-test", export_dir)
            await db.close()

            meta_path = os.path.join(export_dir, "export_metadata.json")
            with open(meta_path) as f:
                metadata = json.load(f)

            for info in metadata["files"].values():
                assert "sha256" in info
                assert len(info["sha256"]) == 64

    async def test_export_idempotent_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "study.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path, study_id="idem-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            r1 = await export_synthetic_dataset(db, "idem-test", export_dir)
            r2 = await export_synthetic_dataset(db, "idem-test", export_dir)
            await db.close()

            assert r1["files"].keys() == r2["files"].keys()


class TestExportValidator:
    async def test_validates_clean_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "study.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path, study_id="val-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            await export_synthetic_dataset(db, "val-test", export_dir)
            await db.close()

            result = validate_export(export_dir)
            assert result["valid"] is True
            assert result["files_checked"] > 0

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_export(tmpdir)
            assert result["valid"] is False
            assert "Missing export_metadata.json" in result["errors"]

    async def test_tampered_file_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "study.db")
            export_dir = os.path.join(tmpdir, "export")

            await run_synthetic_study(
                db_path=db_path, study_id="tamp-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            await export_synthetic_dataset(db, "tamp-test", export_dir)
            await db.close()

            sessions_path = os.path.join(export_dir, "sessions.csv")
            if os.path.exists(sessions_path):
                with open(sessions_path, "a") as f:
                    f.write("tampered_row\n")

                result = validate_export(export_dir)
                assert result["valid"] is False
                assert any("Checksum mismatch" in e for e in result["errors"])
