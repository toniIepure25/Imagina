"""SQLite table schemas — kept as raw SQL for aiosqlite (no ORM dependency)."""

TABLES = {
    "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            display_name TEXT,
            mode TEXT NOT NULL DEFAULT 'simulated',
            status TEXT NOT NULL DEFAULT 'created',
            task_id TEXT NOT NULL DEFAULT 'corridor_simple',
            created_at TEXT NOT NULL,
            started_at TEXT,
            ended_at TEXT,
            safety_disclaimer_acknowledged INTEGER NOT NULL DEFAULT 0,
            baseline_json TEXT
        )
    """,
    "events": """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload TEXT NOT NULL,
            schema_version TEXT NOT NULL DEFAULT '1.0',
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """,
    "events_idx": """
        CREATE INDEX IF NOT EXISTS idx_events_session
        ON events(session_id, timestamp)
    """,
}
