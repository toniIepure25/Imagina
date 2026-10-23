"""Typed response contract for the ANIMUS Studio product API.

The service returns plain dictionaries so it stays independent from FastAPI. These models are the
serialization boundary: they document every field the product promises, keep OpenAPI useful, and make
schema drift fail loudly in tests instead of silently changing the wire format.

All models allow extra fields. That is deliberate: the scene graph is versioned (ANIMUS-SG-v1) and may
gain renderer metadata without breaking older clients. Required fields still describe the stable core.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StudioModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SceneAttributeModel(_StudioModel):
    value: Any
    confidence: float = 0.0
    provenance: str = "SYSTEM_DEFAULT"
    locked: bool = False
    source_text: str | None = None
    renderable: bool = True


class SceneTransformModel(_StudioModel):
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])


class SceneEntityModel(_StudioModel):
    id: str
    kind: str
    label: str
    role: str = "prop"
    transform: SceneTransformModel = Field(default_factory=SceneTransformModel)
    attributes: dict[str, SceneAttributeModel] = Field(default_factory=dict)
    confidence: float = 0.0
    provenance: str = "SYSTEM_DEFAULT"
    locked: bool = False
    visible: bool = True
    parent_id: str | None = None


class SceneRelationModel(_StudioModel):
    subject_id: str
    relation: str
    object_id: str
    confidence: float = 0.0
    provenance: str = "SYSTEM_DEFAULT"


class SceneConstraintModel(_StudioModel):
    kind: str
    target: str
    value: Any = None
    strength: float = 1.0
    provenance: str = "USER_EXPLICIT"


class CameraModel(_StudioModel):
    position: list[float]
    target: list[float]
    fov: float
    motion: str
    speed: float


class LightingKeyModel(_StudioModel):
    color: str
    intensity: float
    direction: list[float]


class LightingAmbientModel(_StudioModel):
    color: str
    intensity: float


class LightingModel(_StudioModel):
    key: LightingKeyModel
    ambient: LightingAmbientModel
    rim: LightingAmbientModel


class FogModel(_StudioModel):
    color: str
    density: float


class SkyModel(_StudioModel):
    top: str
    horizon: str
    bottom: str
    stars: int
    aurora: bool


class AtmosphereModel(_StudioModel):
    fog: FogModel
    sky: SkyModel
    weather: str
    time_of_day: str


class DynamicsModel(_StudioModel):
    wind: float
    water: float
    fire: float
    floating: float
    pulse: float


class SceneGraphModel(_StudioModel):
    scene_id: str
    version: int
    seed: int
    title: str
    version_tag: str
    entities: list[SceneEntityModel] = Field(default_factory=list)
    relations: list[SceneRelationModel] = Field(default_factory=list)
    style: str
    camera: CameraModel
    lighting: LightingModel
    atmosphere: AtmosphereModel
    dynamics: DynamicsModel
    constraints: list[SceneConstraintModel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneDiffChangeModel(_StudioModel):
    scope: str
    entity_id: str | None = None
    label: str
    path: str
    before: Any = None
    after: Any = None
    provenance: str = "SYSTEM_DEFAULT"


class SceneDiffEntityModel(_StudioModel):
    entity_id: str
    label: str
    kind: str


class SceneDiffModel(_StudioModel):
    added: list[SceneDiffEntityModel] = Field(default_factory=list)
    removed: list[SceneDiffEntityModel] = Field(default_factory=list)
    changed: list[SceneDiffChangeModel] = Field(default_factory=list)
    locked_untouched: list[str] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    before_hash: str = ""
    after_hash: str = ""


class VersionSummaryModel(_StudioModel):
    version_id: str
    number: int
    branch_id: str
    parent_version_id: str | None = None
    source: str
    label: str
    intention: str | None = None
    claim_level: str
    created_at: str
    content_hash: str
    entity_count: int


class VersionDetailModel(VersionSummaryModel):
    scene: SceneGraphModel
    commands: list[dict[str, Any]] = Field(default_factory=list)
    diff: SceneDiffModel = Field(default_factory=SceneDiffModel)
    generator: str = "compose.v1"


class BranchSummaryModel(_StudioModel):
    branch_id: str
    name: str
    head_version_id: str
    created_at: str
    parent_branch_id: str | None = None
    fork_version_id: str | None = None
    is_active: bool = False


class CandidateModel(_StudioModel):
    candidate_id: str
    session_id: str | None = None
    source_version_id: str
    variant_index: int = 0
    scene: SceneGraphModel
    diff: SceneDiffModel = Field(default_factory=SceneDiffModel)
    notes: list[str] = Field(default_factory=list)
    selected: bool = False
    created_at: str


class CapabilityModel(_StudioModel):
    scene_graph: str
    renderer: str
    image_generation: str
    neural_content: str
    dream_content: str
    neural_reconstruction: str
    network_calls: str
    uploads: str
    privacy_scope: str
    claim_ceiling: str


class StudioSnapshotModel(_StudioModel):
    session_id: str
    title: str
    intention: str
    mode: str
    status: str
    seed: int
    privacy_scope: str
    claim_level: str
    claim_label: str
    claim_ceiling: str
    unauthorized_claims: list[str] = Field(default_factory=list)
    capabilities: CapabilityModel
    active_branch_id: str
    active_branch_name: str
    active_version_id: str
    scene: SceneGraphModel
    version: VersionSummaryModel
    diff: SceneDiffModel = Field(default_factory=SceneDiffModel)
    branches: list[BranchSummaryModel] = Field(default_factory=list)
    history: list[VersionSummaryModel] = Field(default_factory=list)
    candidates: list[CandidateModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    has_undo: bool = False
    has_redo: bool = False
    last_event_seq: int = 0
    created_at: str
    updated_at: str
    generated: list[CandidateModel] | None = None
    source_version_id: str | None = None
    active_locks: list[str] | None = None
    needs_clarification: bool | None = None
    clarification: str | None = None
    resolutions: list[str] | None = None
    parse_warnings: list[str] | None = None
    applied: int | None = None


class StudioIntentResponseModel(StudioSnapshotModel):
    needs_clarification: bool
    clarification: str | None = None
    resolutions: list[str] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    applied: int = 0


class StudioCommandsResponseModel(StudioSnapshotModel):
    applied: int
    warnings: list[str] = Field(default_factory=list)


class StudioRegenerateResponseModel(StudioSnapshotModel):
    generated: list[CandidateModel] = Field(default_factory=list)
    source_version_id: str
    active_locks: list[str] = Field(default_factory=list)


class StudioHistoryResponseModel(_StudioModel):
    session_id: str
    active_branch_id: str
    branches: list[BranchSummaryModel] = Field(default_factory=list)
    versions: list[VersionSummaryModel] = Field(default_factory=list)
    has_undo: bool = False
    has_redo: bool = False


class SessionSummaryModel(_StudioModel):
    session_id: str
    title: str
    intention: str
    status: str
    seed: int
    claim_level: str
    created_at: str
    updated_at: str


class SessionListResponseModel(_StudioModel):
    sessions: list[SessionSummaryModel] = Field(default_factory=list)


class WorldItemModel(_StudioModel):
    item_id: str
    world_id: str
    label: str
    kind: str
    scene: SceneEntityModel
    created_at: str


class WorldModel(_StudioModel):
    world_id: str
    name: str
    description: str = ""
    scene: SceneGraphModel
    created_at: str
    source_session_id: str | None = None
    items: list[WorldItemModel] = Field(default_factory=list)


class WorldListResponseModel(_StudioModel):
    worlds: list[WorldModel] = Field(default_factory=list)


class DeleteResponseModel(_StudioModel):
    deleted: str


class StudioHealthResponseModel(_StudioModel):
    status: str
    system: str
    product: str
    schema_version: int
    claim_level: str
    claim_label: str
    claim_ceiling: str
    unauthorized_claims: list[str] = Field(default_factory=list)
    capabilities: CapabilityModel
    journal_mode: str | None = None
    synchronous: int | None = None
    foreign_keys: bool | None = None
    event_count: int | None = None
    integrity: str | None = None
    foreign_key_violations: int | None = None


class EventRecordModel(_StudioModel):
    seq: int
    session_id: str
    event_type: str
    version_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class StudioEventsResponseModel(_StudioModel):
    session_id: str
    events: list[EventRecordModel] = Field(default_factory=list)
    has_more: bool = False


class StudioCapabilitiesResponseModel(_StudioModel):
    claim_level: str
    claim_label: str
    claim_ceiling: str
    unauthorized_claims: list[str] = Field(default_factory=list)
    capabilities: CapabilityModel


class StudioErrorResponseModel(_StudioModel):
    detail: str


__all__ = [
    "SceneAttributeModel",
    "SceneTransformModel",
    "SceneEntityModel",
    "SceneRelationModel",
    "SceneConstraintModel",
    "SceneGraphModel",
    "SceneDiffModel",
    "VersionSummaryModel",
    "VersionDetailModel",
    "BranchSummaryModel",
    "CandidateModel",
    "CapabilityModel",
    "StudioSnapshotModel",
    "StudioIntentResponseModel",
    "StudioCommandsResponseModel",
    "StudioRegenerateResponseModel",
    "StudioHistoryResponseModel",
    "SessionSummaryModel",
    "SessionListResponseModel",
    "WorldItemModel",
    "WorldModel",
    "WorldListResponseModel",
    "DeleteResponseModel",
    "StudioHealthResponseModel",
    "StudioCapabilitiesResponseModel",
    "EventRecordModel",
    "StudioEventsResponseModel",
    "StudioErrorResponseModel",
]
