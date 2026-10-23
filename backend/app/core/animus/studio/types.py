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
    "StudioWorldItemRecord",
    "StudioWorldRecord",
    "StudioSessionSummaryRecord",
    "StudioEventRecord",
]
