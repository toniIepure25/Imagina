"""Claim and privacy guards for the Studio product surface."""
from __future__ import annotations

from app.core.animus import claims

STUDIO_FORBIDDEN_PHRASES = (
    "read your mind", "reads your mind", "reading your mind", "mind reading", "mind-reading",
    "read your thoughts", "reads your thoughts", "reading your thoughts", "decoded your thought",
    "decodes your dreams", "decode your dreams", "what you are imagining", "what you imagined",
    "what i am imagining", "what i'm imagining", "what you imagine", "shows what you imagine",
    "neural reconstruction", "brain decoding", "thought reading",
    "cures aphantasia", "guarantees lucid dreaming", "clinically validated neurofeedback",
    "measures consciousness objectively",
)


class StudioClaimError(RuntimeError):
    """Raised when user-facing Studio text would make an unauthorized claim."""


def audit_studio_text(text: str) -> list[str]:
    low = " ".join((text or "").lower().split())
    hits = [phrase for phrase in STUDIO_FORBIDDEN_PHRASES if phrase in low]
    hits.extend(phrase for phrase in claims.audit_text_for_forbidden_claims(text) if phrase not in hits)
    return hits


def enforce_studio_text(text: str, *, field: str = "text") -> str:
    hits = audit_studio_text(text)
    if hits:
        raise StudioClaimError(
            f"{field} contains a phrase that implies mind-reading or clinical validity: {hits[0]!r}")
    return text


def claim_envelope(level: str = claims.L1_BEHAVIORAL_ASSISTED) -> dict:
    level = claims.ClaimAuthorization().enforce(level)
    return {
        "claim_level": level,
        "claim_label": claims.label_for(level),
        "claim_ceiling": claims.MAX_AUTHORIZED_LEVEL,
        "unauthorized_claims": [
            "neural imagery reconstruction", "dream decoding", "thought-content claims", "clinical diagnosis",
        ],
    }


def capability_envelope() -> dict:
    return {
        "scene_graph": "ANIMUS-SG-v1",
        "renderer": "procedural-local",
        "image_generation": "DISABLED",
        "neural_content": "UNAUTHORIZED",
        "dream_content": "UNAUTHORIZED",
        "neural_reconstruction": "UNAUTHORIZED",
        "network_calls": "DISABLED",
        "uploads": "DISABLED",
        "privacy_scope": "local_only",
        "claim_ceiling": claims.MAX_AUTHORIZED_LEVEL,
    }


__all__ = [
    "STUDIO_FORBIDDEN_PHRASES", "StudioClaimError", "audit_studio_text", "enforce_studio_text",
    "claim_envelope", "capability_envelope",
]
