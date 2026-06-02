"""IMAGINA Imagery Quality Index (IQI) v1 — Rule-based composite proxy metric.

Estimates imagery quality from self-report, attention, engagement, relaxation,
fatigue, and uncertainty. NOT a clinical or validated neural measure.
"""

from typing import Optional


def compute_iqi(
    self_report_vividness: float = 5.0,
    self_report_stability: float = 5.0,
    self_report_effort: float = 5.0,
    attention_stability: float = 0.5,
    relaxation: float = 0.5,
    imagery_engagement: float = 0.5,
    fatigue: float = 0.2,
    uncertainty: float = 0.3,
    sensory_detail: Optional[float] = None,
    temporal_stability: Optional[float] = None,
) -> dict:
    """Compute IQI score and components from proxy features.

    All inputs normalized to [0, 1] or [0, 10] for self-reports.
    Returns score in [0, 1] with confidence and component breakdown.
    """

    # Normalize self-reports from 0-10 to 0-1
    vividness_norm = min(1.0, max(0.0, self_report_vividness / 10.0))
    stability_norm = min(1.0, max(0.0, self_report_stability / 10.0))
    effort_norm = min(1.0, max(0.0, self_report_effort / 10.0))

    # Self-report consistency: how close are vividness and stability?
    sr_consistency = 1.0 - abs(vividness_norm - stability_norm)

    # Sensory detail proxy (default to vividness if not provided)
    sensory = min(1.0, max(0.0, (sensory_detail or vividness_norm)))
    temporal = min(1.0, max(0.0, (temporal_stability or stability_norm)))

    # Composite IQI
    score = (
        0.20 * vividness_norm
        + 0.20 * stability_norm
        + 0.10 * attention_stability
        + 0.10 * imagery_engagement
        + 0.10 * relaxation
        + 0.10 * sr_consistency
        + 0.05 * sensory
        + 0.05 * temporal
        + 0.05 * min(1.0, effort_norm)
        - 0.08 * fatigue
        - 0.07 * uncertainty
    )

    score = max(0.0, min(1.0, score))

    # Confidence estimate based on input quality and uncertainty
    confidence = max(0.0, min(1.0, 1.0 - uncertainty * 0.7))

    # Warnings
    warnings_list = []
    if fatigue > 0.75:
        warnings_list.append("high_fatigue")
    if uncertainty > 0.6:
        warnings_list.append("high_uncertainty")
    if attention_stability < 0.3:
        warnings_list.append("low_attention")

    # Interpretation
    if score >= 0.80:
        interpretation = "Strong imagery quality — vivid and stable."
    elif score >= 0.60:
        interpretation = "Moderate imagery quality — developing consistency."
    elif score >= 0.40:
        interpretation = "Weak imagery — needs simplification or rest."
    else:
        interpretation = "Very weak imagery — consider pausing or switching task."

    return {
        "iqi_score": round(score, 4),
        "confidence": round(confidence, 4),
        "components": {
            "vividness_contribution": round(0.20 * vividness_norm, 4),
            "stability_contribution": round(0.20 * stability_norm, 4),
            "attention_contribution": round(0.10 * attention_stability, 4),
            "engagement_contribution": round(0.10 * imagery_engagement, 4),
            "relaxation_contribution": round(0.10 * relaxation, 4),
            "consistency_contribution": round(0.10 * sr_consistency, 4),
            "sensory_contribution": round(0.05 * sensory, 4),
            "temporal_contribution": round(0.05 * temporal, 4),
            "effort_contribution": round(0.05 * effort_norm, 4),
            "fatigue_penalty": round(-0.08 * fatigue, 4),
            "uncertainty_penalty": round(-0.07 * uncertainty, 4),
        },
        "warnings": warnings_list,
        "interpretation": interpretation,
        "disclaimer": "Experimental proxy metric — not a clinical or validated imagery measure.",
    }
