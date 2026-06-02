"""IMAGINA V15 — Adaptive Plan Execution.

Persists and manages execution state for each adaptive training plan.
Day-by-day tracking, check-in logging, calibration checkpoint attachment.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
EXEC_DIR = os.path.join(BASE, "adaptive_executions")

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


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _exec_manifest_path(user_id, execution_id):
    return os.path.join(EXEC_DIR, user_id, execution_id, "manifest.json")


def _daily_logs_path(user_id, execution_id):
    return os.path.join(EXEC_DIR, user_id, execution_id, "daily_logs.jsonl")


def _load_plan(user_id):
    from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
    return load_latest_adaptive_training_plan(user_id)


def start_plan_execution(user_id="default", plan_id=None):
    plan = _load_plan(user_id)
    if not plan:
        return {"error": "no_adaptive_plan", "message": "Generate an adaptive plan first.",
                **SAFETY}

    existing = get_latest_plan_execution(user_id)
    if existing and existing.get("status") == "active":
        return {"error": "active_execution_exists",
                "message": "Close the current active execution before starting a new one.",
                "existing_execution_id": existing["execution_id"],
                **SAFETY}

    execution_id = str(uuid4())
    days = []
    for d in plan.get("daily_plan", []):
        is_calib = d.get("calibration_task_id") is not None
        days.append({
            "day": d["day"],
            "status": "pending",
            "planned_exercise": {
                "title": d.get("title", ""),
                "exercise": d.get("exercise", ""),
                "duration_minutes": d.get("duration_minutes", 10),
                "target_dimension": d.get("target_dimension", ""),
                "success_criterion": d.get("success_criterion", ""),
            },
            "requires_calibration": is_calib,
            "calibration_task_id": d.get("calibration_task_id"),
            "checkin": None,
            "calibration_session_id": None,
        })

    manifest = {
        "execution_id": execution_id,
        "user_id": user_id,
        "plan_id": plan.get("adaptive_plan_id", plan_id or ""),
        "status": "active",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "plan_title": plan.get("plan_title", ""),
        "training_focus": plan.get("training_focus", ""),
        "days": days,
        "summary": {
            "completed_days": 0,
            "skipped_days": 0,
            "pending_days": len(days),
            "total_days": len(days),
            "calibration_checkpoints_attached": 0,
        },
        **SAFETY,
    }

    _save_json(_exec_manifest_path(user_id, execution_id), manifest)
    return manifest


def get_plan_execution(user_id, execution_id):
    return _load_json(_exec_manifest_path(user_id, execution_id))


def get_latest_plan_execution(user_id="default"):
    d = os.path.join(EXEC_DIR, user_id)
    if not os.path.isdir(d):
        return None
    latest = None
    latest_ts = ""
    for eid in os.listdir(d):
        mp = _exec_manifest_path(user_id, eid)
        m = _load_json(mp)
        if m and m.get("started_at", "") > latest_ts:
            latest_ts = m["started_at"]
            latest = m
    return latest


def list_plan_executions(user_id="default"):
    d = os.path.join(EXEC_DIR, user_id)
    if not os.path.isdir(d):
        return []
    results = []
    for eid in os.listdir(d):
        mp = _exec_manifest_path(user_id, eid)
        m = _load_json(mp)
        if m:
            results.append(m)
    return sorted(results, key=lambda x: x.get("started_at", ""), reverse=True)


def complete_execution_day(user_id, execution_id, day, checkin_payload):
    manifest = get_plan_execution(user_id, execution_id)
    if not manifest:
        return {"error": "execution_not_found", **SAFETY}
    if manifest.get("status") != "active":
        return {"error": "execution_not_active", **SAFETY}

    day_entry = None
    for d in manifest["days"]:
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
        "notes": checkin_payload.get("notes", ""),
    }

    _recompute_summary(manifest)
    _save_json(_exec_manifest_path(user_id, execution_id), manifest)

    log_entry = {
        "event": "day_checkin",
        "execution_id": execution_id,
        "user_id": user_id,
        "day": day,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **day_entry["checkin"],
    }
    _append_jsonl(_daily_logs_path(user_id, execution_id), log_entry)

    return manifest


def attach_calibration_to_execution_day(user_id, execution_id, day, calibration_session_id):
    manifest = get_plan_execution(user_id, execution_id)
    if not manifest:
        return {"error": "execution_not_found", **SAFETY}

    day_entry = None
    for d in manifest["days"]:
        if d["day"] == day:
            day_entry = d
            break

    if day_entry is None:
        return {"error": "invalid_day", **SAFETY}
    if not day_entry.get("requires_calibration"):
        return {"error": "day_not_a_checkpoint",
                "message": f"Day {day} is not a calibration checkpoint.",
                **SAFETY}

    from app.core.calibration.pid_v2_calibration import get_calibration_session
    calib = get_calibration_session(calibration_session_id)
    if not calib:
        return {"error": "calibration_session_not_found", **SAFETY}

    day_entry["calibration_session_id"] = calibration_session_id
    if calib.get("pid_v2"):
        day_entry["checkpoint_pid"] = calib["pid_v2"]["pid_v2"]
    if manifest["summary"].get("calibration_checkpoints_attached") is not None:
        manifest["summary"]["calibration_checkpoints_attached"] += 1
    else:
        manifest["summary"]["calibration_checkpoints_attached"] = 1

    _save_json(_exec_manifest_path(user_id, execution_id), manifest)

    log_entry = {
        "event": "calibration_attached",
        "execution_id": execution_id,
        "user_id": user_id,
        "day": day,
        "calibration_session_id": calibration_session_id,
        "pid_v2": calib.get("pid_v2", {}).get("pid_v2") if calib.get("pid_v2") else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_jsonl(_daily_logs_path(user_id, execution_id), log_entry)

    return manifest


def close_plan_execution(user_id, execution_id):
    manifest = get_plan_execution(user_id, execution_id)
    if not manifest:
        return {"error": "execution_not_found", **SAFETY}
    if manifest.get("status") == "completed":
        return {"error": "execution_already_completed", **SAFETY}

    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    _recompute_summary(manifest)
    _save_json(_exec_manifest_path(user_id, execution_id), manifest)

    log_entry = {
        "event": "execution_closed",
        "execution_id": execution_id,
        "user_id": user_id,
        "timestamp": manifest["completed_at"],
        "final_adherence": manifest["summary"].get("completed_days", 0) / max(manifest["summary"].get("total_days", 1), 1),
    }
    _append_jsonl(_daily_logs_path(user_id, execution_id), log_entry)

    return manifest


def _recompute_summary(manifest):
    total = len(manifest["days"])
    completed = sum(1 for d in manifest["days"] if d["status"] == "completed")
    skipped = sum(1 for d in manifest["days"] if d["status"] == "skipped")
    pending = total - completed - skipped
    checkpoint_count = sum(1 for d in manifest["days"]
                          if d.get("requires_calibration") and d.get("calibration_session_id"))
    manifest["summary"] = {
        "completed_days": completed,
        "skipped_days": skipped,
        "pending_days": pending,
        "total_days": total,
        "adherence_rate": round(completed / max(total, 1), 3),
        "calibration_checkpoints_attached": checkpoint_count,
    }


def _append_jsonl(path, entry):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def get_daily_logs(user_id, execution_id):
    p = _daily_logs_path(user_id, execution_id)
    if not os.path.exists(p):
        return []
    logs = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs
