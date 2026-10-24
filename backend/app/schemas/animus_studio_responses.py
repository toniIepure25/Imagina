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
    behavioral_profile: str = "EXPERIMENTAL"
    behavioral_reconstruction: str = "EXPERIMENTAL"
    adaptive_practice: str = "EXPERIMENTAL"
    epistemic_interview: str = "EXPERIMENTAL"
    contrast_observatory: str = "EXPERIMENTAL"
    clinical_use: str = "DISABLED"
    claim_ceiling: str


class ProfileDimensionModel(_StudioModel):
    id: str
    label: str
    description: str
    construct: str
    estimate: float | None = None
    uncertainty: float = 1.0
    n: int = 0
    reliability: float = 0.0
    status: str = "no_evidence"
    brier_score: float | None = None
    provenance: str = "BEHAVIORAL_PRACTICE"


class ErrorSignatureModel(_StudioModel):
    n: int = 0
    omissions: int = 0
    intrusions: int = 0
    mean_spatial_error: float | None = None
    spatial_n: int = 0
    epistemic_n: int = 0


class EpistemicSummaryModel(_StudioModel):
    n_interviews: int = 0
    n_probes: int = 0
    mean_brier: float | None = None
    overconfidence: float | None = None
    abstention_rate: float | None = None
    mean_information_gain: float | None = None
    last_interview_id: str | None = None


class ProfileContrastModel(_StudioModel):
    n_sessions: int = 0
    n_completed: int = 0
    n_trials: int = 0
    median_threshold: float | None = None
    mean_dprime: float | None = None
    mean_brier: float | None = None
    calibration_n: int = 0
    last_contrast_id: str | None = None


class ProfileModel(_StudioModel):
    profile_id: str
    profile_version: str
    claim_level: str
    privacy_scope: str
    trial_count: int = 0
    dimensions: list[ProfileDimensionModel] = Field(default_factory=list)
    error_signature: ErrorSignatureModel = Field(default_factory=ErrorSignatureModel)
    epistemic: EpistemicSummaryModel = Field(default_factory=EpistemicSummaryModel)
    contrast: ProfileContrastModel = Field(default_factory=ProfileContrastModel)
    limitations: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    measured_at: str


class PracticeOptionModel(_StudioModel):
    id: str
    label: str
    value: Any = None
    scene: SceneGraphModel | None = None


class PracticeTokenModel(_StudioModel):
    token_id: str
    kind: str
    label: str
    role: str = "prop"
    color: str | None = None


class PracticeLayoutModel(_StudioModel):
    width: float = 1.0
    height: float = 1.0
    grid: int = 7
    tolerance: float = 0.3


class PracticeTaskModel(_StudioModel):
    task_id: str
    task_type: str
    dimension: str
    prompt: str
    options: list[PracticeOptionModel] = Field(default_factory=list)
    difficulty: float
    task_seed: int
    preview_seconds: int
    response_kind: str = "option"
    tokens: list[PracticeTokenModel] = Field(default_factory=list)
    layout: PracticeLayoutModel | None = None


class PracticeAdaptiveModel(_StudioModel):
    dimension: str
    task_type: str
    difficulty: float
    reason: str
    expected_gain: float | None = None
    trial_index: int | None = None


class PracticeStartResponseModel(_StudioModel):
    session_id: str
    source_version_id: str
    task: PracticeTaskModel
    adaptive: PracticeAdaptiveModel
    profile: ProfileModel
    claim_level: str


class PracticeTrialModel(_StudioModel):
    trial_id: str | None = None
    session_id: str | None = None
    client_trial_id: str | None = None
    task_type: str | None = None
    dimension: str | None = None
    difficulty: float | None = None
    task_family: str | None = None
    response_kind: str | None = None
    scoring_version: str | None = None
    stimulus: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    outcome: dict[str, Any] = Field(default_factory=dict)
    error_profile: dict[str, Any] = Field(default_factory=dict)
    interview_id: str | None = None
    probe_index: int | None = None
    probe_type: str | None = None
    information_gain: float | None = None
    confidence: float | None = None
    latency_ms: int | None = None
    created_at: str | None = None


