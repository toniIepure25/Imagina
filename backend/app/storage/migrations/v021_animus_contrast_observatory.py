"""v021: Scene Threshold contrast sessions and observatory metadata.

Additive and non-destructive. Existing ERI interviews and practice trials remain readable; the new
tables store the source version, deterministic pair parameters, server-only target side, and the
per-trial score needed to reproduce a threshold.
"""
from __future__ import annotations

VERSION = 21
DESCRIPTION = "ANIMUS Scene Threshold contrast sessions, trials, and observatory metadata"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS animus_studio_contrast_sessions (
        contrast_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        source_version_id TEXT NOT NULL,
        scene_hash TEXT NOT NULL,
        protocol_version TEXT NOT NULL,
        form_id TEXT NOT NULL DEFAULT 'A',
        seed INTEGER NOT NULL,
        max_trials INTEGER NOT NULL DEFAULT 16,
        difficulty REAL NOT NULL DEFAULT 0.45,
        occasion TEXT NOT NULL DEFAULT 'baseline',
        delay_hours REAL,
        reflection_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS animus_studio_contrast_trials (
        trial_id TEXT PRIMARY KEY,
        contrast_id TEXT NOT NULL
            REFERENCES animus_studio_contrast_sessions(contrast_id) ON DELETE CASCADE,
        trial_index INTEGER NOT NULL,
        task_id TEXT NOT NULL,
        feature_type TEXT NOT NULL,
        feature_key TEXT NOT NULL,
        delta REAL,
        staircase_level REAL,
        target_side TEXT NOT NULL,
        chosen_option_id TEXT,
        correct INTEGER,
        confidence REAL,
        abstained INTEGER NOT NULL DEFAULT 0,
        latency_ms INTEGER,
        client_trial_id TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(contrast_id, trial_index),
        UNIQUE(contrast_id, client_trial_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_studio_contrast_session "
    "ON animus_studio_contrast_sessions(session_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_studio_contrast_scene "
    "ON animus_studio_contrast_sessions(scene_hash, form_id, occasion)",
    "CREATE INDEX IF NOT EXISTS idx_studio_contrast_trials "
    "ON animus_studio_contrast_trials(contrast_id, trial_index)",
]


async def upgrade(db) -> None:
    for statement in STATEMENTS:
        await db.execute(statement)
    await db.commit()
