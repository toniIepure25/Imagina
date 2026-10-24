"""v009: Add leakage audit, trial transition, replay run, and outbox tables."""

VERSION = 9
DESCRIPTION = "Persist leakage audits, trial transitions, replay runs, and objective outbox"


async def upgrade(db) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_leakage_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL REFERENCES objective_task_blocks(id),
            trial_id TEXT NOT NULL,
            passed INTEGER NOT NULL,
            violations TEXT NOT NULL DEFAULT '[]',
            policy_fields TEXT NOT NULL DEFAULT '[]',
            checked_fields TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_trial_transitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL REFERENCES objective_task_blocks(id),
            trial_spec_id INTEGER REFERENCES objective_trial_specs(id),
            trial_index INTEGER NOT NULL,
            from_state TEXT NOT NULL,
            to_state TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_replay_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            exact_match INTEGER NOT NULL,
            manifest_verified INTEGER NOT NULL DEFAULT 0,
            seal_verified INTEGER NOT NULL DEFAULT 0,
            schedule_verified INTEGER NOT NULL DEFAULT 0,
            scoring_verified INTEGER NOT NULL DEFAULT 0,
            response_provider_verified INTEGER NOT NULL DEFAULT 0,
            n_divergences INTEGER NOT NULL DEFAULT 0,
            original_content_hash TEXT,
            replayed_content_hash TEXT,
            replay_version TEXT NOT NULL DEFAULT '1.0',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_replay_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            replay_run_id INTEGER NOT NULL REFERENCES objective_replay_runs(id),
            trial_index INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            original_value TEXT,
            replayed_value TEXT,
            divergence_magnitude REAL,
            match INTEGER NOT NULL DEFAULT 1
        )
    """)

    await db.execute("""
        CREATE TABLE IF NOT EXISTS objective_outbox_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL REFERENCES objective_task_blocks(id),
            event_type TEXT NOT NULL,
            trial_index INTEGER,
            payload TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.commit()
