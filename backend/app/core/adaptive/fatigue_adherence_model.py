"""IMAGINA V16 — Fatigue & Adherence Pattern Detector.

Analyzes fatigue and adherence patterns across plan executions
to recommend session length, rest patterns, and intensity adjustments.
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


def _get_all_execution_data(user_id="default"):
    from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions

    executions = list_plan_executions(user_id)
    results = []
    for ex in executions:
        a = analyze_plan_execution(user_id, ex["execution_id"])
        results.append({"manifest": ex, "analysis": a})
    return results


def analyze_fatigue_adherence_patterns(user_id="default") -> dict:
    executions = _get_all_execution_data(user_id)

    if not executions:
        return {
            "user_id": user_id, "n_executions": 0,
            "status": "no_data",
            "message": "No training executions found. Complete at least one plan execution.",
            **SAFETY,
        }

    all_fatigue = []
    all_adherence = []
    focus_fatigue = {}
    focus_adherence = {}
    daily_fatigue = {}
    daily_count = {}
    skipped_day_indices = []
    difficulties = []
    clarities = []
    focus_qualities = []

    for ex in executions:
        a = ex["analysis"]
        sm = a.get("subjective_metrics", {})
        f = sm.get("avg_fatigue")
        if f is not None:
            all_fatigue.append(f)
            focus = ex["manifest"].get("training_focus", "unknown")
            focus_fatigue.setdefault(focus, []).append(f)

        adh = a.get("adherence", {}).get("adherence_rate")
        if adh is not None:
            all_adherence.append(adh)
            focus_adherence.setdefault(focus, []).append(adh)

        if a.get("adherence", {}).get("skipped_days"):
            skipped_day_indices.extend(a["adherence"]["skipped_days"])

        for day in ex["manifest"].get("days", []):
            checkin = day.get("checkin", {})
            d = day["day"]
            if checkin and checkin.get("fatigue_rating") is not None:
                daily_fatigue[d] = daily_fatigue.get(d, 0) + checkin["fatigue_rating"]
                daily_count[d] = daily_count.get(d, 0) + 1
            if checkin and checkin.get("difficulty_rating") is not None:
                difficulties.append(checkin["difficulty_rating"])
            if checkin and checkin.get("clarity_rating") is not None:
                clarities.append(checkin["clarity_rating"])
            if checkin and checkin.get("focus_quality") is not None:
                focus_qualities.append(checkin["focus_quality"])

    avg_fatigue = round(sum(all_fatigue) / max(len(all_fatigue), 1), 2)
    avg_adherence = round(sum(all_adherence) / max(len(all_adherence), 1), 3)
    avg_difficulty = round(sum(difficulties) / max(len(difficulties), 1), 2)
    avg_clarity = round(sum(clarities) / max(len(clarities), 1), 2)

    fatigue_risk = "high" if avg_fatigue > 7 else "medium" if avg_fatigue > 5 else "low"
    adherence_risk = "high" if avg_adherence < 0.5 else "medium" if avg_adherence < 0.7 else "low"

    daily_fatigue_avg = {
        str(d): round(v / max(daily_count.get(d, 1), 1), 2)
        for d, v in sorted(daily_fatigue.items())
    }

    focus_fatigue_avg = {
        f: round(sum(vals) / max(len(vals), 1), 2)
        for f, vals in focus_fatigue.items()
    }
    focus_adh_avg = {
        f: round(sum(vals) / max(len(vals), 1), 3)
        for f, vals in focus_adherence.items()
    }

    cluster_after_day3 = sum(1 for d in skipped_day_indices if d > 3)
    skip_clustering = cluster_after_day3 >= 2

    rec_length = 10
    if avg_fatigue > 7:
        rec_length = 6
    elif avg_fatigue > 5:
        rec_length = 8
    elif avg_fatigue < 3:
        rec_length = 12

    rest_pattern = "alternating"
    if avg_fatigue > 7:
        rest_pattern = "2_days_on_1_day_rest"
    elif avg_adherence < 0.5:
        rest_pattern = "1_day_on_1_day_rest"

    recommendations = []
    if fatigue_risk == "high":
        recommendations.append(
            "High fatigue detected. Consider micro-sessions (5-8 min) and rest between days.")
    if skip_clustering:
        recommendations.append(
            "Skipped days tend to occur after day 3. A shorter plan or lower intensity may help.")
    if avg_difficulty > 7 and avg_fatigue > 6:
        recommendations.append(
            "High difficulty with high fatigue suggests reducing exercise difficulty by 1-2 levels.")
    if avg_fatigue < 3 and avg_adherence > 0.8:
        recommendations.append(
            "Low fatigue and high adherence — you may be ready to increase session intensity.")

    patterns = []
    if daily_fatigue_avg:
        latest = max(daily_fatigue_avg.keys(), key=int)
        earliest = min(daily_fatigue_avg.keys(), key=int)
        if int(latest) > 1 and daily_fatigue_avg.get(latest, 0) > daily_fatigue_avg.get(earliest, 0) + 2:
            patterns.append("Fatigue tends to increase across later days of each plan.")

    if focus_fatigue_avg:
        most_fatiguing = max(focus_fatigue_avg.items(), key=lambda x: x[1])
        patterns.append(f"Most fatiguing focus: {most_fatiguing[0]} (avg {most_fatiguing[1]:.1f}/10)")

    return {
        "user_id": user_id,
        "n_executions": len(executions),
        "fatigue": {
            "risk_level": fatigue_risk,
            "average": avg_fatigue,
            "by_day": daily_fatigue_avg,
            "by_focus": focus_fatigue_avg,
        },
        "adherence": {
            "risk_level": adherence_risk,
            "average": avg_adherence,
            "by_focus": focus_adh_avg,
            "skipped_day_pattern": "clustered_after_day_3" if skip_clustering else "scattered",
        },
        "correlations": {
            "avg_difficulty": avg_difficulty,
            "avg_clarity": avg_clarity,
            "note": ("These are personal exploratory proxy correlations — "
                     "not clinical or validated metrics."),
        },
        "recommended_session_length_minutes": rec_length,
        "recommended_rest_pattern": rest_pattern,
        "patterns": patterns if patterns else ["No strong patterns detected yet."],
        "recommendations": recommendations if recommendations else [
            "Continue as normal — no fatigue or adherence adjustments needed."],
        **SAFETY,
    }
