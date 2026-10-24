"""v019: reconstruction task metadata and error profiles for the ANIMUS instrument.

Additive columns keep v018 trial data readable and allow old task rows to be scored as the legacy family.
No scene, neural, identity, or network content is added.
"""
from __future__ import annotations

VERSION = 19
DESCRIPTION = "ANIMUS Studio reconstruction task family, response kind, scoring version, and error profiles"

STATEMENTS = [
    "ALTER TABLE animus_studio_trials ADD COLUMN task_family TEXT NOT NULL DEFAULT 'legacy'",
    "ALTER TABLE animus_studio_trials ADD COLUMN response_kind TEXT NOT NULL DEFAULT 'option'",
    "ALTER TABLE animus_studio_trials ADD COLUMN scoring_version TEXT NOT NULL DEFAULT 'v1'",
    "ALTER TABLE animus_studio_trials ADD COLUMN error_profile_json TEXT NOT NULL DEFAULT '{}'",
    "CREATE INDEX IF NOT EXISTS idx_studio_trials_family ON animus_studio_trials(task_family, created_at)",
]


async def upgrade(db) -> None:
    for statement in STATEMENTS:
        await db.execute(statement)
    await db.commit()
