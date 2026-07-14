"""v006: Add status columns to export_runs for validated exports."""

VERSION = 6
DESCRIPTION = "Add status/validation columns to export_runs"


async def upgrade(db) -> None:
    await db.execute("ALTER TABLE export_runs ADD COLUMN status TEXT DEFAULT 'preparing'")
    await db.execute("ALTER TABLE export_runs ADD COLUMN validation_status TEXT")
    await db.execute("ALTER TABLE export_runs ADD COLUMN validation_errors_json TEXT")
    await db.execute("ALTER TABLE export_runs ADD COLUMN finalized_at TEXT")
