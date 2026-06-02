"""IMAGINA Personalization Recommender — Rule-based task/scene suggestions."""


def generate_recommendations(profile: dict) -> list[dict]:
    """Generate ranked recommendations from user profile data."""
    recs = []

    # 1. IQI trend
    iqi_trend = profile.get("iqi_trend_slope", 0)
    if iqi_trend > 0.01:
        recs.append({"type": "task", "priority": "medium",
                     "message": "Imagery quality is improving — continue current difficulty level.",
                     "reason": f"IQI trend +{iqi_trend:.3f}", "next_task_id": None})
    elif iqi_trend < -0.02:
        recs.append({"type": "task", "priority": "high",
                     "message": "Imagery quality declining — simplify to basic stabilization task.",
                     "reason": f"IQI trend {iqi_trend:.3f}", "next_task_id": "shape_stabilization"})

    # 2. Fatigue
    fat_thresh = profile.get("fatigue_threshold_estimate")
    if fat_thresh and fat_thresh < 10:
        recs.append({"type": "session", "priority": "medium",
                     "message": f"Fatigue builds around step {fat_thresh}. "
                                f"Consider sessions of {fat_thresh - 1} steps.",
                     "reason": f"fatigue_threshold={fat_thresh}"})

    fat_trend = profile.get("fatigue_trend_slope", 0)
    if fat_trend > 0.02:
        recs.append({"type": "session", "priority": "high",
                     "message": "Fatigue is increasing across sessions. "
                                "Shorten sessions or add breaks.",
                     "reason": f"fatigue_trend +{fat_trend:.3f}"})

    # 3. Task suggestions
    best_tasks = profile.get("best_tasks", [])
    if best_tasks:
        recs.append({"type": "task", "priority": "low",
                     "message": f"Best performing tasks: {', '.join(best_tasks[:3])}. "
                                "Favor these for future sessions.",
                     "reason": "task_success_rates", "next_task_id": best_tasks[0]})

    # 4. Optimal session length
    opt_len = profile.get("optimal_session_length_steps")
    if opt_len:
        recs.append({"type": "session", "priority": "low",
                     "message": f"Optimal session length appears to be ~{opt_len} steps.",
                     "reason": f"optimal_session_length={opt_len}"})

    # 5. Feedback scene type suggestion
    best_fb = profile.get("best_feedback_params", {})
    if best_fb:
        clarity = best_fb.get("clarity", 0.5)
        complexity = best_fb.get("scene_complexity", 0.5)
        msg = "Scene preferences: "
        if clarity > 0.6:
            msg += "clear/high-clarity, "
        if complexity < 0.4:
            msg += "simple scenes. "
        else:
            msg += "moderate complexity. "
        recs.append({"type": "scene", "priority": "low",
                     "message": msg, "reason": "best_feedback_params"})

    # 6. Safety: ensure stop condition on fatigue
    if profile.get("session_count", 0) > 3 and fat_trend > 0.01:
        recs.append({"type": "safety", "priority": "high",
                     "message": "Multiple sessions show elevated fatigue. "
                                "Take a 1-day break before the next session.",
                     "reason": "safety_fatigue_trend"})

    return sorted(recs, key=lambda r: {"high": 0, "medium": 1, "low": 2}[r["priority"]])
