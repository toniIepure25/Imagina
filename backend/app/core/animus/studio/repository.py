"""Local SQLite persistence for ANIMUS Studio.

The Studio is local-first: every method opens a short-lived connection with WAL, foreign keys, and a
busy timeout enabled. Product mutations are committed as one unit of work (version + branch + session
head + event), so a crash can never leave a version that the session does not point at.
"""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import aiosqlite

from app.storage import database
from app.storage.migration_runner import current_version, run_migrations


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _load(value: str | None, default: Any, *, required: bool = False) -> Any:
    if value is None:
        if required:
            raise ValueError("required JSON record is missing")
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError) as exc:
        if required:
            raise ValueError("stored JSON record is invalid") from exc
        return default


def _require_type(value: Any, expected: type, message: str) -> Any:
    if not isinstance(value, expected):
        raise ValueError(message)
    return value


class StudioRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    def _path(self) -> str:
        return self.db_path or database.DB_PATH

    async def _connect(self) -> aiosqlite.Connection:
        path = self._path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("PRAGMA busy_timeout = 5000")
        # ``synchronous`` is connection-local. Set it on every connection instead of only on the
        # migration connection, otherwise the durability mode silently differs between startup and
        # normal writes. FULL is deliberate for a local product whose database is the only copy.
        await db.execute("PRAGMA synchronous = FULL")
        await db.execute("PRAGMA wal_autocheckpoint = 1000")
        return db

    async def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            db = await self._connect()
            try:
                await db.execute("PRAGMA journal_mode = WAL")
                await run_migrations(db)
            finally:
                await db.close()
            self._schema_ready = True

    async def schema_version(self) -> int:
        await self.ensure_schema()
        db = await self._connect()
        try:
            return await current_version(db)
        finally:
            await db.close()

    async def diagnostics(self, *, deep: bool = False) -> dict[str, Any]:
        """Read-only SQLite diagnostics for the local Studio database.

        The shallow form is cheap enough for a health check. The deep form runs SQLite's own
        integrity checks and is opt-in because it can take noticeable time on a large database.
        """
        await self.ensure_schema()
        db = await self._connect()
        try:
            journal_row = await (await db.execute("PRAGMA journal_mode")).fetchone()
            sync_row = await (await db.execute("PRAGMA synchronous")).fetchone()
            fk_row = await (await db.execute("PRAGMA foreign_keys")).fetchone()
            event_row = await (
                await db.execute("SELECT COUNT(*) AS count FROM animus_studio_events")
            ).fetchone()
            payload: dict[str, Any] = {
                "schema_version": await current_version(db),
                "journal_mode": str(journal_row[0]).lower() if journal_row else None,
                "synchronous": int(sync_row[0]) if sync_row else None,
                "foreign_keys": bool(fk_row[0]) if fk_row else None,
                "event_count": int(event_row["count"]) if event_row else None,
            }
            if deep:
                check_rows = await (await db.execute("PRAGMA quick_check")).fetchall()
                violations = await (await db.execute("PRAGMA foreign_key_check")).fetchall()
                messages = [str(row[0]) for row in check_rows]
                payload["integrity"] = "ok" if messages == ["ok"] else "; ".join(messages)[:500]
                payload["foreign_key_violations"] = len(violations)
            return payload
        finally:
            await db.close()

    @asynccontextmanager
    async def write_transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """One atomic write unit.

        Callers must only use the connection for repository ``_*_tx`` helpers and must not commit or
        roll back themselves. The context manager always closes the connection.
        """
        await self.ensure_schema()
        db = await self._connect()
        try:
            await db.execute("BEGIN IMMEDIATE")
            yield db
            await db.commit()
        except BaseException:
            await db.rollback()
            raise
        finally:
            await db.close()

    # --- low-level transaction helpers ---------------------------------------
    @staticmethod
    async def _upsert_session_tx(db: aiosqlite.Connection, record: dict) -> None:
        await db.execute(
            """INSERT INTO animus_studio_sessions
               (session_id, title, intention, mode, status, seed, claim_level, active_branch_id,
                active_version_id, privacy_scope, warnings_json, metadata_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 title=excluded.title, intention=excluded.intention, mode=excluded.mode,
                 status=excluded.status, seed=excluded.seed, claim_level=excluded.claim_level,
                 active_branch_id=excluded.active_branch_id, active_version_id=excluded.active_version_id,
                 privacy_scope=excluded.privacy_scope, warnings_json=excluded.warnings_json,
                 metadata_json=excluded.metadata_json, updated_at=excluded.updated_at""",
            (record["session_id"], record["title"], record.get("intention", ""),
             record.get("mode", "amplifier"), record.get("status", "active"), int(record["seed"]),
             record.get("claim_level", "L1_BEHAVIORAL_ASSISTED"), record["active_branch_id"],
             record["active_version_id"], record.get("privacy_scope", "local_only"),
             _json(record.get("warnings") or []), _json(record.get("metadata") or {}),
             record["created_at"], record["updated_at"]),
        )

    @staticmethod
    async def _update_session_tx(db: aiosqlite.Connection, session_id: str, *, updated_at: str,
                                 **fields: Any) -> None:
        allowed = {"title", "status", "active_branch_id", "active_version_id", "warnings", "metadata",
                   "claim_level"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in updates.items():
            if key in ("warnings", "metadata"):
                assignments.append(f"{key}_json = ?")
                values.append(_json(value))
            else:
                assignments.append(f"{key} = ?")
                values.append(value)
        assignments.append("updated_at = ?")
        values.extend((updated_at, session_id))
        await db.execute(
            f"UPDATE animus_studio_sessions SET {', '.join(assignments)} WHERE session_id = ?",
            tuple(values),
        )

    @staticmethod
    async def _insert_version_tx(db: aiosqlite.Connection, version: dict) -> None:
        await db.execute(
            """INSERT INTO animus_studio_versions
               (version_id, session_id, number, branch_id, parent_version_id, scene_json,
                commands_json, diff_json, source, label, intention, claim_level, generator,
                content_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (version["version_id"], version["session_id"], int(version["number"]),
             version["branch_id"], version.get("parent_version_id"), _json(version["scene"]),
             _json(version.get("commands") or []), _json(version.get("diff") or {}),
             version.get("source", "compose"), version.get("label", ""), version.get("intention"),
             version.get("claim_level", "L1_BEHAVIORAL_ASSISTED"),
             version.get("generator", "compose.v1"), version["content_hash"],
             version["created_at"]),
        )

    @staticmethod
    async def _upsert_branch_tx(db: aiosqlite.Connection, branch: dict) -> None:
        await db.execute(
            """INSERT INTO animus_studio_branches
               (branch_id, session_id, name, head_version_id, parent_branch_id, fork_version_id,
                created_at, redo_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, branch_id) DO UPDATE SET
                 name=excluded.name, head_version_id=excluded.head_version_id,
                 parent_branch_id=excluded.parent_branch_id, fork_version_id=excluded.fork_version_id,
                 redo_json=excluded.redo_json""",
            (branch["branch_id"], branch["session_id"], branch["name"], branch["head_version_id"],
             branch.get("parent_branch_id"), branch.get("fork_version_id"), branch["created_at"],
             _json(branch.get("redo") or [])),
        )

    @staticmethod
    async def _insert_event_tx(db: aiosqlite.Connection, session_id: str, event_type: str, payload: dict,
                               version_id: str | None = None) -> int:
        cursor = await db.execute(
            """INSERT INTO animus_studio_events (session_id, event_type, version_id, payload_json)
               VALUES (?, ?, ?, ?)""",
            (session_id, event_type, version_id, _json(payload)),
        )
        return int(cursor.lastrowid or 0)

    @staticmethod
    async def _insert_candidate_tx(db: aiosqlite.Connection, candidate: dict) -> None:
        await db.execute(
            """INSERT INTO animus_studio_candidates
               (candidate_id, session_id, source_version_id, variant_index, scene_json, diff_json,
                notes_json, selected, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(candidate_id) DO UPDATE SET
                 scene_json=excluded.scene_json, diff_json=excluded.diff_json,
                 notes_json=excluded.notes_json""",
            (candidate["candidate_id"], candidate["session_id"], candidate["source_version_id"],
             int(candidate["variant_index"]), _json(candidate["scene"]), _json(candidate.get("diff") or {}),
             _json(candidate.get("notes") or []), int(candidate.get("selected", 0)),
             candidate["created_at"]),
        )

    # --- sessions -------------------------------------------------------------
    async def save_session(self, record: dict) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._upsert_session_tx(db, record)
            await db.commit()
        finally:
            await db.close()

    async def update_session(self, session_id: str, *, updated_at: str, **fields: Any) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._update_session_tx(db, session_id, updated_at=updated_at, **fields)
            await db.commit()
        finally:
            await db.close()

    async def get_session(self, session_id: str) -> dict | None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_sessions WHERE session_id = ?", (session_id,))
            row = await cursor.fetchone()
            return self._session_row(row) if row else None
        finally:
            await db.close()

    async def list_sessions(self, limit: int = 50) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [self._session_row(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    async def delete_session(self, session_id: str) -> bool:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "DELETE FROM animus_studio_sessions WHERE session_id = ?", (session_id,))
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    @staticmethod
    def _session_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["warnings"] = _load(payload.pop("warnings_json", None), [])
        payload["metadata"] = _load(payload.pop("metadata_json", None), {})
        return payload

    # --- atomic bundles -------------------------------------------------------
    async def create_session_bundle(self, *, session: dict, version: dict, branch: dict,
                                    event_type: str, event_payload: dict) -> int:
        async with self.write_transaction() as db:
            await self._upsert_session_tx(db, session)
            await self._insert_version_tx(db, version)
            await self._upsert_branch_tx(db, branch)
            return await self._insert_event_tx(db, session["session_id"], event_type, event_payload,
                                               version_id=version["version_id"])

    async def commit_version_bundle(self, *, session: dict, version: dict, branch: dict,
                                    event_type: str, event_payload: dict) -> int:
        async with self.write_transaction() as db:
            await self._upsert_session_tx(db, session)
            await self._insert_version_tx(db, version)
            await self._upsert_branch_tx(db, branch)
            return await self._insert_event_tx(db, session["session_id"], event_type, event_payload,
                                               version_id=version["version_id"])

    async def update_head_bundle(self, *, session: dict, branch: dict, event_type: str,
                                 event_payload: dict, version_id: str | None = None) -> int:
        async with self.write_transaction() as db:
            await self._upsert_session_tx(db, session)
            await self._upsert_branch_tx(db, branch)
            return await self._insert_event_tx(db, session["session_id"], event_type, event_payload,
                                               version_id=version_id)

    async def save_candidates_bundle(self, candidates: list[dict], *, event_type: str | None = None,
                                     event_payload: dict | None = None) -> int:
        if not candidates:
            return 0
        session_id = candidates[0]["session_id"]
        source_version_id = candidates[0]["source_version_id"]
        async with self.write_transaction() as db:
            await db.execute(
                """DELETE FROM animus_studio_candidates
                   WHERE session_id = ? AND source_version_id = ? AND selected = 0""",
                (session_id, source_version_id),
            )
            for candidate in candidates:
                await self._insert_candidate_tx(db, candidate)
            if event_type:
                return await self._insert_event_tx(db, session_id, event_type, event_payload or {},
                                                   version_id=source_version_id)
        return 0

    async def select_candidate_bundle(self, *, session: dict, version: dict, branch: dict,
                                      candidate_id: str, event_type: str, event_payload: dict) -> int:
        async with self.write_transaction() as db:
            await self._upsert_session_tx(db, session)
            await self._insert_version_tx(db, version)
            await self._upsert_branch_tx(db, branch)
            await db.execute(
                """UPDATE animus_studio_candidates SET selected = 1
                   WHERE session_id = ? AND candidate_id = ?""",
                (session["session_id"], candidate_id),
            )
            return await self._insert_event_tx(db, session["session_id"], event_type, event_payload,
                                               version_id=version["version_id"])

    # --- versions -------------------------------------------------------------
    async def save_version(self, version: dict) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._insert_version_tx(db, version)
            await db.commit()
        finally:
            await db.close()

    async def load_versions(self, session_id: str) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_versions WHERE session_id = ? ORDER BY number",
                (session_id,))
            return [self._version_row(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    @staticmethod
    def _version_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["scene"] = _require_type(
            _load(payload.pop("scene_json", None), {}, required=True), dict,
            "stored scene record is invalid")
        payload["commands"] = _require_type(
            _load(payload.pop("commands_json", None), [], required=True), list,
            "stored commands record is invalid")
        payload["diff"] = _require_type(
            _load(payload.pop("diff_json", None), {}, required=True), dict,
            "stored diff record is invalid")
        return payload

    # --- branches -------------------------------------------------------------
    @staticmethod
    def _branch_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["redo"] = _load(payload.pop("redo_json", None), [], required=True)
        if not isinstance(payload["redo"], list) or any(
            not isinstance(item, str) or len(item) > 80 for item in payload["redo"]
        ):
            raise ValueError("stored branch redo stack is invalid")
        return payload

    async def save_branch(self, branch: dict) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._upsert_branch_tx(db, branch)
            await db.commit()
        finally:
            await db.close()

    async def load_branches(self, session_id: str) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_branches WHERE session_id = ? ORDER BY created_at",
                (session_id,))
            return [self._branch_row(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    # --- events ---------------------------------------------------------------
    async def add_event(self, session_id: str, event_type: str, payload: dict,
                        version_id: str | None = None) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._insert_event_tx(db, session_id, event_type, payload, version_id)
            await db.commit()
        finally:
            await db.close()

    async def load_events(self, session_id: str, limit: int = 200) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                """SELECT * FROM animus_studio_events WHERE session_id = ?
                   ORDER BY seq DESC LIMIT ?""", (session_id, limit))
            rows = await cursor.fetchall()
            events = []
            for row in reversed(rows):
                item = dict(row)
                item["payload"] = _require_type(
                    _load(item.pop("payload_json", None), {}, required=True), dict,
                    "stored event payload is invalid")
                events.append(item)
            return events
        finally:
            await db.close()

    async def load_events_after(self, session_id: str, after_seq: int, limit: int = 100) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                """SELECT * FROM animus_studio_events
                   WHERE session_id = ? AND seq > ?
                   ORDER BY seq ASC LIMIT ?""",
                (session_id, after_seq, limit),
            )
            events: list[dict] = []
            for row in await cursor.fetchall():
                item = dict(row)
                item["payload"] = _require_type(
                    _load(item.pop("payload_json", None), {}, required=True), dict,
                    "stored event payload is invalid")
                events.append(item)
            return events
        finally:
            await db.close()

    async def latest_event_seq(self, session_id: str) -> int:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(seq), 0) FROM animus_studio_events WHERE session_id = ?",
                (session_id,),
            )
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            return int(row[0]) if row else 0
        finally:
            await db.close()

    # --- candidates -----------------------------------------------------------
    async def save_candidate(self, candidate: dict) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._insert_candidate_tx(db, candidate)
            await db.commit()
        finally:
            await db.close()

    async def load_candidates(self, session_id: str, limit: int = 30,
                              *, source_version_id: str | None = None,
                              include_selected: bool = True) -> list[dict]:
        await self.ensure_schema()
        where = ["session_id = ?"]
        values: list[Any] = [session_id]
        if source_version_id is not None:
            where.append("source_version_id = ?")
            values.append(source_version_id)
        if not include_selected:
            where.append("selected = 0")
        values.append(limit)
        db = await self._connect()
        try:
            cursor = await db.execute(
                f"""SELECT * FROM animus_studio_candidates
                    WHERE {' AND '.join(where)}
                    ORDER BY created_at DESC LIMIT ?""",
                tuple(values),
            )
            return [self._candidate_row(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    async def get_candidate(self, session_id: str, candidate_id: str) -> dict | None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_candidates WHERE session_id = ? AND candidate_id = ?",
                (session_id, candidate_id))
            row = await cursor.fetchone()
            return self._candidate_row(row) if row else None
        finally:
            await db.close()

    @staticmethod
    def _candidate_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["scene"] = _require_type(
            _load(payload.pop("scene_json", None), {}, required=True), dict,
            "stored candidate scene is invalid")
        payload["diff"] = _require_type(
            _load(payload.pop("diff_json", None), {}, required=True), dict,
            "stored candidate diff is invalid")
        payload["notes"] = _require_type(
            _load(payload.pop("notes_json", None), [], required=True), list,
            "stored candidate notes are invalid")
        payload["selected"] = bool(payload.get("selected"))
        return payload

    # --- worlds ---------------------------------------------------------------
    async def save_world(self, world: dict, items: list[dict] | None = None) -> None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            await self._insert_world_tx(db, world, items or [])
            await db.commit()
        finally:
            await db.close()

    async def save_world_bundle(self, *, session_id: str, world: dict, items: list[dict],
                                event_type: str, event_payload: dict) -> int:
        async with self.write_transaction() as db:
            await self._insert_world_tx(db, world, items)
            return await self._insert_event_tx(db, session_id, event_type, event_payload)

    @staticmethod
    async def _insert_world_tx(db: aiosqlite.Connection, world: dict, items: list[dict]) -> None:
        await db.execute(
            """INSERT INTO animus_studio_worlds
               (world_id, name, description, scene_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (world["world_id"], world["name"], world.get("description", ""),
             _json(world["scene"]), world["created_at"]),
        )
        for item in items:
            await db.execute(
                """INSERT INTO animus_studio_world_items
                   (item_id, world_id, label, kind, scene_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item["item_id"], world["world_id"], item["label"], item["kind"],
                 _json(item["scene"]), item["created_at"]),
            )

    async def list_worlds(self, limit: int = 50) -> list[dict]:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_worlds ORDER BY created_at DESC LIMIT ?", (limit,))
            return [self._world_row(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    async def get_world(self, world_id: str) -> dict | None:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "SELECT * FROM animus_studio_worlds WHERE world_id = ?", (world_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            world = self._world_row(row)
            cursor = await db.execute(
                "SELECT * FROM animus_studio_world_items WHERE world_id = ? ORDER BY label", (world_id,))
            world["items"] = [self._world_item_row(item) for item in await cursor.fetchall()]
            return world
        finally:
            await db.close()

    async def delete_world(self, world_id: str) -> bool:
        await self.ensure_schema()
        db = await self._connect()
        try:
            cursor = await db.execute(
                "DELETE FROM animus_studio_worlds WHERE world_id = ?", (world_id,))
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    @staticmethod
    def _world_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["scene"] = _require_type(
            _load(payload.pop("scene_json", None), {}, required=True), dict,
            "stored world scene is invalid")
        return payload

    @staticmethod
    def _world_item_row(row: aiosqlite.Row) -> dict:
        payload = dict(row)
        payload["scene"] = _require_type(
            _load(payload.pop("scene_json", None), {}, required=True), dict,
            "stored world item scene is invalid")
        return payload


__all__ = ["StudioRepository"]
