"""Request models for the ANIMUS Studio product API.

Unknown fields are rejected: a client typo must not silently become a no-op. All bounds match the
domain limits in the scene model and the service layer.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudioCreateRequest(_StrictModel):
    title: str = Field(default="", max_length=120)
    intention: str = Field(min_length=3, max_length=500)
    seed: int = Field(default=20260909, ge=-(2**31), le=2**31 - 1)


class StudioIntentRequest(_StrictModel):
    text: str = Field(min_length=1, max_length=400)


class StudioCommandsRequest(_StrictModel):
    commands: list[dict[str, Any]] = Field(min_length=1, max_length=24)
    source_text: str = Field(default="", max_length=500)


class StudioRegenerateRequest(_StrictModel):
    count: int = Field(default=3, ge=1, le=6)
    strength: float = Field(default=0.22, ge=0.0, le=1.0)
    seed: int | None = Field(default=None, ge=-(2**31), le=2**31 - 1)
    locks: list[str] = Field(default_factory=list, max_length=80)
    preserve_user_edits: bool = True
    vary_camera: bool = True


class StudioBranchRequest(_StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    from_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioWorldRequest(_StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)


class StudioOpenWorldRequest(_StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class StudioPracticeStartRequest(_StrictModel):
    task_type: str | None = Field(default=None, max_length=40)
    difficulty: float | None = Field(default=None, ge=0.0, le=1.0)


class StudioPracticeSubmitRequest(_StrictModel):
    task_id: str = Field(min_length=8, max_length=80, pattern=r"^task_[A-Za-z0-9]+$")
    task_type: str = Field(min_length=3, max_length=40)
    task_seed: int = Field(ge=-(2**31), le=2**31 - 1)
    difficulty: float = Field(ge=0.0, le=1.0)
    response: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: int = Field(ge=0, le=1_800_000)
    client_trial_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    expected_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioInterviewStartRequest(_StrictModel):
    max_probes: int = Field(default=12, ge=6, le=20)
    form_id: str = Field(default="A", pattern=r"^[ABC]$")
    difficulty: float = Field(default=0.45, ge=0.0, le=1.0)
    expected_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioInterviewSubmitRequest(_StrictModel):
    probe_id: str = Field(min_length=7, max_length=40, pattern=r"^pr_[A-Za-z0-9]+$")
    task_id: str = Field(min_length=8, max_length=60, pattern=r"^eri_[A-Za-z0-9]+$")
    choice: str = Field(default="", max_length=20)
    confidence: float = Field(default=0.75, ge=0.5, le=1.0)
    abstained: bool = False
    latency_ms: int = Field(default=0, ge=0, le=1_800_000)
    client_trial_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    expected_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioContrastStartRequest(_StrictModel):
    max_trials: int = Field(default=16, ge=12, le=24)
    form_id: str = Field(default="A", pattern=r"^[ABC]$")
    difficulty: float = Field(default=0.45, ge=0.0, le=1.0)
    occasion: str = Field(default="baseline", pattern=r"^(baseline|follow_up)$")
    delay_hours: float | None = Field(default=None, ge=0.0, le=720.0)
    source_version_id: str | None = Field(default=None, min_length=3, max_length=80)
    expected_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioContrastSubmitRequest(_StrictModel):
    trial_id: str = Field(min_length=8, max_length=40, pattern=r"^ctr_[A-Za-z0-9]+$")
    task_id: str = Field(min_length=8, max_length=40, pattern=r"^cst_[A-Za-z0-9]+$")
    choice: str = Field(default="", max_length=1, pattern=r"^[ab]?$")
    confidence: float = Field(default=0.75, ge=0.5, le=1.0)
    abstained: bool = False
    latency_ms: int = Field(default=0, ge=0, le=1_800_000)
    client_trial_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    expected_version_id: str | None = Field(default=None, min_length=3, max_length=80)


class StudioContrastReflectionRequest(_StrictModel):
    strategies: list[str] = Field(default_factory=list, max_length=6)
    notes: str = Field(default="", max_length=500)


__all__ = [
    "StudioCreateRequest", "StudioIntentRequest", "StudioCommandsRequest", "StudioRegenerateRequest",
    "StudioBranchRequest", "StudioWorldRequest", "StudioOpenWorldRequest",
    "StudioPracticeStartRequest", "StudioPracticeSubmitRequest",
    "StudioInterviewStartRequest", "StudioInterviewSubmitRequest",
    "StudioContrastStartRequest", "StudioContrastSubmitRequest",
    "StudioContrastReflectionRequest",
]
