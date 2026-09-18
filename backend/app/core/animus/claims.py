"""ANIMUS claim-level engine (ANIMUS-P1).

A single, machine-readable ladder that governs what the product may assert about an observation or a
session. ANIMUS-P1 is permitted to operate ONLY at L0 (fully simulated) or L1 (behavioral-assisted).
Anything above requires an explicit, future scientific authorization gate; there is no manual bypass.

This module is intentionally dependency-free so every other ANIMUS component (and the CI claim audit) can
import it cheaply.
"""
from __future__ import annotations

from dataclasses import dataclass

# Ordered from weakest to strongest evidentiary claim.
L0_SIMULATED = "L0_SIMULATED"
L1_BEHAVIORAL_ASSISTED = "L1_BEHAVIORAL_ASSISTED"
L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL = "L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL"
L3_NEURAL_CONTENT_INFORMED_VALIDATED = "L3_NEURAL_CONTENT_INFORMED_VALIDATED"

CLAIM_ORDER = [
    L0_SIMULATED,
    L1_BEHAVIORAL_ASSISTED,
    L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL,
    L3_NEURAL_CONTENT_INFORMED_VALIDATED,
]

# The maximum claim level ANIMUS-P1 is allowed to reach in this milestone.
MAX_AUTHORIZED_LEVEL = L1_BEHAVIORAL_ASSISTED

# Human-facing phrasing derived ONLY from the claim level (UI/exports must use these, never invent stronger).
CLAIM_LABELS = {
    L0_SIMULATED: "Simulated imagination loop (no biosignals, no decoded thoughts)",
    L1_BEHAVIORAL_ASSISTED: "Behavioral-assisted imagination amplifier (no decoded neural content)",
    L2_BIOSIGNAL_ASSISTED_EXPERIMENTAL: "Experimental biosignal-assisted (research only; not validated)",
    L3_NEURAL_CONTENT_INFORMED_VALIDATED: "Validated neural-content-informed (requires scientific gate)",
}

# Phrases the product must NEVER emit at L0/L1.
FORBIDDEN_CLAIM_PHRASES = (
    "read your thought", "reading your thoughts", "decoded your thought", "mind reading",
    "we know what you imagined", "neural reconstruction of your", "brain decoding of your image",
)


def rank(level: str) -> int:
    try:
        return CLAIM_ORDER.index(level)
    except ValueError as exc:  # unknown level is never trusted
        raise ClaimLevelError(f"unknown claim level: {level!r}") from exc


class ClaimLevelError(RuntimeError):
    """Raised when a claim level is unknown or exceeds the authorized ceiling."""


@dataclass(frozen=True)
class ClaimAuthorization:
    max_level: str = MAX_AUTHORIZED_LEVEL
    reason: str = "ANIMUS-P1 vertical slice: simulated/behavioral only; higher levels need a scientific gate"

    def is_allowed(self, level: str) -> bool:
        return rank(level) <= rank(self.max_level)

    def enforce(self, level: str) -> str:
        """Return the level if permitted, else raise. Fail-closed: never silently downgrade."""
        if not self.is_allowed(level):
            raise ClaimLevelError(
                f"claim level {level} exceeds authorized ceiling {self.max_level} ({self.reason})")
        return level


def label_for(level: str) -> str:
    return CLAIM_LABELS[level]


def audit_text_for_forbidden_claims(text: str) -> list[str]:
    """Return any forbidden mind-reading phrases found in user-facing text (case-insensitive)."""
    low = text.lower()
    return [p for p in FORBIDDEN_CLAIM_PHRASES if p in low]
