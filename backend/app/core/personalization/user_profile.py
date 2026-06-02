"""IMAGINA User Profile — Local-first personal imagery profile."""

import json
import os
from datetime import datetime, timezone

PROFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "..", "data", "imagina", "profiles")


def _profile_path(user_id: str) -> str:
    os.makedirs(PROFILES_DIR, exist_ok=True)
    return os.path.join(PROFILES_DIR, f"{user_id}.json")


def _default_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "session_count": 0,
        "total_steps": 0,
        "iqi_history": [],
        "pid_history": [],
        "fatigue_history": [],
        "attention_history": [],
        "mean_iqi": 0.0,
        "mean_pid": 0.0,
        "best_iqi": 0.0,
        "best_pid": 1.0,
        "iqi_trend_slope": 0.0,
        "pid_trend_slope": 0.0,
        "fatigue_trend_slope": 0.0,
        "level_success_rates": {},
        "task_success_rates": {},
        "best_tasks": [],
        "weak_tasks": [],
        "best_demo_profile": None,
        "best_feedback_params": {},
        "fatigue_threshold_estimate": None,
        "optimal_session_length_steps": None,
        "recommendations": [],
    }


def load_profile(user_id: str) -> dict:
    path = _profile_path(user_id)
    if not os.path.exists(path):
        return _default_profile(user_id)
    with open(path) as f:
        return json.load(f)


def save_profile(profile: dict):
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _profile_path(profile["user_id"])
    with open(path, "w") as f:
        json.dump(profile, f, indent=2, default=str)


def reset_profile(user_id: str) -> dict:
    p = _default_profile(user_id)
    save_profile(p)
    return p


def _compute_trend(values: list[float]) -> float:
    """Simple linear trend slope from last N values."""
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return round(num / max(den, 1e-10), 4)


def update_profile_from_session(user_id: str, session_id: str) -> dict:
    """Update a user profile by analyzing a completed session's events."""
    from app.core.analytics.session_analytics import analyze_session
    from app.core.events.event_store import load_events

    profile = load_profile(user_id)
    events = load_events(session_id)
    if not events:
        return profile

    analytics = analyze_session(session_id)
    if not analytics or analytics.get("n_steps", 0) == 0:
        return profile

    # Extract metric histories
    iqi_vals = [e["payload"]["iqi_score"] for e in events if e["event_type"] == "iqi_computed"]
    pid_vals = [e["payload"]["pid_score"] for e in events if e["event_type"] == "pid_computed"]
    state_vals = [e["payload"]["state"] for e in events if e["event_type"] == "state_estimate"]
    fatigue_vals = [s["fatigue"] for s in state_vals]
    attn_vals = [s["attention_stability"] for s in state_vals]

    # Update histories (keep last 100)
    profile["iqi_history"].extend(iqi_vals)
    profile["pid_history"].extend(pid_vals)
    profile["fatigue_history"].extend(fatigue_vals)
    profile["attention_history"].extend(attn_vals)
    for key in ["iqi_history", "pid_history", "fatigue_history", "attention_history"]:
        profile[key] = profile[key][-100:]

    # Counters
    profile["session_count"] += 1
    profile["total_steps"] += analytics["n_steps"]

    # Means
    if iqi_vals:
        profile["mean_iqi"] = round(sum(profile["iqi_history"]) / len(profile["iqi_history"]), 3)
        profile["best_iqi"] = max(profile["best_iqi"], max(iqi_vals))
    if pid_vals:
        profile["mean_pid"] = round(sum(profile["pid_history"]) / len(profile["pid_history"]), 3)
        profile["best_pid"] = min(profile["best_pid"], min(pid_vals))

    # Trends
    profile["iqi_trend_slope"] = _compute_trend(profile["iqi_history"][-20:])
    profile["pid_trend_slope"] = _compute_trend(profile["pid_history"][-20:])
    profile["fatigue_trend_slope"] = _compute_trend(profile["fatigue_history"][-20:])

    # Task success rates (from curriculum actions)
    cur_acts = [e["payload"]["action"] for e in events if e["event_type"] == "curriculum_decision"]
    advances = cur_acts.count("advance")
    if advances > 0:
        # Find which task was active
        task_starts = [e["payload"].get("task_id", "unknown") for e in events if e["event_type"] == "task_started"]
        for t in set(task_starts):
            profile["task_success_rates"][t] = profile["task_success_rates"].get(t, 0) + advances

    # Best tasks (top 3 by success rate if available)
    if profile["task_success_rates"]:
        sorted_tasks = sorted(profile["task_success_rates"].items(), key=lambda x: x[1], reverse=True)
        profile["best_tasks"] = [t for t, _ in sorted_tasks[:3]]

    # Fatigue threshold: point where fatigue first exceeded 0.6
    for s in state_vals:
        if s.get("fatigue", 0) > 0.6:
            profile["fatigue_threshold_estimate"] = state_vals.index(s) + 1
            break

    # Optimal session length: where IQI peaks
    if iqi_vals:
        best_idx = iqi_vals.index(max(iqi_vals))
        profile["optimal_session_length_steps"] = best_idx + 1

    # Best feedback params from best IQI step
    fb_acts = [e["payload"] for e in events if e["event_type"] == "feedback_action"]
    if iqi_vals and fb_acts:
        best_iqi_idx = iqi_vals.index(max(iqi_vals))
        if best_iqi_idx < len(fb_acts):
            profile["best_feedback_params"] = {
                k: v for k, v in fb_acts[best_iqi_idx].get("scene_params", {}).items()
                if k != "prompt"
            }

    # Auto profile
    best_demo = analytics.get("demo_profile")
    if best_demo:
        profile["best_demo_profile"] = best_demo

    save_profile(profile)

    # Generate recommendations
    from app.core.personalization.recommender import generate_recommendations
    recs = generate_recommendations(profile)
    profile["recommendations"] = recs
    save_profile(profile)

    return profile
