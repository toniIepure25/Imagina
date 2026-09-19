"""ANIMUS capability-scoped scientific authorization (P2 claim-engine upgrade).

P1 used a single scalar claim ceiling. That is no longer sufficient: P2 may validate neural content for
PERCEPTION while imagery stays unvalidated. This module replaces the global scalar with a per-capability
authorization matrix. Validating one capability NEVER raises another — in particular, validating
PERCEPTION_NEURAL_CONTENT cannot authorize IMAGERY_NEURAL_CONTENT (that needs an independent scientific
gate; see P3). Backward compatible with P1: BEHAVIORAL_IMAGERY_ASSIST stays authorized and the behavioral
loop keeps operating at claim level L1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.animus.claims import (
    L1_BEHAVIORAL_ASSISTED,
    L3_NEURAL_CONTENT_INFORMED_VALIDATED,
)

# Capabilities (domains).
BEHAVIORAL_IMAGERY_ASSIST = "BEHAVIORAL_IMAGERY_ASSIST"
BIOSIGNAL_STATE = "BIOSIGNAL_STATE"
PERCEPTION_NEURAL_CONTENT = "PERCEPTION_NEURAL_CONTENT"
IMAGERY_NEURAL_CONTENT = "IMAGERY_NEURAL_CONTENT"
DREAM_NEURAL_CONTENT = "DREAM_NEURAL_CONTENT"
NEURAL_RECONSTRUCTION = "NEURAL_RECONSTRUCTION"

CAPABILITIES = [
    BEHAVIORAL_IMAGERY_ASSIST, BIOSIGNAL_STATE, PERCEPTION_NEURAL_CONTENT,
    IMAGERY_NEURAL_CONTENT, DREAM_NEURAL_CONTENT, NEURAL_RECONSTRUCTION,
]

# Authorization statuses (ordered weak -> strong for the *authorized* track).
UNAUTHORIZED = "UNAUTHORIZED"          # no evidence, product may not use it
NOT_VALIDATED = "NOT_VALIDATED"        # gate defined but not passed / pending
BLOCKED = "BLOCKED"                    # gate attempted but could not complete
AUTHORIZED = "AUTHORIZED"              # allowed (behavioral / non-content)
VALIDATED = "VALIDATED"                # neural-content validated for this domain

USABLE_STATUSES = {AUTHORIZED, VALIDATED}

# The default (pre-P2-confirmatory) matrix. Perception is defined-but-not-yet-validated; imagery/dream/
# reconstruction are unauthorized. This is the single source of truth the product consults.
DEFAULT_MATRIX: dict[str, str] = {
    BEHAVIORAL_IMAGERY_ASSIST: AUTHORIZED,
    BIOSIGNAL_STATE: NOT_VALIDATED,
    PERCEPTION_NEURAL_CONTENT: NOT_VALIDATED,
    IMAGERY_NEURAL_CONTENT: UNAUTHORIZED,
    DREAM_NEURAL_CONTENT: UNAUTHORIZED,
    NEURAL_RECONSTRUCTION: UNAUTHORIZED,
}

# Claim level a capability may express when usable.
CAPABILITY_CLAIM_LEVEL: dict[str, str] = {
    BEHAVIORAL_IMAGERY_ASSIST: L1_BEHAVIORAL_ASSISTED,
    PERCEPTION_NEURAL_CONTENT: L3_NEURAL_CONTENT_INFORMED_VALIDATED,  # only when VALIDATED, domain=PERCEPTION
}

# Human-facing labels.
CAPABILITY_LABELS: dict[str, str] = {
    BEHAVIORAL_IMAGERY_ASSIST: "Behavioral-assisted imagination amplifier (no decoded neural content)",
    PERCEPTION_NEURAL_CONTENT: "Validated perception-content neural adapter (visual perception only)",
    IMAGERY_NEURAL_CONTENT: "Imagery neural content — NOT authorized (requires C3XRP replication + P3 gate)",
    DREAM_NEURAL_CONTENT: "Dream neural content — NOT authorized",
    NEURAL_RECONSTRUCTION: "Neural image reconstruction — NOT authorized",
    BIOSIGNAL_STATE: "Biosignal state — not validated",
}


class CapabilityError(RuntimeError):
    """Raised when a capability is used without authorization (fail-closed)."""


@dataclass
class ScientificCapabilityAuthorization:
    """Per-capability authorization. Never auto-promotes one capability from another."""
    matrix: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_MATRIX))

    def status(self, capability: str) -> str:
        if capability not in CAPABILITIES:
            raise CapabilityError(f"unknown capability {capability!r}")
        return self.matrix.get(capability, UNAUTHORIZED)

    def is_usable(self, capability: str) -> bool:
        return self.status(capability) in USABLE_STATUSES

    def enforce(self, capability: str) -> str:
        st = self.status(capability)
        if st not in USABLE_STATUSES:
            raise CapabilityError(
                f"capability {capability} is {st}; not usable (fail-closed, no cross-capability promotion)")
        return st

    def validate_perception(self, decision: str) -> "ScientificCapabilityAuthorization":
        """Return a NEW authorization with PERCEPTION_NEURAL_CONTENT set from a P2 decision. Imagery/dream/
        reconstruction are untouched — validating perception cannot raise them."""
        new = dict(self.matrix)
        if decision == "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED":
            new[PERCEPTION_NEURAL_CONTENT] = VALIDATED
        elif decision.startswith("ANIMUS_P2_BLOCKED"):
            new[PERCEPTION_NEURAL_CONTENT] = BLOCKED
        else:  # LIMITED / FAIL
            new[PERCEPTION_NEURAL_CONTENT] = NOT_VALIDATED
        # invariant: imagery/dream/reconstruction never become usable via a perception decision
        for cap in (IMAGERY_NEURAL_CONTENT, DREAM_NEURAL_CONTENT, NEURAL_RECONSTRUCTION):
            new[cap] = UNAUTHORIZED
        return ScientificCapabilityAuthorization(matrix=new)

    def claim_level_for(self, capability: str) -> str | None:
        if not self.is_usable(capability):
            return None
        return CAPABILITY_CLAIM_LEVEL.get(capability)

    def to_dict(self) -> dict:
        return {"matrix": dict(self.matrix),
                "usable": {c: self.is_usable(c) for c in CAPABILITIES},
                "labels": {c: CAPABILITY_LABELS.get(c, c) for c in CAPABILITIES}}


def imagery_unauthorized_invariant(auth: ScientificCapabilityAuthorization) -> bool:
    """P2/P3 firewall: imagery neural content must remain unusable no matter the perception state."""
    return not auth.is_usable(IMAGERY_NEURAL_CONTENT)


# Backward-compatible default the product boots with.
default_authorization = ScientificCapabilityAuthorization()
