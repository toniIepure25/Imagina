"""v001: Legacy schema — sessions, events, calibrations, user_profiles, experiment_runs.

This migration creates the original IMAGINA tables if they don't exist.
For databases that already have these tables, all statements are idempotent.
"""

VERSION = 1
DESCRIPTION = "Legacy schema: sessions, events, calibrations, user_profiles, experiment_runs"

_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    display_name TEXT,
    mode TEXT NOT NULL DEFAULT 'simulated',
    status TEXT NOT NULL DEFAULT 'created',
    task_id TEXT NOT NULL DEFAULT 'corridor_simple',
    signal_provider_id TEXT NOT NULL DEFAULT 'simulated.default',
    scenario TEXT,
    experiment_run_id TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    safety_disclaimer_acknowledged INTEGER NOT NULL DEFAULT 0,
    baseline_json TEXT
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, timestamp);

CREATE TABLE IF NOT EXISTS calibrations (
    calibration_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_calibrations_session ON calibrations(session_id, created_at);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    protocol_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experiment_runs_protocol ON experiment_runs(protocol_id, started_at);
"""


async def upgrade(db) -> None:
    await db.executescript(_SQL)
