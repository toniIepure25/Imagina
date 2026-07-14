"""Tests for atomic export service and validator."""
import json
import os
import tempfile

import aiosqlite
import pytest

from app.research.export_service import (
    ExportExistsError,
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
                assert "package_hash" in result
                assert "export_id" in result
            finally:
                await db.close()

    async def test_export_includes_manifests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "manifest-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                result = await export_synthetic_dataset(db, "manifest-export", export_dir)
                assert "manifests/" in result["files"]
                assert result["files"]["manifests/"]["count"] == 6
                manifests_dir = os.path.join(export_dir, "manifests")
                assert os.path.isdir(manifests_dir)
                assert len(os.listdir(manifests_dir)) == 6
            finally:
                await db.close()

    async def test_export_includes_seals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "seal-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                result = await export_synthetic_dataset(db, "seal-export", export_dir)
                assert "completion_seals/" in result["files"]
                seals_dir = os.path.join(export_dir, "completion_seals")
                assert os.path.isdir(seals_dir)
            finally:
                await db.close()

    async def test_export_includes_yoked_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "yoked-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                result = await export_synthetic_dataset(db, "yoked-export", export_dir)
                assert "yoked_library.json" in result["files"]
                assert os.path.exists(os.path.join(export_dir, "yoked_library.json"))
            finally:
                await db.close()

    async def test_export_has_checksums(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "cksum-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "cksum-export", export_dir)
                checksums_path = os.path.join(export_dir, "checksums.sha256")
                assert os.path.exists(checksums_path)
                with open(checksums_path) as f:
                    lines = f.readlines()
                assert len(lines) > 0
            finally:
                await db.close()

    async def test_export_has_metadata_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "meta-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "meta-export", export_dir)
                meta_path = os.path.join(export_dir, "metadata.json")
                assert os.path.exists(meta_path)
                with open(meta_path) as f:
                    meta = json.load(f)
                assert meta["data_classification"] == "synthetic"
                assert meta["export_schema_version"] == "3.1"
            finally:
                await db.close()

    async def test_no_overwrite_without_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "noover-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                await export_synthetic_dataset(db, "noover-export", export_dir)
                with pytest.raises(ExportExistsError):
                    await export_synthetic_dataset(db, "noover-export", export_dir)
            finally:
                await db.close()

    async def test_overwrite_with_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "over-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                r1 = await export_synthetic_dataset(db, "over-export", export_dir)
                r2 = await export_synthetic_dataset(
                    db, "over-export", export_dir, allow_overwrite=True
                )
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
                    assert any("checksum" in e.lower() or "Checksum" in e for e in result["errors"])
            finally:
                await db.close()

    async def test_export_persists_in_export_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_db(tmpdir, "persist-export")
            export_dir = os.path.join(tmpdir, "export")
            try:
                result = await export_synthetic_dataset(db, "persist-export", export_dir)
                row = await (await db.execute(
                    "SELECT * FROM export_runs WHERE export_id = ?",
                    (result["export_id"],),
                )).fetchone()
                assert row is not None
                assert row["study_id"] == "persist-export"
                assert row["data_classification"] == "synthetic"
            finally:
                await db.close()
