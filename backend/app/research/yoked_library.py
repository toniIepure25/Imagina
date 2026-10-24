"""Frozen yoked trajectory library — generation, freezing, validation, assignment.

A library is a collection of deterministic trajectories generated before any
participant session begins. Once frozen, no points can be added/modified/deleted.
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite


class YokedLibraryError(Exception):
    pass


class YokedLibraryFrozenError(YokedLibraryError):
    pass


class YokedLibraryValidationError(YokedLibraryError):
    pass


async def create_library(
    db: aiosqlite.Connection,
    study_id: str,
    protocol_version_id: str,
    schedule_hash: str,
    generation_seed: int,
) -> str:
    library_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO frozen_yoked_libraries "
        "(library_id, study_id, protocol_version_id, generation_seed, "
        "schedule_hash, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'draft', ?)",
        (library_id, study_id, protocol_version_id, generation_seed, schedule_hash, now),
    )
    await db.commit()
    return library_id


async def generate_trajectories(
    db: aiosqlite.Connection,
    library_id: str,
    trajectory_count: int,
    windows_per_trajectory: int,
    schedule_hash: str,
) -> list[str]:
    row = await (await db.execute(
        "SELECT status, generation_seed FROM frozen_yoked_libraries WHERE library_id = ?",
        (library_id,),
    )).fetchone()
    if not row:
        raise YokedLibraryError(f"Library {library_id} not found")
    if row["status"] == "frozen":
        raise YokedLibraryFrozenError("Cannot add trajectories to a frozen library")

    seed = row["generation_seed"]
    trajectory_ids: list[str] = []

    for t_idx in range(trajectory_count):
        trajectory_id = str(uuid.uuid4())
        points: list[dict[str, Any]] = []

        for w_idx in range(windows_per_trajectory):
            t = (t_idx * 100 + w_idx + seed) * 0.1
            params = {
                "scene_clarity": round(0.4 + 0.3 * math.sin(t), 4),
                "blur": round(0.35 - 0.15 * math.cos(t * 0.8), 4),
                "wall_distortion": round(0.2 + 0.1 * math.sin(t * 1.2), 4),
                "light_stability": round(0.6 + 0.2 * math.cos(t * 0.5), 4),
                "texture_detail": round(0.15 + 0.1 * math.sin(t * 1.5), 4),
                "particle_stability": round(0.6 + 0.1 * math.cos(t), 4),
                "door_complexity": 0.0,
                "fog_density": round(0.3 + 0.1 * math.sin(t * 0.3), 4),
                "color_saturation": round(0.5 + 0.15 * math.cos(t * 0.7), 4),
                "breathing_cue_strength": 0.2,
            }
            points.append(params)

        content_hash = _hash_points(points)

        await db.execute(
            "INSERT INTO frozen_yoked_trajectories "
            "(trajectory_id, library_id, trajectory_label, compatible_schedule_hash, "
            "window_count, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                trajectory_id, library_id, f"traj_{t_idx:03d}",
                schedule_hash, windows_per_trajectory, content_hash,
            ),
        )

        for w_idx, params in enumerate(points):
            point_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO frozen_yoked_points "
                "(point_id, trajectory_id, window_index, scene_params_json) "
                "VALUES (?, ?, ?, ?)",
                (point_id, trajectory_id, w_idx, json.dumps(params, sort_keys=True)),
            )

        trajectory_ids.append(trajectory_id)

    await db.commit()
    return trajectory_ids


async def freeze_library(db: aiosqlite.Connection, library_id: str) -> str:
    row = await (await db.execute(
        "SELECT status FROM frozen_yoked_libraries WHERE library_id = ?",
        (library_id,),
    )).fetchone()
    if not row:
        raise YokedLibraryError(f"Library {library_id} not found")
    if row["status"] == "frozen":
        return library_id

    cursor = await db.execute(
        "SELECT trajectory_id, content_hash FROM frozen_yoked_trajectories WHERE library_id = ?",
        (library_id,),
    )
    trajectories = await cursor.fetchall()
    if not trajectories:
        raise YokedLibraryValidationError("Cannot freeze empty library")

    all_hashes = ":".join(sorted(t["content_hash"] for t in trajectories))
    library_hash = hashlib.sha256(all_hashes.encode()).hexdigest()[:16]

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE frozen_yoked_libraries SET status = 'frozen', frozen_at = ?, content_hash = ? "
        "WHERE library_id = ?",
        (now, library_hash, library_id),
    )
    await db.commit()
    return library_id


async def validate_library(db: aiosqlite.Connection, library_id: str, expected_schedule_hash: str) -> bool:
    lib_row = await (await db.execute(
        "SELECT status, schedule_hash, content_hash FROM frozen_yoked_libraries WHERE library_id = ?",
        (library_id,),
    )).fetchone()
    if not lib_row:
        raise YokedLibraryError(f"Library {library_id} not found")
    if lib_row["status"] != "frozen":
        raise YokedLibraryValidationError("Library is not frozen")
    if lib_row["schedule_hash"] != expected_schedule_hash:
        raise YokedLibraryValidationError(
            f"Schedule hash mismatch: library has '{lib_row['schedule_hash']}', "
            f"expected '{expected_schedule_hash}'"
        )

    cursor = await db.execute(
        "SELECT trajectory_id, content_hash, window_count FROM frozen_yoked_trajectories "
        "WHERE library_id = ?",
        (library_id,),
    )
    trajectories = await cursor.fetchall()

    for traj in trajectories:
        pts_cursor = await db.execute(
            "SELECT scene_params_json FROM frozen_yoked_points "
            "WHERE trajectory_id = ? ORDER BY window_index",
            (traj["trajectory_id"],),
        )
        points_rows = await pts_cursor.fetchall()
        if len(points_rows) != traj["window_count"]:
            raise YokedLibraryValidationError(
                f"Trajectory {traj['trajectory_id']} has {len(points_rows)} points "
                f"but expected {traj['window_count']}"
            )
        actual_hash = _hash_points([json.loads(r["scene_params_json"]) for r in points_rows])
        if actual_hash != traj["content_hash"]:
            raise YokedLibraryValidationError(
                f"Content hash mismatch for trajectory {traj['trajectory_id']}"
            )

    return True


async def assign_trajectory(
    db: aiosqlite.Connection,
    library_id: str,
    study_seed: int,
    participant_id: str,
    session_index: int,
) -> str:
    cursor = await db.execute(
        "SELECT trajectory_id, trajectory_label FROM frozen_yoked_trajectories "
        "WHERE library_id = ? ORDER BY trajectory_label",
        (library_id,),
    )
    trajectories = await cursor.fetchall()
    if not trajectories:
        raise YokedLibraryError("No trajectories in library")

    key = f"{study_seed}:{participant_id}:{session_index}"
    h = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    idx = h % len(trajectories)
    return trajectories[idx]["trajectory_id"]


async def get_trajectory_points(db: aiosqlite.Connection, trajectory_id: str) -> list[dict[str, Any]]:
    cursor = await db.execute(
        "SELECT scene_params_json, prompt_text FROM frozen_yoked_points "
        "WHERE trajectory_id = ? ORDER BY window_index",
        (trajectory_id,),
    )
    rows = await cursor.fetchall()
    return [
        {"scene_params": json.loads(r["scene_params_json"]), "prompt_text": r["prompt_text"] or ""}
        for r in rows
    ]


def _hash_points(points: list[dict]) -> str:
    canonical = json.dumps(points, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
