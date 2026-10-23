"""v015: scope Studio branch identity to its session.

v014 declared `branch_id` as a global primary key. Every session uses the `main` branch id, so
saving a second session's root branch overwrote the first session's branch row. Versions and
sessions were unaffected, but a process restart could not rebuild history for the overwritten
session.

The table is rebuilt with `PRIMARY KEY (session_id, branch_id)`, and any branch rows that were
lost are reconstructed from the immutable version rows.
"""

VERSION = 15
DESCRIPTION = "Scope ANIMUS Studio branches by session and repair missing branch rows"

_CREATE = """CREATE TABLE IF NOT EXISTS animus_studio_branches_v2 (
    branch_id TEXT NOT NULL,
    session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    head_version_id TEXT NOT NULL,
    parent_branch_id TEXT,
    fork_version_id TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (session_id, branch_id)
)"""

_REPAIR = """INSERT OR IGNORE INTO animus_studio_branches
    (branch_id, session_id, name, head_version_id, parent_branch_id, fork_version_id, created_at)
SELECT
    v.branch_id,
    v.session_id,
    CASE WHEN v.branch_id = 'main' THEN 'Main' ELSE v.branch_id END,
    (
        SELECT v2.version_id
        FROM animus_studio_versions v2
        WHERE v2.session_id = v.session_id AND v2.branch_id = v.branch_id
        ORDER BY v2.number DESC
        LIMIT 1
    ),
    NULL,
    NULL,
    MIN(v.created_at)
FROM animus_studio_versions v
GROUP BY v.session_id, v.branch_id"""


async def upgrade(db) -> None:
    cursor = await db.execute("PRAGMA table_info(animus_studio_branches)")
    columns = await cursor.fetchall()
    if not columns:
        # A partially initialized database may have v014 recorded without the branch table. Build the
        # scoped table directly; there is no legacy row to copy.
        await db.execute("DROP TABLE IF EXISTS animus_studio_branches_v2")
        await db.execute(_CREATE)
        await db.execute("ALTER TABLE animus_studio_branches_v2 RENAME TO animus_studio_branches")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_studio_branches_session "
            "ON animus_studio_branches(session_id, created_at)"
        )
        await db.execute(_REPAIR)
        await db.commit()
        return

    primary_key_columns = [row for row in columns if row[5]]
    if len(primary_key_columns) > 1:
        await db.execute(_REPAIR)
        await db.commit()
        return

    await db.execute("DROP TABLE IF EXISTS animus_studio_branches_v2")
    await db.execute(_CREATE)
    await db.execute(
        """INSERT OR IGNORE INTO animus_studio_branches_v2
           (branch_id, session_id, name, head_version_id, parent_branch_id, fork_version_id, created_at)
           SELECT branch_id, session_id, name, head_version_id, parent_branch_id, fork_version_id, created_at
           FROM animus_studio_branches"""
    )
    await db.execute("DROP TABLE animus_studio_branches")
    await db.execute("ALTER TABLE animus_studio_branches_v2 RENAME TO animus_studio_branches")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_studio_branches_session "
        "ON animus_studio_branches(session_id, created_at)"
    )
    await db.execute(_REPAIR)
    await db.commit()
