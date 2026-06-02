"""IMAGINA V16 — Plan Response Model.

Analyzes completed executions and estimates how well different
training focuses work for the user.
"""

import json
import os
from datetime import datetime, timezone

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


def _get_completed_executions(user_id="default"):
    from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions

    executions = list_plan_executions(user_id)
    results = []
    for ex in executions:
        if ex.get("status") == "completed":
            a = analyze_plan_execution(user_id, ex["execution_id"])
            results.append({"manifest": ex, "analysis": a})
    return results


def build_plan_response_model(user_id="default") -> dict:
    executions = _get_completed_executions(user_id)

    if len(executions) < 2:
        return {
            "user_id": user_id, "n_executions": len(executions),
            "status": "insufficient_data",
            "message": "Complete at least 2 training executions for a response model.",
            **SAFETY,
        }

    focus_groups = {}
    for ex in executions:
        focus = ex["manifest"].get("training_focus", "unknown")
        if focus not in focus_groups:
            focus_groups[focus] = []
        focus_groups[focus].append(ex)

    focus_models = {}
    for focus, focused_exs in focus_groups.items():
        n_focus = len(focused_exs)
        pid_changes = []
        adherences = []
        fatigues = []
        clarities = []
        focus_qualities = []
        positive_count = 0
        negative_count = 0

        for ex in focused_exs:
            a = ex["analysis"]
            pca = a.get("pid_checkpoint_analysis", {})
            sm = a.get("subjective_metrics", {})

            bc = pca.get("baseline_to_final_change")
            if bc is not None:
                pid_changes.append(bc)

            adh = a.get("adherence", {}).get("adherence_rate")
            if adh is not None:
                adherences.append(adh)

            f = sm.get("avg_fatigue")
            if f is not None:
                fatigues.append(f)

            c = sm.get("avg_clarity")
            if c is not None:
                clarities.append(c)

            fq = sm.get("avg_focus_quality")
            if fq is not None:
                focus_qualities.append(fq)

            cat = a.get("response_category", "")
            if "positive" in cat:
                positive_count += 1
            elif cat == "negative_response":
                negative_count += 1

        mean_pid_change = round(sum(pid_changes) / max(len(pid_changes), 1), 3) if pid_changes else 0
        mean_adherence = round(sum(adherences) / max(len(adherences), 1), 3) if adherences else 0
        mean_fatigue = round(sum(fatigues) / max(len(fatigues), 1), 2) if fatigues else 0
        mean_clarity = round(sum(clarities) / max(len(clarities), 1), 2) if clarities else 0
        mean_fq = round(sum(focus_qualities) / max(len(focus_qualities), 1), 2) if focus_qualities else 0

        pos_rate = round(positive_count / max(n_focus, 1), 2)
        neg_rate = round(negative_count / max(n_focus, 1), 2)

        pid_std = round(
            (sum((pc - mean_pid_change) ** 2 for pc in pid_changes) / max(len(pid_changes), 1)) ** 0.5, 3
        ) if len(pid_changes) > 1 else 0.1

        pid_gain = max(0, -mean_pid_change) / 0.15
        adherence_bonus = mean_adherence * 0.25
        focus_bonus = mean_fq / 10 * 0.15
        fatigue_penalty = mean_fatigue / 10 * 0.20
        instability_penalty = min(pid_std, 0.3) * 0.20

        response_score = round(max(0.01, min(0.99,
            pid_gain + adherence_bonus + focus_bonus - fatigue_penalty - instability_penalty)), 2)

        conf = "high" if n_focus >= 3 else "medium" if n_focus >= 2 else "low"

        focus_models[focus] = {
            "n_executions": n_focus,
            "mean_pid_change": mean_pid_change,
            "mean_adherence": mean_adherence,
            "mean_fatigue": mean_fatigue,
            "mean_clarity": mean_clarity,
            "mean_focus_quality": mean_fq,
            "positive_response_rate": pos_rate,
            "negative_response_rate": neg_rate,
            "pid_change_std": pid_std,
            "response_score": response_score,
            "confidence_level": conf,
            "interpretation": _focus_interpretation(
                focus, response_score, mean_pid_change, mean_fatigue, conf),
        }

    sorted_foci = sorted(
        focus_models.items(), key=lambda x: x[1]["response_score"], reverse=True)
    best_focus = sorted_foci[0][0] if sorted_foci else ""
    worst_focus = sorted_foci[-1][0] if len(sorted_foci) > 1 else ""

    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_executions": len(executions),
        "focus_models": focus_models,
        "best_focus": best_focus,
        "worst_focus": worst_focus,
        "model_reliability": "high" if len(executions) >= 5 else "medium" if len(executions) >= 3 else "low",
        **SAFETY,
    }


def _focus_interpretation(focus, score, pid_change, fatigue, confidence):
    if confidence == "low":
        return ("Limited data — this is a preliminary personal exploratory observation, "
                "not a definitive pattern.")

    focus_label = focus.replace("_", " ")
    if score > 0.65:
        return (f"Your response to {focus_label} is promising, with consistently "
                f"lower PID values. This suggests this type of practice may be a personal strength.")
    if score > 0.40:
        return (f"{focus_label} shows moderate response. PID change is {pid_change:.2f} "
                f"and fatigue is {fatigue:.1f}. Continue exploring this focus.")
    if fatigue > 7:
        return (f"{focus_label} had high average fatigue ({fatigue:.1f}). "
                "You may benefit from shorter sessions or different timing.")
    if pid_change > 0:
        return (f"{focus_label} showed PID increase on average. "
                "This could indicate practice variability, not necessarily a poor fit.")
    return f"{focus_label} produced mixed or limited results. More sessions may clarify the pattern."
