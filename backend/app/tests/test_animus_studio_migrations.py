"""Migration repair tests for the Studio branch/redo schema."""
from __future__ import annotations

import os
import tempfile

import aiosqlite
import pytest

from app.storage.migrations import (
    v014_animus_studio,
    v015_animus_studio_branch_scope,
    v017_animus_studio_branch_redo,
)

pytestmark = pytest.mark.core

_LEGACY_BRANCHES = """
CREATE TABLE animus_studio_branches (
    branch_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    head_version_id TEXT NOT NULL,
    parent_branch_id TEXT,
    fork_version_id TEXT,
    created_at TEXT NOT NULL
)
"""


@pytest.fixture
async def legacy_db():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "legacy.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await v014_animus_studio.upgrade(db)
        await db.executescript("DROP TABLE animus_studio_branches")
        await db.executescript(_LEGACY_BRANCHES)
        for session_id, version_id in (("s1", "v1"), ("s2", "v2")):
            await db.execute(
                """INSERT INTO animus_studio_sessions
                   (session_id, title, seed, active_branch_id, active_version_id)
                   VALUES (?, ?, 1, 'main', ?)""",
                (session_id, session_id, version_id),
            )
            await db.execute(
                """INSERT INTO animus_studio_versions
                   (version_id, session_id, number, branch_id, scene_json, source, content_hash, created_at)
                   VALUES (?, ?, 1, 'main', '{}', 'generated', 'hash', '2026-01-01T00:00:00Z')""",
                (version_id, session_id),
            )
        # This is the v014 failure mode: the second session's main branch overwrote the first row.
        await db.execute(
            """INSERT INTO animus_studio_branches
               (branch_id, session_id, name, head_version_id, created_at)
               VALUES ('main', 's2', 'Main', 'v2', '2026-01-01T00:00:00Z')"""
        )
        await db.commit()
        yield db
        await db.close()


async def test_v015_rebuilds_scoped_branches_and_repairs_missing_main(legacy_db):
    await v015_animus_studio_branch_scope.upgrade(legacy_db)
    cursor = await legacy_db.execute(
        "SELECT session_id, head_version_id FROM animus_studio_branches ORDER BY session_id"
    )
    rows = await cursor.fetchall()
    assert [(row["session_id"], row["head_version_id"]) for row in rows] == [("s1", "v1"), ("s2", "v2")]


async def test_v017_adds_redo_column_idempotently(legacy_db):
    await v015_animus_studio_branch_scope.upgrade(legacy_db)
    await v017_animus_studio_branch_redo.upgrade(legacy_db)
    await v017_animus_studio_branch_redo.upgrade(legacy_db)
    cursor = await legacy_db.execute("PRAGMA table_info(animus_studio_branches)")
    columns = {row["name"] for row in await cursor.fetchall()}
    assert "redo_json" in columns
    cursor = await legacy_db.execute("SELECT DISTINCT redo_json FROM animus_studio_branches")
    assert [row[0] for row in await cursor.fetchall()] == ["[]"]
