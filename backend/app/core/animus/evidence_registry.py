"""ANIMUS scientific-evidence registry (the science->product boundary).

References the immutable scientific results (C3XAT-R1, C3XRP, C3XRA) WITHOUT reinterpreting them, and states
plainly what is and is not yet supported. Product code consults this so it can never outrun the science:
the claim-level ceiling is derived here, and no entry here upgrades a claim on its own.
"""
from __future__ import annotations

from app.core.animus.claims import L1_BEHAVIORAL_ASSISTED

SCIENTIFIC_REGISTRY = {
    "imagery_reliability": {
        "result": "LIMITED cohort evidence",
        "source": "C3XAT-R1 (1/6 sessions; sub-03 only)",
        "authorizes_content_claim": False,
    },
    "independent_replication": {
        "result": "not yet executed",
        "source": "C3XRA acquisition-ready; C3XRP human replication not run",
        "authorizes_content_claim": False,
    },
    "content_decoder": {
        "result": "not validated",
        "source": "no validated neural content decoder exists",
        "authorizes_content_claim": False,
    },
    "geometry": {
        "result": "not authorized",
        "source": "C3XAG not authorized",
        "authorizes_content_claim": False,
    },
    "neural_reconstruction": {
        "result": "not validated",
        "source": "no validated neural reconstruction",
        "authorizes_content_claim": False,
    },
}


def max_authorized_claim_level() -> str:
    """The product ceiling is behavioral-assisted until a registry entry authorizes a neural-content claim
    (none do in ANIMUS-P1)."""
    if any(v["authorizes_content_claim"] for v in SCIENTIFIC_REGISTRY.values()):
        raise RuntimeError("registry inconsistency: no scientific gate authorizes a content claim in P1")
    return L1_BEHAVIORAL_ASSISTED


def registry_snapshot() -> dict:
    return {"registry": SCIENTIFIC_REGISTRY, "max_authorized_claim_level": max_authorized_claim_level(),
            "note": "product code must not assert neural-content decoding at this level"}
