"""IMAGINA V19 — Imagery Task Session Manager.

Manages individual imagery task sessions: start, rate, complete, query.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
SESSIONS_DIR = os.path.join(BASE, "imagery_task_sessions")

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


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _session_path(session_id):
    return os.path.join(SESSIONS_DIR, session_id, "manifest.json")


def _index_path(user_id):
    return os.path.join(SESSIONS_DIR, f"{user_id}_index.json")


def start_imagery_task_session(user_id, task_id):
    from app.core.imagery.task_battery import get_imagery_task
    task = get_imagery_task(task_id)
    if task.get("error"):
        return task

    session_id = str(uuid4())
    manifest = {
        "session_id": session_id, "user_id": user_id,
        "task_id": task_id, "task_metadata": {
            "title": task["title"], "category": task["category"],
            "target_dimensions": task.get("target_dimensions", []),
            "difficulty": task.get("difficulty", 1),
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None, "status": "active",
        "rating_payload": None, "dimension_scores": None,
        "overall_task_score": None,
        **SAFETY,
    }
    _save_json(_session_path(session_id), manifest)
    _update_index(user_id, session_id)
    return manifest


def submit_imagery_task_rating(session_id, rating_payload):
    manifest = _load_json(_session_path(session_id))
    if not manifest:
        return {"error": "session_not_found", **SAFETY}
    if manifest["status"] != "active":
        return {"error": f"Session not active (status={manifest['status']})", **SAFETY}

    manifest["rating_payload"] = rating_payload
    _save_json(_session_path(session_id), manifest)
    return manifest


def complete_imagery_task_session(session_id):
    manifest = _load_json(_session_path(session_id))
    if not manifest:
        return {"error": "session_not_found", **SAFETY}
    if manifest["status"] != "active":
        return {"error": f"Session not active (status={manifest['status']})", **SAFETY}
    if not manifest.get("rating_payload"):
        return {"error": "no_rating_submitted", "message": "Submit rating before completing.", **SAFETY}

    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

    from app.core.imagery.task_battery import get_imagery_task
    task = get_imagery_task(manifest["task_id"])
    targets = task.get("target_dimensions", [])
    weights = task.get("dimension_weights", {})
    ratings = manifest["rating_payload"]
    effort = max(1, ratings.get("effort", 5))
    fatigue = max(1, ratings.get("fatigue", 5))
    e_norm = effort / 10
    f_norm = fatigue / 10

    dim_scores = {}
    weighted_sum = 0
    total_weight = 0
    for dim in targets:
        raw = ratings.get(dim, 5)
        adjusted = max(0.0, min(1.0, raw / 10 - 0.05 * e_norm - 0.05 * f_norm))
        dim_scores[dim] = round(adjusted, 3)
        w = weights.get(dim, 1.0 / max(len(targets), 1))
        weighted_sum += adjusted * w
        total_weight += w

    manifest["dimension_scores"] = dim_scores
    manifest["overall_task_score"] = round(weighted_sum / max(total_weight, 0.01), 3)
    _save_json(_session_path(session_id), manifest)
    return manifest


def get_imagery_task_session(session_id):
    return _load_json(_session_path(session_id))


def list_imagery_task_sessions(user_id):
    sessions = []
    if not os.path.isdir(SESSIONS_DIR):
        return sessions
    for sid in os.listdir(SESSIONS_DIR):
        mp = _session_path(sid)
        m = _load_json(mp)
        if m and m.get("user_id") == user_id:
            sessions.append(m)
    return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)


def _update_index(user_id, session_id):
    idx = _load_json(_index_path(user_id)) or {"user_id": user_id, "session_ids": []}
    idx["session_ids"].append(session_id)
    _save_json(_index_path(user_id), idx)
