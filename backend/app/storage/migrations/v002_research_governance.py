"""v002: Research governance tables — studies, protocols, ethics, consent, participants, allocations, audit.

Normalized relational tables for the research platform. Key fields are
stored as columns with constraints; extensible metadata goes in payload JSON.
"""

VERSION = 2
DESCRIPTION = "Research governance: studies, protocols, ethics, consents, participants, allocations, audit"

_SQL = """
CREATE TABLE IF NOT EXISTS studies (
    study_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    application_mode TEXT NOT NULL DEFAULT 'demo',
    data_classification TEXT NOT NULL DEFAULT 'synthetic',
    lifecycle_status TEXT NOT NULL DEFAULT 'draft',
    active_protocol_version_id TEXT,
    study_seed INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS protocol_versions (
    protocol_version_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    frozen_at TEXT,
    protocol_hash TEXT,
    created_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    UNIQUE(study_id, version)
);

CREATE INDEX IF NOT EXISTS idx_protocol_versions_study ON protocol_versions(study_id);

CREATE TABLE IF NOT EXISTS ethics_reviews (
    ethics_review_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    protocol_version_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_submitted',
    reference TEXT NOT NULL DEFAULT '',
    valid_from TEXT,
    valid_until TEXT,
    recorded_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (protocol_version_id) REFERENCES protocol_versions(protocol_version_id)
);

CREATE INDEX IF NOT EXISTS idx_ethics_reviews_study ON ethics_reviews(study_id);

CREATE TABLE IF NOT EXISTS consent_document_versions (
    consent_document_version_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    protocol_version_id TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    content_hash TEXT,
    effective_from TEXT,
    superseded_at TEXT,
    created_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (protocol_version_id) REFERENCES protocol_versions(protocol_version_id),
    UNIQUE(study_id, version)
);

CREATE INDEX IF NOT EXISTS idx_consent_doc_versions_study ON consent_document_versions(study_id);

CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    pseudonym TEXT NOT NULL,
    participant_kind TEXT NOT NULL DEFAULT 'synthetic',
    eligibility_confirmed INTEGER NOT NULL DEFAULT 0,
    withdrawn_at TEXT,
    created_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    UNIQUE(study_id, pseudonym)
);

CREATE INDEX IF NOT EXISTS idx_participants_study ON participants(study_id);

CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    protocol_version_id TEXT,
    consent_document_version_id TEXT,
    consented_at TEXT NOT NULL,
    withdrawn_at TEXT,
    withdrawal_reason_code TEXT,
    payload TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id)
);

CREATE INDEX IF NOT EXISTS idx_consents_participant ON consents(participant_id, study_id);

CREATE TABLE IF NOT EXISTS sequence_allocations (
    allocation_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    sequence_id TEXT NOT NULL,
    sequence_label TEXT NOT NULL,
    study_seed INTEGER,
    tie_break_value INTEGER,
    allocated_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    UNIQUE(study_id, participant_id)
);

CREATE INDEX IF NOT EXISTS idx_sequence_allocations_study ON sequence_allocations(study_id);

CREATE TABLE IF NOT EXISTS condition_assignments (
    assignment_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    study_id TEXT NOT NULL,
    session_index INTEGER NOT NULL,
    condition TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    payload TEXT,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id),
    FOREIGN KEY (study_id) REFERENCES studies(study_id),
    UNIQUE(participant_id, study_id, session_index)
);

CREATE INDEX IF NOT EXISTS idx_condition_assignments_participant
    ON condition_assignments(participant_id, study_id);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_event_id TEXT PRIMARY KEY,
    study_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_events_entity
    ON audit_events(entity_type, entity_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_study
    ON audit_events(study_id, timestamp);
"""

_DROP_OLD_RESEARCH = """
DROP TABLE IF EXISTS condition_assignments;
DROP TABLE IF EXISTS consents;
DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS studies;
"""


async def upgrade(db) -> None:
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='studies'"
    )
    old_studies = await cursor.fetchone()

    if old_studies:
        cursor2 = await db.execute("PRAGMA table_info(studies)")
        columns = {row[1] for row in await cursor2.fetchall()}
        if "lifecycle_status" not in columns:
            await db.executescript(_DROP_OLD_RESEARCH)

    await db.executescript(_SQL)
