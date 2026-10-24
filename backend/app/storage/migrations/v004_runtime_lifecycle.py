"""v004 — Additive columns for runtime lifecycle hardening.

Adds current_phase and state_version to runtime_runs,
and dispatch_attempts/last_error to runtime_event_outbox.
"""
VERSION = 4
DESCRIPTION = "Runtime lifecycle hardening columns"


_ALTERS = [
    "ALTER TABLE runtime_runs ADD COLUMN current_phase TEXT DEFAULT 'created'",
    "ALTER TABLE runtime_runs ADD COLUMN prepared_sessions INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE runtime_runs ADD COLUMN state_version INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE runtime_runs ADD COLUMN updated_at TEXT",
    "ALTER TABLE runtime_event_outbox ADD COLUMN dispatch_attempts INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE runtime_event_outbox ADD COLUMN last_error TEXT",
]


async def upgrade(db) -> None:
    for stmt in _ALTERS:
        try:
            await db.execute(stmt)
        except Exception:
            pass
    await db.commit()
