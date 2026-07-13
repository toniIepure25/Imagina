"""v005: Completion seals and replay persistence.

Adds append-only session_completion_seals table for immutable seal records,
and replay_runs / replay_results tables for persisted replay outcomes.
"""

VERSION = 5
DESCRIPTION = "Completion seals (append-only) and replay persistence"

_SQL = """
CREATE TABLE IF NOT EXISTS session_completion_seals (
    completion_seal_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    manifest_id TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    terminal_status TEXT NOT NULL,
    terminal_reason TEXT,
    scientific_content_hash TEXT NOT NULL,
    canonicalization_version TEXT NOT NULL,
    sealed_at TEXT NOT NULL,
    seal_hash TEXT NOT NULL,
    software_version TEXT NOT NULL,
    git_sha TEXT,
    schema_version INTEGER NOT NULL DEFAULT 5,
    UNIQUE(research_session_id),
    FOREIGN KEY (research_session_id)
        REFERENCES research_sessions(research_session_id),
    FOREIGN KEY (manifest_id)
        REFERENCES session_manifests(manifest_id)
);

CREATE INDEX IF NOT EXISTS idx_completion_seals_session
    ON session_completion_seals(research_session_id);

CREATE TABLE IF NOT EXISTS replay_runs (
    replay_run_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    manifest_id TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    seal_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','running','completed','failed')),
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    schema_version INTEGER NOT NULL DEFAULT 5,
    FOREIGN KEY (research_session_id)
        REFERENCES research_sessions(research_session_id),
    FOREIGN KEY (manifest_id)
        REFERENCES session_manifests(manifest_id)
);

CREATE INDEX IF NOT EXISTS idx_replay_runs_session
    ON replay_runs(research_session_id);

CREATE TABLE IF NOT EXISTS replay_results (
    replay_result_id TEXT PRIMARY KEY,
    replay_run_id TEXT NOT NULL,
    research_session_id TEXT NOT NULL,
    original_content_hash TEXT NOT NULL,
    replay_content_hash TEXT NOT NULL,
    seal_content_hash TEXT NOT NULL,
    match INTEGER NOT NULL DEFAULT 0,
    divergence_json TEXT,
    canonicalization_version TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 5,
    FOREIGN KEY (replay_run_id)
        REFERENCES replay_runs(replay_run_id),
    FOREIGN KEY (research_session_id)
        REFERENCES research_sessions(research_session_id),
    UNIQUE(replay_run_id)
);

CREATE INDEX IF NOT EXISTS idx_replay_results_session
    ON replay_results(research_session_id);
"""


async def upgrade(db) -> None:
    await db.executescript(_SQL)
