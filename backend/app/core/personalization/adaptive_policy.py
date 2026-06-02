"""IMAGINA Adaptive Policy V1 — Personalization applied to live session.

Takes user profile and recommends next task, feedback tweaks, safety adjustments.
Conservative — never overrides safety, never forces task changes.
"""

from typing import Optional


def recommend_next_task(profile: dict, available_tasks: list[dict]) -> Optional[str]:
    """Suggest next task based on profile history. Returns task_id or None."""
    if profile.get("session_count", 0) < 1:
        return "shape_stabilization"

    best_tasks = profile.get("best_tasks", [])
    if best_tasks:
        for t in best_tasks:
            if any(a["id"] == t for a in available_tasks):
                return t

    return available_tasks[0]["id"] if available_tasks else None


def tweak_feedback_params(profile: dict, base_params: dict) -> dict:
    """Apply personalization to scene feedback without overriding safety."""
    if not profile or profile.get("session_count", 0) < 2:
        return base_params

    params = dict(base_params)
    fatigue_trend = profile.get("fatigue_trend_slope", 0)
    attn_trend = profile.get("attention_history", [])
    mean_attn = sum(attn_trend[-10:]) / max(len(attn_trend[-10:]), 1) if attn_trend else 0.5

    # If fatigue is trending up, soften the scene
    if fatigue_trend > 0.015:
        params["clarity"] = max(0.2, base_params.get("clarity", 0.5) - 0.1)
        params["scene_complexity"] = max(0.1, base_params.get("scene_complexity", 0.5) - 0.1)
        params["motion_speed"] = max(0.0, base_params.get("motion_speed", 0.3) - 0.1)

    # If attention is low, increase breathing cue
    if mean_attn < 0.35:
        params["breathing_cue_intensity"] = min(1.0, base_params.get("breathing_cue_intensity", 0.3) + 0.3)

    return params


def recommend_session_length(profile: dict) -> int:
    """Suggest optimal session length in steps."""
    opt = profile.get("optimal_session_length_steps")
    fat = profile.get("fatigue_threshold_estimate")
    if opt and fat:
        return min(opt, max(1, fat - 1))
    if opt:
        return int(opt)
    if fat:
        return max(1, int(fat) - 1)
    return 8


def personalization_confidence(profile: dict) -> str:
    """Estimate confidence in personalization based on data volume."""
    n = profile.get("session_count", 0)
    if n < 2:
        return "low"
    if n < 5:
        return "medium"
    return "high"


def get_disclaimer() -> str:
    return ("Experimental proxy recommendation. Not medical advice, not clinical guidance. "
            "Based on limited self-report and simulated proxy data. "
            "Imagery quality varies naturally across individuals and sessions.")
