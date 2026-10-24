"""Deterministic replay validation — canonical hashing and verification.

Verifies that running the same synthetic session with the same manifest
produces identical scientific content. Requires a valid completion seal.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

CANONICALIZATION_VERSION = "2.0"
FLOAT_PRECISION = 8


def normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value == float("inf") or value == float("-inf"):
            raise ValueError(f"Cannot canonicalize non-finite float: {value}")
        return round(value, FLOAT_PRECISION)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    return str(value)


def canonical_serialize(data: Any) -> bytes:
    normalized = normalize(data)
    return json.dumps(
        normalized, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")


def _canonical_default(obj: Any) -> Any:
    if isinstance(obj, float):
        if obj != obj or obj == float("inf") or obj == float("-inf"):
            raise ValueError(f"Cannot canonicalize non-finite float: {obj}")
        return round(obj, FLOAT_PRECISION)
    raise TypeError(f"Cannot canonicalize type: {type(obj)}")


def canonical_hash(data: Any) -> str:
    return hashlib.sha256(canonical_serialize(data)).hexdigest()


async def compute_session_replay_hash(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> dict[str, Any]:
    fb_cursor = await db.execute(
        "SELECT window_index, condition, policy_id, policy_version, "
        "pid_value, iqi_value, scene_params_json, reason_code, safety_override "
        "FROM feedback_records WHERE research_session_id = ? ORDER BY window_index",
        (research_session_id,),
    )
    feedback_rows = await fb_cursor.fetchall()

    canonical_fb = []
    for row in feedback_rows:
        scene_params = json.loads(row["scene_params_json"])
        canonical_fb.append(normalize({
            "window_index": row["window_index"],
            "condition": row["condition"],
            "policy_id": row["policy_id"],
            "policy_version": row["policy_version"],
            "pid": row["pid_value"],
            "iqi": row["iqi_value"],
            "scene_params": scene_params,
            "reason": row["reason_code"],
            "safety_override": bool(row["safety_override"]),
        }))

    tr_cursor = await db.execute(
        "SELECT tr.trial_id, tr.vividness, tr.confidence, tr.effort, "
        "tr.imagery_formation_latency_ms, tr.rating_completion_latency_ms "
        "FROM trial_responses tr JOIN trials t ON tr.trial_id = t.trial_id "
        "WHERE t.research_session_id = ? ORDER BY t.trial_index",
        (research_session_id,),
    )
    response_rows = await tr_cursor.fetchall()
    canonical_responses = []
    for row in response_rows:
        canonical_responses.append(normalize({
            "vividness": row["vividness"],
            "confidence": row["confidence"],
            "effort": row["effort"],
            "formation_ms": row["imagery_formation_latency_ms"],
            "rating_ms": row["rating_completion_latency_ms"],
        }))

    session_row = await (await db.execute(
        "SELECT status, terminal_reason FROM research_sessions WHERE research_session_id = ?",
        (research_session_id,),
    )).fetchone()

    content = {
        "canonicalization_version": CANONICALIZATION_VERSION,
        "feedback": canonical_fb,
        "responses": canonical_responses,
        "terminal_status": session_row["status"] if session_row else None,
        "terminal_reason": session_row["terminal_reason"] if session_row else None,
    }

    return {
        "session_id": research_session_id,
        "content_hash": canonical_hash(content),
        "feedback_count": len(canonical_fb),
        "response_count": len(canonical_responses),
        "canonicalization_version": CANONICALIZATION_VERSION,
    }


async def verify_replay_equivalence(
    db_original: aiosqlite.Connection,
    db_replay: aiosqlite.Connection,
    session_id: str,
) -> dict[str, Any]:
    orig = await compute_session_replay_hash(db_original, session_id)
    replay = await compute_session_replay_hash(db_replay, session_id)

    match = orig["content_hash"] == replay["content_hash"]
    result = {
        "match": match,
        "original_hash": orig["content_hash"],
        "replay_hash": replay["content_hash"],
        "session_id": session_id,
    }

    if not match:
        result["divergence"] = await _find_divergence(db_original, db_replay, session_id)

    return result


async def replay_session_from_manifest(
    original_db: aiosqlite.Connection,
    research_session_id: str,
    persist_result: bool = False,
) -> dict[str, Any]:
    """Load sealed manifest, verify seal, reconstruct deps, rerun, compare hashes."""
    from app.research.manifest import get_completion_seal, get_manifest, verify_seal_integrity

    manifest_data = await get_manifest(original_db, research_session_id)
    if not manifest_data:
        return {"match": False, "error": "No manifest found"}

    manifest = manifest_data["manifest"]

    seal = await get_completion_seal(original_db, research_session_id)
    if not seal:
        return {"match": False, "error": "No completion seal — replay requires sealed session"}

    seal_check = await verify_seal_integrity(original_db, research_session_id)
    if not seal_check["valid"]:
        return {"match": False, "error": f"Seal integrity failed: {seal_check['error']}"}

    original_content_hash = seal["scientific_content_hash"]

    current_hash_result = await compute_session_replay_hash(original_db, research_session_id)
    if current_hash_result["content_hash"] != original_content_hash:
        return {
            "match": False,
            "error": "Original content hash no longer matches sealed hash — data may have been altered",
        }

    condition = manifest["condition"]

    dep_error = _verify_manifest_dependencies(manifest)
    if dep_error:
        return {"match": False, "error": dep_error}

    if condition == "yoked":
        yoked_info = manifest.get("yoked", {})
        if not yoked_info.get("library_id"):
            return {"match": False, "error": "Yoked session missing library_id"}
        if not yoked_info.get("trajectory_id"):
            return {"match": False, "error": "Yoked session missing trajectory_id"}

    replay_run_id = str(uuid.uuid4()) if persist_result else None
    if persist_result and replay_run_id:
        manifest_row = await (await original_db.execute(
            "SELECT manifest_id FROM session_manifests WHERE research_session_id = ?",
            (research_session_id,),
        )).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        await original_db.execute(
            "INSERT INTO replay_runs "
            "(replay_run_id, research_session_id, manifest_id, manifest_hash, "
            "seal_hash, status, started_at) VALUES (?, ?, ?, ?, ?, 'running', ?)",
            (
                replay_run_id, research_session_id,
                manifest_row["manifest_id"], manifest_data["manifest_hash"],
                seal["seal_hash"], now,
            ),
        )
        await original_db.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        replay_db_path = os.path.join(tmpdir, "replay.db")
        replay_db = await aiosqlite.connect(replay_db_path)
        replay_db.row_factory = aiosqlite.Row

        try:
            from app.storage.migration_runner import run_migrations
            await run_migrations(replay_db)

            now_str = "2026-01-01T00:00:00+00:00"
            await replay_db.execute(
                "INSERT INTO studies (study_id, title, application_mode, data_classification, "
                "lifecycle_status, created_at, updated_at) "
                "VALUES (?, 'Replay', 'research', ?, 'active', ?, ?)",
                (manifest["study_id"], manifest["data_classification"], now_str, now_str),
            )
            await replay_db.execute(
                "INSERT INTO protocol_versions (protocol_version_id, study_id, version, "
                "status, created_at) VALUES (?, ?, 'replay', 'frozen', ?)",
                (manifest["protocol_version_id"], manifest["study_id"], now_str),
            )
            await replay_db.execute(
                "INSERT INTO participants (participant_id, study_id, participant_kind, "
                "pseudonym, created_at) VALUES (?, ?, 'synthetic', 'replay', ?)",
                (manifest["participant_id"], manifest["study_id"], now_str),
            )
            await replay_db.execute(
                "INSERT INTO research_sessions (research_session_id, study_id, participant_id, "
                "protocol_version_id, allocation_id, session_index, condition, "
                "data_classification, signal_provider_id, policy_id, policy_version, "
                "runtime_seed, status, state_version, planned_at, software_version, git_sha) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', 0, ?, ?, ?)",
                (
                    research_session_id,
                    manifest["study_id"],
                    manifest["participant_id"],
                    manifest["protocol_version_id"],
                    manifest["allocation_id"],
                    manifest["session_index"],
                    manifest["condition"],
                    manifest["data_classification"],
                    manifest["signal_provider"]["id"],
                    manifest["feedback_policy"]["id"],
                    manifest["feedback_policy"]["version"],
                    manifest["runtime_seed"],
                    now_str,
                    manifest["software_version"],
                    manifest["git_sha"],
                ),
            )
            await replay_db.commit()

            from app.research.event_sinks import NullEventSink
            from app.research.id_generator import DeterministicIdGenerator
            from app.research.runtime import ResearchSessionRuntime
            from app.research.runtime_clock import DeterministicClock
            from app.research.synthetic_orchestrator import SyntheticSafetyMonitor

            clock = DeterministicClock()
            id_gen = DeterministicIdGenerator(
                manifest["study_id"],
                manifest.get("protocol_hash") or "replay",
                manifest["runtime_seed"],
            )

            if condition == "adaptive":
                from app.research.feedback_policies import AdaptiveFeedbackPolicy
                policy = AdaptiveFeedbackPolicy()
            elif condition == "fixed":
                from app.research.feedback_policies import FixedResearchFeedbackPolicy
                policy = FixedResearchFeedbackPolicy()
            else:
                from app.research.feedback_policies import FrozenYokedFeedbackPolicy
                from app.research.yoked_library import get_trajectory_points
                yoked_info = manifest.get("yoked", {})
                traj_id = yoked_info.get("trajectory_id")
                if not traj_id:
                    error_msg = "Yoked replay requires trajectory_id — fallback prohibited"
                    if persist_result and replay_run_id:
                        await _persist_replay_failure(original_db, replay_run_id, error_msg)
                    return {"match": False, "error": error_msg}
                points = await get_trajectory_points(original_db, traj_id)
                if not points:
                    error_msg = f"Yoked trajectory {traj_id} has no points"
                    if persist_result and replay_run_id:
                        await _persist_replay_failure(original_db, replay_run_id, error_msg)
                    return {"match": False, "error": error_msg}
                policy = FrozenYokedFeedbackPolicy(points, trajectory_id=traj_id)

            runtime = ResearchSessionRuntime(
                db=replay_db,
                clock=clock,
                id_gen=id_gen,
                feedback_policy=policy,
                safety_monitor=SyntheticSafetyMonitor(),
                event_sink=NullEventSink(),
            )

            await runtime.run_session(
                research_session_id,
                trial_count=manifest.get("trial_count", 5),
                windows_per_trial=manifest.get("windows_per_trial", 3),
            )

            replay_hash_result = await compute_session_replay_hash(replay_db, research_session_id)

            match = original_content_hash == replay_hash_result["content_hash"]
            result = {
                "match": match,
                "original_hash": original_content_hash,
                "replay_hash": replay_hash_result["content_hash"],
                "session_id": research_session_id,
                "manifest_hash": manifest_data["manifest_hash"],
                "seal_hash": seal["seal_hash"],
            }

            if not match:
                result["divergence"] = await _find_divergence(
                    original_db, replay_db, research_session_id
                )

            if persist_result and replay_run_id:
                await _persist_replay_result(
                    original_db, replay_run_id, research_session_id,
                    original_content_hash, replay_hash_result["content_hash"],
                    seal["scientific_content_hash"], match, result.get("divergence"),
                )

            return result
        except Exception as exc:
            if persist_result and replay_run_id:
                await _persist_replay_failure(original_db, replay_run_id, str(exc))
            raise
        finally:
            await replay_db.close()


async def _persist_replay_result(
    db: aiosqlite.Connection,
    replay_run_id: str,
    research_session_id: str,
    original_hash: str,
    replay_hash: str,
    seal_content_hash: str,
    match: bool,
    divergence: dict | None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    result_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO replay_results "
        "(replay_result_id, replay_run_id, research_session_id, "
        "original_content_hash, replay_content_hash, seal_content_hash, "
        "match, divergence_json, canonicalization_version, verified_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            result_id, replay_run_id, research_session_id,
            original_hash, replay_hash, seal_content_hash,
            1 if match else 0,
            json.dumps(divergence) if divergence else None,
            CANONICALIZATION_VERSION, now,
        ),
    )
    await db.execute(
        "UPDATE replay_runs SET status = 'completed', completed_at = ? "
        "WHERE replay_run_id = ?",
        (now, replay_run_id),
    )
    await db.commit()


async def _persist_replay_failure(
    db: aiosqlite.Connection,
    replay_run_id: str,
    error_message: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE replay_runs SET status = 'failed', completed_at = ?, error_message = ? "
        "WHERE replay_run_id = ?",
        (now, error_message, replay_run_id),
    )
    await db.commit()


async def get_replay_results(
    db: aiosqlite.Connection,
    research_session_id: str,
) -> list[dict[str, Any]]:
    rows = await (await db.execute(
        "SELECT rr.*, rruns.status as run_status "
        "FROM replay_results rr "
        "JOIN replay_runs rruns ON rr.replay_run_id = rruns.replay_run_id "
        "WHERE rr.research_session_id = ? ORDER BY rr.verified_at DESC",
        (research_session_id,),
    )).fetchall()
    return [dict(r) for r in rows]


def _verify_manifest_dependencies(manifest: dict[str, Any]) -> str | None:
    """Fail-closed verification of manifest dependency fields.

    Returns an error string if any dependency is missing, unknown, or
    mismatched. Returns None if all dependencies are valid.
    """
    from app.research.manifest import DEPENDENCY_REGISTRY

    required_components = [
        ("signal_provider", ["id", "version"]),
        ("feature_processor", ["id", "version"]),
        ("state_estimator", ["id", "version"]),
        ("metric_processor", ["id", "version"]),
        ("curriculum_processor", ["id", "version"]),
        ("feedback_policy", ["id", "version"]),
        ("safety_monitor", ["id", "version"]),
    ]

    for comp_name, required_fields in required_components:
        comp = manifest.get(comp_name)
        if not comp or not isinstance(comp, dict):
            return f"Missing or invalid {comp_name} in manifest"
        for field in required_fields:
            if not comp.get(field):
                return f"Missing {comp_name}.{field} in manifest"
        dep_id = comp["id"]
        if dep_id not in DEPENDENCY_REGISTRY and dep_id != "synthetic":
            return f"Unknown {comp_name} ID: {dep_id}"

    for optional in ("id_generator", "clock"):
        comp = manifest.get(optional)
        if comp and isinstance(comp, dict):
            if not comp.get("id") or not comp.get("version"):
                return f"Incomplete {optional} in manifest"

    if manifest.get("canonicalization_version") and manifest["canonicalization_version"] != CANONICALIZATION_VERSION:
        return (
            f"Canonicalization version mismatch: manifest={manifest['canonicalization_version']}, "
            f"current={CANONICALIZATION_VERSION}"
        )

    return None


async def _find_divergence(
    db1: aiosqlite.Connection,
    db2: aiosqlite.Connection,
    session_id: str,
) -> dict[str, Any]:
    c1 = await db1.execute(
        "SELECT window_index, scene_params_json FROM feedback_records "
        "WHERE research_session_id = ? ORDER BY window_index",
        (session_id,),
    )
    c2 = await db2.execute(
        "SELECT window_index, scene_params_json FROM feedback_records "
        "WHERE research_session_id = ? ORDER BY window_index",
        (session_id,),
    )
    rows1 = await c1.fetchall()
    rows2 = await c2.fetchall()

    for r1, r2 in zip(rows1, rows2):
        if r1["scene_params_json"] != r2["scene_params_json"]:
            return {
                "type": "feedback_divergence",
                "window_index": r1["window_index"],
                "original": json.loads(r1["scene_params_json"]),
                "replay": json.loads(r2["scene_params_json"]),
            }

    if len(rows1) != len(rows2):
        return {
            "type": "feedback_count_mismatch",
            "original_count": len(rows1),
            "replay_count": len(rows2),
        }

    return {"type": "unknown_divergence"}
