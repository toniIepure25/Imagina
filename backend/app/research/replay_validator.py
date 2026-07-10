"""Deterministic replay validation — canonical hashing and verification.

Verifies that running the same synthetic session with the same manifest
produces identical scientific content.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import aiosqlite


CANONICALIZATION_VERSION = "1.0"


def canonical_serialize(data: Any) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, default=_canonical_default,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_default(obj: Any) -> Any:
    if isinstance(obj, float):
        if obj != obj or obj == float("inf") or obj == float("-inf"):
            raise ValueError(f"Cannot canonicalize non-finite float: {obj}")
        return round(obj, 8)
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
        canonical_fb.append({
            "window_index": row["window_index"],
            "condition": row["condition"],
            "policy_id": row["policy_id"],
            "policy_version": row["policy_version"],
            "pid": round(row["pid_value"], 8) if row["pid_value"] is not None else None,
            "iqi": round(row["iqi_value"], 8) if row["iqi_value"] is not None else None,
            "scene_params": json.loads(row["scene_params_json"]),
            "reason": row["reason_code"],
            "safety_override": bool(row["safety_override"]),
        })

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
        canonical_responses.append({
            "vividness": round(row["vividness"], 8) if row["vividness"] is not None else None,
            "confidence": round(row["confidence"], 8) if row["confidence"] is not None else None,
            "effort": round(row["effort"], 8) if row["effort"] is not None else None,
            "formation_ms": round(row["imagery_formation_latency_ms"], 4)
            if row["imagery_formation_latency_ms"] is not None else None,
            "rating_ms": round(row["rating_completion_latency_ms"], 4)
            if row["rating_completion_latency_ms"] is not None else None,
        })

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

    for i, (r1, r2) in enumerate(zip(rows1, rows2)):
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
