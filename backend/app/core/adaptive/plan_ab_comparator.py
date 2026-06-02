"""IMAGINA V16 — Plan A/B Comparator.

Compares two or more completed plan executions to identify
which plan/focus performed better.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

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


def compare_plan_executions(user_id="default", execution_ids=None) -> dict:
    from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
    from app.core.adaptive.adaptive_plan_execution import get_plan_execution

    if execution_ids is None:
        from app.core.adaptive.adaptive_plan_execution import list_plan_executions
        all_ex = list_plan_executions(user_id)
        completed = [e for e in all_ex if e.get("status") == "completed"]
        if len(completed) < 2:
            return {
                "user_id": user_id, "status": "insufficient_data",
                "message": "Need at least 2 completed executions to compare.",
                **SAFETY,
            }
        execution_ids = [completed[-2]["execution_id"], completed[-1]["execution_id"]]

    analyses = []
    manifests = []
    for eid in execution_ids:
        a = analyze_plan_execution(user_id, eid)
        m = get_plan_execution(user_id, eid)
        if not m:
            continue
        analyses.append(a)
        manifests.append(m)

    if len(analyses) < 2:
        return {
            "user_id": user_id, "status": "insufficient_data",
            "message": "Both executions must exist to compare.",
            **SAFETY,
        }

    a1, a2 = analyses[0], analyses[1]
    m1, m2 = manifests[0], manifests[1]

    def _pid_change(a):
        return a.get("pid_checkpoint_analysis", {}).get("baseline_to_final_change", 0)

    def _adh(a):
        return a.get("adherence", {}).get("adherence_rate", 0)

    def _fatigue(a):
        return a.get("subjective_metrics", {}).get("avg_fatigue", 0)

    def _clarity(a):
        return a.get("subjective_metrics", {}).get("avg_clarity", 0)

    def _focus_quality(a):
        return a.get("subjective_metrics", {}).get("avg_focus_quality", 0)

    pid1, pid2 = _pid_change(a1), _pid_change(a2)
    adh1, adh2 = _adh(a1), _adh(a2)
    fat1, fat2 = _fatigue(a1), _fatigue(a2)

    metrics = {
        "execution_a": {
            "execution_id": m1.get("execution_id", ""),
            "plan_title": m1.get("plan_title", ""),
            "training_focus": m1.get("training_focus", ""),
            "pid_change": pid1, "adherence": adh1,
            "avg_fatigue": fat1, "avg_clarity": _clarity(a1),
            "focus_quality": _focus_quality(a1),
            "response_category": a1.get("response_category", ""),
        },
        "execution_b": {
            "execution_id": m2.get("execution_id", ""),
            "plan_title": m2.get("plan_title", ""),
            "training_focus": m2.get("training_focus", ""),
            "pid_change": pid2, "adherence": adh2,
            "avg_fatigue": fat2, "avg_clarity": _clarity(a2),
            "focus_quality": _focus_quality(a2),
            "response_category": a2.get("response_category", ""),
        },
        "differences": {
            "pid_change_delta": round(pid2 - pid1, 3),
            "adherence_delta": round(adh2 - adh1, 3),
            "fatigue_delta": round(fat2 - fat1, 2),
        },
    }

    confidence = "medium"
    winner = "inconclusive"

    pid1_better = pid1 < pid2 - 0.05
    pid2_better = pid2 < pid1 - 0.05

    if pid1_better and fat1 <= fat2 + 2:
        winner = "execution_a"
        confidence = "medium"
    elif pid2_better and fat2 <= fat1 + 2:
        winner = "execution_b"
        confidence = "medium"
    elif adh1 > adh2 + 0.3:
        winner = "execution_a"
        confidence = "low"
    elif adh2 > adh1 + 0.3:
        winner = "execution_b"
        confidence = "low"

    if abs(adh1 - adh2) > 0.3:
        confidence = "low"

    if not pid1_better and not pid2_better and abs(pid1 - pid2) < 0.05:
        winner = "inconclusive"
        confidence = "low"

    interpretation = _comparison_interpretation(winner, metrics, confidence)

    return {
        "comparison_id": str(uuid4()),
        "user_id": user_id,
        "executions_compared": execution_ids,
        "metrics": metrics,
        "winner": winner,
        "confidence_level": confidence,
        "interpretation": interpretation,
        **SAFETY,
    }


def _comparison_interpretation(winner, metrics, confidence):
    if winner == "inconclusive":
        return ("PID changes were too similar to determine a clear winner. "
                "This is normal — both plans may produce similar results for you.")
    if confidence == "low":
        return ("One plan appeared better, but adherence differences or limited data "
                "reduce confidence. More executions will clarify the pattern.")
    label = "execution_a" if winner == "execution_a" else "execution_b"
    focus = metrics[label].get("training_focus", "").replace("_", " ")
    return (f"{focus} (execution {label[-1].upper()}) showed a better PID response. "
            "This is a personal exploratory observation — not a clinical verdict.")


def compare_training_focuses(user_id="default") -> dict:
    from app.core.adaptive.plan_response_model import build_plan_response_model

    model = build_plan_response_model(user_id)
    if model.get("status") == "insufficient_data":
        return {**model, "comparison": "insufficient_data"}

    focus_models = model.get("focus_models", {})
    sorted_foci = sorted(
        focus_models.items(), key=lambda x: x[1].get("response_score", 0), reverse=True)

    comparison = {
        "ranked_focuses": [
            {
                "focus": f,
                "response_score": m.get("response_score"),
                "mean_pid_change": m.get("mean_pid_change"),
                "n_executions": m.get("n_executions"),
                "confidence": m.get("confidence_level"),
            }
            for f, m in sorted_foci
        ],
        "top_ranked": sorted_foci[0][0] if sorted_foci else "",
        "interpretation": _focus_comparison_interpretation(sorted_foci),
    }

    return {
        "comparison_id": str(uuid4()),
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison": comparison,
        **SAFETY,
    }


def _focus_comparison_interpretation(sorted_foci):
    if not sorted_foci:
        return "No training focus data to compare."
    top = sorted_foci[0]
    return (f"Based on {top[1].get('n_executions', 0)} execution(s), "
            f"{top[0].replace('_', ' ')} showed the best overall response "
            f"(score={top[1].get('response_score', 0)}). "
            "This is a personal exploratory trend.")
