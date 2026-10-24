"""v014: ANIMUS Studio product persistence (sessions, versions, branches, events, candidates, worlds)."""

VERSION = 14
DESCRIPTION = "ANIMUS Studio scene sessions, revisions, branches, candidates, and worlds"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS animus_studio_sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        intention TEXT NOT NULL DEFAULT '',
        mode TEXT NOT NULL DEFAULT 'amplifier',
        status TEXT NOT NULL DEFAULT 'active',
        seed INTEGER NOT NULL,
        claim_level TEXT NOT NULL DEFAULT 'L1_BEHAVIORAL_ASSISTED',
        active_branch_id TEXT NOT NULL,
        active_version_id TEXT NOT NULL,
        privacy_scope TEXT NOT NULL DEFAULT 'local_only',
        warnings_json TEXT NOT NULL DEFAULT '[]',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_versions (
        version_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        number INTEGER NOT NULL,
        branch_id TEXT NOT NULL,
        parent_version_id TEXT,
        scene_json TEXT NOT NULL,
        commands_json TEXT NOT NULL DEFAULT '[]',
        diff_json TEXT NOT NULL DEFAULT '{}',
        source TEXT NOT NULL,
        label TEXT NOT NULL DEFAULT '',
        intention TEXT,
        claim_level TEXT NOT NULL DEFAULT 'L1_BEHAVIORAL_ASSISTED',
        generator TEXT NOT NULL DEFAULT 'compose.v1',
        content_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(session_id, number)
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_branches (
        branch_id TEXT NOT NULL,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        head_version_id TEXT NOT NULL,
        parent_branch_id TEXT,
        fork_version_id TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (session_id, branch_id)
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        version_id TEXT,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_candidates (
        candidate_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        source_version_id TEXT NOT NULL,
        variant_index INTEGER NOT NULL,
        scene_json TEXT NOT NULL,
        diff_json TEXT NOT NULL DEFAULT '{}',
        notes_json TEXT NOT NULL DEFAULT '[]',
        selected INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        version_id TEXT NOT NULL,
        op TEXT NOT NULL,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_worlds (
        world_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        scene_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_world_items (
        item_id TEXT PRIMARY KEY,
        world_id TEXT NOT NULL REFERENCES animus_studio_worlds(world_id) ON DELETE CASCADE,
        label TEXT NOT NULL,
        kind TEXT NOT NULL,
        scene_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_studio_versions_session ON animus_studio_versions(session_id, number)",
    "CREATE INDEX IF NOT EXISTS idx_studio_versions_branch ON animus_studio_versions(session_id, branch_id, number)",
    "CREATE INDEX IF NOT EXISTS idx_studio_events_session ON animus_studio_events(session_id, seq)",
    "CREATE INDEX IF NOT EXISTS idx_studio_candidates_session ON animus_studio_candidates(session_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_studio_world_items_world ON animus_studio_world_items(world_id)",
]


async def upgrade(db) -> None:
    for stmt in STATEMENTS:
        await db.execute(stmt)
    await db.commit()
