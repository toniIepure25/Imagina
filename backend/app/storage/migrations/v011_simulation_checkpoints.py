"""v011: Add simulation_checkpoints table for accumulator persistence."""

VERSION = 11
DESCRIPTION = "Simulation checkpoint accumulator persistence"


async def upgrade(db) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS simulation_checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL UNIQUE REFERENCES simulation_runs(id),
            checkpoint_iteration INTEGER NOT NULL,
            accumulator_json TEXT NOT NULL,
            accumulator_hash TEXT NOT NULL,
            last_completed_seed INTEGER NOT NULL,
            checkpoint_version TEXT NOT NULL DEFAULT '1.0',
            updated_at TEXT NOT NULL
        )
    """)
    await db.commit()
