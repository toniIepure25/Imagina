"""IMAGINA V21 — Skill Tree + Longitudinal Model + Milestones + Plateaus + Difficulty + Weekly Report + Curriculum."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
SKILL_DIR = os.path.join(BASE, "longitudinal_skill_models")
MILESTONE_DIR = os.path.join(BASE, "mastery_milestones")
PLATEAU_DIR = os.path.join(BASE, "plateau_analysis")
WEEKLY_DIR = os.path.join(BASE, "weekly_progress_reports")
CURRICULUM_DIR = os.path.join(BASE, "curriculum_updates")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

DIMENSIONS = ["vividness", "stability", "color_control", "spatial_control",
              "detail", "motion", "emotion", "multisensory", "meta_control"]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _append_jsonl(p, entry):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ─── SKILL TREE ─────────────────────────────────────────────────

LEVELS = [
    (1, "Foundation", "Basic control and awareness of the dimension.", 0.40, 3),
    (2, "Control", "Consistent deliberate manipulation of the dimension.", 0.55, 5),
    (3, "Stability Under Load", "Maintaining quality under fatigue, effort, or complexity.", 0.65, 8),
    (4, "Complex Integration", "Combining with other dimensions smoothly.", 0.75, 12),
    (5, "Mastery / Transfer", "Flexible, reliable, transferable across contexts.", 0.85, 16),
]

def _branch(dim):
    cats_map = {
        "vividness": ["basic_vividness"], "stability": ["spatial_stability", "meta_control"],
        "color_control": ["color_control"], "spatial_control": ["spatial_stability", "perspective_control"],
        "detail": ["detail_generation"], "motion": ["motion_imagery"],
        "emotion": ["emotional_tone_imagery"], "multisensory": ["multisensory_imagery"],
        "meta_control": ["meta_control"],
    }
    tasks_map = {
        "vividness": ["red_circle_vividness", "blue_cube_vividness", "candle_flame_vividness"],
        "stability": ["static_cube_stability", "hold_image_30_seconds"],
        "color_control": ["color_shift_red_to_blue", "saturation_control"],
        "spatial_control": ["static_cube_stability", "rotating_cube_stability", "room_layout_stability"],
        "detail": ["apple_detail_generation", "face_detail_generation", "forest_scene_detail"],
        "motion": ["rotating_object", "falling_leaf", "walking_path_simulation"],
        "emotion": ["calm_scene_generation", "joyful_memory_scene", "neutral_object_scene"],
        "multisensory": ["visual_plus_sound_scene", "visual_plus_touch_object", "visual_plus_smell_food"],
        "meta_control": ["hold_image_30_seconds", "intentionally_blur_then_refocus", "switch_between_two_images"],
    }
    return [{
        "dimension": dim, "level": lv, "level_name": ln, "description": ld,
        "unlock_criteria": {"min_completed_sessions": mc, "min_avg_iqi_proxy": th - 0.05,
                            "max_avg_pid_proxy": 1.0 - th + 0.05, "min_confidence": 0.5},
        "recommended_task_categories": cats_map.get(dim, []),
        "recommended_task_ids": tasks_map.get(dim, [])[:lv],
        "training_focus": dim.replace("_", "") + "_training",
        "next_unlock": (f"Level {lv+1}: {LEVELS[lv][1]}" if lv < 5 else "This is the highest level."),
    } for lv, ln, ld, th, mc in LEVELS]


SKILL_TREE = {dim: _branch(dim) for dim in DIMENSIONS}


def get_skill_tree():
    return {"branches": SKILL_TREE, "n_dimensions": len(DIMENSIONS), "max_level": 5, **SAFETY}


def get_skill_branch(dimension):
    if dimension not in DIMENSIONS:
        return {"error": "invalid_dimension", "dimension": dimension,
                "valid_dimensions": DIMENSIONS, **SAFETY}
    return {"dimension": dimension, "levels": SKILL_TREE[dimension], **SAFETY}


def get_skill_level(dimension, level):
    if dimension not in DIMENSIONS:
        return {"error": "invalid_dimension", **SAFETY}
    if level < 1 or level > 5:
        return {"error": "invalid_level", "level": level, "valid_range": "1-5", **SAFETY}
    return {"dimension": dimension, "level": level, "details": SKILL_TREE[dimension][level - 1], **SAFETY}


# ─── LONGITUDINAL SKILL MODEL ───────────────────────────────────

def _get_all_session_data(user_id):
    from app.core.imagery.guided_session_runtime import list_guided_sessions
    from app.core.imagery.task_session_manager import list_imagery_task_sessions
    v19 = [s for s in list_imagery_task_sessions(user_id) if s.get("status") == "completed"]
    v20 = [s for s in list_guided_sessions(user_id) if s.get("status") == "completed"]
    return v19, v20


def _dim_sessions(v19, v20):
    all_sessions = []
    for s in v20:
        targets = s.get("task_metadata", {}).get("target_dimensions", [])
        summary = s.get("final_summary") or {}
        all_sessions.append({
            "timestamp": s.get("completed_at", s.get("started_at", "")),
            "targets": targets, "iqi": summary.get("final_iqi_proxy", 0.5),
            "pid": summary.get("final_pid_proxy", 0.5),
            "fatigue": summary.get("avg_fatigue", 3),
            "effort": summary.get("avg_effort", 5),
            "confidence": (s.get("micro_checkins", [{}])[-1].get("confidence", 7) / 10
                           if s.get("micro_checkins") else 0.7),
            "stability": summary.get("avg_stability", 5),
        })
    for s in v19:
        targets = s.get("task_metadata", {}).get("target_dimensions", [])
        scores = s.get("dimension_scores") or {}
        ratings = s.get("rating_payload") or {}
        all_sessions.append({
            "timestamp": s.get("completed_at", s.get("started_at", "")),
            "targets": targets, "iqi": scores.get("vividness", 0.5),
            "pid": 1.0 - scores.get("vividness", 0.5),
            "fatigue": ratings.get("fatigue", 3),
            "effort": ratings.get("effort", 5),
            "confidence": ratings.get("confidence", 7) / 10,
            "stability": ratings.get("stability", 5),
        })
    return sorted(all_sessions, key=lambda x: x.get("timestamp", ""))


def build_longitudinal_skill_model(user_id="default"):
    v19, v20 = _get_all_session_data(user_id)
    all_sessions = _dim_sessions(v19, v20)
    if len(all_sessions) < 2:
        return {"user_id": user_id, "n_sessions": len(all_sessions),
                "status": "insufficient_data", **SAFETY}

    dim_profiles = {}
    for dim in DIMENSIONS:
        dim_sessions = [s for s in all_sessions if dim in s.get("targets", [])]
        n = len(dim_sessions)
        if n < 2:
            dim_profiles[dim] = {"current_score": 0, "baseline_score": 0, "delta": 0,
                                  "trend": "insufficient_data", "n_sessions": n,
                                  "current_level": 1, "unlock_progress": 0, **SAFETY}
            continue

        iqis = [s["iqi"] for s in dim_sessions]
        pids = [s["pid"] for s in dim_sessions]
        avg_iqi = round(sum(iqis) / n, 3)
        avg_pid = round(sum(pids) / n, 3)
        avg_fat = round(sum(s["fatigue"] for s in dim_sessions) / n, 2)
        avg_eff = round(sum(s["effort"] for s in dim_sessions) / n, 2)
        avg_conf = round(sum(s["confidence"] for s in dim_sessions) / n, 2)
        avg_stab = round(sum(s["stability"] for s in dim_sessions) / n, 2)

        baseline = round(sum(iqis[:min(3, n)]) / min(3, n), 3)
        current = iqis[-1]
        delta = round(current - baseline, 3)

        trend = "insufficient_data"
        if n >= 4:
            xs = list(range(n))
            sx = sum(xs)
            sy = sum(iqis)
            sxx = sum(x * x for x in xs)
            sxy = sum(x * y for (x, y) in zip(xs, iqis))
            slope = (n * sxy - sx * sy) / max(n * sxx - sx * sx, 1)
            trend = "improving" if slope > 0.01 else "stable" if abs(slope) <= 0.01 else "declining"

        conf_label = "high" if n >= 8 else "medium" if n >= 4 else "low"

        unlock_p = round(avg_iqi * 0.35 + current * 0.25 + avg_stab / 10 * 0.15 + avg_conf * 0.15 + max(0, 1 - avg_fat / 10) * 0.10, 3)
        for lv, _, _, th, _ in LEVELS:
            if unlock_p < th:
                break
        current_level = max(1, min(5, sum(1 for _, _, _, th, _ in LEVELS if unlock_p >= th - 0.05)))
        next_level = min(5, current_level + 1)

        plateau = "low"
        if trend in ("stable", "declining") and n >= 6 and unlock_p < 0.65:
            plateau = "high"
        elif trend == "stable" and n >= 4:
            plateau = "medium"

        dim_profiles[dim] = {
            "current_score": round(current, 3), "baseline_score": baseline,
            "delta_from_baseline": delta, "trend": trend, "trend_slope": round(slope, 3) if n >= 4 else 0,
            "n_sessions": n, "avg_iqi_proxy": avg_iqi, "avg_pid_proxy": avg_pid,
            "avg_fatigue": avg_fat, "avg_effort": avg_eff, "confidence": conf_label,
            "current_level": current_level, "level_name": LEVELS[current_level-1][1],
            "next_level": next_level, "unlock_progress": unlock_p,
            "plateau_risk": plateau,
            "interpretation": _dim_skill_interpretation(dim, trend, plateau, conf_label),
            **SAFETY,
        }

    model = {
        "user_id": user_id, "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_total_sessions": len(all_sessions),
        "dimensions": dim_profiles,
        "strongest_progress_dimension": max(dim_profiles.items(), key=lambda x: x[1].get("delta_from_baseline", -999))[0],
        "highest_level_dimension": max(dim_profiles.items(), key=lambda x: x[1].get("current_level", 0))[0],
        **SAFETY,
    }
    _save_skill_model(user_id, model)
    _check_milestones(user_id, model)
    return model


def _dim_skill_interpretation(dim, trend, plateau, conf):
    label = dim.replace("_", " ")
    if trend == "improving":
        return f"{label} is improving. Continue current training approach."
    if trend == "stable" and plateau == "high":
        return f"{label} appears stable with possible plateau. Consider varying tasks or difficulty."
    if trend == "stable":
        return f"{label} is stable. Consistent practice may lead to improvement."
    if trend == "declining":
        return f"{label} shows decline. Check for fatigue, overtraining, or reduced engagement."
    return f"Insufficient data to assess {label} trend."


def load_skill_model(user_id="default"):
    return _load_json(os.path.join(SKILL_DIR, user_id, "latest_skill_model.json"))


def _save_skill_model(user_id, model):
    d = os.path.join(SKILL_DIR, user_id)
    sn = os.path.join(d, "snapshots")
    os.makedirs(sn, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    _save_json(os.path.join(sn, f"{ts}.json"), model)
    _save_json(os.path.join(d, "latest_skill_model.json"), model)


# ─── MASTERY MILESTONES ─────────────────────────────────────────

MILESTONE_DEFS = [
    {"id": "first_guided_session", "title": "First Guided Session", "desc": "Completed the first guided imagery session.", "dim": None},
    {"id": "first_task_plan_done", "title": "First Task Plan Completed", "desc": "Completed all days in a task-based plan.", "dim": None},
    {"id": "level2_vividness", "title": "Vividness Level 2", "desc": "Reached Control level in vividness.", "dim": "vividness", "level": 2},
    {"id": "level2_stability", "title": "Stability Level 2", "desc": "Reached Control level in stability.", "dim": "stability", "level": 2},
    {"id": "level2_detail", "title": "Detail Level 2", "desc": "Reached Control level in detail.", "dim": "detail", "level": 2},
    {"id": "level3_any", "title": "First Level 3", "desc": "Reached Stability Under Load in any dimension.", "dim": None, "level": 3},
    {"id": "consistency_5", "title": "Consistent Practice (5)", "desc": "Completed 5 sessions in any dimension.", "dim": None},
    {"id": "consistency_10", "title": "Dedicated Practice (10)", "desc": "Completed 10 total sessions across all dimensions.", "dim": None},
    {"id": "fatigue_down", "title": "Fatigue Managed", "desc": "Average fatigue below 4 over last 5 sessions.", "dim": None},
    {"id": "multisensory_unlocked", "title": "Multisensory Explorer", "desc": "Completed at least 2 multisensory tasks.", "dim": "multisensory"},
    {"id": "meta_control_unlocked", "title": "Meta-Control Achieved", "desc": "Completed at least 2 meta-control tasks.", "dim": "meta_control"},
    {"id": "first_plateau_resolved", "title": "First Plateau Breaked", "desc": "Recovered from a plateau with improvement.", "dim": None},
]


def _check_milestones(user_id, model):
    existing = _load_json(os.path.join(MILESTONE_DIR, user_id, "latest_milestones.json"))
    achieved_ids = {m["milestone_id"] for m in (existing or {}).get("milestones", []) if m.get("achieved")}

    milestones = []
    dims = model.get("dimensions", {})
    n_total = model.get("n_total_sessions", 0)
    now = datetime.now(timezone.utc).isoformat()

    for md in MILESTONE_DEFS:
        mid = md["id"]
        achieved = mid in achieved_ids
        if not achieved:
            if mid == "first_guided_session" and n_total >= 1:
                achieved = True
            elif mid == "first_task_plan_done":
                try:
                    from app.core.imagery.guided_session_runtime import get_guided_plan_progress
                    prog = get_guided_plan_progress(user_id)
                    if prog.get("run", {}).get("status") == "completed":
                        achieved = True
                except Exception:
                    pass
            elif mid.startswith("level2_") and md.get("dim"):
                d = dims.get(md["dim"], {})
                if d.get("current_level", 1) >= 2:
                    achieved = True
            elif mid == "level3_any":
                if any(dims.get(d, {}).get("current_level", 1) >= 3 for d in DIMENSIONS):
                    achieved = True
            elif mid == "consistency_5":
                if any(dims.get(d, {}).get("n_sessions", 0) >= 5 for d in DIMENSIONS):
                    achieved = True
            elif mid == "consistency_10" and n_total >= 10:
                achieved = True
            elif mid == "fatigue_down":
                recent_dims = [d for d in dims.values() if d.get("n_sessions", 0) > 0]
                if recent_dims and sum(d.get("avg_fatigue", 5) for d in recent_dims) / len(recent_dims) < 4:
                    achieved = True
            elif mid == "multisensory_unlocked":
                if dims.get("multisensory", {}).get("n_sessions", 0) >= 2:
                    achieved = True
            elif mid == "meta_control_unlocked":
                if dims.get("meta_control", {}).get("n_sessions", 0) >= 2:
                    achieved = True
            elif mid == "first_plateau_resolved":
                try:
                    plat = _load_json(os.path.join(PLATEAU_DIR, user_id, "latest_plateau_analysis.json"))
                    if plat and not plat.get("plateau_detected", True):
                        prev_milestones = _load_json(os.path.join(MILESTONE_DIR, user_id, "latest_milestones.json"))
                        had_plateau = any(m.get("milestone_id") == "first_plateau_detected" and m.get("achieved")
                                          for m in (prev_milestones or {}).get("milestones", []))
                        if had_plateau:
                            achieved = True
                except Exception:
                    pass

        entry = dict(md)
        entry["milestone_id"] = mid
        entry["achieved"] = achieved
        entry["achieved_at"] = now if achieved else None
        entry["evidence"] = [f"n_total_sessions={n_total}"]
        entry["next_step"] = "Continue practicing to unlock." if not achieved else "Achieved!"
        if achieved and mid not in achieved_ids:
            _append_jsonl(os.path.join(MILESTONE_DIR, user_id, "milestone_events.jsonl"),
                          {"event": "milestone_achieved", "milestone_id": mid, "timestamp": now})
        milestones.append(entry)

    result = {
        "user_id": user_id, "generated_at": now,
        "achieved_milestones": [m for m in milestones if m["achieved"]],
        "pending_milestones": [m for m in milestones if not m["achieved"]],
        "latest_milestone": next((m for m in reversed(milestones) if m["achieved"]), None),
        "next_recommended_milestone": next((m for m in milestones if not m["achieved"]), milestones[-1]),
        **SAFETY,
    }
    d = os.path.join(MILESTONE_DIR, user_id)
    _save_json(os.path.join(d, "latest_milestones.json"), result)
    return result


def evaluate_mastery_milestones(user_id="default"):
    model = load_skill_model(user_id)
    if not model or model.get("status") == "insufficient_data":
        return {"user_id": user_id, "status": "insufficient_data", "milestones": [], **SAFETY}
    return _check_milestones(user_id, model)


# ─── PLATEAU DETECTOR ───────────────────────────────────────────

def detect_imagery_plateaus(user_id="default"):
    model = load_skill_model(user_id)
    if not model or model.get("status") == "insufficient_data":
        return {"user_id": user_id, "plateau_detected": False, "plateaus": [],
                "overall_risk": "low", "recommended_next_action": "Collect more session data.", **SAFETY}

    dims = model.get("dimensions", {})
    plateaus = []
    for dim in DIMENSIONS:
        d = dims.get(dim, {})
        if d.get("plateau_risk") == "high":
            plateaus.append({
                "type": "dimension_plateau", "dimension": dim, "severity": "high",
                "evidence": [f"trend={d.get('trend')}, sessions={d.get('n_sessions')}, unlock_progress={d.get('unlock_progress',0):.2f}"],
                "recommended_intervention": "Switch task category or reduce difficulty.",
                "recommended_task_adjustment": {"difficulty_delta": -1, "duration_multiplier": 0.75, "switch_task_category": _alt_category(dim)},
            })
        elif d.get("avg_fatigue", 0) >= 6:
            plateaus.append({
                "type": "fatigue_plateau", "dimension": dim, "severity": "medium",
                "evidence": [f"avg_fatigue={d.get('avg_fatigue')}"],
                "recommended_intervention": "Reduce duration and intensity.",
                "recommended_task_adjustment": {"difficulty_delta": -1, "duration_multiplier": 0.6},
            })

    recent = [d for d in dims.values() if d.get("n_sessions", 0) > 0]
    if recent:
        avg_fat = sum(d.get("avg_fatigue", 3) for d in recent) / len(recent)
        declining_iqis = sum(1 for d in dims.values() if d.get("trend") == "declining")
        if avg_fat >= 6 and declining_iqis >= 2:
            plateaus.append({"type": "overtraining_risk", "dimension": "overall", "severity": "high",
                             "evidence": [f"avg_fatigue={avg_fat:.1f}, declining_dims={declining_iqis}"],
                             "recommended_intervention": "Take a rest day. Reduce session length and difficulty."})

    overall = "high" if any(p["severity"] == "high" for p in plateaus) else \
              "medium" if plateaus else "low"

    result = {
        "user_id": user_id, "plateau_detected": len(plateaus) > 0,
        "plateaus": plateaus, "overall_risk": overall,
        "recommended_next_action": (plateaus[0]["recommended_intervention"] if plateaus
                                     else "Continue current training. No plateau detected."),
        **SAFETY,
    }
    d = os.path.join(PLATEAU_DIR, user_id)
    _save_json(os.path.join(d, "latest_plateau_analysis.json"), result)
    return result


def _alt_category(dim):
    m = {"vividness": "color_control", "stability": "meta_control", "color_control": "basic_vividness",
         "spatial_control": "perspective_control", "detail": "scene_construction", "motion": "spatial_stability",
         "emotion": "basic_vividness", "multisensory": "detail_generation", "meta_control": "basic_vividness"}
    return m.get(dim, "basic_vividness")


# ─── DIFFICULTY PROGRESSION ────────────────────────────────────

def recommend_next_difficulty(user_id="default", task_id=None, dimension=None):
    model = load_skill_model(user_id)
    plat = detect_imagery_plateaus(user_id)
    dim = dimension or (list(model.get("dimensions", {}).keys())[0] if model and model.get("dimensions") else "vividness")
    d = (model.get("dimensions", {}) if model else {}).get(dim, {})

    iqi = d.get("avg_iqi_proxy", 0.5)
    fatigue = d.get("avg_fatigue", 3)
    confidence = d.get("confidence", "medium")
    stability = d.get("current_score", 0.5) * 10

    reasons = []
    delta = 0
    if plat.get("overall_risk") == "high":
        delta = -1
        reasons.append("Plateau risk detected. Reducing difficulty to prevent overtraining.")
    elif fatigue >= 7:
        delta = -1
        reasons.append(f"High average fatigue ({fatigue:.1f}). Reducing difficulty for recovery.")
    elif iqi >= 0.7 and fatigue <= 5 and confidence in ("medium", "high") and stability >= 6:
        delta = +1
        reasons.append(f"Strong scores (IQI={iqi:.2f}, fatigue={fatigue:.1f}). Ready for more challenge.")

    target_lv = (d.get("current_level", 1) or 1) + delta
    target_lv = max(1, min(5, target_lv))
    rec = "increase" if delta > 0 else "decrease" if delta < 0 else "maintain"

    return {
        "recommendation": rec, "difficulty_delta": delta,
        "recommended_difficulty": target_lv, "reasoning": reasons if reasons else ["Maintaining current difficulty."],
        "next_task_suggestions": _suggest_tasks_for_level(dim, target_lv),
        "safety_state": "continue", **SAFETY,
    }


def _suggest_tasks_for_level(dim, level):
    try:
        from app.core.imagery.task_battery import list_imagery_tasks
        branch = SKILL_TREE.get(dim, [])
        cats = branch[min(level - 1, len(branch) - 1)].get("recommended_task_categories", [])
        tasks = list_imagery_tasks(cats[0])["tasks"] if cats else list_imagery_tasks()["tasks"]
        return [t["task_id"] for t in tasks[:3]]
    except Exception:
        return ["red_circle_vividness"]


# ─── WEEKLY PROGRESS REPORT ─────────────────────────────────────

def generate_weekly_imagery_progress_report(user_id="default", days=7):
    import datetime as dt

    from app.core.imagery.guided_session_runtime import list_guided_sessions
    cutoff = (datetime.now(timezone.utc) - dt.timedelta(days=days)).isoformat()
    sessions = [s for s in list_guided_sessions(user_id)
                if s.get("status") == "completed" and s.get("completed_at", "") > cutoff]
    n = len(sessions)
    if n == 0:
        return {"user_id": user_id, "window_days": days, "n_guided_sessions": 0,
                "status": "no_sessions_in_window", **SAFETY}

    iqis = [(s.get("final_summary") or {}).get("final_iqi_proxy", 0.5) for s in sessions]
    pids = [(s.get("final_summary") or {}).get("final_pid_proxy", 0.5) for s in sessions]
    avg_iqi = round(sum(iqis) / n, 3)
    avg_pid = round(sum(pids) / n, 3)
    consistency = round(n / days, 3)

    dim_counts = {}
    for s in sessions:
        for d in s.get("task_metadata", {}).get("target_dimensions", []):
            dim_counts[d] = dim_counts.get(d, 0) + 1
    most_trained = max(dim_counts.items(), key=lambda x: x[1])[0] if dim_counts else ""

    model = load_skill_model(user_id)
    most_improved = model.get("strongest_progress_dimension", "") if model else ""

    report = {
        "report_id": str(uuid4()), "user_id": user_id,
        "window_days": days, "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_guided_sessions": n, "practice_consistency": consistency,
        "average_iqi_proxy": avg_iqi, "average_pid_proxy": avg_pid,
        "most_trained_dimension": most_trained,
        "most_improved_dimension": most_improved,
        "recommended_next_week_focus": most_improved or most_trained or "vividness",
        "recommended_task_categories": _suggest_tasks_for_level(most_trained or "vividness", 2),
        "summary_markdown": "",
        **SAFETY,
    }
    report["summary_markdown"] = _weekly_md(report, model)
    d = os.path.join(WEEKLY_DIR, user_id)
    _save_json(os.path.join(d, "latest_weekly_report.json"), report)
    _save_json(os.path.join(d, "latest_weekly_report.md"), report["summary_markdown"])
    sn = os.path.join(d, "snapshots")
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    _save_json(os.path.join(sn, f"{ts}.json"), report)
    return report


def _weekly_md(report, model):
    dims = ""
    if model and model.get("dimensions"):
        for d, v in sorted(model["dimensions"].items(), key=lambda x: x[1].get("delta_from_baseline", -999), reverse=True)[:3]:
            dims += f"- {d.replace('_', ' ')}: L{v.get('current_level', 1)} ({v.get('delta_from_baseline', 0):+.2f})\n"
    return f"""# Weekly Imagery Progress

