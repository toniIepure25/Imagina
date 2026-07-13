"""Deterministic replay validation — canonical hashing and verification.

Verifies that running the same synthetic session with the same manifest
produces identical scientific content.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any

import aiosqlite

CANONICALIZATION_VERSION = "1.1"
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
) -> dict[str, Any]:
    """Load sealed manifest, reconstruct deps, rerun, compare hashes."""
    from app.research.manifest import get_manifest

    manifest_data = await get_manifest(original_db, research_session_id)
    if not manifest_data:
        return {"match": False, "error": "No manifest found"}

    manifest = manifest_data["manifest"]
    original_hash_result = await compute_session_replay_hash(original_db, research_session_id)

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

            condition = manifest["condition"]
            if condition == "adaptive":
                from app.research.feedback_policies import AdaptiveFeedbackPolicy
                policy = AdaptiveFeedbackPolicy()
            elif condition == "fixed":
                from app.research.feedback_policies import FixedResearchFeedbackPolicy
                policy = FixedResearchFeedbackPolicy()
            else:
                from app.research.feedback_policies import FrozenYokedFeedbackPolicy
                yoked_info = manifest.get("yoked", {})
                traj_id = yoked_info.get("trajectory_id")
                if traj_id:
                    from app.research.yoked_library import get_trajectory_points
                    points = await get_trajectory_points(original_db, traj_id)
                    policy = FrozenYokedFeedbackPolicy(points, trajectory_id=traj_id)
                else:
                    from app.research.feedback_policies import FixedResearchFeedbackPolicy as Fallback
                    policy = Fallback()

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

            match = original_hash_result["content_hash"] == replay_hash_result["content_hash"]
            result = {
                "match": match,
                "original_hash": original_hash_result["content_hash"],
                "replay_hash": replay_hash_result["content_hash"],
                "session_id": research_session_id,
                "manifest_hash": manifest_data["manifest_hash"],
            }

            if not match:
                result["divergence"] = await _find_divergence(
                    original_db, replay_db, research_session_id
                )

            return result
        finally:
            await replay_db.close()


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
