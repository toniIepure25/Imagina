"""Typed records shared by the Studio service, repository, and event bus.

These TypedDicts describe the dictionaries that cross internal boundaries. They are intentionally
runtime-free: the service still returns plain JSON-compatible dictionaries, while type checkers and
reviewers get one authoritative description of each persisted shape. The public HTTP contract lives in
``app.schemas.animus_studio_responses``; these types describe storage and internal payloads.
"""
from __future__ import annotations

from typing import Any, TypedDict


class _StudioSessionOptional(TypedDict, total=False):
    metadata: dict[str, Any]
    warnings: list[str]


class StudioSessionRecord(_StudioSessionOptional):
    session_id: str
    title: str
    intention: str
    mode: str
    status: str
    seed: int
    privacy_scope: str
    claim_level: str
    active_branch_id: str
    active_version_id: str
    created_at: str
    updated_at: str


class StudioBranchRecord(TypedDict):
    branch_id: str
    session_id: str
    name: str
    head_version_id: str
    parent_branch_id: str | None
    fork_version_id: str | None
    created_at: str


class StudioBranchSummaryRecord(StudioBranchRecord):
    is_active: bool


class StudioVersionSummaryRecord(TypedDict):
    version_id: str
    number: int
    branch_id: str
    parent_version_id: str | None
    source: str
    label: str
    intention: str | None
    claim_level: str
    created_at: str
    content_hash: str
    entity_count: int


class StudioVersionRecord(StudioVersionSummaryRecord):
    scene: dict[str, Any]
    commands: list[dict[str, Any]]
    diff: dict[str, Any]
    generator: str


class StudioCandidateRecord(TypedDict):
    candidate_id: str
    session_id: str
    source_version_id: str
    variant_index: int
    scene: dict[str, Any]
    diff: dict[str, Any]
    notes: list[str]
    selected: bool
    created_at: str


class StudioProfileRecord(TypedDict):
    profile_id: str
    profile_version: str
    consent: dict[str, Any]
    created_at: str
    updated_at: str


class StudioProfileEstimateRecord(TypedDict):
    profile_id: str
    dimension: str
    estimate: float | None
    uncertainty: float | None
    n: int
    reliability: float
    stats: dict[str, Any]
    updated_at: str


class StudioTrialRecord(TypedDict):
    trial_id: str
    session_id: str
    profile_id: str
    protocol_run_id: str | None
    client_trial_id: str
    task_type: str
    dimension: str
    difficulty: float
    stimulus: dict[str, Any]
    response: dict[str, Any]
    outcome: dict[str, Any]
    error_profile: dict[str, Any]
    task_family: str
    response_kind: str
    scoring_version: str
    interview_id: str | None
    probe_index: int | None
    probe_type: str | None
    belief: dict[str, Any]
    information_gain: float | None
    confidence: float
    latency_ms: int
    created_at: str


class StudioInterviewRecord(TypedDict):
    interview_id: str
    session_id: str
    source_version_id: str
    scene_hash: str
    protocol_version: str
    form_id: str
    seed: int
    difficulty: float
    max_probes: int
    status: str
    created_at: str
    completed_at: str | None


class StudioContrastSessionRecord(TypedDict):
    contrast_id: str
    session_id: str
    source_version_id: str
    scene_hash: str
    protocol_version: str
    form_id: str
    seed: int
    max_trials: int
    difficulty: float
    occasion: str
    delay_hours: float | None
    reflection_json: str
    status: str
    created_at: str
    completed_at: str | None


class StudioContrastTrialRecord(TypedDict):
    trial_id: str
    contrast_id: str
    trial_index: int
    task_id: str
    feature_type: str
    feature_key: str
    delta: float | None
    staircase_level: float | None
    target_side: str
    chosen_option_id: str | None
    correct: int | None
    confidence: float | None
    abstained: int
    latency_ms: int | None
    client_trial_id: str
    created_at: str


class StudioWorldItemRecord(TypedDict):
    item_id: str
    world_id: str
    label: str
    kind: str
    scene: dict[str, Any]
    created_at: str


class StudioWorldRecord(TypedDict):
    world_id: str
    name: str
    description: str
    scene: dict[str, Any]
    created_at: str
    source_session_id: str
    items: list[StudioWorldItemRecord]


class StudioSessionSummaryRecord(TypedDict):
    session_id: str
    title: str
    intention: str
    status: str
    seed: int
    claim_level: str
    created_at: str
    updated_at: str


class StudioEventRecord(TypedDict, total=False):
    type: str
    event_type: str
    session_id: str
    version: StudioVersionSummaryRecord
    diff: dict[str, Any]
    branch_id: str
    head_version_id: str
    source_version_id: str
    candidates: list[dict[str, Any]]
    count: int
    candidate_ids: list[str]
    commands: list[dict[str, Any]]
    warnings: list[str]
    text: str
    resolutions: list[str]


__all__ = [
    "StudioSessionRecord",
    "StudioBranchRecord",
    "StudioBranchSummaryRecord",
    "StudioVersionSummaryRecord",
    "StudioVersionRecord",
    "StudioCandidateRecord",
    "StudioProfileRecord",
    "StudioProfileEstimateRecord",
    "StudioTrialRecord",
    "StudioContrastSessionRecord",
    "StudioContrastTrialRecord",
    "StudioWorldItemRecord",
    "StudioWorldRecord",
    "StudioSessionSummaryRecord",
    "StudioEventRecord",
]
