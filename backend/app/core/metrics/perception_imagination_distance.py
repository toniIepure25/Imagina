"""IMAGINA Perception-Imagination Distance (PID) v1 — Proxy metric.

Estimates distance between a perception reference state and current imagery state.
Lower PID = more perception-like imagery. NOT a validated neural distance measure.
"""

from typing import Optional


def compute_pid(
    attention_stability: float = 0.5,
    relaxation: float = 0.5,
    imagery_engagement: float = 0.5,
    vividness_proxy: float = 0.5,
    sensory_detail: float = 0.5,
    temporal_stability: float = 0.5,
    self_report_vividness: Optional[float] = None,
    self_report_stability: Optional[float] = None,
    perception_reference: Optional[dict] = None,
    current_state: Optional[dict] = None,
) -> dict:
    """Compute PID score. Lower PID = closer to perception-like state.

    Uses feature distance, cosine similarity proxy, and self-report alignment.
    """

    # Default perception reference (idealized perception state)
    ref = perception_reference or {
        "attention_stability": 0.85,
        "relaxation": 0.6,
        "imagery_engagement": 0.9,
        "vividness_proxy": 0.9,
        "sensory_detail": 0.9,
        "temporal_stability": 0.85,
    }

    cur = current_state or {
        "attention_stability": attention_stability,
        "relaxation": relaxation,
        "imagery_engagement": imagery_engagement,
        "vividness_proxy": vividness_proxy,
        "sensory_detail": sensory_detail,
        "temporal_stability": temporal_stability,
    }

    # Feature vector distance (Euclidean, normalized)
    keys = ["attention_stability", "relaxation", "imagery_engagement",
            "vividness_proxy", "sensory_detail", "temporal_stability"]
    vec_ref = [ref.get(k, 0.5) for k in keys]
    vec_cur = [cur.get(k, 0.5) for k in keys]

    squared_diff = sum((a - b) ** 2 for a, b in zip(vec_ref, vec_cur))
    feature_distance = min(1.0, squared_diff / len(keys)) ** 0.5

    # Cosine similarity proxy (1 - cos_sim mapped to distance)
    dot = sum(a * b for a, b in zip(vec_ref, vec_cur))
    norm_ref = sum(a ** 2 for a in vec_ref) ** 0.5 + 1e-10
    norm_cur = sum(b ** 2 for b in vec_cur) ** 0.5 + 1e-10
    cos_sim = dot / (norm_ref * norm_cur)
    cosine_distance = max(0.0, min(1.0, (1.0 - cos_sim) / 2.0))

    # Self-report alignment
    sr_dist = 0.5
    if self_report_vividness is not None and self_report_stability is not None:
        sr_norm_v = min(1.0, max(0.0, self_report_vividness / 10.0))
        sr_norm_s = min(1.0, max(0.0, self_report_stability / 10.0))
        sr_dist = 1.0 - ((sr_norm_v + sr_norm_s) / 2.0)

    # Composite PID
    pid = 0.35 * feature_distance + 0.30 * cosine_distance + 0.20 * sr_dist + 0.15 * (1.0 - imagery_engagement)
    pid = max(0.0, min(1.0, pid))

    confidence = max(0.0, min(1.0, 0.7 + imagery_engagement * 0.3))

    if pid < 0.3:
        interpretation = "Imagery state close to perception-like — strong coherence."
    elif pid < 0.5:
        interpretation = "Moderate perception-imagination distance — developing clarity."
    elif pid < 0.7:
        interpretation = "Significant distance from perception — imagery is weak or diffuse."
    else:
        interpretation = "Large perception-imagination gap — imagery is very different from perception."

    return {
        "pid_score": round(pid, 4),
        "confidence": round(confidence, 4),
        "components": {
            "feature_distance": round(feature_distance, 4),
            "cosine_distance": round(cosine_distance, 4),
            "self_report_distance": round(sr_dist, 4),
            "engagement_penalty": round(0.15 * (1.0 - imagery_engagement), 4),
        },
        "interpretation": interpretation,
        "disclaimer": "Experimental proxy metric — PID does NOT measure actual neural distance. "
                      "Lower PID may indicate more perception-like imagery, not necessarily better imagery.",
    }
