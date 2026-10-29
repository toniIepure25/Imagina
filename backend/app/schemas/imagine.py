"""Contracts for the Imagine lab and its future diffusion worker."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Vec3 = tuple[float, float, float]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImagineConditioningVector(_Strict):
    attention: float = Field(ge=0, le=1)
    arousal: float = Field(ge=0, le=1)
    valence: float = Field(ge=0, le=1)
    vividness: float = Field(ge=0, le=1)
    fatigue: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    theta: float = Field(ge=0, le=1)
    alpha: float = Field(ge=0, le=1)
    beta: float = Field(ge=0, le=1)
    gamma: float = Field(ge=0, le=1)
    hrv: float = Field(ge=0, le=1)
    eda: float = Field(ge=0, le=1)
    signal_quality: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    trend: float = Field(ge=0, le=1)
    stability: float = Field(ge=0, le=1)


class ImagineConditioning(_Strict):
    schema: Literal["IMAGINA-CONDITIONING-v1"]
    adapter: Literal["conditioning-v0"]
    source: Literal["demo", "scenario", "replay", "device"]
    vector: ImagineConditioningVector
    quality: float = Field(ge=0, le=1)
    uncertainty: float = Field(ge=0, le=1)
    trend: float = Field(ge=0, le=1)
    stability: float = Field(ge=0, le=1)
    vector_hash: str = Field(min_length=8, max_length=128)


class ImagineBrief(_Strict):
    prompt: str = Field(min_length=3, max_length=1200)
    negative_prompt: str = Field(default="", max_length=600)
    style: Literal["dream", "cinematic", "gothic", "surreal", "minimal"]
    seed: str = Field(min_length=1, max_length=64)


class ImagineControls(_Strict):
    clarity: float = Field(ge=0, le=1)
    fog: float = Field(ge=0, le=1)
    motion: float = Field(ge=0, le=1)
    saturation: float = Field(ge=0, le=1)
    detail: float = Field(ge=0, le=1)
    glow: float = Field(ge=0, le=1)
    cameraPace: float = Field(ge=0, le=1)
    depthFalloff: float = Field(ge=0, le=1)


class ImagineCameraPoint(_Strict):
    position: Vec3
    target: Vec3


class ImagineCamera(_Strict):
    mode: Literal["first_person"]
    path: list[ImagineCameraPoint] = Field(default_factory=list, max_length=64)
    start: Vec3
    fov: float = Field(ge=40, le=100)


class ImagineAdaptive(_Strict):
    target: Literal["calm", "immersion", "exploration"]
    hz: float = Field(ge=0.05, le=2)


class ImagineOutput(_Strict):
    skybox: dict[str, int]
    preview: dict[str, int]
    materials: Literal[False] = False


class ImagineProvenance(_Strict):
    composer_version: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=64)
    app_version: str = Field(min_length=1, max_length=64)


class ImagineJobRequest(_Strict):
    schema: Literal["IMAGINA-DIFFUSION-REQUEST-v2"]
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    brief: ImagineBrief
    conditioning: ImagineConditioning
    controls: ImagineControls
    camera: ImagineCamera
    adaptive: ImagineAdaptive
    output: ImagineOutput
    provenance: ImagineProvenance
    boundary: str = Field(min_length=1, max_length=500)


class ImagineAsset(BaseModel):
    url: str
    width: int = Field(gt=0, le=8192)
    height: int = Field(gt=0, le=8192)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")


class ImagineManifest(BaseModel):
    schema: Literal["IMAGINA-DIFFUSION-MANIFEST-v1"]
    job_id: str
    state: Literal["succeeded"]
    model_slot: str
    model_hash: str
    seed: int
    prompt_hash: str
    conditioning_hash: str
    controls: dict[str, float]
    skybox: ImagineAsset
    preview: ImagineAsset
    created_at: str
    expires_at: str
    provenance: dict[str, str | int | float | bool | None]


class ImagineJobPublic(BaseModel):
    schema: Literal["IMAGINA-DIFFUSION-JOB-v2"] = "IMAGINA-DIFFUSION-JOB-v2"
    id: str
    state: Literal["queued", "running", "cancelling", "cancelled", "succeeded", "failed"]
    provider: str
    model_slot: str
    created_at: str
    updated_at: str
    error_code: str | None = None
    error_message: str | None = None
    staged: str | None = None
    manifest: ImagineManifest | None = None


class ImagineLocalCapability(BaseModel):
    status: Literal["ready"] = "ready"
    engine: Literal["local-procedural"] = "local-procedural"
    first_person: bool = True


class ImagineDiffusionCapability(BaseModel):
    status: Literal["ready", "blocked"]
    provider: Literal["remote-diffusion"] = "remote-diffusion"
    reason: str | None
    model_slot: str
    consent_required: Literal[True] = True
    max_skybox: dict[str, int]
    max_preview: dict[str, int]


class ImagineCapabilities(BaseModel):
    local: ImagineLocalCapability
    diffusion: ImagineDiffusionCapability
    claim_ceiling: Literal["L1_BEHAVIORAL_ASSISTED"] = "L1_BEHAVIORAL_ASSISTED"


class ImagineJobList(BaseModel):
    jobs: list[ImagineJobPublic]


class ImagineError(BaseModel):
    code: str
    message: str
    retryable: bool = False