class PracticeSubmitResponseModel(_StudioModel):
    session_id: str
    trial: PracticeTrialModel | None = None
    idempotent: bool = False
    feedback: dict[str, Any] | None = None
    next_task: PracticeTaskModel | None = None
    adaptive: PracticeAdaptiveModel | None = None
    profile: ProfileModel
    last_event_seq: int


class EpistemicOptionModel(_StudioModel):
    id: str
    label: str


class EpistemicProbeModel(_StudioModel):
    probe_id: str
    task_id: str
    probe_type: str
    prompt: str
    options: list[EpistemicOptionModel] = Field(default_factory=list)
    dimension: str
    difficulty: float
    preview_seconds: int = 4


class InterviewSummaryModel(_StudioModel):
    interview_id: str
    session_id: str
    source_version_id: str
    protocol_version: str = "eri-v1"
    form_id: str = "A"
    difficulty: float = 0.45
    status: str = "active"
    probe_count: int = 0
    max_probes: int = 12
    created_at: str | None = None
    completed_at: str | None = None


class EpistemicObjectModel(_StudioModel):
    label: str
    kind: str = "custom"
    probability: float
    status: str


class EpistemicRelationModel(_StudioModel):
    subject: str
    relation: str
    object: str
    probability: float
    status: str


class EpistemicUncertaintyModel(_StudioModel):
    object_entropy: float = 0.0
    relation_entropy: float = 0.0


class EpistemicScoresModel(_StudioModel):
    n_probes: int = 0
    n_answered: int = 0
    object_accuracy: float | None = None
    spatial_accuracy: float | None = None
    mean_brier: float | None = None
    coverage: float = 0.0
    abstention_rate: float = 0.0
    overconfidence: float | None = None
    mean_information_gain: float | None = None


class EpistemicReconstructionModel(_StudioModel):
    objects: list[EpistemicObjectModel] = Field(default_factory=list)
    relations: list[EpistemicRelationModel] = Field(default_factory=list)
    uncertainty: EpistemicUncertaintyModel = Field(default_factory=EpistemicUncertaintyModel)
    scores: EpistemicScoresModel = Field(default_factory=EpistemicScoresModel)
    protocol_version: str = "eri-v1"
    scoring_version: str = "eri-v1"


class InterviewStartResponseModel(_StudioModel):
    session_id: str
    interview: InterviewSummaryModel
    probe: EpistemicProbeModel
    profile: ProfileModel
    claim_level: str


class InterviewSubmitResponseModel(_StudioModel):
    session_id: str
    interview: InterviewSummaryModel | None = None
    trial: PracticeTrialModel | None = None
    idempotent: bool = False
    feedback: dict[str, Any] | None = None
    next_probe: EpistemicProbeModel | None = None
    reconstruction: EpistemicReconstructionModel | None = None
    profile: ProfileModel
    last_event_seq: int


class InterviewSummaryResponseModel(_StudioModel):
    session_id: str
    interview: InterviewSummaryModel
    reconstruction: EpistemicReconstructionModel
    profile: ProfileModel
    claim_level: str


class InterviewListResponseModel(_StudioModel):
    session_id: str
    interviews: list[InterviewSummaryModel] = Field(default_factory=list)


class ContrastSummaryModel(_StudioModel):
    contrast_id: str
    session_id: str
    source_version_id: str
    protocol_version: str = "contrast-v1"
    form_id: str = "A"
    max_trials: int = 16
    difficulty: float = 0.45
    occasion: str = "baseline"
    delay_hours: float | None = None
    status: str = "active"
    trial_count: int = 0
    reflection: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    completed_at: str | None = None


class ContrastOptionModel(_StudioModel):
    id: str
    label: str
    scene: SceneGraphModel


class ContrastTrialModel(_StudioModel):
    trial_id: str
    task_id: str
    trial_index: int
    prompt: str = "Which scene matches the one you saw?"
    options: list[ContrastOptionModel] = Field(default_factory=list)
    preview_seconds: int = 5


class ContrastThresholdModel(_StudioModel):
    threshold: float | None = None
    slope: float | None = None
    ci: list[float] | None = None
    censored: bool | None = None
    n: int = 0
    status: str = "insufficient_evidence"
    scoring_version: str = "sdt-v1"


class ContrastCalibrationModel(_StudioModel):
    n: int = 0
    brier: float | None = None
    overconfidence: float | None = None
    type2_auc: float | None = None


