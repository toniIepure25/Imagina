import os

import aiosqlite

DB_PATH = os.environ.get("IMAGINA_DB_PATH", "data/imagina.db")

_SCHEMA = """
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

CREATE TABLE IF NOT EXISTS studies (
    study_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    pseudonym TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_participants_study ON participants(study_id);

CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    consented_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_consents_participant ON consents(participant_id, study_id);

CREATE TABLE IF NOT EXISTS condition_assignments (
    assignment_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    session_index INTEGER NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    UNIQUE(participant_id, study_id, session_index)
);
"""

_SESSION_MIGRATIONS = {
    "signal_provider_id": (
        "ALTER TABLE sessions ADD COLUMN signal_provider_id TEXT NOT NULL DEFAULT 'simulated.default'"
    ),
    "scenario": "ALTER TABLE sessions ADD COLUMN scenario TEXT",
    "experiment_run_id": "ALTER TABLE sessions ADD COLUMN experiment_run_id TEXT",
}


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(_SCHEMA)
        cursor = await db.execute("PRAGMA table_info(sessions)")
        existing_columns = {row["name"] for row in await cursor.fetchall()}
        for column, statement in _SESSION_MIGRATIONS.items():
            if column not in existing_columns:
                await db.execute(statement)
        await db.commit()
    finally:
        await db.close()
