"""Atomic export service for synthetic study data.

Exports study data to a sibling staging directory, validates the complete
package, then atomically renames to the final path. Persists export
records with granular status and validation columns.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

EXPORT_SCHEMA_VERSION = "3.1"


class ExportValidationError(Exception):
    pass


class ExportExistsError(Exception):
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


def _write_json(staging: str, filename: str, data: Any) -> str:
    path = os.path.join(staging, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True, default=str)
    return path


def _compute_package_hash(checksums: dict[str, str]) -> str:
    canonical = "\n".join(f"{checksums[k]}  {k}" for k in sorted(checksums.keys()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def export_synthetic_dataset(
    db: aiosqlite.Connection,
    study_id: str,
    output_dir: str,
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    if os.path.exists(output_dir) and not allow_overwrite:
        raise ExportExistsError(
            f"Export directory already exists: {output_dir}. Use allow_overwrite=True to replace."
        )

    parent = os.path.dirname(output_dir) or "."
    os.makedirs(parent, exist_ok=True)
    staging = tempfile.mkdtemp(dir=parent, prefix=".imagina_export_staging_")
    export_id = str(uuid.uuid4())

    try:
        files_written: dict[str, int] = {}

        study_row = await (await db.execute(
            "SELECT * FROM studies WHERE study_id = ?", (study_id,)
        )).fetchone()
        if study_row:
            _write_json(staging, "study.json", dict(study_row))
            files_written["study.json"] = 1

        protocol_rows = await (await db.execute(
            "SELECT * FROM protocol_versions WHERE study_id = ?", (study_id,)
        )).fetchall()
        if protocol_rows:
            _write_json(staging, "protocol.json", [dict(r) for r in protocol_rows])
            files_written["protocol.json"] = len(protocol_rows)

        files_written["participants.csv"] = await _export_table(
            db, staging, "participants.csv",
            "SELECT * FROM participants WHERE study_id = ? ORDER BY participant_id",
            (study_id,),
        )

        files_written["allocations.csv"] = await _export_table(
            db, staging, "allocations.csv",
            "SELECT * FROM sequence_allocations WHERE study_id = ? ORDER BY allocation_id",
            (study_id,),
        )

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

        files_written["runtime_commands.csv"] = await _export_table(
            db, staging, "runtime_commands.csv",
            "SELECT * FROM runtime_commands ORDER BY created_at",
            (),
        )

        manifests_dir = os.path.join(staging, "manifests")
        os.makedirs(manifests_dir, exist_ok=True)
        manifest_rows = await (await db.execute(
            "SELECT sm.* FROM session_manifests sm "
            "JOIN research_sessions s ON sm.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY sm.research_session_id",
            (study_id,),
        )).fetchall()
        for m in manifest_rows:
            fname = f"{m['research_session_id']}.json"
            manifest_data = json.loads(m["manifest_json"])
            manifest_data["_manifest_hash"] = m["manifest_hash"]
            manifest_data["_sealed_at"] = m["sealed_at"]
            _write_json(manifests_dir, fname, manifest_data)
        files_written["manifests/"] = len(manifest_rows)

        seals_dir = os.path.join(staging, "completion_seals")
        os.makedirs(seals_dir, exist_ok=True)
        seal_rows = await (await db.execute(
            "SELECT cs.* FROM session_completion_seals cs "
            "JOIN research_sessions s ON cs.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY cs.research_session_id",
            (study_id,),
        )).fetchall()
        for seal in seal_rows:
            fname = f"{seal['research_session_id']}.json"
            _write_json(seals_dir, fname, dict(seal))
        files_written["completion_seals/"] = len(seal_rows)

        lib_rows = await (await db.execute(
            "SELECT * FROM frozen_yoked_libraries WHERE study_id = ?", (study_id,)
        )).fetchall()
        if lib_rows:
            _write_json(staging, "yoked_library.json", [dict(r) for r in lib_rows])
            files_written["yoked_library.json"] = len(lib_rows)

        if lib_rows:
            lib_ids = [r["library_id"] for r in lib_rows]
            placeholders = ",".join("?" * len(lib_ids))
            files_written["yoked_trajectories.csv"] = await _export_table(
                db, staging, "yoked_trajectories.csv",
                f"SELECT * FROM frozen_yoked_trajectories WHERE library_id IN ({placeholders}) "
                "ORDER BY trajectory_id",
                tuple(lib_ids),
            )
            traj_rows = await (await db.execute(
                f"SELECT trajectory_id FROM frozen_yoked_trajectories WHERE library_id IN ({placeholders})",
                tuple(lib_ids),
            )).fetchall()
            if traj_rows:
                traj_ids = [r["trajectory_id"] for r in traj_rows]
                tp = ",".join("?" * len(traj_ids))
                files_written["yoked_points.csv"] = await _export_table(
                    db, staging, "yoked_points.csv",
                    f"SELECT * FROM frozen_yoked_points WHERE trajectory_id IN ({tp}) "
                    "ORDER BY trajectory_id, window_index",
                    tuple(traj_ids),
                )

        files_written["replay_results.csv"] = await _export_table(
            db, staging, "replay_results.csv",
            "SELECT rr.* FROM replay_results rr "
            "JOIN research_sessions s ON rr.research_session_id = s.research_session_id "
            "WHERE s.study_id = ? ORDER BY rr.verified_at",
            (study_id,),
        )

        # --- Correct ordering: metadata THEN checksums ---
        metadata = {
            "study_id": study_id,
            "data_classification": "synthetic",
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }
        for fname, row_count in files_written.items():
            if fname.endswith("/"):
                metadata["files"][fname] = {"count": row_count}
            else:
                fpath = os.path.join(staging, fname)
                if os.path.exists(fpath):
                    metadata["files"][fname] = {
                        "rows": row_count,
                        "sha256": _file_sha256(fpath),
                    }
        _write_json(staging, "metadata.json", metadata)

        checksums: dict[str, str] = {}
        for root, _dirs, filenames in os.walk(staging):
            for fname in filenames:
                if fname == "checksums.sha256":
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, staging).replace("\\", "/")
                checksums[rel] = _file_sha256(fpath)

        checksums_path = os.path.join(staging, "checksums.sha256")
        with open(checksums_path, "w", encoding="utf-8") as f:
            for rel_path in sorted(checksums.keys()):
                f.write(f"{checksums[rel_path]}  {rel_path}\n")

        package_hash = _compute_package_hash(checksums)

        validation_result = validate_export(staging)

        if not validation_result["valid"]:
            await _persist_export_record(
                db, export_id, study_id, package_hash,
                checksums, "invalid",
                validation_result,
            )
            if os.path.exists(staging):
                shutil.rmtree(staging, ignore_errors=True)
            return {
                "export_id": export_id,
                "output_dir": output_dir,
                "study_id": study_id,
                "data_classification": "synthetic",
                "package_hash": package_hash,
                "validation": validation_result,
                "status": "invalid",
            }

        if os.path.exists(output_dir) and allow_overwrite:
            backup = output_dir + ".bak"
            if os.path.exists(backup):
                shutil.rmtree(backup)
            os.rename(output_dir, backup)
            try:
                os.rename(staging, output_dir)
                shutil.rmtree(backup, ignore_errors=True)
            except Exception:
                if os.path.exists(backup) and not os.path.exists(output_dir):
                    os.rename(backup, output_dir)
                raise
        else:
            os.rename(staging, output_dir)

        await _persist_export_record(
            db, export_id, study_id, package_hash,
            checksums, "valid",
            validation_result,
        )

        return {
            "export_id": export_id,
            "output_dir": output_dir,
            "files": metadata["files"],
            "study_id": study_id,
            "data_classification": "synthetic",
            "package_hash": package_hash,
            "validation": validation_result,
            "status": "valid",
        }
    except Exception:
        if os.path.exists(staging):
            shutil.rmtree(staging, ignore_errors=True)
        raise


async def _persist_export_record(
    db: aiosqlite.Connection,
    export_id: str,
    study_id: str,
    package_hash: str,
    checksums: dict[str, str],
    status: str,
    validation_result: dict[str, Any],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    validation_errors = json.dumps(validation_result.get("errors", []))
    try:
        await db.execute(
            "INSERT INTO export_runs "
            "(export_id, study_id, data_classification, manifest_hash, "
            "file_hashes_json, output_path, created_at, export_schema_version, "
            "status, validation_status, validation_errors_json, finalized_at) "
            "VALUES (?, ?, 'synthetic', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                export_id, study_id, package_hash,
                json.dumps(checksums), study_id,
                now, EXPORT_SCHEMA_VERSION,
                status,
                "valid" if validation_result["valid"] else "invalid",
                validation_errors,
                now if status == "valid" else None,
            ),
        )
        await db.commit()
    except Exception:
        logger.warning("Could not persist export_runs record", exc_info=True)


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


REQUIRED_FILES = {
    "metadata.json", "study.json", "protocol.json",
    "sessions.csv", "participants.csv", "allocations.csv",
}

REQUIRED_SESSION_HEADERS = {
    "research_session_id", "study_id", "participant_id", "condition",
    "data_classification", "status",
}

TERMINAL_STATUSES = {"completed", "safety_stopped", "aborted"}


def validate_export(export_dir: str) -> dict[str, Any]:
    errors: list[str] = []

    meta_path = os.path.join(export_dir, "metadata.json")
    if not os.path.exists(meta_path):
        return {"valid": False, "errors": ["Missing metadata.json"]}

    with open(meta_path) as f:
        metadata = json.load(f)

    if metadata.get("data_classification") != "synthetic":
        errors.append(f"Data classification is '{metadata.get('data_classification')}', expected 'synthetic'")

    checksums_path = os.path.join(export_dir, "checksums.sha256")
    checksums_cover_metadata = False
    if os.path.exists(checksums_path):
        with open(checksums_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                expected_hash, rel_path = parts
                if rel_path == "metadata.json":
                    checksums_cover_metadata = True
                fpath = os.path.join(export_dir, rel_path.replace("/", os.sep))
                if not os.path.exists(fpath):
                    errors.append(f"Checksums reference missing file: {rel_path}")
                    continue
                actual = _file_sha256(fpath)
                if actual != expected_hash:
                    errors.append(f"Checksum mismatch for {rel_path}")
    else:
        errors.append("Missing checksums.sha256")

    if not checksums_cover_metadata:
        errors.append("metadata.json is not covered by checksums")

    for fname, info in metadata.get("files", {}).items():
        if fname.endswith("/"):
            continue
        fpath = os.path.join(export_dir, fname)
        if not os.path.exists(fpath):
            if info.get("rows", 0) > 0:
                errors.append(f"Missing file with data: {fname}")

    sessions_path = os.path.join(export_dir, "sessions.csv")
    session_ids: set[str] = set()
    if os.path.exists(sessions_path):
        with open(sessions_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
            missing_headers = REQUIRED_SESSION_HEADERS - headers
            if missing_headers:
                errors.append(f"sessions.csv missing headers: {sorted(missing_headers)}")
            for row in reader:
                sid = row.get("research_session_id", "")
                if sid in session_ids:
                    errors.append(f"Duplicate session ID: {sid}")
                session_ids.add(sid)
                if row.get("data_classification") != "synthetic":
                    errors.append(f"Non-synthetic session: {sid}")
                if row.get("status") not in TERMINAL_STATUSES:
                    errors.append(f"Non-terminal session {sid}: status={row.get('status')}")

    manifests_dir = os.path.join(export_dir, "manifests")
    if os.path.isdir(manifests_dir):
        for fname in os.listdir(manifests_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(manifests_dir, fname)
                try:
                    with open(fpath) as f:
                        mdata = json.load(f)
                    if "_manifest_hash" in mdata:
                        pass
                except json.JSONDecodeError:
                    errors.append(f"Invalid manifest JSON: {fname}")

    seals_dir = os.path.join(export_dir, "completion_seals")
    if os.path.isdir(seals_dir):
        for fname in os.listdir(seals_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(seals_dir, fname)
                try:
                    with open(fpath) as f:
                        seal_data = json.load(f)
                    if "seal_hash" not in seal_data:
                        errors.append(f"Seal missing seal_hash: {fname}")
                except json.JSONDecodeError:
                    errors.append(f"Invalid seal JSON: {fname}")

    for dirpath, _dirnames, filenames in os.walk(export_dir):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "consent" in fname.lower() or "ethics" in fname.lower():
                    errors.append(f"Prohibited file: {fname}")
                if any(prefix in content for prefix in ("C:\\", "D:\\", "/home/", "/Users/")):
                    errors.append(f"Absolute filesystem path detected in: {fname}")
            except Exception:
                pass

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "files_checked": len(metadata.get("files", {})),
    }
