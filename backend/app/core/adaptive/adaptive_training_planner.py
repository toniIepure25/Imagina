"""IMAGINA V14 — Adaptive PID-Based Training Loop.

Uses PID v2 calibration results to identify weakest imagery dimensions,
generate personalized 7-day training plans, and track improvement over time.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
PLANS_DIR = os.path.join(BASE, "adaptive_plans")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

PID_DIMENSION_MAP = {
    "clarity_gap": "vividness_foundation",
    "detail_gap": "detail_generation",
    "color_gap": "color_intensity_training",
    "spatial_gap": "spatial_stability_training",
    "emotional_gap": "emotional_tone_control",
}

FOCUS_RATIONALE = {
    "vividness_foundation": "PID indicates imagery vividness could improve — "
        "starting with simple shapes and contrast exercises builds perceptual clarity.",
    "detail_generation": "PID detail gap is largest — "
        "layered detail practice can help generate richer mental images over time.",
    "color_intensity_training": "PID color gap is largest — "
        "color saturation and hue stability exercises strengthen color imagery.",
    "spatial_stability_training": "PID spatial gap is largest — "
        "spatial anchoring practice improves position and stability control.",
    "emotional_tone_control": "PID emotional gap is largest — "
        "practicing neutral emotional tone stability builds calm, controlled imagery.",
    "baseline_rebuild": "PID is large across many dimensions — "
        "rebuilding from simple exercises and collecting more data establishes a stable baseline.",
    "fatigue_resistance": "Fatigue scores are high — "
        "shorter, paced sessions help build endurance without degradation.",
    "confidence_stabilization": "Confidence is low — "
        "repeated easy exercises build self-rating stability and trust.",
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _get_pid_history(user_id="default"):
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


def _identify_weakest_dimension(sessions):
    dims = {}
    for s in sessions[-5:]:
        subs = s["pid_v2"].get("subscores", {})
        for k, v in subs.items():
            dims.setdefault(k, []).append(v)
    if not dims:
        return "detail_gap", {}
    dim_means = {}
    for k, vals in dims.items():
        dim_means[k] = round(sum(vals) / len(vals), 3)
    sorted_dims = sorted(dim_means.items(), key=lambda x: x[1], reverse=True)
    return sorted_dims[0][0], dim_means


def _suggest_calibration_task(focus, dim_name):
    task_map = {
        "vividness_foundation": "simple_red_circle_reference",
        "detail_generation": "textured_object_reference",
        "color_intensity_training": "blue_square_position_reference",
        "spatial_stability_training": "blue_square_position_reference",
        "emotional_tone_control": "symbolic_dream_scene_reference",
        "baseline_rebuild": "simple_red_circle_reference",
        "fatigue_resistance": "blue_square_position_reference",
        "confidence_stabilization": "simple_red_circle_reference",
    }
    return task_map.get(focus, "simple_red_circle_reference")


# ─── ADAPTIVE TRAINING PLAN ──────────────────────────────────────

def build_adaptive_training_plan(user_id="default") -> dict:
    sessions = _get_pid_history(user_id)
    if len(sessions) < 2:
        return {
            "user_id": user_id, "status": "insufficient_data",
            "message": "Collect at least 2 calibration sessions with PID v2 results first.",
            **SAFETY,
        }

    pids = [s["pid_v2"]["pid_v2"] for s in sessions]
    mean_pid = round(sum(pids) / len(pids), 3)
    weakest_dim, dim_means = _identify_weakest_dimension(sessions)

    # Check special conditions
    recent = sessions[-3:]
    avg_fatigue = sum(s.get("imagery_rating", {}).get("fatigue", 3) for s in recent) / max(len(recent), 1)
    avg_confidence = sum(s.get("imagery_rating", {}).get("confidence", 5) for s in recent) / max(len(recent), 1)
    avg_confidence = sum(s.get("imagery_rating", {}).get("confidence", 5) for s in recent) / max(len(recent), 1)

    focus = PID_DIMENSION_MAP.get(weakest_dim, "baseline_rebuild")
    if avg_fatigue > 7:
        focus = "fatigue_resistance"
    elif avg_confidence < 4:
        focus = "confidence_stabilization"
    elif mean_pid > 0.6:
        focus = "baseline_rebuild"

    conf_level = "high" if len(sessions) >= 8 else "medium" if len(sessions) >= 4 else "low"
    calib_task = _suggest_calibration_task(focus, weakest_dim)

    daily_plan = generate_daily_plan_from_focus(focus, weakest_dim, calib_task)

    plan = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adaptive_plan_id": str(uuid4()),
        "source": {
            "n_pid_sessions": len(sessions),
            "mean_pid_v2": mean_pid,
            "weakest_dimension": weakest_dim,
            "dimension_means": dim_means,
            "avg_fatigue_1_10": round(avg_fatigue, 1),
            "avg_confidence_1_10": round(avg_confidence, 1),
            "confidence_level": conf_level,
        },
        "training_focus": focus,
        "plan_title": _plan_title(focus),
        "plan_rationale": FOCUS_RATIONALE.get(focus, ""),
        "daily_plan": daily_plan,
        "checkpoint_schedule": [
            {"day": 1, "type": "baseline_calibration", "task_id": calib_task},
            {"day": 4, "type": "midpoint_calibration", "task_id": calib_task},
            {"day": 7, "type": "final_calibration", "task_id": calib_task},
        ],
        "expected_change": {
            "target_metric": "pid_v2",
            "desired_direction": "decrease",
            "minimum_meaningful_change": 0.05,
        },
        "safety": {
            "max_session_minutes": 15,
            "pause_if_distressed": True,
            "no_clinical_claims": True,
            "personal_exploratory_only": True,
        },
        **SAFETY,
    }

    save_adaptive_training_plan(user_id, plan)

    _add_phenotype_context(plan, user_id)

    return plan


# ─── PERSISTENCE ─────────────────────────────────────────────────

def save_adaptive_training_plan(user_id, plan):
    d = os.path.join(PLANS_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    sn = os.path.join(d, "snapshots")
    os.makedirs(sn, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    with open(os.path.join(sn, f"{ts}.json"), "w") as f:
        json.dump(plan, f, indent=2, default=str)
    with open(os.path.join(d, "latest_plan.json"), "w") as f:
        json.dump(plan, f, indent=2, default=str)


def load_latest_adaptive_training_plan(user_id="default"):
    p = os.path.join(PLANS_DIR, user_id, "latest_plan.json")
    return _load_json(p)


def list_adaptive_training_plans(user_id="default"):
    d = os.path.join(PLANS_DIR, user_id, "snapshots")
    if not os.path.isdir(d):
        return []
    plans = []
    for fn in sorted(os.listdir(d), reverse=True):
        r = _load_json(os.path.join(d, fn))
        if r:
            plans.append(r)
    return plans


def _add_phenotype_context(plan, user_id):
    try:
        from app.core.imagery.imagery_phenotype import analyze_imagery_gaps, load_imagery_phenotype
        phenotype = load_imagery_phenotype(user_id)
        if phenotype and phenotype.get("status") != "no_data":
            gaps = analyze_imagery_gaps(user_id)
            plan["imagery_phenotype_context"] = {
                "has_phenotype": True,
                "phenotype_label": phenotype.get("phenotype_label", ""),
                "primary_gap": gaps.get("primary_gap", ""),
                "target_dimensions": gaps.get("ranked_gaps", [{}])[0].get("recommended_task_categories", []) if gaps.get("ranked_gaps") else [],
                "recommended_task_ids": _suggest_tasks(gaps),
            }
    except Exception:
        pass


def _suggest_tasks(gaps):
    try:
        from app.core.imagery.task_battery import list_imagery_tasks
        categories = []
        for g in (gaps.get("ranked_gaps") or [])[:2]:
            categories.extend(g.get("recommended_task_categories", []))
        all_tasks = list_imagery_tasks()["tasks"]
        suggested = []
        for cat in categories[:3]:
            matches = [t for t in all_tasks if t.get("category") == cat]
            if matches:
                suggested.append(matches[0]["task_id"])
        return suggested[:5]
    except Exception:
        return []


_planner_module_safety = SAFETY
