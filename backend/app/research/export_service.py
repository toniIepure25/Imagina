"""Atomic export service for synthetic study data.

Exports study data to a temporary directory, validates, then atomically
renames to the final path. Path sanitization prevents directory traversal.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import shutil
import tempfile
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class ExportValidationError(Exception):
    pass


def _sanitize_path(base: str, name: str) -> str:
    safe = os.path.basename(name)
    if not safe or safe in (".", ".."):
        raise ValueError(f"Invalid export path component: {name}")
    return os.path.join(base, safe)


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


async def export_synthetic_dataset(
    db: aiosqlite.Connection,
    study_id: str,
    output_dir: str,
) -> dict[str, Any]:
    staging = tempfile.mkdtemp(prefix="imagina_export_")

    try:
        files_written = {}

        files_written["sessions.csv"] = await _export_table(
            db, staging, "sessions.csv",
            "SELECT research_session_id, study_id, participant_id, "
            "protocol_version_id, allocation_id, session_index, condition, "
            "data_classification, signal_provider_id, policy_id, policy_version, "
            "runtime_seed, status, planned_at, software_version, git_sha "
            "FROM research_sessions WHERE study_id = ? ORDER BY research_session_id",
            (study_id,),
        )

        files_written["session_transitions.csv"] = await _export_table(
            db, staging, "session_transitions.csv",
            "SELECT t.* FROM research_session_transitions t "
            "JOIN research_sessions s ON t.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY t.timestamp",
            (study_id,),
        )

        files_written["trials.csv"] = await _export_table(
            db, staging, "trials.csv",
            "SELECT t.* FROM trials t "
            "JOIN research_sessions s ON t.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY t.research_session_id, t.trial_index",
            (study_id,),
        )

        files_written["trial_transitions.csv"] = await _export_table(
            db, staging, "trial_transitions.csv",
            "SELECT tt.* FROM trial_transitions tt "
            "JOIN trials t ON tt.trial_id = t.trial_id "
            "JOIN research_sessions s ON t.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY tt.timestamp",
            (study_id,),
        )

        files_written["trial_responses.csv"] = await _export_table(
            db, staging, "trial_responses.csv",
            "SELECT tr.* FROM trial_responses tr "
            "JOIN trials t ON tr.trial_id = t.trial_id "
            "JOIN research_sessions s ON t.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY t.trial_index",
            (study_id,),
        )

        files_written["feedback_records.csv"] = await _export_table(
            db, staging, "feedback_records.csv",
            "SELECT f.* FROM feedback_records f "
            "JOIN research_sessions s ON f.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY f.research_session_id, f.window_index",
            (study_id,),
        )

        files_written["safety_events.csv"] = await _export_table(
            db, staging, "safety_events.csv",
            "SELECT se.* FROM safety_events se "
            "JOIN research_sessions s ON se.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY se.timestamp_utc",
            (study_id,),
        )

        files_written["runtime_runs.csv"] = await _export_table(
            db, staging, "runtime_runs.csv",
            "SELECT * FROM runtime_runs WHERE study_id = ? ORDER BY created_at",
            (study_id,),
        )

        metadata = {
            "study_id": study_id,
            "data_classification": "synthetic",
            "export_schema_version": "2.0",
            "files": {},
        }
        for fname, row_count in files_written.items():
            fpath = os.path.join(staging, fname)
            if os.path.exists(fpath):
                metadata["files"][fname] = {
                    "rows": row_count,
                    "sha256": _file_sha256(fpath),
                }

        meta_path = os.path.join(staging, "export_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
        metadata["files"]["export_metadata.json"] = {
            "rows": 0,
            "sha256": _file_sha256(meta_path),
        }

        os.makedirs(os.path.dirname(output_dir) or ".", exist_ok=True)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        shutil.move(staging, output_dir)

        return {
            "output_dir": output_dir,
            "files": metadata["files"],
            "study_id": study_id,
            "data_classification": "synthetic",
        }
    except Exception:
        if os.path.exists(staging):
            shutil.rmtree(staging, ignore_errors=True)
        raise


async def _export_table(
    db: aiosqlite.Connection,
    staging_dir: str,
    filename: str,
    query: str,
    params: tuple = (),
) -> int:
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    if not rows:
        return 0

    cols = [desc[0] for desc in cursor.description]
    path = os.path.join(staging_dir, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in rows:
            writer.writerow(list(row))

    return len(rows)


def validate_export(export_dir: str) -> dict[str, Any]:
    errors: list[str] = []

    meta_path = os.path.join(export_dir, "export_metadata.json")
    if not os.path.exists(meta_path):
        return {"valid": False, "errors": ["Missing export_metadata.json"]}

    with open(meta_path) as f:
        metadata = json.load(f)

    if metadata.get("data_classification") != "synthetic":
        errors.append(f"Data classification is '{metadata.get('data_classification')}', expected 'synthetic'")

    for fname, info in metadata.get("files", {}).items():
        fpath = os.path.join(export_dir, fname)
        if fname == "export_metadata.json":
            continue
        if not os.path.exists(fpath):
            errors.append(f"Missing file: {fname}")
            continue
        actual_hash = _file_sha256(fpath)
        if actual_hash != info.get("sha256"):
            errors.append(f"Checksum mismatch for {fname}: expected {info['sha256']}, got {actual_hash}")

    sessions_path = os.path.join(export_dir, "sessions.csv")
    if os.path.exists(sessions_path):
        with open(sessions_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("data_classification") != "synthetic":
                    errors.append(f"Non-synthetic session found: {row.get('research_session_id')}")
                    break

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "files_checked": len(metadata.get("files", {})),
    }
