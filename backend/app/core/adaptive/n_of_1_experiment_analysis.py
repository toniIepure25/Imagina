"""IMAGINA V17 — N-of-1 Experiment Analysis & Evidence Score.

Analyzes controlled experiment results: baseline vs optimized, condition metrics,
effect-size proxy, evidence scoring.
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
    "scientific_boundary": ("Personal exploratory mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _get_experiment(user_id, experiment_id=None):
    from app.core.adaptive.n_of_1_experiment_execution import (
        get_latest_n_of_1_experiment,
        get_n_of_1_experiment,
    )
    if experiment_id:
        exp = get_n_of_1_experiment(user_id, experiment_id)
    else:
        exp = get_latest_n_of_1_experiment(user_id)
    if not exp:
        return None
    return exp, exp.get("experiment_id", experiment_id)


def analyze_n_of_1_experiment(user_id="default", experiment_id=None) -> dict:
    data = _get_experiment(user_id, experiment_id)
    if data is None:
        return {"error": "no_experiment_found", **SAFETY}
    exp, eid = data

    days = exp.get("days", [])
    baseline_days = [d for d in days if d.get("condition") == "baseline" and d["status"] == "completed"]
    optimized_days = [d for d in days if d.get("condition") == "optimized" and d["status"] == "completed"]

    def avg_metric(days_list, key):
        vals = [d.get("checkin", {}).get(key) for d in days_list if d.get("checkin", {}).get(key) is not None]
        return round(sum(vals) / max(len(vals), 1), 2) if vals else 0

    baseline_metrics = {
        "days": len(baseline_days),
        "adherence_blocks": _block_adherence(days, "baseline"),
        "avg_fatigue": avg_metric(baseline_days, "fatigue_rating"),
        "avg_clarity": avg_metric(baseline_days, "clarity_rating"),
        "avg_focus_quality": avg_metric(baseline_days, "focus_quality"),
        "avg_confidence": avg_metric(baseline_days, "confidence_rating"),
    }
    optimized_metrics = {
        "days": len(optimized_days),
        "adherence_blocks": _block_adherence(days, "optimized"),
        "avg_fatigue": avg_metric(optimized_days, "fatigue_rating"),
        "avg_clarity": avg_metric(optimized_days, "clarity_rating"),
        "avg_focus_quality": avg_metric(optimized_days, "focus_quality"),
        "avg_confidence": avg_metric(optimized_days, "confidence_rating"),
    }

    baseline_pids = [d["checkpoint_pid"] for d in days
                     if d["condition"] == "baseline" and d.get("checkpoint_pid") is not None]
    optimized_pids = [d["checkpoint_pid"] for d in days
                      if d["condition"] == "optimized" and d.get("checkpoint_pid") is not None]

    pid_analysis = {}
    if len(baseline_pids) >= 2 and len(optimized_pids) >= 2:
        base_change = baseline_pids[-1] - baseline_pids[0]
        opt_change = optimized_pids[-1] - optimized_pids[0]
        pid_analysis = {
            "baseline_pid_change": round(base_change, 3),
            "optimized_pid_change": round(opt_change, 3),
            "pid_delta_advantage": round(base_change - opt_change, 3),
            "baseline_start_pid": baseline_pids[0],
            "baseline_end_pid": baseline_pids[-1],
            "optimized_start_pid": optimized_pids[0],
            "optimized_end_pid": optimized_pids[-1],
        }

    direction = "inconclusive"
    if pid_analysis:
        delta = pid_analysis.get("pid_delta_advantage", 0)
        if delta > 0.10:
            direction = "strong_optimized_signal"
        elif delta > 0.05:
            direction = "optimized_better"
        elif delta < -0.05:
            direction = "baseline_better"

    confounds = []
    fat_diff = abs(baseline_metrics["avg_fatigue"] - optimized_metrics["avg_fatigue"])
    adh_diff = abs(baseline_metrics.get("adherence_blocks", 0) - optimized_metrics.get("adherence_blocks", 0))

    if fat_diff > 2:
        confounds.append("fatigue_difference_high")
    if adh_diff > 0.30:
        confounds.append("adherence_difference_high")
    if len(optimized_days) < 2 or len(baseline_days) < 2:
        confounds.append("low_completion_count")

    conf = "low"
    total_cp = len(baseline_pids) + len(optimized_pids)
    if total_cp >= 4 and not confounds:
        conf = "high"
    elif total_cp >= 2 and len(confounds) <= 1:
        conf = "medium"

    return {
        "experiment_id": eid,
        "user_id": user_id,
        "design_type": exp.get("design_type", ""),
        "status": exp.get("status", ""),
        "primary_result": {
            "direction": direction,
            "pid_delta_advantage": pid_analysis.get("pid_delta_advantage", 0),
            "effect_size_proxy": _effect_label(pid_analysis.get("pid_delta_advantage", 0)),
            "confidence_level": conf,
        },
        "condition_metrics": {
            "baseline": baseline_metrics,
            "optimized": optimized_metrics,
        },
        "pid_comparison": pid_analysis,
        "confounds": confounds,
        "interpretation": _experiment_interpretation(direction, confounds, conf),
        **SAFETY,
    }


def _block_adherence(days, condition):
    cond_days = [d for d in days if d.get("condition") == condition]
    total = len(cond_days)
    if total == 0:
        return 0
    completed = sum(1 for d in cond_days if d["status"] == "completed")
    return round(completed / total, 3)


def _effect_label(delta):
    if abs(delta) > 0.15:
        return "large"
    if abs(delta) > 0.08:
        return "medium"
    if abs(delta) > 0.03:
        return "small"
    return "negligible"


def _experiment_interpretation(direction, confounds, confidence):
    parts = []
    if direction == "strong_optimized_signal" or direction == "optimized_better":
        parts.append("The optimized plan showed a stronger PID decrease than baseline. "
                     "This suggests the personalized plan may work better for you — "
                     "a personal exploratory observation, not causal proof.")
    elif direction == "baseline_better":
        parts.append("The baseline plan showed a stronger PID decrease. "
                     "This could mean the simpler approach is more effective, "
                     "or that other factors (practice, timing) influenced results.")
    else:
        parts.append("No clear difference was detected between baseline and optimized conditions.")
    if confounds:
        parts.append(f"Confounds present: {', '.join(confounds)}. These reduce confidence.")
    if confidence == "low":
        parts.append("Low confidence — more checkpoint calibrations are needed for clearer results.")
    return " ".join(parts)


def compute_n_of_1_evidence_score(user_id="default", experiment_id=None) -> dict:
    analysis = analyze_n_of_1_experiment(user_id, experiment_id)
    if analysis.get("error"):
        return {**analysis, "evidence_score": 0, "category": "insufficient_data"}

    exp_data = _get_experiment(user_id, experiment_id)
    if exp_data is None:
        return {"error": "no_experiment_found", "evidence_score": 0, **SAFETY}
    exp, _ = exp_data

    pid = analysis.get("pid_comparison", {})
    pid_effect_raw = abs(pid.get("pid_delta_advantage", 0))
    pid_effect_score = min(35, int(pid_effect_raw * 200))

    adh = max(
        analysis.get("condition_metrics", {}).get("baseline", {}).get("adherence_blocks", 0),
        analysis.get("condition_metrics", {}).get("optimized", {}).get("adherence_blocks", 0),
    )
    adherence_score = int(adh * 20)

    baseline_f = analysis.get("condition_metrics", {}).get("baseline", {}).get("avg_fatigue", 5)
    optimized_f = analysis.get("condition_metrics", {}).get("optimized", {}).get("avg_fatigue", 5)
    max_fatigue = max(baseline_f, optimized_f)
    fatigue_score = max(0, 15 - int(max_fatigue * 2))

    total_cp = len(pid.get("baseline_start_pid", "")) if pid else 0
    cals = analysis.get("condition_metrics", {}).get("baseline", {}).get("days", 0) + \
           analysis.get("condition_metrics", {}).get("optimized", {}).get("days", 0)
    checkpoint_ratio = min(1.0, total_cp / max(cals, 1))
    checkpoint_score = int(checkpoint_ratio * 15)

    design = exp.get("design_type", "AB")
    from app.core.adaptive.n_of_1_experiment_designer import DESIGN_STRENGTHS
    design_score = DESIGN_STRENGTHS.get(design, 6)

    confounds = analysis.get("confounds", [])
    confound_penalty = min(10, len(confounds) * 3)

    total_score = max(0, min(100,
        pid_effect_score + adherence_score + fatigue_score + checkpoint_score + design_score - confound_penalty))

    category = ("very_strong_personal_signal" if total_score >= 86 else
                "strong_personal_signal" if total_score >= 71 else
                "promising_personal_signal" if total_score >= 51 else
                "exploratory_signal" if total_score >= 31 else "weak_evidence")

    safe_claims = {
        "very_strong_personal_signal": (
            "The optimized plan showed a very strong personal exploratory signal "
            "compared with baseline. This is an interesting personal observation — "
            "not clinical validation."),
        "strong_personal_signal": (
            "The optimized plan showed a strong personal exploratory signal. "
            "Results are consistent with personal benefit but are not clinical evidence."),
        "promising_personal_signal": (
            "The optimized plan showed a promising personal exploratory signal "
            "compared with baseline. More sessions would strengthen confidence."),
        "exploratory_signal": (
            "A mild exploratory signal was detected. The personal evidence is suggestive "
            "but not conclusive — continue practicing and calibrating."),
        "weak_evidence": (
            "The personal experiment did not produce strong evidence. "
            "This is normal for early exploratory work and does not indicate failure."),
    }

    limitations = []
    if confounds:
        limitations.append(f"Confounds detected: {', '.join(confounds)}")
    if total_cp < 4:
        limitations.append("Fewer than 4 calibration checkpoints. More data needed.")
    if design_score < 12:
        limitations.append(f"Design strength ({design_score}/15) is moderate. "
                           "Stronger designs (ABAB, randomized) would increase confidence.")
    if not limitations:
        limitations.append("No major limitations detected for a personal exploratory experiment.")

    return {
        "evidence_score": total_score,
        "category": category,
        "safe_claim": safe_claims.get(category, safe_claims["weak_evidence"]),
        "component_scores": {
            "pid_effect_strength": pid_effect_score,
            "adherence_quality": adherence_score,
            "fatigue_control": fatigue_score,
            "checkpoint_completeness": checkpoint_score,
            "design_strength": design_score,
            "confound_penalty": confound_penalty,
        },
        "main_limitations": limitations,
        **SAFETY,
    }
