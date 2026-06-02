"""IMAGINA V15 — Adaptive Execution Analytics.

Analyzes plan execution: adherence, subjective metrics, PID checkpoint analysis,
response categorization, multi-execution patterns.
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


def _get_execution(user_id, execution_id):
    from app.core.adaptive.adaptive_plan_execution import get_plan_execution
    return get_plan_execution(user_id, execution_id)


def analyze_plan_execution(user_id="default", execution_id=None):
    if not execution_id:
        from app.core.adaptive.adaptive_plan_execution import get_latest_plan_execution
        ex = get_latest_plan_execution(user_id)
        if not ex:
            return {"error": "no_execution_found", **SAFETY}
        execution_id = ex["execution_id"]

    manifest = _get_execution(user_id, execution_id)
    if not manifest:
        return {"error": "execution_not_found", **SAFETY}

    days = manifest.get("days", [])
    total = len(days)
    completed = [d for d in days if d["status"] == "completed"]
    skipped = [d for d in days if d["status"] == "skipped"]

    adherence_rate = len(completed) / max(total, 1)

    ratings = {
        "difficulty": [], "fatigue": [], "clarity": [], "focus_quality": [],
    }
    for d in completed:
        c = d.get("checkin", {})
        for k in ratings:
            v = c.get(f"{k.split('_')[0] if k != 'focus_quality' else k}_rating", None)
            if k == "focus_quality":
                v = c.get("focus_quality")
            if v is not None:
                ratings[k].append(v)

    subjective = {
        "avg_difficulty": round(sum(ratings["difficulty"]) / max(len(ratings["difficulty"]), 1), 2),
        "avg_fatigue": round(sum(ratings["fatigue"]) / max(len(ratings["fatigue"]), 1), 2),
        "avg_clarity": round(sum(ratings["clarity"]) / max(len(ratings["clarity"]), 1), 2),
        "avg_focus_quality": round(sum(ratings["focus_quality"]) / max(len(ratings["focus_quality"]), 1), 2),
    }

    checkpoint_days = [d for d in days if d.get("requires_calibration")]
    checkpoint_pids = []
    for d in checkpoint_days:
        if d.get("checkpoint_pid") is not None:
            checkpoint_pids.append({"day": d["day"], "pid_v2": d["checkpoint_pid"]})

    pid_analysis = {}
    if len(checkpoint_pids) >= 2:
        baseline = checkpoint_pids[0]["pid_v2"]
        final = checkpoint_pids[-1]["pid_v2"]
        pid_analysis = {
            "baseline_pid": baseline,
            "final_pid": final,
            "baseline_to_final_change": round(final - baseline, 3),
            "meaningful_improvement": abs(final - baseline) >= 0.05,
            "checkpoint_pid_values": checkpoint_pids,
        }
        if len(checkpoint_pids) >= 3:
            mid = checkpoint_pids[1]["pid_v2"]
            pid_analysis["midpoint_pid"] = mid
            pid_analysis["midpoint_change"] = round(mid - baseline, 3)

    confidence = "low"
    if adherence_rate >= 0.7 and len(checkpoint_pids) >= 2:
        confidence = "high"
    elif adherence_rate >= 0.5 and len(checkpoint_pids) >= 1:
        confidence = "medium"

    response = _categorize_response(pid_analysis, subjective, adherence_rate)

    return {
        "user_id": user_id,
        "execution_id": execution_id,
        "plan_title": manifest.get("plan_title", ""),
        "training_focus": manifest.get("training_focus", ""),
        "execution_status": manifest.get("status", ""),
        "adherence": {
            "completed_days": len(completed),
            "total_days": total,
            "adherence_rate": round(adherence_rate, 3),
            "skipped_days": [d["day"] for d in skipped],
        },
        "subjective_metrics": subjective,
        "pid_checkpoint_analysis": pid_analysis,
        "response_category": response["category"],
        "response_detail": response["detail"],
        "confidence_level": confidence,
        "interpretation": _build_interpretation(response, pid_analysis, adherence_rate),
        **SAFETY,
    }


def _categorize_response(pid_analysis, subjective, adherence):
    cat = "insufficient_checkpoint_data"
    detail = "Not enough calibration checkpoints attached to assess response."

    if pid_analysis and pid_analysis.get("meaningful_improvement") is not None:
        change = pid_analysis.get("baseline_to_final_change", 0)

        if subjective.get("avg_fatigue", 3) > 7:
            cat = "fatigue_limited_response"
            detail = "High fatigue may have limited the training effect. Consider shorter sessions or rest between days."
        elif change < -0.10:
            cat = "strong_positive_response"
            detail = ("PID decreased by more than 0.10, suggesting a strong reduction in "
                      "perception-imagination distance. This is a positive personal observation "
                      "— not a clinical outcome.")
        elif change < -0.05:
            cat = "mild_positive_response"
            detail = ("PID decreased by more than 0.05, suggesting mild improvement. "
                      "A positive personal observation to continue exploring.")
        elif abs(change) < 0.03:
            cat = "stable_response"
            detail = ("PID remained stable. This is normal and can indicate a consistent baseline "
                      "or early-stage practice without measurable change yet.")
        elif change > 0.05:
            cat = "negative_response"
            detail = ("PID increased. Possible causes: fatigue, environmental changes, practice "
                      "effects, or natural variability. This is not a measure of training failure.")
        else:
            cat = "stable_response"
            detail = "PID change was small. Continue collecting data for a clearer trend."

    return {"category": cat, "detail": detail}


def _build_interpretation(response, pid_analysis, adherence):
    parts = []
    if response["category"] == "strong_positive_response":
        parts.append("Training appears to have reduced your perception-imagination distance. This is an exploratory personal observation.")
    elif response["category"] == "mild_positive_response":
        parts.append("Training shows a mild reduction in PID. Continue — more sessions may strengthen this trend.")
    elif response["category"] == "stable_response":
        parts.append("PID is stable. Consistency can be a useful baseline. Consider varying focus or difficulty.")
    elif response["category"] == "fatigue_limited_response":
        parts.append("High fatigue may have affected results. Try a fatigue-aware plan with shorter sessions.")
    elif response["category"] == "negative_response":
        parts.append("PID increased — this could be fatigue, context, or variability. Adjust plan and retry.")

    if adherence < 0.5:
        parts.append(f"Low adherence ({adherence:.0%}) limits confidence in these results.")
    if adherence < 1.0:
        parts.append(f"Adherence was {adherence:.0%} — completing more days improves signal quality.")

    return " ".join(parts)


def analyze_all_executions(user_id="default"):
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions
    executions = list_plan_executions(user_id)
    if not executions:
        return {"n_executions": 0, "status": "no_data", **SAFETY}

    analyses = []
    for ex in executions:
        a = analyze_plan_execution(user_id, ex["execution_id"])
        analyses.append(a)

    completed = [a for a in analyses if a.get("execution_status") == "completed"]
    adh_values = [a["adherence"]["adherence_rate"] for a in analyses]

    focus_responses = {}
    for a in analyses:
        f = a.get("training_focus", "unknown")
        cat = a.get("response_category", "")
        if f not in focus_responses:
            focus_responses[f] = []
        focus_responses[f].append(cat)

    best_focus = ""
    best_score = -1
    for f, cats in focus_responses.items():
        score = sum(1 for c in cats if c in ("strong_positive_response", "mild_positive_response"))
        if score > best_score:
            best_score = score
            best_focus = f

    avg_fatigue = round(
        sum(a.get("subjective_metrics", {}).get("avg_fatigue", 3) for a in analyses) / max(len(analyses), 1), 2
    )

    return {
        "user_id": user_id,
        "n_executions": len(executions),
        "n_completed": len(completed),
        "average_adherence": round(sum(adh_values) / max(len(adh_values), 1), 3),
        "best_training_focus": best_focus,
        "focus_responses": focus_responses,
        "average_fatigue": avg_fatigue,
        "recommendation": _execution_recommendation(focus_responses, avg_fatigue),
        **SAFETY,
    }


def _execution_recommendation(focus_responses, avg_fatigue):
    if avg_fatigue > 7:
        return "Consider fatigue-aware plans with shorter sessions and recovery days."
    if not focus_responses:
        return "Complete at least one training execution for personalized recommendations."
    if any("positive" in c for cats in focus_responses.values() for c in cats):
        return "Your training shows promising PID improvements. Continue with the best-responding focus."
    return "PID is stable or variable. Try a different training focus or consistency over more days."
