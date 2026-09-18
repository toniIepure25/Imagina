"""ANIMUS feedback normalization.

Turns the many user feedback channels (closer/farther, pairwise, attribute corrections, object edits,
free-text, confidence, re-imagination) into a single ``FeedbackEvidence`` type with uncertainty and
provenance. Also wraps the digital twin's responses for the closed-loop benchmark. Free text is mapped to
structured intents by a small, explicit keyword table — never by an external service.
"""
from __future__ import annotations

from app.core.animus.claims import L0_SIMULATED, L1_BEHAVIORAL_ASSISTED
from app.core.animus.models import (
    FB_ATTRIBUTE,
    FB_CLOSER_FARTHER,
    FB_CONFIDENCE,
    FB_OBJECT,
    FB_PAIRWISE,
    FB_REIMAGINE,
    FeedbackEvidence,
)

# UI attribute-direction -> (attribute, target_option).
DIRECTION_MAP: dict[str, tuple[str, str]] = {
    "more_blue": ("color_palette", "cold"),
    "cooler": ("color_palette", "cold"),
    "warmer": ("color_palette", "warm"),
    "more_vivid": ("color_palette", "vivid"),
    "brighter": ("brightness", "bright"),
    "darker": ("brightness", "dark"),
    "less_fog": ("texture", "smooth"),
    "more_detailed": ("texture", "detailed"),
    "more_depth": ("depth", "deep"),
    "flatter": ("depth", "flat"),
    "more_motion": ("motion", "dynamic"),
    "calmer": ("motion", "still"),
    "wider": ("viewpoint", "wide"),
    "closer_view": ("viewpoint", "close"),
    "more_realistic": ("realism", "realistic"),
    "more_abstract": ("realism", "abstract"),
}

# free-text keyword -> direction token (explicit, auditable).
FREETEXT_KEYWORDS: dict[str, str] = {
    "blue": "more_blue", "cold": "cooler", "warm": "warmer", "vivid": "more_vivid",
    "bright": "brighter", "dark": "darker", "fog": "less_fog", "detail": "more_detailed",
    "depth": "more_depth", "flat": "flatter", "motion": "more_motion", "calm": "calmer",
    "wide": "wider", "close": "closer_view", "realistic": "more_realistic", "abstract": "more_abstract",
}


def normalize_feedback(raw: dict, claim_level: str = L1_BEHAVIORAL_ASSISTED) -> FeedbackEvidence:
    """Normalize a raw UI/twin feedback dict into FeedbackEvidence. Fail-closed on unknown channels."""
    ch = raw.get("channel")
    prov = {"origin": raw.get("origin", "user"), "raw_channel": ch}
    if ch == FB_CLOSER_FARTHER:
        return FeedbackEvidence(FB_CLOSER_FARTHER,
                                {"preferred_embedding": raw["preferred_embedding"],
                                 "closer": bool(raw.get("closer", True))},
                                uncertainty=float(raw.get("uncertainty", 0.2)), provenance=prov,
                                claim_level=claim_level)
    if ch == FB_PAIRWISE:
        return FeedbackEvidence(FB_PAIRWISE,
                                {"preferred_embedding": raw["preferred_embedding"], "closer": True},
                                uncertainty=float(raw.get("uncertainty", 0.2)), provenance=prov,
                                claim_level=claim_level)
    if ch == FB_ATTRIBUTE:
        attr = raw.get("attribute")
        target = raw.get("target_option")
        if target is None and "direction" in raw:
            attr, target = DIRECTION_MAP[raw["direction"]]
        return FeedbackEvidence(FB_ATTRIBUTE,
                                {"attribute": attr, "target_option": target,
                                 "strength": float(raw.get("strength", 1.0))},
                                uncertainty=float(raw.get("uncertainty", 0.25)), provenance=prov,
                                claim_level=claim_level)
    if ch == FB_OBJECT:
        return FeedbackEvidence(FB_OBJECT,
                                {"object": raw["object"], "op": raw.get("op", "add")},
                                uncertainty=float(raw.get("uncertainty", 0.25)), provenance=prov,
                                claim_level=claim_level)
    if ch == FB_CONFIDENCE:
        return FeedbackEvidence(FB_CONFIDENCE, {"confidence": float(raw.get("confidence", 0.0))},
                                uncertainty=float(raw.get("uncertainty", 0.3)), provenance=prov,
                                claim_level=claim_level)
    if ch == FB_REIMAGINE:
        return FeedbackEvidence(FB_REIMAGINE, {"reimagining": True},
                                uncertainty=0.3, provenance=prov, claim_level=claim_level)
    raise ValueError(f"unknown feedback channel: {ch!r}")


def parse_freetext(text: str) -> list[dict]:
    """Map free-text clarification to a list of structured attribute-direction feedback dicts."""
    low = text.lower()
    out = []
    for kw, direction in FREETEXT_KEYWORDS.items():
        if kw in low:
            attr_dir = DIRECTION_MAP[direction]
            out.append({"channel": FB_ATTRIBUTE, "attribute": attr_dir[0],
                        "target_option": attr_dir[1], "origin": "freetext"})
    return out


def twin_confidence_feedback(confidence: float) -> FeedbackEvidence:
    return normalize_feedback({"channel": FB_CONFIDENCE, "confidence": confidence, "origin": "twin"},
                              claim_level=L0_SIMULATED)
