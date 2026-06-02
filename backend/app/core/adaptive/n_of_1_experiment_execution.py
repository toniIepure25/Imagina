"""IMAGINA V17 — N-of-1 Experiment Execution Manager.

Manages execution lifecycle for controlled N-of-1 experiments:
start, complete day, attach calibration, close.
"""

import json
import os
from datetime import datetime, timezone

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
EXPERIMENT_DIR = os.path.join(BASE, "n_of_1_experiments")

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


def _manifest_path(user_id, experiment_id):
    return os.path.join(EXPERIMENT_DIR, user_id, experiment_id, "manifest.json")


def _daily_logs_path(user_id, experiment_id):
    return os.path.join(EXPERIMENT_DIR, user_id, experiment_id, "daily_logs.jsonl")


def _save_manifest(user_id, experiment_id, data):
    _save_json(_manifest_path(user_id, experiment_id), data)
    # Also update latest
    d = os.path.join(EXPERIMENT_DIR, user_id)
    _save_json(os.path.join(d, "latest_experiment.json"), data)


def start_n_of_1_experiment(user_id="default", experiment_id=None):
    if not experiment_id:
        exp = get_latest_n_of_1_experiment(user_id)
        if not exp:
            return {"error": "no_experiment_designed",
                    "message": "Design an experiment first.", **SAFETY}
        experiment_id = exp["experiment_id"]

    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        return {"error": "experiment_not_found", **SAFETY}
    if exp.get("status") == "active":
        return {"error": "already_active",
                "message": "This experiment is already running.", **SAFETY}
    if exp.get("status") == "completed":
        return {"error": "already_completed",
                "message": "This experiment has already been completed.", **SAFETY}

    exp["status"] = "active"
    exp["started_at"] = datetime.now(timezone.utc).isoformat()
    _save_manifest(user_id, experiment_id, exp)
    return exp


def get_n_of_1_experiment(user_id, experiment_id):
    return _load_json(_manifest_path(user_id, experiment_id))


def get_latest_n_of_1_experiment(user_id="default"):
    d = os.path.join(EXPERIMENT_DIR, user_id)
    for fn in ("latest_experiment.json",):
        p = os.path.join(d, fn)
        m = _load_json(p)
        if m:
            return m
    return None


def list_n_of_1_experiments(user_id="default"):
    d = os.path.join(EXPERIMENT_DIR, user_id)
    if not os.path.isdir(d):
        return []
    results = []
    for eid in os.listdir(d):
        mp = _manifest_path(user_id, eid)
        m = _load_json(mp)
        if m:
            results.append(m)
    return sorted(results, key=lambda x: x.get("designed_at", ""), reverse=True)


def complete_experiment_day(user_id, experiment_id, day, checkin_payload):
    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        return {"error": "experiment_not_found", **SAFETY}
    if exp.get("status") != "active":
        return {"error": "experiment_not_active", **SAFETY}

    day_entry = None
    for d in exp.get("days", []):
        if d["day"] == day:
            day_entry = d
            break

    if day_entry is None:
        return {"error": "invalid_day", **SAFETY}
    if day_entry["status"] != "pending":
        return {"error": f"Day {day} already {day_entry['status']}", **SAFETY}

    completed = checkin_payload.get("completed", True)
    day_entry["status"] = "completed" if completed else "skipped"
    day_entry["checkin"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "completed": completed,
        "duration_minutes_actual": checkin_payload.get("duration_minutes_actual", 0),
        "difficulty_rating": checkin_payload.get("difficulty_rating"),
        "clarity_rating": checkin_payload.get("clarity_rating"),
        "fatigue_rating": checkin_payload.get("fatigue_rating"),
        "focus_quality": checkin_payload.get("focus_quality"),
        "confidence_rating": checkin_payload.get("confidence_rating"),
        "notes": checkin_payload.get("notes", ""),
    }

    _recompute_experiment_summary(exp)
    _save_manifest(user_id, experiment_id, exp)

    _append_jsonl(_daily_logs_path(user_id, experiment_id), {
        "event": "day_checkin",
        "experiment_id": experiment_id, "user_id": user_id,
        "day": day, "condition": day_entry["condition"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **day_entry["checkin"],
    })

    return exp


def attach_experiment_calibration(user_id, experiment_id, day, calibration_session_id):
    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        return {"error": "experiment_not_found", **SAFETY}

    day_entry = None
    for d in exp.get("days", []):
        if d["day"] == day:
            day_entry = d
            break

    if day_entry is None:
        return {"error": "invalid_day", **SAFETY}
    if not day_entry.get("requires_calibration"):
        return {"error": "day_not_a_checkpoint", **SAFETY}

    from app.core.calibration.pid_v2_calibration import get_calibration_session
    calib = get_calibration_session(calibration_session_id)
    if not calib:
        return {"error": "calibration_session_not_found", **SAFETY}

    day_entry["calibration_session_id"] = calibration_session_id
    if calib.get("pid_v2"):
        day_entry["checkpoint_pid"] = calib["pid_v2"]["pid_v2"]

    _save_manifest(user_id, experiment_id, exp)

    _append_jsonl(_daily_logs_path(user_id, experiment_id), {
        "event": "calibration_attached",
        "experiment_id": experiment_id, "user_id": user_id,
        "day": day, "condition": day_entry["condition"],
        "calibration_session_id": calibration_session_id,
        "pid_v2": day_entry.get("checkpoint_pid"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return exp


def close_n_of_1_experiment(user_id, experiment_id):
    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        return {"error": "experiment_not_found", **SAFETY}
    if exp.get("status") == "completed":
        return {"error": "already_completed", **SAFETY}

    exp["status"] = "completed"
    exp["completed_at"] = datetime.now(timezone.utc).isoformat()
    _recompute_experiment_summary(exp)
    _save_manifest(user_id, experiment_id, exp)

    _append_jsonl(_daily_logs_path(user_id, experiment_id), {
        "event": "experiment_closed",
        "experiment_id": experiment_id, "user_id": user_id,
        "timestamp": exp["completed_at"],
    })

    return exp


def _recompute_experiment_summary(exp):
    days = exp.get("days", [])
    total = len(days)
    completed = sum(1 for d in days if d["status"] == "completed")
    skipped = sum(1 for d in days if d["status"] == "skipped")
    pending = total - completed - skipped
    cals = sum(1 for d in days if d.get("calibration_session_id"))
    exp["summary"] = {
        "completed_days": completed,
        "skipped_days": skipped,
        "pending_days": pending,
        "total_days": total,
        "adherence_rate": round(completed / max(total, 1), 3),
        "calibration_checkpoints_attached": cals,
    }


def _append_jsonl(path, entry):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
