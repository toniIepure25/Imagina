"""IMAGINA V14 — PID Improvement Tracker.

Tracks whether perception-imagination distance improves across calibration sessions.
Compares first vs latest, rolling means, per-dimension changes, training response analysis.
"""

import json
import os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _get_pid_sessions(user_id="default"):
    d = os.path.join(BASE, "calibration_sessions")
    sessions = []
    if not os.path.isdir(d):
        return sessions
    for sid in os.listdir(d):
        mp = os.path.join(d, sid, "manifest.json")
        m = _load_json(mp)
        if m and m.get("user_id") == user_id and m.get("status") == "completed" and m.get("pid_v2"):
            sessions.append(m)
    return sorted(sessions, key=lambda x: x.get("started_at", ""))


def compute_pid_improvement(user_id="default") -> dict:
    sessions = _get_pid_sessions(user_id)
    n = len(sessions)
    if n < 2:
        return {
            "user_id": user_id, "n_sessions": n, "trend": "insufficient_data",
            "message": "Need at least 2 completed calibration sessions to compute improvement.",
            **SAFETY,
        }

    first_pid = sessions[0]["pid_v2"]["pid_v2"]
    latest_pid = sessions[-1]["pid_v2"]["pid_v2"]
    absolute_change = round(latest_pid - first_pid, 3)
    relative_change_pct = round((absolute_change / max(first_pid, 0.01)) * 100, 1)

    rolling_first_3 = sessions[:3]
    rolling_last_3 = sessions[-3:]
    mean_first_3 = round(sum(s["pid_v2"]["pid_v2"] for s in rolling_first_3) / len(rolling_first_3), 3)
    mean_last_3 = round(sum(s["pid_v2"]["pid_v2"] for s in rolling_last_3) / len(rolling_last_3), 3)
    rolling_change = round(mean_last_3 - mean_first_3, 3)

    meaningful = abs(absolute_change) >= 0.05 or abs(rolling_change) >= 0.05

    if rolling_change < -0.05:
        trend = "improving"
    elif rolling_change > 0.05:
        trend = "declining"
    elif abs(rolling_change) < 0.02:
        trend = "stable"
    elif rolling_change < 0:
        trend = "slightly_improving"
    else:
        trend = "slightly_declining"

    dim_changes = {}
    for dim_key in ["clarity_gap", "detail_gap", "color_gap", "spatial_gap", "emotional_gap"]:
        first_d = sessions[0]["pid_v2"].get("subscores", {}).get(dim_key, 0.3)
        last_d = sessions[-1]["pid_v2"].get("subscores", {}).get(dim_key, 0.3)
        dim_changes[dim_key] = {
            "first": first_d, "latest": last_d,
            "change": round(last_d - first_d, 3),
        }

    avg_confidence = sum(s.get("imagery_rating", {}).get("confidence", 5) for s in sessions[-3:]) / max(len(sessions[-3:]), 1)
    avg_fatigue = sum(s.get("imagery_rating", {}).get("fatigue", 3) for s in sessions[-3:]) / max(len(sessions[-3:]), 1)
    reliability = "high" if n >= 8 and avg_confidence >= 6 and avg_fatigue < 5 else ("medium" if n >= 4 else "low")

    return {
        "user_id": user_id,
        "n_sessions": n,
        "first_pid": first_pid,
        "latest_pid": latest_pid,
        "absolute_change": absolute_change,
        "relative_change_percent": relative_change_pct,
        "rolling_first_3_mean_pid": mean_first_3,
        "rolling_last_3_mean_pid": mean_last_3,
        "rolling_change": rolling_change,
        "trend": trend,
        "meaningful_change": meaningful,
        "dimension_changes": dim_changes,
        "reliability": {
            "level": reliability,
            "avg_confidence_last_3": round(avg_confidence, 1),
            "avg_fatigue_last_3": round(avg_fatigue, 1),
        },
        "interpretation": _improvement_interpretation(trend, meaningful, n),
        **SAFETY,
    }


def _improvement_interpretation(trend, meaningful, n):
    if not meaningful:
        return ("No meaningful change (>=0.05 PID) detected yet. "
                "This is normal in early training. Continue practicing and calibrating.")
    if trend == "improving" or trend == "slightly_improving":
        return ("PID is decreasing, which is consistent with improved perception-imagination similarity. "
                "This is an exploratory personal observation — not a clinical result.")
    if trend == "declining" or trend == "slightly_declining":
        return ("PID is increasing. Possible causes: fatigue, environmental changes, or practice effects. "
                "This is normal variability — not a measure of training failure.")
    return ("PID appears stable. Your perception-imagination distance has not changed substantially. "
            "This is common and expected. Consistency itself can be a useful baseline.")


def compute_training_response(user_id="default", plan_id=None):
    improvement = compute_pid_improvement(user_id)

    if improvement.get("trend") == "insufficient_data":
        return {**improvement, "training_response": "insufficient_data"}

    plans = _load_latest_plan(user_id)

    # Check if there's an active plan
    has_plan = plans is not None
    trend = improvement.get("trend", "insufficient_data")
    meaningful = improvement.get("meaningful_change", False)

    if not has_plan:
        tr = "no_active_plan"
    elif trend in ("improving", "slightly_improving") and meaningful:
        tr = "improved"
    elif trend in ("declining", "slightly_declining"):
        tr = "worsened"
    elif trend == "stable":
        tr = "unchanged"
    else:
        tr = "insufficient_data"

    response_interpretations = {
        "improved": ("Your PID has decreased since training began. "
                     "This suggests perceptual-imagery similarity may be improving — "
                     "a positive personal observation, not a clinical outcome."),
        "worsened": ("Your PID has increased. "
                     "This could be due to fatigue, environmental changes, or natural practice variability. "
                     "Not a sign of training failure."),
        "unchanged": ("Your PID has not changed meaningfully. "
                      "Stability is normal and can indicate a consistent baseline."),
        "insufficient_data": "Not enough data to assess training yet. Continue practice.",
        "no_active_plan": "No active adaptive training plan found. Generate one to track response.",
    }

    return {
        "user_id": user_id,
        "training_response": tr,
        "has_active_plan": has_plan,
        "plan_title": plans.get("plan_title", "") if plans else "",
        "training_focus": plans.get("training_focus", "") if plans else "",
        "pid_improvement": improvement,
        "note": response_interpretations.get(tr, ""),
        **SAFETY,
    }


def _load_latest_plan(user_id):
    d = os.path.join(BASE, "adaptive_plans", user_id, "latest_plan.json")
    return _load_json(d)
