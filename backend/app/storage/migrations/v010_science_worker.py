"""v010: Add science worker lease and checkpoint columns to simulation_runs."""

VERSION = 10
DESCRIPTION = "Science worker lease, checkpoint, and abort columns"


_ALTERS = [
    "ALTER TABLE simulation_runs ADD COLUMN lease_owner TEXT",
    "ALTER TABLE simulation_runs ADD COLUMN lease_acquired_at TEXT",
    "ALTER TABLE simulation_runs ADD COLUMN lease_expires_at TEXT",
    "ALTER TABLE simulation_runs ADD COLUMN heartbeat_at TEXT",
    "ALTER TABLE simulation_runs ADD COLUMN abort_requested INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE simulation_runs ADD COLUMN checkpoint_iteration INTEGER",
    "ALTER TABLE simulation_runs ADD COLUMN worker_attempt INTEGER NOT NULL DEFAULT 0",
]


async def upgrade(db) -> None:
    for stmt in _ALTERS:
        try:
            await db.execute(stmt)
        except Exception:
            pass
    await db.commit()