class ContrastResultModel(_StudioModel):
    protocol_version: str = "contrast-v1"
    scoring_version: str = "sdt-v1"
    n_trials: int = 0
    n_answered: int = 0
    coverage: float | None = None
    dprime: float | None = None
    side_bias: float | None = None
    thresholds: dict[str, ContrastThresholdModel] = Field(default_factory=dict)
    calibration: ContrastCalibrationModel = Field(default_factory=ContrastCalibrationModel)
    notes: list[str] = Field(default_factory=list)


class ContrastStartResponseModel(_StudioModel):
    session_id: str
    contrast: ContrastSummaryModel
    trial: ContrastTrialModel
    profile: ProfileModel
    claim_level: str


class ContrastSubmitResponseModel(_StudioModel):
    session_id: str
    contrast: ContrastSummaryModel
    trial: dict[str, Any]
    recorded: bool = True
    idempotent: bool = False
    next_trial: ContrastTrialModel | None = None
    result: ContrastResultModel | None = None
    profile: ProfileModel
    last_event_seq: int


class ContrastSummaryResponseModel(_StudioModel):
    session_id: str
    contrast: ContrastSummaryModel
    result: ContrastResultModel
    profile: ProfileModel
    claim_level: str


class ContrastListResponseModel(_StudioModel):
    session_id: str
    contrasts: list[ContrastSummaryModel] = Field(default_factory=list)


class EvidenceSourceModel(_StudioModel):
    probe_id: str
    probe_type: str
    choice: str = ""
    confidence: float | None = None
    abstained: bool = False
    information_gain: float | None = None
    created_at: str | None = None


class EvidenceItemModel(_StudioModel):
    variable_id: str
    label: str
    probe_type: str
    provenance: str = "prior"
    posterior: float = 0.5
    uncertainty: float = 0.5
    n_sources: int = 0
    leave_one_out_delta: float = 0.0
    dependence_group: str
    sources: list[EvidenceSourceModel] = Field(default_factory=list)


class ObservatoryModel(_StudioModel):
    session_id: str
    source_version_id: str
    scene_hash: str
    belief: EpistemicReconstructionModel
    evidence: list[EvidenceItemModel] = Field(default_factory=list)
    discrimination: dict[str, Any] = Field(default_factory=dict)
    reliability: dict[str, Any] = Field(default_factory=dict)
    boundaries: list[str] = Field(default_factory=list)
    claim_level: str = "L1_BEHAVIORAL_ASSISTED"


class ProtocolSummaryModel(_StudioModel):
    protocol_id: str
    version: str
    name: str
    description: str = ""
    builtin: bool = False
    total_trials: int = 0
    max_minutes: int = 0
    dimensions: list[str] = Field(default_factory=list)


class ProtocolListResponseModel(_StudioModel):
    protocol_version: str
    protocols: list[ProtocolSummaryModel] = Field(default_factory=list)


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
    "ProfileDimensionModel",
    "ErrorSignatureModel",
    "EpistemicSummaryModel",
    "ProfileContrastModel",
    "ProfileModel",
    "PracticeOptionModel",
    "PracticeTokenModel",
    "PracticeLayoutModel",
    "PracticeTaskModel",
    "PracticeAdaptiveModel",
    "PracticeStartResponseModel",
    "PracticeTrialModel",
    "PracticeSubmitResponseModel",
    "EpistemicOptionModel",
    "EpistemicProbeModel",
    "InterviewSummaryModel",
    "EpistemicObjectModel",
    "EpistemicRelationModel",
    "EpistemicUncertaintyModel",
    "EpistemicScoresModel",
    "EpistemicReconstructionModel",
    "InterviewStartResponseModel",
    "InterviewSubmitResponseModel",
    "InterviewSummaryResponseModel",
    "InterviewListResponseModel",
    "ContrastSummaryModel",
    "ContrastOptionModel",
    "ContrastTrialModel",
    "ContrastThresholdModel",
    "ContrastCalibrationModel",
    "ContrastResultModel",
    "ContrastStartResponseModel",
    "ContrastSubmitResponseModel",
    "ContrastSummaryResponseModel",
    "ContrastListResponseModel",
    "EvidenceSourceModel",
    "EvidenceItemModel",
    "ObservatoryModel",
    "ProtocolSummaryModel",
    "ProtocolListResponseModel",
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
