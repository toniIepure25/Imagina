"""v012: Add content_hash_match column to objective_replay_runs."""

VERSION = 12
DESCRIPTION = "Persist content_hash_match verification flag for objective replay runs"


async def upgrade(db) -> None:
    try:
        await db.execute(
            "ALTER TABLE objective_replay_runs ADD COLUMN content_hash_match INTEGER NOT NULL DEFAULT 0"
        )
    except Exception:
        pass
    await db.commit()
