"""v003: Persistent synthetic runtime schema.

Adds tables for research sessions, trials, feedback records, safety events,
frozen yoked trajectory libraries, session manifests, and export runs.
This migration is additive — no existing v001/v002 tables are modified.
"""

VERSION = 3
DESCRIPTION = "Persistent synthetic runtime: sessions, trials, feedback, safety, yoked, manifests, exports"

_SQL = """
CREATE TABLE IF NOT EXISTS research_sessions (
    research_session_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    protocol_version_id TEXT NOT NULL,
    allocation_id TEXT NOT NULL,
    session_index INTEGER NOT NULL,
    condition TEXT NOT NULL,
    data_classification TEXT NOT NULL CHECK(data_classification IN ('demo','synthetic','usability_nonresearch','human_research')),
    signal_provider_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    stimulus_schedule_hash TEXT,
    runtime_seed INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','ready','running','completed','aborted','withdrawn','invalidated','safety_stopped')),
    state_version INTEGER NOT NULL DEFAULT 0,
    planned_at TEXT NOT NULL,
    ready_at TEXT,
    started_at TEXT,
    ended_at TEXT,
    terminal_reason TEXT,
    manifest_hash TEXT,
    software_version TEXT NOT NULL,
    git_sha TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    FOREIGN KEY (protocol_version_id) REFERENCES protocol_versions(protocol_version_id),
    FOREIGN KEY (allocation_id) REFERENCES sequence_allocations(allocation_id),
    UNIQUE(study_id, participant_id, session_index)
);

CREATE INDEX IF NOT EXISTS idx_research_sessions_study_participant
    ON research_sessions(study_id, participant_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status
    ON research_sessions(study_id, status);

CREATE TABLE IF NOT EXISTS research_session_transitions (
    transition_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,
    reason_code TEXT,
    actor TEXT NOT NULL DEFAULT 'system',
    idempotency_key TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id)
);

CREATE INDEX IF NOT EXISTS idx_session_transitions_session
    ON research_session_transitions(research_session_id);

CREATE TABLE IF NOT EXISTS trials (
    trial_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    trial_index INTEGER NOT NULL,
    stimulus_id TEXT NOT NULL,
    stimulus_version TEXT,
    stimulus_hash TEXT,
    status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','ready','running','completed','aborted','invalidated','safety_stopped')),
    state_version INTEGER NOT NULL DEFAULT 0,
    planned_duration_ms INTEGER,
    planned_iti_ms INTEGER,
    planned_at TEXT NOT NULL,
    ready_at TEXT,
    started_at TEXT,
    ended_at TEXT,
    mono_start REAL,
    mono_end REAL,
    terminal_reason TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id),
    UNIQUE(research_session_id, trial_index)
);

CREATE INDEX IF NOT EXISTS idx_trials_session
    ON trials(research_session_id, trial_index);

CREATE TABLE IF NOT EXISTS trial_transitions (
    transition_id TEXT PRIMARY KEY,
    trial_id TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,
    reason_code TEXT,
    actor TEXT NOT NULL DEFAULT 'system',
    idempotency_key TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
);

CREATE INDEX IF NOT EXISTS idx_trial_transitions_trial
    ON trial_transitions(trial_id);

CREATE TABLE IF NOT EXISTS trial_responses (
    trial_response_id TEXT PRIMARY KEY,
    trial_id TEXT NOT NULL,
    vividness REAL,
    confidence REAL,
    effort REAL,
    imagery_formation_latency_ms REAL,
    rating_completion_latency_ms REAL,
    response_source TEXT NOT NULL DEFAULT 'synthetic' CHECK(response_source IN ('synthetic','human','replay')),
    synthetic_generation_version TEXT,
    recorded_at TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
);

CREATE INDEX IF NOT EXISTS idx_trial_responses_trial
    ON trial_responses(trial_id);

CREATE TABLE IF NOT EXISTS feedback_records (
    feedback_record_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    trial_id TEXT,
    window_index INTEGER NOT NULL,
    condition TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    state_hash TEXT,
    pid_value REAL,
    iqi_value REAL,
    scene_params_json TEXT NOT NULL,
    reason_code TEXT,
    yoked_trajectory_id TEXT,
    yoked_point_index INTEGER,
    safety_override INTEGER NOT NULL DEFAULT 0,
    timestamp_utc TEXT NOT NULL,
    mono_elapsed REAL,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id),
    FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
);

CREATE INDEX IF NOT EXISTS idx_feedback_records_session
    ON feedback_records(research_session_id, window_index);

CREATE TABLE IF NOT EXISTS safety_events (
    safety_event_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    trial_id TEXT,
    severity TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    metric_name TEXT,
    metric_value REAL,
    action_taken TEXT NOT NULL,
    payload_json TEXT,
    timestamp_utc TEXT NOT NULL,
    mono_elapsed REAL,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id),
    FOREIGN KEY (trial_id) REFERENCES trials(trial_id)
);

CREATE INDEX IF NOT EXISTS idx_safety_events_session
    ON safety_events(research_session_id);

CREATE TABLE IF NOT EXISTS frozen_yoked_libraries (
    library_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    protocol_version_id TEXT NOT NULL,
    library_version TEXT NOT NULL DEFAULT '1.0',
    generation_seed INTEGER NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'synthetic_adaptive',
    schedule_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','frozen')),
    created_at TEXT NOT NULL,
    frozen_at TEXT,
    content_hash TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (protocol_version_id) REFERENCES protocol_versions(protocol_version_id)
);

CREATE INDEX IF NOT EXISTS idx_yoked_libraries_study
    ON frozen_yoked_libraries(study_id);

CREATE TABLE IF NOT EXISTS frozen_yoked_trajectories (
    trajectory_id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL,
    trajectory_label TEXT NOT NULL,
    compatible_schedule_hash TEXT NOT NULL,
    window_count INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    source_provenance TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (library_id) REFERENCES frozen_yoked_libraries(library_id),
    UNIQUE(library_id, trajectory_label)
);

CREATE INDEX IF NOT EXISTS idx_yoked_trajectories_library
    ON frozen_yoked_trajectories(library_id);

CREATE TABLE IF NOT EXISTS frozen_yoked_points (
    point_id TEXT PRIMARY KEY,
    trajectory_id TEXT NOT NULL,
    window_index INTEGER NOT NULL,
    scene_params_json TEXT NOT NULL,
    prompt_text TEXT,
    reason_code TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (trajectory_id) REFERENCES frozen_yoked_trajectories(trajectory_id),
    UNIQUE(trajectory_id, window_index)
);

CREATE INDEX IF NOT EXISTS idx_yoked_points_trajectory
    ON frozen_yoked_points(trajectory_id, window_index);

CREATE TABLE IF NOT EXISTS session_manifests (
    manifest_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL UNIQUE,
    manifest_json TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    sealed_at TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id)
);

CREATE TABLE IF NOT EXISTS runtime_runs (
    run_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    status TEXT NOT NULL DEFAULT 'created' CHECK(status IN ('created','running','completed','failed','interrupted','aborted')),
    total_sessions INTEGER NOT NULL DEFAULT 0,
    completed_sessions INTEGER NOT NULL DEFAULT 0,
    failed_sessions INTEGER NOT NULL DEFAULT 0,
    runtime_seed INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    error_message TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_runs_study
    ON runtime_runs(study_id);

CREATE TABLE IF NOT EXISTS runtime_commands (
    command_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    command_type TEXT NOT NULL,
    target_entity_type TEXT,
    target_entity_id TEXT,
    input_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','completed','failed','conflict')),
    result_reference TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error_code TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    UNIQUE(idempotency_key)
);

CREATE TABLE IF NOT EXISTS runtime_event_outbox (
    outbox_id TEXT PRIMARY KEY,
    research_session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT,
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (research_session_id) REFERENCES research_sessions(research_session_id)
);

CREATE INDEX IF NOT EXISTS idx_event_outbox_unpublished
    ON runtime_event_outbox(published_at) WHERE published_at IS NULL;

CREATE TABLE IF NOT EXISTS export_runs (
    export_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    data_classification TEXT NOT NULL,
    filters_json TEXT,
    manifest_hash TEXT,
    file_hashes_json TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL,
    export_schema_version TEXT NOT NULL DEFAULT '1.0',
    schema_version INTEGER NOT NULL DEFAULT 3,
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_export_runs_study
    ON export_runs(study_id);
"""


async def upgrade(db) -> None:
    await db.executescript(_SQL)
