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
from app.storage.migration_runner import run_migrations


async def _make_db(tmpdir, study_id, seed=42, participant_count=2):
    db_path = os.path.join(tmpdir, f"{study_id}.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    await run_synthetic_study(
        db=db, study_id=study_id,
        participant_count=participant_count, seed=seed,
        trials_per_session=2, windows_per_trial=2,
    )
    return db


class TestAtomicExport:
    async def test_export_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "export-test")
            export_dir = os.path.join(tmpdir, "export")
            try:
                result = await export_synthetic_dataset(db, "export-test", export_dir)
                assert os.path.isdir(export_dir)
                assert "sessions.csv" in result["files"]
                assert "feedback_records.csv" in result["files"]
                assert result["data_classification"] == "synthetic"
            finally:
                await db.close()

    async def test_export_metadata_has_checksums(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "cksum-test")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "cksum-test", export_dir)
                meta_path = os.path.join(export_dir, "export_metadata.json")
                with open(meta_path) as f:
                    metadata = json.load(f)
                for info in metadata["files"].values():
                    assert "sha256" in info
                    assert len(info["sha256"]) == 64
            finally:
                await db.close()

    async def test_export_idempotent_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "idem-test")
            export_dir = os.path.join(tmpdir, "export")
            try:
                r1 = await export_synthetic_dataset(db, "idem-test", export_dir)
                r2 = await export_synthetic_dataset(db, "idem-test", export_dir)
                assert r1["files"].keys() == r2["files"].keys()
            finally:
                await db.close()


class TestExportValidator:
    async def test_validates_clean_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "val-test")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "val-test", export_dir)
                result = validate_export(export_dir)
                assert result["valid"] is True
                assert result["files_checked"] > 0
            finally:
                await db.close()

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_export(tmpdir)
            assert result["valid"] is False
            assert "Missing export_metadata.json" in result["errors"]

    async def test_tampered_file_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "tamp-test")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "tamp-test", export_dir)
                sessions_path = os.path.join(export_dir, "sessions.csv")
                if os.path.exists(sessions_path):
                    with open(sessions_path, "a") as f:
                        f.write("tampered_row\n")
                    result = validate_export(export_dir)
                    assert result["valid"] is False
                    assert any("Checksum mismatch" in e for e in result["errors"])
            finally:
                await db.close()
