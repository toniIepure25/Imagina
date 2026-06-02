"""IMAGINA Adaptive Curriculum Manager — 8-level staircase with safety gates."""



def decide_curriculum_action(
    current_level: int,
    recent_iqi_scores: list[float],
    recent_pid_trend: str = "stable",
    fatigue: float = 0.2,
    attention_stability: float = 0.5,
    session_duration_minutes: float = 5.0,
    max_duration_minutes: float = 20.0,
) -> dict:
    """Decide next curriculum action: advance, stay, regress, simplify, or stop."""

    # Safety gates first
    if fatigue > 0.80:
        return {"action": "stop", "next_task_id": None, "reason": "fatigue_threshold_exceeded",
                "message": "High fatigue detected. Session should end. Rest and return later."}
    if session_duration_minutes >= max_duration_minutes:
        return {"action": "stop", "next_task_id": None, "reason": "max_duration_reached",
                "message": "Session time limit reached. Consider ending the session."}
    if fatigue > 0.65:
        return {"action": "simplify", "next_task_id": None,
                "reason": "elevated_fatigue",
                "message": "Fatigue is elevated. Simplify current task or take a short break."}

    if not recent_iqi_scores or len(recent_iqi_scores) < 2:
        return {"action": "stay", "next_task_id": None, "reason": "insufficient_data",
                "message": "Continue current task to gather enough data for curriculum decision."}

    # 3-up-1-down staircase
    recent_3 = recent_iqi_scores[-3:]
    if len(recent_3) >= 3 and all(s > 0.70 for s in recent_3) and fatigue < 0.5:
        return {"action": "advance", "next_task_id": None,
                "reason": "three_consecutive_successes",
                "message": "Strong consistent performance — advancing to next level."}

    # Regression: 2 low scores or fatigue
    recent_2 = recent_iqi_scores[-2:]
    if len(recent_2) >= 2 and all(s < 0.40 for s in recent_2):
        return {"action": "regress", "next_task_id": None,
                "reason": "two_consecutive_failures",
                "message": "Consistently low imagery quality — returning to simpler task."}

    if fatigue > 0.55 or attention_stability < 0.35:
        return {"action": "simplify", "next_task_id": None,
                "reason": "fatigue_or_attention",
                "message": "Simplify the scene to reduce cognitive load."}

    # Default: stay
    return {"action": "stay", "next_task_id": None,
            "reason": "stable_performance",
            "message": "Continue at current level. Performance is stable."}


def get_curriculum_summary(session_history: list[dict]) -> dict:
    """Summarize curriculum progression from session event history."""
    if not session_history:
        return {"levels_visited": [], "advances": 0, "regressions": 0, "final_level": 0}

    levels = set()
    advances = sum(1 for e in session_history if e.get("payload", {}).get("action") == "advance")
    regressions = sum(1 for e in session_history if e.get("payload", {}).get("action") == "regress")
    for e in session_history:
        if e.get("event_type") == "task_started":
            lvl = e.get("payload", {}).get("task_config", {}).get("level", 0)
            levels.add(lvl)

    return {
        "levels_visited": sorted(levels),
        "advances": advances,
        "regressions": regressions,
        "final_level": max(levels) if levels else 0,
    }
