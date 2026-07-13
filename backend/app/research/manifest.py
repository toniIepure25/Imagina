"""Session manifest creation and completion sealing.

A manifest is an immutable record of every configuration parameter used to
execute a session. It is created before the session starts and sealed with
the terminal state and content hash after the session completes.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

import aiosqlite

MANIFEST_SCHEMA_VERSION = 1
SOFTWARE_VERSION = "0.5.0"


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


async def create_session_manifest(
    db: aiosqlite.Connection,
    research_session_id: str,
    *,
    study_id: str,
    protocol_version_id: str,
    protocol_hash: str | None,
    participant_id: str,
    allocation_id: str,
    condition: str,
    session_index: int,
    data_classification: str,
    runtime_seed: int,
    signal_provider_id: str,
    signal_provider_version: str = "1.0",
    policy_id: str,
    policy_version: str,
    policy_config_hash: str | None = None,
    yoked_library_id: str | None = None,
    yoked_trajectory_id: str | None = None,
    yoked_schedule_hash: str | None = None,
    safety_config: dict[str, Any] | None = None,
    processor_ids: dict[str, str] | None = None,
    git_sha: str = "synthetic",
    trial_count: int = 5,
    windows_per_trial: int = 3,
) -> str:
    manifest_data = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "research_session_id": research_session_id,
        "study_id": study_id,
        "protocol_version_id": protocol_version_id,
        "protocol_hash": protocol_hash,
        "participant_id": participant_id,
        "allocation_id": allocation_id,
        "condition": condition,
        "session_index": session_index,
        "data_classification": data_classification,
        "runtime_seed": runtime_seed,
        "signal_provider": {
            "id": signal_provider_id,
            "version": signal_provider_version,
        },
        "feedback_policy": {
            "id": policy_id,
            "version": policy_version,
            "config_hash": policy_config_hash,
        },
        "yoked": {
            "library_id": yoked_library_id,
            "trajectory_id": yoked_trajectory_id,
            "schedule_hash": yoked_schedule_hash,
        },
        "safety_config": safety_config or {},
        "processors": processor_ids or {},
        "trial_count": trial_count,
        "windows_per_trial": windows_per_trial,
        "software_version": SOFTWARE_VERSION,
        "git_sha": git_sha,
    }

    manifest_json = _canonical_json(manifest_data)
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    manifest_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO session_manifests "
        "(manifest_id, research_session_id, manifest_json, manifest_hash, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        (manifest_id, research_session_id, manifest_json, manifest_hash, 4),
    )

    return manifest_id


async def seal_session_completion(
    db: aiosqlite.Connection,
    research_session_id: str,
    *,
    terminal_status: str,
    terminal_reason: str,
    content_hash: str,
    sealed_at: datetime,
) -> str:
    manifest_row = await (await db.execute(
        "SELECT manifest_id, manifest_hash FROM session_manifests "
        "WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()

    if not manifest_row:
        raise ValueError(f"No manifest found for session {research_session_id}")

    seal_data = {
        "manifest_hash": manifest_row["manifest_hash"],
        "terminal_status": terminal_status,
        "terminal_reason": terminal_reason,
        "content_hash": content_hash,
        "sealed_at": sealed_at.isoformat(),
    }
    seal_json = _canonical_json(seal_data)
    seal_hash = hashlib.sha256(seal_json.encode("utf-8")).hexdigest()

    await db.execute(
        "UPDATE session_manifests SET sealed_at = ? WHERE manifest_id = ?",
        (sealed_at.isoformat(), manifest_row["manifest_id"]),
    )

    return seal_hash


async def get_manifest(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> dict[str, Any] | None:
    row = await (await db.execute(
        "SELECT manifest_json, manifest_hash, sealed_at FROM session_manifests "
        "WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()

    if not row:
        return None

    return {
        "manifest": json.loads(row["manifest_json"]),
        "manifest_hash": row["manifest_hash"],
        "sealed_at": row["sealed_at"],
    }


async def validate_manifest(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> dict[str, Any]:
    row = await (await db.execute(
        "SELECT manifest_json, manifest_hash, sealed_at FROM session_manifests "
        "WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()

    if not row:
        return {"valid": False, "error": "No manifest found"}

    recomputed = hashlib.sha256(row["manifest_json"].encode("utf-8")).hexdigest()
    if recomputed != row["manifest_hash"]:
        return {"valid": False, "error": "Manifest hash mismatch"}

    try:
        json.loads(row["manifest_json"])
    except json.JSONDecodeError:
        return {"valid": False, "error": "Invalid JSON in manifest"}

    return {
        "valid": True,
        "sealed": row["sealed_at"] is not None,
        "manifest_hash": row["manifest_hash"],
    }
