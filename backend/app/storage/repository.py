import json
from datetime import datetime

from app.schemas.session import Session
from app.storage.database import get_db


async def create_session(session: Session) -> Session:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, display_name, mode, status, task_id, "
            "signal_provider_id, scenario, experiment_run_id, "
            "created_at, started_at, ended_at, safety_disclaimer_acknowledged, baseline_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.session_id,
                session.user_id,
                session.display_name,
                session.mode,
                session.status,
                session.task_id,
                session.signal_provider_id,
                session.scenario,
                session.experiment_run_id,
                session.created_at.isoformat(),
                session.started_at.isoformat() if session.started_at else None,
                session.ended_at.isoformat() if session.ended_at else None,
                int(session.safety_disclaimer_acknowledged),
                None,
            ),
        )
        await db.commit()
    finally:
        await db.close()
    return session


async def get_session(session_id: str) -> Session | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_session(row)
    finally:
        await db.close()


async def update_session_status(
    session_id: str,
    status: str,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> None:
    db = await get_db()
    try:
        parts = ["status = ?"]
        params: list = [status]
        if started_at:
            parts.append("started_at = ?")
            params.append(started_at.isoformat())
        if ended_at:
            parts.append("ended_at = ?")
            params.append(ended_at.isoformat())
        params.append(session_id)
        await db.execute(
            f"UPDATE sessions SET {', '.join(parts)} WHERE session_id = ?",
            params,
        )
        await db.commit()
    finally:
        await db.close()


async def set_baseline(session_id: str, baseline: dict) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE sessions SET baseline_json = ? WHERE session_id = ?",
            (json.dumps(baseline), session_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_baseline(session_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT baseline_json FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["baseline_json"]:
            return None
        return json.loads(row["baseline_json"])
    finally:
        await db.close()


async def upsert_json(table: str, key_column: str, key: str, payload: dict, columns: dict | None = None) -> None:
    columns = columns or {}
    db = await get_db()
    try:
        all_columns = {key_column: key, **columns, "payload": json.dumps(payload)}
        names = list(all_columns.keys())
        placeholders = ", ".join("?" for _ in names)
        updates = ", ".join(f"{name} = excluded.{name}" for name in names if name != key_column)
        await db.execute(
            f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders}) "
            f"ON CONFLICT({key_column}) DO UPDATE SET {updates}",
            [all_columns[name] for name in names],
        )
        await db.commit()
    finally:
        await db.close()


async def get_json(table: str, key_column: str, key: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            f"SELECT payload FROM {table} WHERE {key_column} = ?", (key,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return json.loads(row["payload"])
    finally:
        await db.close()


async def list_json(table: str, order_by: str | None = None) -> list[dict]:
    db = await get_db()
    try:
        query = f"SELECT payload FROM {table}"
        if order_by:
            query += f" ORDER BY {order_by}"
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        return [json.loads(row["payload"]) for row in rows]
    finally:
        await db.close()


def _row_to_session(row) -> Session:
    return Session(
        session_id=row["session_id"],
        user_id=row["user_id"],
        display_name=row["display_name"],
        mode=row["mode"],
        status=row["status"],
        task_id=row["task_id"],
        signal_provider_id=row["signal_provider_id"] if "signal_provider_id" in row.keys() else "simulated.default",
        scenario=row["scenario"] if "scenario" in row.keys() else "improving_user",
        experiment_run_id=row["experiment_run_id"] if "experiment_run_id" in row.keys() else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        safety_disclaimer_acknowledged=bool(row["safety_disclaimer_acknowledged"]),
    )
