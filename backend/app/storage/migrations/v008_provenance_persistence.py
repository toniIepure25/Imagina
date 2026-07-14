"""v008: Add objective manifests and completion seals tables for provenance persistence."""

VERSION = 8
DESCRIPTION = "Persist objective manifests and completion seals"


async def upgrade(db) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_manifests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            manifest_hash TEXT NOT NULL,
            manifest_json TEXT NOT NULL,
            provenance_version TEXT NOT NULL DEFAULT '1.0',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_completion_seals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            seal_hash TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            manifest_hash TEXT NOT NULL,
            trial_count INTEGER NOT NULL,
            target_hash TEXT NOT NULL,
            response_hash TEXT NOT NULL,
            score_hash TEXT NOT NULL,
            rating_hash TEXT NOT NULL,
            leakage_audit_hash TEXT NOT NULL,
            calibration_ref TEXT,
            valid INTEGER NOT NULL DEFAULT 1,
            seal_version TEXT NOT NULL DEFAULT '1.0',
            seal_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(study_id, session_id)
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS replay_divergences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            trial_index INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            original_value TEXT,
            replay_value TEXT,
            divergence_magnitude REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.commit()
