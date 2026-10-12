"""v013: Durable multimodal closed-loop sessions (metadata, decisions, safety events, feedback, calibrations)."""

VERSION = 13
DESCRIPTION = "Multimodal session persistence and recovery state"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS mm_sessions (
        session_id TEXT PRIMARY KEY,
        participant_pseudo_id TEXT NOT NULL,
        status TEXT NOT NULL,
        mode TEXT NOT NULL,
        policy TEXT NOT NULL,
        source_kinds TEXT NOT NULL,
        modality_config TEXT NOT NULL,
        experiment_params TEXT NOT NULL,
        calibration_version INTEGER,
        model_versions TEXT NOT NULL DEFAULT '{}',
        recovery_state TEXT NOT NULL DEFAULT '{}',
        last_tick INTEGER NOT NULL DEFAULT 0,
        last_t REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS mm_decisions (
        session_id TEXT NOT NULL REFERENCES mm_sessions(session_id) ON DELETE CASCADE,
        tick INTEGER NOT NULL,
        t REAL NOT NULL,
        controller_state TEXT NOT NULL,
        delivered INTEGER NOT NULL,
        hash TEXT NOT NULL,
        prev_hash TEXT NOT NULL,
        decision TEXT NOT NULL,
        PRIMARY KEY (session_id, tick)
    )""",
    """CREATE TABLE IF NOT EXISTS mm_safety_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES mm_sessions(session_id) ON DELETE CASCADE,
        tick INTEGER NOT NULL,
        t REAL NOT NULL,
        code TEXT NOT NULL,
        severity TEXT NOT NULL,
        detail TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS mm_feedback_actions (
        session_id TEXT NOT NULL REFERENCES mm_sessions(session_id) ON DELETE CASCADE,
        tick INTEGER NOT NULL,
        action_id TEXT NOT NULL,
        delivered INTEGER NOT NULL,
        action TEXT NOT NULL,
        PRIMARY KEY (session_id, tick)
    )""",
    """CREATE TABLE IF NOT EXISTS mm_calibrations (
        session_id TEXT NOT NULL REFERENCES mm_sessions(session_id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        profile TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (session_id, version)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_mm_safety_session ON mm_safety_events(session_id, tick)",
]


async def upgrade(db) -> None:
    for stmt in STATEMENTS:
        await db.execute(stmt)
    await db.commit()
