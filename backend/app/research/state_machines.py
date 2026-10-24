"""Persistent state machines for research sessions and trials.

Uses compare-and-swap (state_version) for optimistic concurrency control.
Every transition is persisted in the corresponding transition table.
Terminal states are immutable — no further transitions allowed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

import aiosqlite

SessionStatus = Literal[
    "planned", "ready", "running", "completed",
    "aborted", "withdrawn", "invalidated", "safety_stopped",
]

TrialStatus = Literal[
    "planned", "ready", "running", "completed",
    "aborted", "invalidated", "safety_stopped",
]

TERMINAL_SESSION_STATES: set[str] = {"completed", "aborted", "withdrawn", "invalidated", "safety_stopped"}
TERMINAL_TRIAL_STATES: set[str] = {"completed", "aborted", "invalidated", "safety_stopped"}

VALID_SESSION_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"ready", "aborted", "withdrawn", "invalidated"},
    "ready": {"running", "aborted", "withdrawn", "invalidated"},
    "running": {"completed", "aborted", "withdrawn", "invalidated", "safety_stopped"},
}

VALID_TRIAL_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"ready", "aborted", "invalidated"},
    "ready": {"running", "aborted", "invalidated"},
    "running": {"completed", "aborted", "invalidated", "safety_stopped"},
}


class StateTransitionError(Exception):
    pass


class ConcurrencyConflictError(StateTransitionError):
    pass


class TerminalStateError(StateTransitionError):
    pass


class InvalidTransitionError(StateTransitionError):
    pass


async def transition_session(
    db: aiosqlite.Connection,
    research_session_id: str,
    expected_status: str,
    expected_version: int,
    new_status: SessionStatus,
    reason_code: str | None = None,
    actor: str = "system",
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> int:
    if expected_status in TERMINAL_SESSION_STATES:
        raise TerminalStateError(
            f"Session '{research_session_id}' is in terminal state '{expected_status}'"
        )

    valid_targets = VALID_SESSION_TRANSITIONS.get(expected_status, set())
    if new_status not in valid_targets:
        raise InvalidTransitionError(
            f"Cannot transition session from '{expected_status}' to '{new_status}'. "
            f"Valid targets: {valid_targets}"
        )

    if idempotency_key:
        dup = await (await db.execute(
            "SELECT transition_id FROM research_session_transitions "
            "WHERE research_session_id = ? AND idempotency_key = ?",
            (research_session_id, idempotency_key),
        )).fetchone()
        if dup:
            row = await (await db.execute(
                "SELECT state_version FROM research_sessions WHERE research_session_id = ?",
                (research_session_id,),
            )).fetchone()
            return row["state_version"] if row else expected_version + 1

    ts = timestamp or datetime.now(timezone.utc)
    ts_iso = ts.isoformat()
    new_version = expected_version + 1

    time_col = _session_time_column(new_status)
    is_terminal = new_status in TERMINAL_SESSION_STATES

    set_clauses = ["status = ?", "state_version = ?"]
    params: list = [new_status, new_version]

    if is_terminal:
        set_clauses.append("ended_at = COALESCE(ended_at, ?)")
        params.append(ts_iso)

    if time_col:
        set_clauses.append(f"{time_col} = ?")
        params.append(ts_iso)

    params.extend([research_session_id, expected_status, expected_version])

    sql = (
        f"UPDATE research_sessions SET {', '.join(set_clauses)} "
        f"WHERE research_session_id = ? AND status = ? AND state_version = ?"
    )
    cursor = await db.execute(sql, params)

    if cursor.rowcount == 0:
        row = await (await db.execute(
            "SELECT status, state_version FROM research_sessions WHERE research_session_id = ?",
            (research_session_id,),
        )).fetchone()
        if not row:
            raise StateTransitionError(f"Session '{research_session_id}' not found")
        if row["status"] in TERMINAL_SESSION_STATES:
            raise TerminalStateError(
                f"Session '{research_session_id}' is in terminal state '{row['status']}'"
            )
        raise ConcurrencyConflictError(
            f"Session '{research_session_id}': expected status='{expected_status}' "
            f"version={expected_version}, found status='{row['status']}' version={row['state_version']}"
        )

    if new_status in TERMINAL_SESSION_STATES:
        await db.execute(
            "UPDATE research_sessions SET terminal_reason = ? WHERE research_session_id = ?",
            (reason_code, research_session_id),
        )

    await db.execute(
        "INSERT INTO research_session_transitions "
        "(transition_id, research_session_id, from_status, to_status, "
        "from_version, to_version, reason_code, actor, idempotency_key, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), research_session_id, expected_status, new_status,
            expected_version, new_version, reason_code, actor, idempotency_key, ts_iso,
        ),
    )

    return new_version


async def transition_trial(
    db: aiosqlite.Connection,
    trial_id: str,
    expected_status: str,
    expected_version: int,
    new_status: TrialStatus,
    reason_code: str | None = None,
    actor: str = "system",
    idempotency_key: str | None = None,
    timestamp: datetime | None = None,
) -> int:
    if expected_status in TERMINAL_TRIAL_STATES:
        raise TerminalStateError(
            f"Trial '{trial_id}' is in terminal state '{expected_status}'"
        )

    valid_targets = VALID_TRIAL_TRANSITIONS.get(expected_status, set())
    if new_status not in valid_targets:
        raise InvalidTransitionError(
            f"Cannot transition trial from '{expected_status}' to '{new_status}'. "
            f"Valid targets: {valid_targets}"
        )

    if idempotency_key:
        dup = await (await db.execute(
            "SELECT transition_id FROM trial_transitions "
            "WHERE trial_id = ? AND idempotency_key = ?",
            (trial_id, idempotency_key),
        )).fetchone()
        if dup:
            row = await (await db.execute(
                "SELECT state_version FROM trials WHERE trial_id = ?",
                (trial_id,),
            )).fetchone()
            return row["state_version"] if row else expected_version + 1

    ts = timestamp or datetime.now(timezone.utc)
    ts_iso = ts.isoformat()
    new_version = expected_version + 1

    time_col = _trial_time_column(new_status)
    time_update = f", {time_col} = ?" if time_col else ""
    params: list = [new_status, new_version]
    if time_col:
        params.append(ts_iso)
    params.extend([trial_id, expected_status, expected_version])

    cursor = await db.execute(
        f"UPDATE trials SET status = ?, state_version = ?"
        f"{time_update} "
        f"WHERE trial_id = ? AND status = ? AND state_version = ?",
        params,
    )

    if cursor.rowcount == 0:
        row = await (await db.execute(
            "SELECT status, state_version FROM trials WHERE trial_id = ?",
            (trial_id,),
        )).fetchone()
        if not row:
            raise StateTransitionError(f"Trial '{trial_id}' not found")
        if row["status"] in TERMINAL_TRIAL_STATES:
            raise TerminalStateError(
                f"Trial '{trial_id}' is in terminal state '{row['status']}'"
            )
        raise ConcurrencyConflictError(
            f"Trial '{trial_id}': expected status='{expected_status}' "
            f"version={expected_version}, found status='{row['status']}' version={row['state_version']}"
        )

    if new_status in TERMINAL_TRIAL_STATES:
        await db.execute(
            "UPDATE trials SET terminal_reason = ? WHERE trial_id = ?",
            (reason_code, trial_id),
        )

    await db.execute(
        "INSERT INTO trial_transitions "
        "(transition_id, trial_id, from_status, to_status, "
        "from_version, to_version, reason_code, actor, idempotency_key, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()), trial_id, expected_status, new_status,
            expected_version, new_version, reason_code, actor, idempotency_key, ts_iso,
        ),
    )

    return new_version


def _session_time_column(status: str) -> str | None:
    return {
        "ready": "ready_at",
        "running": "started_at",
    }.get(status)


def _trial_time_column(status: str) -> str | None:
    return {
        "ready": "ready_at",
        "running": "started_at",
    }.get(status)
