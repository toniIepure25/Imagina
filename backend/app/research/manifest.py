"""Session manifest creation and completion sealing.

A manifest is an immutable record of every configuration parameter used to
execute a session. It is created before the session starts and sealed with
the terminal state and content hash after the session completes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import uuid
from datetime import datetime
from typing import Any

import aiosqlite

from app.research.replay_validator import canonical_serialize

MANIFEST_SCHEMA_VERSION = 2
CANONICALIZATION_VERSION = "2.0"
SOFTWARE_VERSION = "0.5.0"
DB_SCHEMA_VERSION = 6

logger = logging.getLogger(__name__)


def _resolve_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode("utf-8").strip()
    except Exception:
        return "unknown"


_GIT_SHA: str = _resolve_git_sha()

DEPENDENCY_REGISTRY: dict[str, type] = {}


def register_dependency(dep_id: str, cls: type) -> None:
    DEPENDENCY_REGISTRY[dep_id] = cls


def resolve_dependency(dep_id: str) -> type | None:
    return DEPENDENCY_REGISTRY.get(dep_id)


def _init_registry() -> None:
    from app.research.feedback_policies import (
        AdaptiveFeedbackPolicy,
        FixedResearchFeedbackPolicy,
        FrozenYokedFeedbackPolicy,
    )
    from app.research.pipeline_adapters import (
        CompositeMetricProcessor,
        DeterministicSignalProvider,
        FixedCurriculumProcessor,
        PassthroughFeatureProcessor,
        RuleBasedStateEstimator,
    )
    register_dependency("synthetic.deterministic", DeterministicSignalProvider)
    register_dependency("passthrough", PassthroughFeatureProcessor)
    register_dependency("rule_based", RuleBasedStateEstimator)
    register_dependency("composite", CompositeMetricProcessor)
    register_dependency("fixed_level", FixedCurriculumProcessor)
    register_dependency("adaptive", AdaptiveFeedbackPolicy)
    register_dependency("fixed", FixedResearchFeedbackPolicy)
    register_dependency("yoked", FrozenYokedFeedbackPolicy)


_init_registry()


def _canonical_hash(data: Any) -> str:
    return hashlib.sha256(canonical_serialize(data)).hexdigest()


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
    signal_provider_config_hash: str | None = None,
    policy_id: str,
    policy_version: str,
    policy_config_hash: str | None = None,
    feature_processor_id: str = "passthrough",
    feature_processor_version: str = "1.0",
    feature_processor_config_hash: str | None = None,
    state_estimator_id: str = "rule_based",
    state_estimator_version: str = "1.0",
    state_estimator_config_hash: str | None = None,
    metric_processor_id: str = "composite",
    metric_processor_version: str = "1.0",
    metric_processor_config_hash: str | None = None,
    curriculum_processor_id: str = "fixed_level",
    curriculum_processor_version: str = "1.0",
    curriculum_processor_config_hash: str | None = None,
    safety_monitor_id: str = "synthetic",
    safety_monitor_version: str = "1.0",
    safety_monitor_config_hash: str | None = None,
    id_generator_id: str = "deterministic",
    id_generator_version: str = "1.0",
    clock_id: str = "deterministic",
    clock_version: str = "1.0",
    yoked_library_id: str | None = None,
    yoked_trajectory_id: str | None = None,
    yoked_schedule_hash: str | None = None,
    yoked_content_hash: str | None = None,
    safety_config: dict[str, Any] | None = None,
    schedule_hash: str | None = None,
    allocation_sequence_label: str | None = None,
    git_sha: str | None = None,
    trial_count: int = 5,
    windows_per_trial: int = 3,
    processor_ids: dict[str, str] | None = None,
) -> str:
    manifest_data = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "research_session_id": research_session_id,
        "study_id": study_id,
        "protocol_version_id": protocol_version_id,
        "protocol_hash": protocol_hash,
        "participant_id": participant_id,
        "allocation_id": allocation_id,
        "allocation_sequence_label": allocation_sequence_label,
        "condition": condition,
        "session_index": session_index,
        "data_classification": data_classification,
        "runtime_seed": runtime_seed,
        "schedule_hash": schedule_hash,
        "signal_provider": {
            "id": signal_provider_id,
            "version": signal_provider_version,
            "config_hash": signal_provider_config_hash,
        },
        "feature_processor": {
            "id": feature_processor_id,
            "version": feature_processor_version,
            "config_hash": feature_processor_config_hash,
        },
        "state_estimator": {
            "id": state_estimator_id,
            "version": state_estimator_version,
            "config_hash": state_estimator_config_hash,
        },
        "metric_processor": {
            "id": metric_processor_id,
            "version": metric_processor_version,
            "config_hash": metric_processor_config_hash,
        },
        "curriculum_processor": {
            "id": curriculum_processor_id,
            "version": curriculum_processor_version,
            "config_hash": curriculum_processor_config_hash,
        },
        "feedback_policy": {
            "id": policy_id,
            "version": policy_version,
            "config_hash": policy_config_hash,
        },
        "safety_monitor": {
            "id": safety_monitor_id,
            "version": safety_monitor_version,
            "config_hash": safety_monitor_config_hash,
        },
        "id_generator": {
            "id": id_generator_id,
            "version": id_generator_version,
        },
        "clock": {
            "id": clock_id,
            "version": clock_version,
        },
        "yoked": {
            "library_id": yoked_library_id,
            "trajectory_id": yoked_trajectory_id,
            "schedule_hash": yoked_schedule_hash,
            "content_hash": yoked_content_hash,
        },
        "safety_config": safety_config or {},
        "trial_count": trial_count,
        "windows_per_trial": windows_per_trial,
        "db_schema_version": DB_SCHEMA_VERSION,
        "software_version": SOFTWARE_VERSION,
        "git_sha": git_sha or _GIT_SHA,
    }

    if processor_ids:
        manifest_data["processors_legacy"] = processor_ids

    manifest_json_bytes = canonical_serialize(manifest_data)
    manifest_json = manifest_json_bytes.decode("utf-8")
    manifest_hash = hashlib.sha256(manifest_json_bytes).hexdigest()
    manifest_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO session_manifests "
        "(manifest_id, research_session_id, manifest_json, manifest_hash, schema_version) "
        "VALUES (?, ?, ?, ?, ?)",
        (manifest_id, research_session_id, manifest_json, manifest_hash, DB_SCHEMA_VERSION),
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
    canonicalization_version: str = CANONICALIZATION_VERSION,
    git_sha: str | None = None,
) -> str:
    manifest_row = await (await db.execute(
        "SELECT manifest_id, manifest_hash FROM session_manifests "
        "WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()

    if not manifest_row:
        raise ValueError(f"No manifest found for session {research_session_id}")

    existing_seal = await (await db.execute(
        "SELECT completion_seal_id FROM session_completion_seals "
        "WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()
    if existing_seal:
        raise ValueError(f"Seal already exists for session {research_session_id}")

    resolved_sha = git_sha or _GIT_SHA
    seal_fields = {
        "research_session_id": research_session_id,
        "manifest_id": manifest_row["manifest_id"],
        "manifest_hash": manifest_row["manifest_hash"],
        "terminal_status": terminal_status,
        "terminal_reason": terminal_reason,
        "scientific_content_hash": content_hash,
        "canonicalization_version": canonicalization_version,
        "sealed_at": sealed_at.isoformat(),
        "software_version": SOFTWARE_VERSION,
        "git_sha": resolved_sha,
    }
    seal_json_bytes = canonical_serialize(seal_fields)
    seal_hash = hashlib.sha256(seal_json_bytes).hexdigest()

    seal_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO session_completion_seals "
        "(completion_seal_id, research_session_id, manifest_id, manifest_hash, "
        "terminal_status, terminal_reason, scientific_content_hash, "
        "canonicalization_version, sealed_at, seal_hash, software_version, git_sha) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            seal_id, research_session_id,
            manifest_row["manifest_id"], manifest_row["manifest_hash"],
            terminal_status, terminal_reason, content_hash,
            canonicalization_version, sealed_at.isoformat(),
            seal_hash, SOFTWARE_VERSION, resolved_sha,
        ),
    )

    await db.execute(
        "UPDATE session_manifests SET sealed_at = ? WHERE manifest_id = ?",
        (sealed_at.isoformat(), manifest_row["manifest_id"]),
    )

    return seal_hash


async def get_completion_seal(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> dict[str, Any] | None:
    row = await (await db.execute(
        "SELECT * FROM session_completion_seals WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()
    return dict(row) if row else None


async def verify_seal_integrity(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> dict[str, Any]:
    seal = await get_completion_seal(db, research_session_id)
    if not seal:
        return {"valid": False, "error": "No completion seal found"}

    seal_fields = {
        "research_session_id": seal["research_session_id"],
        "manifest_id": seal["manifest_id"],
        "manifest_hash": seal["manifest_hash"],
        "terminal_status": seal["terminal_status"],
        "terminal_reason": seal["terminal_reason"],
        "scientific_content_hash": seal["scientific_content_hash"],
        "canonicalization_version": seal["canonicalization_version"],
        "sealed_at": seal["sealed_at"],
        "software_version": seal["software_version"],
        "git_sha": seal["git_sha"],
    }
    expected_hash = hashlib.sha256(
        canonical_serialize(seal_fields)
    ).hexdigest()

    if expected_hash != seal["seal_hash"]:
        return {"valid": False, "error": "Seal hash mismatch — possible tampering"}

    manifest = await get_manifest(db, research_session_id)
    if not manifest:
        return {"valid": False, "error": "Referenced manifest missing"}

    if manifest["manifest_hash"] != seal["manifest_hash"]:
        return {"valid": False, "error": "Manifest hash does not match seal"}

    return {
        "valid": True,
        "seal_hash": seal["seal_hash"],
        "content_hash": seal["scientific_content_hash"],
        "manifest_hash": seal["manifest_hash"],
    }


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
        "SELECT manifest_id, manifest_json, manifest_hash, sealed_at FROM session_manifests "
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

    seal = await get_completion_seal(db, research_session_id)

    return {
        "valid": True,
        "sealed": row["sealed_at"] is not None,
        "has_completion_seal": seal is not None,
        "manifest_hash": row["manifest_hash"],
        "manifest_id": row["manifest_id"],
    }
