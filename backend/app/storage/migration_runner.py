"""Sequential versioned migration runner for local SQLite.

Each migration is a module in app.storage.migrations with:
  VERSION: int
  DESCRIPTION: str
  async def upgrade(db: aiosqlite.Connection) -> None

Migrations are applied in VERSION order. The schema_version table
tracks which versions have been applied. A migration that fails
does not advance the version.

Before a non-empty database is upgraded, a consistent copy is written
with VACUUM INTO under <db_dir>/backups/. If that copy fails, the
runner refuses to migrate rather than risk an unrecoverable upgrade.

Usage:
    from app.storage.migration_runner import run_migrations
    await run_migrations(db)
"""
from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

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
    "app.storage.migrations.v012_replay_content_hash_match",
    "app.storage.migrations.v013_multimodal_sessions",
    "app.storage.migrations.v014_animus_studio",
    "app.storage.migrations.v015_animus_studio_branch_scope",
    "app.storage.migrations.v016_animus_studio_integrity",
    "app.storage.migrations.v017_animus_studio_branch_redo",
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
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    return row[0] if row else 0


async def current_version(db: aiosqlite.Connection) -> int:
    await _ensure_version_table(db)
    return await _current_version(db)


@lru_cache(maxsize=1)
def latest_version() -> int:
    """Return the newest migration version declared by the ordered module list."""
    return max(importlib.import_module(path).VERSION for path in _MIGRATION_MODULES)


async def _has_user_tables(db: aiosqlite.Connection) -> bool:
    cursor = await db.execute(
        """SELECT COUNT(*) FROM sqlite_master
           WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name != 'schema_version'"""
    )
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    return bool(row and row[0])


def _sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def backup_before_migration(
    db: aiosqlite.Connection, *, current: int, target: int
) -> str | None:
    """Create a consistent copy before a migration can change existing data.

    ``VACUUM INTO`` is used instead of copying the main database file because WAL content may not
    have been checkpointed. A backup failure is fatal: refusing to migrate is safer than risking an
    unrecoverable half-upgrade.
    """
    cursor = await db.execute("PRAGMA database_list")
    try:
        row = await cursor.fetchone()
    finally:
        await cursor.close()
    file_path = str(row[2]) if row and row[2] else ""
    if not file_path or file_path == ":memory:":
        return None

    source = Path(file_path).resolve()
    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = backup_dir / f"pre-migration-v{current:03d}-to-v{target:03d}-{stamp}.db"

    try:
        vacuum = await db.execute(f"VACUUM INTO {_sql_string_literal(str(destination))}")
        await vacuum.close()
        verification = await aiosqlite.connect(destination)
        try:
            check = await verification.execute("PRAGMA quick_check")
            try:
                result = await check.fetchone()
            finally:
                await check.close()
        finally:
            await verification.close()
        if not result or str(result[0]).lower() != "ok":
            raise RuntimeError("pre-migration backup failed integrity check")
    except Exception as exc:  # noqa: BLE001 - startup must fail closed on backup failure
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove failed migration backup %s", destination)
        logger.exception(
            "Pre-migration backup failed: current=v%03d target=v%03d path=%s",
            current, target, destination,
        )
        raise RuntimeError("pre-migration backup failed; refusing to migrate") from exc

    logger.info(
        "Pre-migration backup created: current=v%03d target=v%03d path=%s",
        current, target, destination,
    )
    for stale in sorted(
        backup_dir.glob("pre-migration-v*-to-v*.db"), key=lambda path: path.name, reverse=True
    )[5:]:
        try:
            stale.unlink()
        except OSError:
            logger.warning("Could not prune old migration backup %s", stale)
    return str(destination)


async def run_migrations(db: aiosqlite.Connection) -> int:
    await _ensure_version_table(db)
    current = await _current_version(db)
    target = latest_version()
    if current < target and await _has_user_tables(db):
        await backup_before_migration(db, current=current, target=target)
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
