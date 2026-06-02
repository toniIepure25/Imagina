"""Imagery Quality Index v2 — compositional experimental EEG proxy metric."""

import numpy as np

METRIC_NAME = "ImageryQualityIndex"
METRIC_VERSION = "v2.0"
ALLOWED_CLAIMS = [
    "experimental EEG-derived proxy metric",
    "engineering/scientific evaluation tool",
    "requires controlled experiments for validation",
]
FORBIDDEN_CLAIMS = [
    "clinical validation", "diagnostic tool", "mind reading",
    "dream decoding", "validated imagery measure", "cognitive enhancement",
]


def _stat(vals):
    if not vals:
        return {"mean": 0, "std": 0, "min": 0, "max": 0}
    a = np.array(vals)
    return {"mean": round(float(np.mean(a)), 4), "std": round(float(np.std(a)), 4) if len(vals) > 1 else 0,
            "min": round(float(np.min(a)), 4), "max": round(float(np.max(a)), 4)}


def _component(name, score, weight, conf, expl, ev):
    return {"name": name, "score": score, "weight": weight,
            "confidence": conf, "explanation": expl, "evidence_summary": ev}


def signal_quality_component(fvs):
    sq = [fv.signal_quality for fv in fvs]
    return _component("SignalQualityComponent", round(min(1.0, float(np.mean(sq)) if sq else 0), 4),
                      0.22, round(min(1.0, len(fvs) / 10.0), 4),
                      f"Mean signal quality across {len(fvs)} windows", _stat(sq))


def artifact_penalty_component(fvs):
    bl = float(np.mean([fv.blink_score or 0 for fv in fvs]))
    mu = float(np.mean([fv.muscle_score or 0 for fv in fvs]))
    cl = float(np.mean([fv.clipping_score or 0 for fv in fvs]))
    md = float(np.mean([fv.missing_data_ratio or 0 for fv in fvs]))
    p = bl * 0.3 + mu * 0.3 + cl * 0.2 + md * 0.2
    return _component("ArtifactPenaltyComponent", round(max(0.0, 1.0 - p), 4),
                      0.14, round(min(1.0, len(fvs) / 10.0), 4),
                      f"blink={bl:.3f} muscle={mu:.3f} clip={cl:.3f} mdr={md:.3f}",
                      {"blink_mean": round(bl, 4), "muscle_mean": round(mu, 4),
                       "clip_mean": round(cl, 4), "mdr_mean": round(md, 4)})


def alpha_stability_component(fvs):
    al = [fv.alpha_power for fv in fvs]
    if len(al) < 2:
        return _component("AlphaStabilityComponent", 0.5, 0.14, 0.0, "Insufficient windows", {})
    cv = float(np.std(al)) / max(float(np.mean(al)), 0.001)
    return _component("AlphaStabilityComponent", round(max(0.0, 1.0 - min(1.0, cv * 2.0)), 4),
                      0.14, round(min(1.0, len(fvs) / 20.0), 4), f"Alpha CV={cv:.3f}", _stat(al))


def theta_alpha_balance_component(fvs):
    tb = [fv.theta_beta_ratio for fv in fvs]
    m = float(np.mean(tb)) if tb else 1.0
    return _component("ThetaAlphaBalanceComponent", round(max(0.0, min(1.0, 1.0 - abs(m - 1.0) * 0.5)), 4),
                      0.10, round(min(1.0, len(fvs) / 10.0), 4), f"Theta/beta ratio={m:.3f}", _stat(tb))


def beta_arousal_penalty_component(fvs):
    be = [fv.beta_power for fv in fvs]
    m = float(np.mean(be)) if be else 0.3
    p = max(0.0, m - 0.5) * 2.0
    return _component("BetaArousalPenaltyComponent", round(max(0.0, 1.0 - p), 4),
                      0.10, round(min(1.0, len(fvs) / 10.0), 4), f"Mean beta={m:.3f}", _stat(be))


def temporal_consistency_component(fvs):
    if len(fvs) < 3:
        return _component("TemporalConsistencyComponent", 0.5, 0.15, 0.0, "Insufficient windows", {})
    vecs = np.array([[fv.theta_power, fv.alpha_power, fv.beta_power, fv.signal_quality] for fv in fvs])
    diffs = np.diff(vecs, axis=0)
    vol = float(np.mean(np.abs(diffs)))
    return _component("TemporalConsistencyComponent", round(max(0.0, 1.0 - vol * 3.0), 4),
                      0.15, round(min(1.0, len(fvs) / 30.0), 4), f"Feature volatility={vol:.4f}",
                      {"volatility": round(vol, 6)})


def representation_consistency_component(fvs):
    if len(fvs) < 3:
        return _component("RepresentationConsistencyComponent", 0.5, 0.15, 0.0, "Insufficient windows", {})
    vecs = np.array([[fv.theta_power, fv.alpha_power, fv.beta_power, fv.signal_quality,
                      fv.theta_beta_ratio, fv.alpha_stability] for fv in fvs])
    mean_vec = np.mean(vecs, axis=0)
    distances = np.linalg.norm(vecs - mean_vec, axis=1)
    md = float(np.mean(distances))
    mx = md or 0.001
    return _component("RepresentationConsistencyComponent", round(max(0.0, 1.0 - min(1.0, md / max(0.1, mx))), 4),
                      0.15, round(min(1.0, len(fvs) / 30.0), 4),
                      f"Mean embedding distance={md:.4f}", {"mean_embedding_distance": round(md, 6)})


def compute_iqi_v2(fvs):
    comps = [
        signal_quality_component(fvs), artifact_penalty_component(fvs),
        alpha_stability_component(fvs), theta_alpha_balance_component(fvs),
        beta_arousal_penalty_component(fvs), temporal_consistency_component(fvs),
        representation_consistency_component(fvs),
    ]
    tw = sum(c["weight"] for c in comps)
    score = round(sum(c["score"] * c["weight"] for c in comps) / max(tw, 0.01), 4)
    conf = round(float(np.mean([c["confidence"] for c in comps])), 4)
    return {
        "metric_name": METRIC_NAME, "metric_version": METRIC_VERSION,
        "final_score": score, "confidence": conf, "component_scores": comps,
        "allowed_claims": ALLOWED_CLAIMS, "forbidden_claims": FORBIDDEN_CLAIMS,
    }
