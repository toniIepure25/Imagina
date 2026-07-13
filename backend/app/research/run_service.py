"""Persistent runtime run service — DB-backed lifecycle for synthetic runs."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite


class RunConflictError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


class RunTerminalError(Exception):
    pass


RUN_TERMINAL_STATUSES = frozenset({"completed", "completed_with_failures", "failed", "aborted", "interrupted"})


async def create_run(
    db: aiosqlite.Connection,
    study_id: str,
    idempotency_key: str,
    input_params: dict[str, Any],
    seed: int,
    total_sessions: int,
) -> dict[str, Any]:
    input_hash = hashlib.sha256(
        json.dumps(input_params, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]

    existing_cmd = await (await db.execute(
        "SELECT command_id, result_reference, input_hash, status FROM runtime_commands "
        "WHERE idempotency_key = ?", (idempotency_key,)
    )).fetchone()

    if existing_cmd:
        if existing_cmd["input_hash"] != input_hash:
            raise RunConflictError(
                f"Idempotency key '{idempotency_key}' already used with different input"
            )
        run_row = await (await db.execute(
            "SELECT * FROM runtime_runs WHERE run_id = ?",
            (existing_cmd["result_reference"],)
        )).fetchone()
        if run_row:
            return dict(run_row)
        raise RunNotFoundError("Command references missing run")

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO runtime_commands "
        "(command_id, idempotency_key, command_type, target_entity_type, "
        "target_entity_id, input_hash, status, result_reference, created_at, completed_at) "
        "VALUES (?, ?, 'create_run', 'runtime_run', ?, ?, 'completed', ?, ?, ?)",
        (str(uuid.uuid4()), idempotency_key, study_id, input_hash,
         run_id, now, now),
    )

    await db.execute(
        "INSERT INTO runtime_runs "
        "(run_id, study_id, idempotency_key, status, total_sessions, "
        "completed_sessions, failed_sessions, prepared_sessions, "
        "runtime_seed, current_phase, state_version, created_at, updated_at) "
        "VALUES (?, ?, ?, 'accepted', ?, 0, 0, 0, ?, 'accepted', 0, ?, ?)",
        (run_id, study_id, idempotency_key, total_sessions, seed, now, now),
    )
    await db.commit()

    row = await (await db.execute(
        "SELECT * FROM runtime_runs WHERE run_id = ?", (run_id,)
    )).fetchone()
    return dict(row)


async def update_run_phase(
    db: aiosqlite.Connection,
    run_id: str,
    new_status: str,
    phase: str,
    **kwargs: Any,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    sets = ["status = ?", "current_phase = ?", "state_version = state_version + 1", "updated_at = ?"]
    params: list[Any] = [new_status, phase, now]

    for col, val in kwargs.items():
        sets.append(f"{col} = ?")
        params.append(val)

    params.extend([run_id])
    await db.execute(
        f"UPDATE runtime_runs SET {', '.join(sets)} WHERE run_id = ?",
        params,
    )
    await db.commit()


async def update_run_progress(
    db: aiosqlite.Connection,
    run_id: str,
    completed: int,
    failed: int,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE runtime_runs SET completed_sessions = ?, failed_sessions = ?, "
        "updated_at = ? WHERE run_id = ?",
        (completed, failed, now, run_id),
    )
    await db.commit()


async def request_abort(
    db: aiosqlite.Connection, run_id: str, actor: str = "api",
) -> dict[str, Any]:
    row = await (await db.execute(
        "SELECT * FROM runtime_runs WHERE run_id = ?", (run_id,)
    )).fetchone()
    if not row:
        raise RunNotFoundError(f"Run {run_id} not found")
    if row["status"] in RUN_TERMINAL_STATUSES:
        raise RunTerminalError(f"Run already {row['status']}")
    if row["status"] == "abort_requested":
        return dict(row)

    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE runtime_runs SET status = 'abort_requested', updated_at = ? WHERE run_id = ?",
        (now, run_id),
    )
    await db.commit()
    updated = await (await db.execute(
        "SELECT * FROM runtime_runs WHERE run_id = ?", (run_id,)
    )).fetchone()
    return dict(updated)


async def finalize_abort(
    db: aiosqlite.Connection,
    run_id: str,
    completed_sessions: int,
    terminal_reason: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE runtime_runs SET status = 'aborted', "
        "completed_sessions = ?, error_message = ?, ended_at = ?, updated_at = ? "
        "WHERE run_id = ? AND status IN ('abort_requested', 'running', 'accepted')",
        (completed_sessions, terminal_reason, now, now, run_id),
    )
    await db.commit()


async def check_abort_requested(db: aiosqlite.Connection, run_id: str) -> bool:
    row = await (await db.execute(
        "SELECT status FROM runtime_runs WHERE run_id = ?", (run_id,)
    )).fetchone()
    return row is not None and row["status"] == "abort_requested"


async def get_run(db: aiosqlite.Connection, run_id: str) -> dict[str, Any] | None:
    row = await (await db.execute(
        "SELECT * FROM runtime_runs WHERE run_id = ?", (run_id,)
    )).fetchone()
    return dict(row) if row else None


async def list_runs(db: aiosqlite.Connection, study_id: str | None = None) -> list[dict[str, Any]]:
    if study_id:
        rows = await (await db.execute(
            "SELECT * FROM runtime_runs WHERE study_id = ? ORDER BY created_at DESC",
            (study_id,),
        )).fetchall()
    else:
        rows = await (await db.execute(
            "SELECT * FROM runtime_runs ORDER BY created_at DESC"
        )).fetchall()
    return [dict(r) for r in rows]


async def mark_interrupted_on_startup(db: aiosqlite.Connection) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        "UPDATE runtime_runs SET status = 'interrupted', "
        "error_message = 'Process restarted while run was active', "
        "ended_at = ?, updated_at = ? "
        "WHERE status IN ('accepted', 'running', 'abort_requested') "
        "AND ended_at IS NULL",
        (now, now),
    )
    count = cursor.rowcount
    if count > 0:
        await db.commit()
    return count