**Period**: Last {report['window_days']} days | **Sessions**: {report['n_guided_sessions']} | **Consistency**: {report['practice_consistency']:.0%}

## IQI/PID
- Avg IQI: {report['average_iqi_proxy']:.2f}
- Avg PID: {report['average_pid_proxy']:.2f}

## Top Dimensions
{dims}

## Next Week
Focus on: **{report['recommended_next_week_focus'].replace('_', ' ')}**

Self-report proxies only — not clinical or neural measurement.
"""


def get_weekly_progress_report(user_id="default"):
    return _load_json(os.path.join(WEEKLY_DIR, user_id, "latest_weekly_report.json"))


# ─── CURRICULUM UPDATE ──────────────────────────────────────────

def update_imagery_curriculum(user_id="default"):
    model = load_skill_model(user_id)
    plat = detect_imagery_plateaus(user_id)

    if not model or model.get("status") == "insufficient_data":
        return {"user_id": user_id, "status": "insufficient_data",
                "message": "Continue collecting session data.", **SAFETY}

    dims = model.get("dimensions", {})
    best_dim = model.get("strongest_progress_dimension", "vividness")
    worst_dim = min(dims.items(), key=lambda x: x[1].get("delta_from_baseline", 999))[0]

    rec = recommend_next_difficulty(user_id)
    delta = rec.get("difficulty_delta", 0)

    new_focus = best_dim
    reason = f"Based on recent progress, {best_dim.replace('_', ' ')} shows the strongest improvement."
    regenerate = False
    if plat.get("overall_risk") == "high" or delta < 0:
        new_focus = worst_dim
        reason = f"Plateau or fatigue detected. Shifting focus to {worst_dim.replace('_', ' ')} for recovery and variety."
        regenerate = True
    elif delta > 0:
        reason += " Increasing difficulty to build on gains."

    from app.core.imagery.imagery_phenotype import generate_task_based_imagery_plan
    new_plan = generate_task_based_imagery_plan(user_id, 7)

    update = {
        "curriculum_update_id": str(uuid4()), "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_focus": best_dim, "new_focus": new_focus,
        "reason_for_update": reason,
        "difficulty_adjustments": [{"dimension": new_focus, "delta": delta}],
        "task_replacements": _suggest_tasks_for_level(new_focus, dims.get(new_focus, {}).get("current_level", 1) + delta),
        "new_week_plan": {"plan_id": new_plan.get("plan_id", ""), "primary_gap": new_plan.get("primary_gap", "")},
        "should_regenerate_task_plan": regenerate,
        "should_continue_current_plan": not regenerate,
        **SAFETY,
    }
    d = os.path.join(CURRICULUM_DIR, user_id)
    _save_json(os.path.join(d, "latest_curriculum_update.json"), update)
    _append_jsonl(os.path.join(d, "updates.jsonl"), {"event": "curriculum_updated", **update})
    return update


def get_curriculum_update(user_id="default"):
    return _load_json(os.path.join(CURRICULUM_DIR, user_id, "latest_curriculum_update.json"))
