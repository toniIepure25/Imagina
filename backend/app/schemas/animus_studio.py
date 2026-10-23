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


__all__ = [
    "StudioCreateRequest", "StudioIntentRequest", "StudioCommandsRequest", "StudioRegenerateRequest",
    "StudioBranchRequest", "StudioWorldRequest", "StudioOpenWorldRequest",
]
