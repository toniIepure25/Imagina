"""v018: local behavioral measurement for the ANIMUS Imagination Instrument.

Adds a single local profile, per-dimension posterior summaries, practice trials, and protocol runs.
Everything is additive and local-only; no table stores neural content or identity data. The fixed profile
row makes the first measurement usable without an account while keeping every estimate scoped to this
installation.
"""
from __future__ import annotations

VERSION = 18
DESCRIPTION = "ANIMUS Studio behavioral profile, practice trials, and protocol runs"

PROFILE_ID = "local_default"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS animus_studio_profiles (
        profile_id TEXT PRIMARY KEY,
        profile_version TEXT NOT NULL,
        consent_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_profile_estimates (
        profile_id TEXT NOT NULL REFERENCES animus_studio_profiles(profile_id) ON DELETE CASCADE,
        dimension TEXT NOT NULL,
        estimate REAL,
        uncertainty REAL,
        n INTEGER NOT NULL DEFAULT 0,
        reliability REAL NOT NULL DEFAULT 0,
        stats_json TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (profile_id, dimension)
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_protocols (
        protocol_id TEXT PRIMARY KEY,
        version TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        spec_json TEXT NOT NULL,
        builtin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_protocol_runs (
        run_id TEXT PRIMARY KEY,
        protocol_id TEXT NOT NULL REFERENCES animus_studio_protocols(protocol_id),
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'active',
        current_index INTEGER NOT NULL DEFAULT 0,
        total_trials INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_trials (
        trial_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        profile_id TEXT NOT NULL REFERENCES animus_studio_profiles(profile_id) ON DELETE CASCADE,
        protocol_run_id TEXT REFERENCES animus_studio_protocol_runs(run_id) ON DELETE SET NULL,
        client_trial_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        dimension TEXT NOT NULL,
        difficulty REAL NOT NULL DEFAULT 0.5,
        stimulus_json TEXT NOT NULL,
        response_json TEXT NOT NULL,
        outcome_json TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 0.0,
        latency_ms INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(session_id, client_trial_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_studio_trials_session ON animus_studio_trials(session_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_studio_trials_profile ON animus_studio_trials(profile_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_studio_protocol_runs_session ON animus_studio_protocol_runs(session_id, status)",
]


async def upgrade(db) -> None:
    for statement in STATEMENTS:
        await db.execute(statement)
    await db.execute(
        """INSERT INTO animus_studio_profiles (profile_id, profile_version, consent_json)
           VALUES (?, 'ANIMUS-PROFILE-v1', '{}')
           ON CONFLICT(profile_id) DO NOTHING""",
        (PROFILE_ID,),
    )
    await db.commit()
