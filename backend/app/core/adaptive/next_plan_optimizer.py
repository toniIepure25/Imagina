"""IMAGINA V16 — Next Plan Optimizer.

Recommends and generates optimized adaptive plans based on
response model, fatigue/adherence patterns, and PID history.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
OPTIMIZED_DIR = os.path.join(BASE, "adaptive_optimized_plans")

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


def recommend_optimized_next_plan(user_id="default") -> dict:
    from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
    from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
    from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement
    from app.core.adaptive.plan_response_model import build_plan_response_model

    response_model = build_plan_response_model(user_id)
    fatigue_model = analyze_fatigue_adherence_patterns(user_id)
    pid_improvement = compute_pid_improvement(user_id)
    current_plan = load_latest_adaptive_training_plan(user_id)

    has_data = response_model.get("n_executions", 0) >= 2
    fatigue_risk = fatigue_model.get("fatigue", {}).get("risk_level", "low")
    adherence_risk = fatigue_model.get("adherence", {}).get("risk_level", "low")
    best_focus = response_model.get("best_focus", "")
    current_focus = current_plan.get("training_focus", "") if current_plan else ""
    pid_trend = pid_improvement.get("trend", "insufficient_data")

    recommendations = []
    rec_type = "insufficient_data"
    recommended_focus = ""
    adjustments = {
        "duration_multiplier": 1.0,
        "difficulty_delta": 0,
        "rest_days_added": False,
        "checkpoint_frequency": "day_1_4_7",
    }

    if not has_data:
        return {
            "user_id": user_id, "generated_at": datetime.now(timezone.utc).isoformat(),
            "recommendation_type": "insufficient_data",
            "message": "Complete at least 2 training executions for optimized recommendations.",
            "fallback_action": "Use standard V14 adaptive plan.",
            "confidence_level": "low",
            **SAFETY,
        }

    if fatigue_risk == "high":
        rec_type = "reduce_fatigue"
        recommended_focus = "fatigue_resistance"
        adjustments["duration_multiplier"] = 0.6
        adjustments["rest_days_added"] = True
        adjustments["difficulty_delta"] = -2
        recommendations.append(
            "Fatigue is high. Switching to fatigue-aware training with shorter sessions and rest days.")
    elif adherence_risk == "high":
        rec_type = "simplify_for_adherence"
        recommended_focus = best_focus if best_focus and best_focus != current_focus else "vividness_foundation"
        adjustments["duration_multiplier"] = 0.7
        adjustments["difficulty_delta"] = -1
        recommendations.append(
            "Adherence has been low. Simpler exercises and shorter duration may improve completion rate.")
    elif best_focus and best_focus == current_focus:
        resp_data = response_model.get("focus_models", {}).get(best_focus, {})
        resp_score = resp_data.get("response_score", 0)
        pid_change = resp_data.get("mean_pid_change", 0)

        if resp_score > 0.55 and pid_change < 0:
            rec_type = "continue_best_focus"
            recommended_focus = best_focus
            adjustments["difficulty_delta"] = 1
            recommendations.append(
                f"Your best-responding focus ({best_focus.replace('_', ' ')}) continues. "
                "Slightly increasing difficulty to build on positive response.")
        elif resp_score > 0.40:
            rec_type = "continue_best_focus"
            recommended_focus = best_focus
            recommendations.append(
                f"Continuing with {best_focus.replace('_', ' ')} — response has been moderate but stable.")
        else:
            rec_type = "switch_focus"
            foci = response_model.get("focus_models", {})
            alt_foci = [(f, m.get("response_score", 0)) for f, m in foci.items() if f != current_focus]
            alt_foci.sort(key=lambda x: x[1], reverse=True)
            recommended_focus = alt_foci[0][0] if alt_foci else "baseline_rebuild"
            recommendations.append(
                f"Current focus response is low. Trying {recommended_focus.replace('_', ' ')} instead.")
    elif best_focus and best_focus != current_focus:
        rec_type = "switch_to_best_focus"
        recommended_focus = best_focus
        recommendations.append(
            f"Switching to your best-responding focus: {best_focus.replace('_', ' ')}.")
    elif pid_trend in ("declining", "slightly_declining"):
        rec_type = "rebuild_baseline"
        recommended_focus = "baseline_rebuild"
        adjustments["difficulty_delta"] = -1
        recommendations.append(
            "PID has been increasing. Rebuilding from simpler baseline exercises.")
    else:
        rec_type = "continue_best_focus"
        recommended_focus = best_focus or "vividness_foundation"
        recommendations.append(
            "No strong indicators. Continuing with best-responding focus based on available data.")

    rec_len = fatigue_model.get("recommended_session_length_minutes", 10)
    target_duration = int(rec_len * adjustments["duration_multiplier"])
    adjustments["target_duration_minutes"] = target_duration

    conf = response_model.get("model_reliability", "low")

    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recommendation_type": rec_type,
        "recommended_focus": recommended_focus,
        "why": recommendations,
        "expected_adjustments": adjustments,
        "source": {
            "best_focus_from_model": best_focus,
            "current_focus": current_focus,
            "fatigue_risk": fatigue_risk,
            "adherence_risk": adherence_risk,
            "pid_trend": pid_trend,
        },
        "confidence_level": conf,
        **SAFETY,
    }


def generate_optimized_adaptive_plan(user_id="default") -> dict:
    recommendation = recommend_optimized_next_plan(user_id)

    if recommendation.get("recommendation_type") == "insufficient_data":
        return {**recommendation, "optimized_plan": None}

    from app.core.adaptive.adaptive_training_planner import (
        _suggest_calibration_task,
        generate_daily_plan_from_focus,
    )

    focus = recommendation["recommended_focus"]
    adj = recommendation.get("expected_adjustments", {})
    calib_task = _suggest_calibration_task(focus, "")

    daily_plan = generate_daily_plan_from_focus(focus, "detail_gap", calib_task)
    target_dur = adj.get("target_duration_minutes", 10)

    title_map = {
        "vividness_foundation": "Optimized Vividness",
        "detail_generation": "Optimized Detail Generation",
        "color_intensity_training": "Optimized Color Training",
        "spatial_stability_training": "Optimized Spatial Stability",
        "emotional_tone_control": "Optimized Emotional Control",
        "fatigue_resistance": "Optimized Fatigue-Aware",
        "confidence_stabilization": "Optimized Confidence",
        "baseline_rebuild": "Optimized Baseline Rebuild",
    }

    for d in daily_plan:
        d["duration_minutes"] = target_dur
        d["difficulty"] = max(1, min(6, d.get("difficulty", 2) + adj.get("difficulty_delta", 0)))

    plan_id = str(uuid4())
    plan = {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adaptive_plan_id": plan_id,
        "optimization_source": recommendation,
        "training_focus": focus,
        "plan_title": f"{title_map.get(focus, 'Optimized')} — 7-Day",
        "plan_rationale": " ".join(recommendation.get("why", [])),
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
        "adjustments_applied": adj,
        "safety": {
            "max_session_minutes": target_dur + 5,
            "pause_if_distressed": True,
            "no_clinical_claims": True,
            "personal_exploratory_only": True,
        },
        **SAFETY,
    }

    _save_optimized_plan(user_id, plan)
    return plan


def _save_optimized_plan(user_id, plan):
    d = os.path.join(OPTIMIZED_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    sn = os.path.join(d, "snapshots")
    os.makedirs(sn, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    with open(os.path.join(sn, f"{ts}.json"), "w") as f:
        json.dump(plan, f, indent=2, default=str)
    with open(os.path.join(d, "latest_optimized_plan.json"), "w") as f:
        json.dump(plan, f, indent=2, default=str)


def load_latest_optimized_plan(user_id="default"):
    p = os.path.join(OPTIMIZED_DIR, user_id, "latest_optimized_plan.json")
    return _load_json(p)
