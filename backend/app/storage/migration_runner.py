"""Sequential versioned migration runner for local SQLite.

Each migration is a module in app.storage.migrations with:
  VERSION: int
  DESCRIPTION: str
  async def upgrade(db: aiosqlite.Connection) -> None

Migrations are applied in VERSION order. The schema_version table
tracks which versions have been applied. A migration that fails
does not advance the version.

Usage:
    from app.storage.migration_runner import run_migrations
    await run_migrations(db)
"""
from __future__ import annotations

import importlib
import logging

import aiosqlite

logger = logging.getLogger(__name__)

_MIGRATION_MODULES = [
    "app.storage.migrations.v001_legacy_schema",
    "app.storage.migrations.v002_research_governance",
    "app.storage.migrations.v003_persistent_synthetic_runtime",
    "app.storage.migrations.v004_runtime_lifecycle",
    "app.storage.migrations.v005_completion_seals_and_replay",
    "app.storage.migrations.v006_export_runs_status",
    "app.storage.migrations.v007_objective_measurement",
    "app.storage.migrations.v008_provenance_persistence",
    "app.storage.migrations.v009_objective_audit_tables",
    "app.storage.migrations.v010_science_worker",
    "app.storage.migrations.v011_simulation_checkpoints",
]

_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


async def _ensure_version_table(db: aiosqlite.Connection) -> None:
    await db.execute(_VERSION_TABLE)
    await db.commit()


async def _current_version(db: aiosqlite.Connection) -> int:
    cursor = await db.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_version"
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def current_version(db: aiosqlite.Connection) -> int:
    await _ensure_version_table(db)
    return await _current_version(db)


async def run_migrations(db: aiosqlite.Connection) -> int:
    await _ensure_version_table(db)
    current = await _current_version(db)
    applied = 0

    for module_path in _MIGRATION_MODULES:
        mod = importlib.import_module(module_path)
        version: int = mod.VERSION
        description: str = mod.DESCRIPTION

        if version <= current:
            continue

        logger.info("Applying migration v%03d: %s", version, description)
        try:
            await mod.upgrade(db)
            await db.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (version, description),
            )
            await db.commit()
            applied += 1
            logger.info("Migration v%03d applied successfully", version)
        except Exception:
            logger.exception("Migration v%03d FAILED — rolling back", version)
            await db.rollback()
            raise

    final = await _current_version(db)
    logger.info(
        "Migration complete: was v%03d, now v%03d (%d applied)",
        current, final, applied,
    )
    return final
