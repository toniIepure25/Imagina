"""v020: epistemic reconstruction interviews for the ANIMUS instrument.

Adds an interview header and additive probe metadata to the existing trial ledger. The migration is
local-only and non-destructive: v019 practice rows remain readable, and no target scene or answer is
duplicated into a new table.
"""
from __future__ import annotations

VERSION = 20
DESCRIPTION = "ANIMUS Studio epistemic reconstruction interviews and belief snapshots"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS animus_studio_interviews (
        interview_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES animus_studio_sessions(session_id) ON DELETE CASCADE,
        source_version_id TEXT NOT NULL,
        scene_hash TEXT NOT NULL,
        protocol_version TEXT NOT NULL,
        form_id TEXT NOT NULL DEFAULT 'A',
        seed INTEGER NOT NULL,
        difficulty REAL NOT NULL DEFAULT 0.45,
        max_probes INTEGER NOT NULL DEFAULT 12,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
    )""",
    "ALTER TABLE animus_studio_trials ADD COLUMN interview_id TEXT",
    "ALTER TABLE animus_studio_trials ADD COLUMN probe_index INTEGER",
    "ALTER TABLE animus_studio_trials ADD COLUMN probe_type TEXT",
    "ALTER TABLE animus_studio_trials ADD COLUMN belief_json TEXT NOT NULL DEFAULT '{}'",
    "ALTER TABLE animus_studio_trials ADD COLUMN information_gain REAL",
    "CREATE INDEX IF NOT EXISTS idx_studio_interviews_session "
    "ON animus_studio_interviews(session_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_studio_trials_interview "
    "ON animus_studio_trials(interview_id, probe_index)",
]


async def upgrade(db) -> None:
    for statement in STATEMENTS:
        await db.execute(statement)
    await db.commit()
