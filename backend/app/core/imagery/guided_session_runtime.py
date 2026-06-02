"""IMAGINA V20 — Guided Session Schema + Runtime + Proxies + Feedback + Report + Plan Runner."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
GUIDED_DIR = os.path.join(BASE, "guided_sessions")
PLAN_RUN_DIR = os.path.join(BASE, "guided_plan_runs")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

PHASES = ["preparation", "grounding", "image_generation", "stabilization",
          "deepening", "manipulation", "micro_checkin", "adaptive_feedback",
          "integration", "completion"]

STATES = ["created", "active", "paused", "completed", "aborted", "safety_stopped"]

MODALITY_DISCLAIMER = "Self-report proxy only — not neural measurement, not BCI, not mind-reading."


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _append_jsonl(p, entry):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _session_path(session_id):
    return os.path.join(GUIDED_DIR, session_id, "manifest.json")


def _events_path(session_id):
    return os.path.join(GUIDED_DIR, session_id, "events.jsonl")


def _index_path(user_id):
    return os.path.join(GUIDED_DIR, f"{user_id}_index.json")


def get_guided_session_schema():
    return {
        "phases": PHASES, "states": STATES,
        "micro_checkin_fields": ["vividness", "stability", "effort", "fatigue",
                                   "confidence", "discomfort", "free_note"],
        "live_proxy_fields": ["iqi_proxy", "pid_proxy", "stability_proxy",
                               "fatigue_risk", "safety_state", "adaptation_reason"],
        "modality_disclaimer": MODALITY_DISCLAIMER,
        **SAFETY,
    }


# ─── RUNTIME ────────────────────────────────────────────────────

def _get_phenotype_context(user_id):
    try:
        from app.core.imagery.imagery_phenotype import analyze_imagery_gaps, load_imagery_phenotype
        ph = load_imagery_phenotype(user_id)
        if ph and ph.get("status") != "no_data":
            gaps = analyze_imagery_gaps(user_id)
            return {"phenotype_label": ph.get("phenotype_label", ""),
                    "primary_gap": gaps.get("primary_gap", ""),
                    "weakest_dimensions": ph.get("weakest_dimensions", []), **SAFETY}
    except Exception:
        pass
    return {"phenotype_label": "unknown", "primary_gap": "",
            "weakest_dimensions": [], "note": "No phenotype yet — beginner mode.", **SAFETY}


def start_guided_imagery_session(user_id, task_id, source="manual", biosignal_source_id=None):
    from app.core.imagery.task_battery import get_imagery_task
    task = get_imagery_task(task_id)
    if task.get("error"):
        return task

    phenotype = _get_phenotype_context(user_id)
    session_id = str(uuid4())

    marker_session_id = None
    monitor_id = None
    if biosignal_source_id:
        try:
            from app.core.biosignals.biosignal_module import (
                create_marker_session,
                start_biosignal_monitor_for_guided_session,
            )
            mark = create_marker_session(session_id, biosignal_source_id)
            marker_session_id = mark.get("marker_session_id")
            mon = start_biosignal_monitor_for_guided_session(session_id, biosignal_source_id)
            monitor_id = mon.get("monitor_id")
        except Exception:
            pass

    manifest = {
        "session_id": session_id, "user_id": user_id, "task_id": task_id,
        "task_metadata": {"title": task["title"], "category": task["category"],
                          "target_dimensions": task.get("target_dimensions", []),
                          "difficulty": task.get("difficulty", 1),
                          "duration_seconds": task.get("duration_seconds", 60)},
        "phenotype_context": phenotype, "source": source,
        "current_phase": "preparation", "status": "active",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "phase_history": [{"phase": "preparation", "entered_at": datetime.now(timezone.utc).isoformat()}],
         "micro_checkins": [], "live_proxy_history": [],
         "final_summary": None,
         "biosignal_source_id": biosignal_source_id,
         "biosignal_marker_session_id": marker_session_id,
         "biosignal_monitor_id": monitor_id,
        **SAFETY,
    }
    _save_json(_session_path(session_id), manifest)
    _append_jsonl(_events_path(session_id), {"event": "session_started",
                  "session_id": session_id, "user_id": user_id, "task_id": task_id,
                  "timestamp": manifest["started_at"]})
    _update_index(user_id, session_id)
    return manifest


def get_guided_session(session_id):
    return _load_json(_session_path(session_id))


def advance_guided_session_phase(session_id):
    m = get_guided_session(session_id)
    if not m or m["status"] != "active":
        return {"error": "session_not_active", **SAFETY}

    current = m["current_phase"]
    idx = PHASES.index(current) if current in PHASES else 0
    if idx >= len(PHASES) - 1:
        return {"error": "already_at_final_phase", "phase": current, **SAFETY}

    checkin_phases = {"grounding", "stabilization", "deepening", "manipulation"}
    if idx >= 1 and current not in checkin_phases:
        pass

    next_phase = PHASES[idx + 1]
    m["current_phase"] = next_phase
    m["phase_history"].append({"phase": next_phase, "entered_at": datetime.now(timezone.utc).isoformat()})
    _save_json(_session_path(session_id), m)
    _append_jsonl(_events_path(session_id), {"event": "phase_advanced",
                  "session_id": session_id, "from": current, "to": next_phase,
                  "timestamp": datetime.now(timezone.utc).isoformat()})

    feedback = None
    if next_phase in ("stabilization", "deepening", "manipulation"):
        feedback = _generate_adaptive_feedback_inner(m)
    scene_state = {}
    try:
        from app.core.imagery.scene_simulator import update_scene_from_guided_session
        scene_state = update_scene_from_guided_session(session_id)
    except Exception:
        pass
    return {"session": m, "feedback": feedback, "scene_state": scene_state}


def submit_guided_micro_checkin(session_id, checkin_payload):
    m = get_guided_session(session_id)
    if not m or m["status"] not in ("active", "paused"):
        return {"error": "session_not_active", **SAFETY}

    checkin = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": m["current_phase"],
        "vividness": checkin_payload.get("vividness", 5),
        "stability": checkin_payload.get("stability", 5),
        "effort": checkin_payload.get("effort", 5),
        "fatigue": checkin_payload.get("fatigue", 3),
        "confidence": checkin_payload.get("confidence", 7),
        "discomfort": checkin_payload.get("discomfort", 1),
        "free_note": checkin_payload.get("free_note", ""),
    }
    m["micro_checkins"].append(checkin)

    proxies = _compute_live_proxies(m)
    m["live_proxy_history"].append(proxies)

    safety_state = proxies.get("safety_state", "continue")
    if safety_state == "stop":
        m["status"] = "safety_stopped"
        m["completed_at"] = datetime.now(timezone.utc).isoformat()
    elif safety_state == "pause":
        m["status"] = "paused"

    _save_json(_session_path(session_id), m)
    _append_jsonl(_events_path(session_id), {"event": "micro_checkin_submitted",
                  "session_id": session_id, "phase": m["current_phase"],
                  "proxies": proxies, "timestamp": checkin["timestamp"]})

    feedback = _generate_adaptive_feedback_inner(m)
    scene_state = {}
    try:
        from app.core.imagery.scene_simulator import update_scene_after_checkin
        scene_state = update_scene_after_checkin(session_id, {"session": m, "feedback": feedback})
    except Exception:
        pass

    return {"session": m, "proxies": proxies, "feedback": feedback, "scene_state": scene_state}


def _compute_live_proxies(m):
    checkins = m.get("micro_checkins", [])
    if not checkins:
        return {"iqi_proxy": 0.5, "pid_proxy": 0.5, "stability_proxy": 0.5,
                "fatigue_risk": "low", "safety_state": "continue",
                "adaptation_reason": "no_data", "modality_disclaimer": MODALITY_DISCLAIMER, **SAFETY}

    latest = checkins[-1]
    vividness = latest.get("vividness", 5) / 10
    stability = latest.get("stability", 5) / 10
    confidence = latest.get("confidence", 7) / 10
    effort = latest.get("effort", 5) / 10
    fatigue = latest.get("fatigue", 3) / 10

    iqi = vividness * 0.35 + stability * 0.25 + confidence * 0.20 + (1 - effort) * 0.10 + (1 - fatigue) * 0.10
    iqi = round(max(0.01, min(0.99, iqi)), 3)

    pid = round(max(0.01, min(0.99, 1.0 - iqi)), 3)
    ph = m.get("phenotype_context", {})
    if ph.get("primary_gap") and ph.get("primary_gap") != "":
        pid = round(min(0.99, pid + 0.03), 3)
    if confidence < 0.4:
        pid = round(min(0.99, pid + 0.03), 3)
    if fatigue > 0.7:
        pid = round(min(0.99, pid + 0.03), 3)

    stab_p = round(stability * (1.0 - fatigue * 0.3), 3)

    fat_risk = "high" if fatigue >= 0.8 else "medium" if fatigue >= 0.5 else "low"

    raw_fatigue = latest.get("fatigue", 3)
    raw_effort = latest.get("effort", 5)
    raw_discomfort = latest.get("discomfort", 1)
    reason = ""
    safety = "continue"
    if raw_discomfort >= 8:
        safety = "stop"
        reason = "High discomfort detected."
    elif raw_fatigue >= 8:
        safety = "pause"
        reason = "High fatigue. Recommend pausing."
    elif raw_fatigue >= 6 or raw_effort >= 8:
        safety = "slow_down"
        reason = "Moderate fatigue or high effort. Consider slowing down."
    else:
        reason = "Proceeding normally."

    return {
        "iqi_proxy": iqi, "pid_proxy": pid, "stability_proxy": stab_p,
        "fatigue_risk": fat_risk, "safety_state": safety,
        "adaptation_reason": reason, "modality_disclaimer": MODALITY_DISCLAIMER, **SAFETY,
    }


def pause_guided_session(session_id):
    m = get_guided_session(session_id)
    if not m or m["status"] != "active":
        return {"error": "session_not_active", **SAFETY}
    m["status"] = "paused"
    _save_json(_session_path(session_id), m)
    _append_jsonl(_events_path(session_id), {"event": "session_paused",
                  "session_id": session_id, "timestamp": datetime.now(timezone.utc).isoformat()})
    return m


def resume_guided_session(session_id):
    m = get_guided_session(session_id)
    if not m or m["status"] != "paused":
        return {"error": "session_not_paused", **SAFETY}
    m["status"] = "active"
    _save_json(_session_path(session_id), m)
    return m


def complete_guided_session(session_id):
    m = get_guided_session(session_id)
    if not m or m["status"] not in ("active", "paused"):
        return {"error": "session_not_active", **SAFETY}
    m["status"] = "completed"
    m["completed_at"] = datetime.now(timezone.utc).isoformat()
    m["final_summary"] = _build_final_summary(m)
    _save_json(_session_path(session_id), m)
    _append_jsonl(_events_path(session_id), {"event": "session_completed",
                  "session_id": session_id, "timestamp": m["completed_at"]})
    return m


def abort_guided_session(session_id, reason=""):
    m = get_guided_session(session_id)
    if not m:
        return {"error": "session_not_found", **SAFETY}
    if m["status"] in ("completed", "aborted"):
        return {"error": "session_already_finalized", **SAFETY}
    m["status"] = "aborted"
    m["completed_at"] = datetime.now(timezone.utc).isoformat()
    m["abort_reason"] = reason
    _save_json(_session_path(session_id), m)
    _append_jsonl(_events_path(session_id), {"event": "session_aborted",
                  "session_id": session_id, "reason": reason,
                  "timestamp": m["completed_at"]})
    return m


def list_guided_sessions(user_id):
    sessions = []
    if not os.path.isdir(GUIDED_DIR):
        return sessions
    for sid in os.listdir(GUIDED_DIR):
        mp = _session_path(sid)
        m = _load_json(mp)
        if m and m.get("user_id") == user_id:
            sessions.append(m)
    return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)


def _update_index(user_id, session_id):
    idx = _load_json(_index_path(user_id)) or {"user_id": user_id, "session_ids": []}
    idx["session_ids"].append(session_id)
    _save_json(_index_path(user_id), idx)


# ─── ADAPTIVE FEEDBACK ──────────────────────────────────────────

def _generate_adaptive_feedback_inner(m):
    checkins = m.get("micro_checkins", [])
    latest = checkins[-1] if checkins else {}
    proxies = _compute_live_proxies(m) if checkins else {}
    phase = m.get("current_phase", "")
    targets = m.get("task_metadata", {}).get("target_dimensions", [])

    vivid = latest.get("vividness", 5)
    stab = latest.get("stability", 5)
    effort = latest.get("effort", 5)
    fatigue = latest.get("fatigue", 3)

    feedback_type = "continue"
    guidance = "Continue with the current imagery. "

    if fatigue >= 7 or effort >= 8:
        feedback_type = "simplify"
        guidance = "Notice your effort level. Simplify the image — a softer, simpler version is fine. "
    elif vivid < 4:
        feedback_type = "stabilize"
        guidance = "Focus on one detail or edge to anchor and stabilize your image. "
    elif stab < 4:
        feedback_type = "stabilize"
        guidance = "Hold the image still. If it drifts, gently bring it back to center. "
    elif proxies.get("iqi_proxy", 0.5) > 0.65:
        guidance = "Your imagery is clear and stable. Try adding a detail or deepening the image. "
        feedback_type = "deepen"

    scene = {
        "clarity": min(1.0, vivid / 10 + 0.3),
        "fog": max(0.0, 1.0 - vivid / 10),
        "brightness": min(1.0, (vivid + latest.get("confidence", 5)) / 20 + 0.3),
        "color_saturation": 0.6 if "color_control" in targets else 0.4,
        "motion_speed": 0.3 if "motion" in targets else 0.0,
        "stability_anchor": max(0.3, stab / 10),
        "detail_density": 0.5 if "detail" in targets else 0.3,
        "audio_calmness": 0.7,
    }

    return {
        "feedback_id": str(uuid4()),
        "phase": phase,
        "feedback_type": feedback_type,
        "guidance_text": guidance,
        "scene_feedback": scene,
        "why": [f"Phase: {phase}", f"Target dimensions: {targets}",
                f"Vividness={vivid}, Stability={stab}, Effort={effort}, Fatigue={fatigue}"],
        "safety_state": proxies.get("safety_state", "continue"),
        **SAFETY,
    }


def generate_adaptive_feedback(session_id):
    m = get_guided_session(session_id)
    if not m:
        return {"error": "session_not_found", **SAFETY}
    return _generate_adaptive_feedback_inner(m)


# ─── SESSION REPORT ─────────────────────────────────────────────

def _build_final_summary(m):
    checkins = m.get("micro_checkins", [])
    n = len(checkins)
    if n == 0:
        return {"n_checkins": 0, "status": "no_data"}
    def _avg(k):
        return round(sum(c.get(k, 5) for c in checkins) / n, 2)
    proxies = _compute_live_proxies(m) if checkins else {}
    return {
        "n_checkins": n,
        "avg_vividness": _avg("vividness"), "avg_stability": _avg("stability"),
        "avg_effort": _avg("effort"), "avg_fatigue": _avg("fatigue"),
        "avg_confidence": _avg("confidence"),
        "final_iqi_proxy": proxies.get("iqi_proxy"),
        "final_pid_proxy": proxies.get("pid_proxy"),
        "phase_coverage": f"{len(set(c['phase'] for c in checkins))}/{len(PHASES)}",
        **SAFETY,
    }


def build_guided_session_report(session_id):
    m = get_guided_session(session_id)
    if not m:
        return {"error": "session_not_found", **SAFETY}

    summary = m.get("final_summary") or _build_final_summary(m)
    task = m.get("task_metadata", {})
    ph = m.get("phenotype_context", {})

    report = {
        "session_id": session_id, "user_id": m.get("user_id"),
        "task_title": task.get("title", ""), "task_category": task.get("category", ""),
        "target_dimensions": task.get("target_dimensions", []),
        "status": m.get("status"), "started_at": m.get("started_at"),
        "completed_at": m.get("completed_at"),
        "summary": summary,
        "recommended_next_dimension": ph.get("primary_gap", ""),
        "recommended_next_task": _recommend_next_task(m),
        "safety_notes": _safety_notes(m),
        **SAFETY,
    }

    rd = os.path.join(GUIDED_DIR, session_id)
    os.makedirs(rd, exist_ok=True)
    _save_json(os.path.join(rd, "session_report.json"), report)
    return report


def _recommend_next_task(m):
    ph = m.get("phenotype_context", {})
    gap = ph.get("primary_gap", "")
    if gap:
        from app.core.imagery.task_battery import list_imagery_tasks
        cats = {"vividness": "basic_vividness", "spatial_control": "spatial_stability",
                "detail": "detail_generation", "motion": "motion_imagery",
                "emotion": "emotional_tone_imagery", "multisensory": "multisensory_imagery",
                "color_control": "color_control", "stability": "spatial_stability",
                "meta_control": "meta_control"}
        cat = cats.get(gap, "basic_vividness")
        tasks = list_imagery_tasks(cat).get("tasks", [])
        if tasks:
            return tasks[0]["task_id"]
    return "red_circle_vividness"


def _safety_notes(m):
    notes = ["Self-report proxy only — not neural measurement."]
    checkins = m.get("micro_checkins", [])
    if any(c.get("discomfort", 1) >= 5 for c in checkins):
        notes.append("Moderate discomfort was reported. Consider adjusting task difficulty or duration.")
    if any(c.get("fatigue", 3) >= 7 for c in checkins):
        notes.append("High fatigue was reported. Consider a rest day before the next session.")
    return notes


def export_guided_session_as_task_rating(session_id):
    m = get_guided_session(session_id)
    if not m:
        return {"error": "session_not_found", **SAFETY}
    if m["status"] != "completed":
        return {"error": "session_not_completed", **SAFETY}

    checkins = m.get("micro_checkins", [])
    if not checkins:
        return {"error": "no_checkins_to_export", **SAFETY}

    n = len(checkins)
    def _avg2(k):
        return round(sum(c.get(k, 5) for c in checkins) / n, 1)
    from app.core.imagery.task_session_manager import (
        complete_imagery_task_session,
        start_imagery_task_session,
        submit_imagery_task_rating,
    )
    s = start_imagery_task_session(m.get("user_id", "default"), m.get("task_id", ""))
    if s.get("error"):
        return s
    ratings = {dim: _avg2(dim) for dim in ["vividness", "stability", "color_control", "spatial_control",
             "detail", "motion", "emotion", "multisensory", "meta_control"]}
    ratings.update({"effort": _avg2("effort"), "fatigue": _avg2("fatigue"), "confidence": _avg2("confidence")})
    submit_imagery_task_rating(s["session_id"], ratings)
    complete_imagery_task_session(s["session_id"])
    return {"linked_task_session_id": s["session_id"], "averaged_ratings": ratings, **SAFETY}


# ─── GUIDED PLAN RUNNER ─────────────────────────────────────────

def _load_task_plan(user_id):
    from app.core.imagery.imagery_phenotype import generate_task_based_imagery_plan, load_task_based_plan
    plan = load_task_based_plan(user_id)
    if not plan:
        plan = generate_task_based_imagery_plan(user_id)
    return plan


def _plan_run_path(user_id):
    return os.path.join(PLAN_RUN_DIR, user_id, "latest_run.json")


def start_next_guided_task_from_plan(user_id):
    plan = _load_task_plan(user_id)
    run = _load_json(_plan_run_path(user_id)) or {
        "user_id": user_id, "plan_id": plan.get("plan_id", ""),
        "current_day": 1, "completed_days": [], "active_session_id": None,
        "status": "active", "adherence_rate": 0,
    }
    current = run.get("current_day", 1)
    daily = plan.get("daily_tasks", [])
    if current > len(daily):
        run["status"] = "completed"
        run["adherence_rate"] = round(len(run.get("completed_days", [])) / max(len(daily), 1), 3)
        _save_json(_plan_run_path(user_id), run)
        return {"status": "plan_completed", "run": run, **SAFETY}

    task = daily[current - 1]
    session = start_guided_imagery_session(user_id, task["task_id"], "task_plan")
    if session.get("error"):
        return session
    run["active_session_id"] = session["session_id"]
    run["current_day"] = current
    _save_json(_plan_run_path(user_id), run)
    return {"session": session, "run": run, **SAFETY}


def get_guided_plan_progress(user_id):
    run = _load_json(_plan_run_path(user_id))
    if not run:
        return {"status": "no_plan_run", "message": "Start a guided task from your task plan.", **SAFETY}
    return {"run": run, **SAFETY}


def mark_guided_plan_day_completed(user_id, session_id):
    run = _load_json(_plan_run_path(user_id))
    if not run:
        return {"error": "no_plan_run", **SAFETY}
    run["completed_days"].append(run.get("current_day", 0))
    run["current_day"] += 1
    run["active_session_id"] = None
    plan = _load_task_plan(user_id)
    total = len(plan.get("daily_tasks", []))
    done = len(run.get("completed_days", []))
    run["adherence_rate"] = round(done / max(total, 1), 3)
    if run["current_day"] > total:
        run["status"] = "completed"
    _save_json(_plan_run_path(user_id), run)
    return {"run": run, "completed_session_id": session_id, **SAFETY}


# ─── LIVE PROXY EXPORTS ─────────────────────────────────────────

def compute_live_iqi_proxy(checkins, task_metadata):
    if not checkins:
        return {"iqi_proxy": 0.5, "modality_disclaimer": MODALITY_DISCLAIMER, **SAFETY}
    latest = checkins[-1]
    v = latest.get("vividness", 5) / 10
    s = latest.get("stability", 5) / 10
    c = latest.get("confidence", 7) / 10
    e = latest.get("effort", 5) / 10
    f = latest.get("fatigue", 3) / 10
    iqi = round(v * 0.35 + s * 0.25 + c * 0.20 + (1 - e) * 0.10 + (1 - f) * 0.10, 3)
    return {"iqi_proxy": iqi, "modality_disclaimer": MODALITY_DISCLAIMER, **SAFETY}


def compute_live_pid_proxy(checkins, task_metadata, phenotype_context=None):
    iqi = compute_live_iqi_proxy(checkins, task_metadata).get("iqi_proxy", 0.5)
    pid = round(1.0 - iqi, 3)
    return {"pid_proxy": pid, "modality_disclaimer": MODALITY_DISCLAIMER, **SAFETY}
