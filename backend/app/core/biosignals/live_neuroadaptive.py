"""IMAGINA V31 — Live Event Bus + Neuroadaptive Orchestrator + Control Room + Safe Export."""

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
    "not_neurofeedback_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, validated BCI, or validated neurofeedback."),
    "biosignal_boundary": ("Biosignal streaming is optional and exploratory."),
    "fusion_boundary": ("Multimodal fusion uses self-report and derived engineering summaries only."),
    "live_dashboard_boundary": ("Live dashboard events are local engineering telemetry. "
                                 "They are not neural decoding, mental content reconstruction, "
                                 "BCI output, or validated neurofeedback."),
    "raw_eeg_export_default": False,
}

EVENT_TYPES = [
    "live_session_started", "biosignal_feed_started", "biosignal_frame",
    "signal_quality_gate_updated", "guided_phase_changed", "micro_checkin_received",
    "scene_state_updated", "multimodal_observation_built", "adaptive_state_estimated",
    "neuroadaptive_policy_recommended", "policy_preview_applied", "safety_warning",
    "live_session_completed", "live_session_aborted",
]


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


# ─── LIVE EVENT SCHEMA + BUS ────────────────────────────────────

def get_live_event_schema():
    return {"event_types": EVENT_TYPES, "safe_payload_default": True,
            "raw_eeg_included": False, **SAFETY}


def make_live_event(event_type, payload, context=None):
    ctx = context or {}
    evt = {"event_id": str(uuid4()), "event_type": event_type,
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "user_id": ctx.get("user_id", "demo_user"),
           "guided_session_id": ctx.get("guided_session_id"),
           "feed_id": ctx.get("feed_id"), "phase": ctx.get("phase", ""),
           "payload": payload, "safe_payload": True,
           "raw_eeg_included": False, **SAFETY}
    return evt


def publish_live_event(event):
    uid = event.get("user_id", "demo_user")
    d = os.path.join(BASE, "live_events", uid)
    _append_jsonl(os.path.join(d, "events.jsonl"), event)
    _save_json(os.path.join(d, "latest_event.json"), event)
    return event


def get_recent_live_events(user_id="demo_user", limit=100):
    p = os.path.join(BASE, "live_events", user_id, "events.jsonl")
    if not os.path.exists(p):
        return []
    events = [json.loads(line) for line in open(p) if line.strip()]
    return events[-limit:]


def clear_live_events(user_id="demo_user"):
    d = os.path.join(BASE, "live_events", user_id)
    for fn in ["events.jsonl", "latest_event.json", "summary.json"]:
        path = os.path.join(d, fn)
        if os.path.exists(path):
            os.remove(path)
    return {"status": "cleared", **SAFETY}


# ─── NEUROADAPTIVE ORCHESTRATOR ─────────────────────────────────

def _live_dir(live_session_id):
    return os.path.join(BASE, "live_sessions", live_session_id)


def _live_index(user_id):
    return os.path.join(BASE, "live_sessions", f"{user_id}_index.json")


def start_live_neuroadaptive_demo(user_id="demo_user", task_id="red_circle_vividness", source_id="simulated_eeg"):
    from app.core.biosignals.biosignal_module import create_simulated_eeg_source
    try:
        create_simulated_eeg_source(source_id)
    except Exception:
        pass

    from app.core.imagery.guided_session_runtime import start_guided_imagery_session
    gs = start_guided_imagery_session(user_id, task_id, "live_demo", biosignal_source_id=source_id)
    if gs.get("error"):
        return gs
    sid = gs["session_id"]

    from app.core.biosignals.biosignal_dashboard import create_realtime_feed_session
    feed = create_realtime_feed_session(sid, source_id)
    fid = feed["feed_id"]

    lsid = str(uuid4())
    manifest = {"live_session_id": lsid, "user_id": user_id,
                "guided_session_id": sid, "feed_id": fid,
                "source_id": source_id, "status": "active",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "task_id": task_id, "n_steps": 0, **SAFETY}
    d = _live_dir(lsid)
    _save_json(os.path.join(d, "manifest.json"), manifest)

    ctx = {"user_id": user_id, "guided_session_id": sid, "feed_id": fid}
    publish_live_event(make_live_event("live_session_started", {"live_session_id": lsid}, ctx))
    publish_live_event(make_live_event("biosignal_feed_started", {"feed_id": fid}, ctx))

    return manifest


def step_live_neuroadaptive_demo(live_session_id):
    d = _live_dir(live_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m or m.get("status") != "active":
        return {"error": "not_active", **SAFETY}
    uid = m["user_id"]
    sid = m["guided_session_id"]
    fid = m["feed_id"]
    ctx = {"user_id": uid, "guided_session_id": sid, "feed_id": fid}

    from app.core.biosignals.biosignal_dashboard import poll_realtime_feed
    frame = poll_realtime_feed(fid)
    sq = frame.get("signal_quality", {})
    publish_live_event(make_live_event("biosignal_frame", {"sqi": sq.get("overall_sqi"), "quality_state": sq.get("quality_state")}, ctx))
    publish_live_event(make_live_event("signal_quality_gate_updated", {"gate_state": frame.get("signal_quality", {}).get("quality_state", "unknown")}, ctx))

    from app.core.biosignals.fusion_multimodal import run_single_fusion_step
    fusion = run_single_fusion_step(uid, sid, fid)
    state = fusion.get("adaptive_state", {})
    policy = fusion.get("policy", {})
    publish_live_event(make_live_event("multimodal_observation_built", {"completeness": fusion.get("observation", {}).get("data_completeness")}, ctx))
    publish_live_event(make_live_event("adaptive_state_estimated", {"state": state.get("state"), "confidence": state.get("confidence")}, ctx))
    publish_live_event(make_live_event("neuroadaptive_policy_recommended", {"action": policy.get("recommended_action")}, ctx))

    scene = {}
    try:
        from app.core.biosignals.scene_dynamics_engine import build_live_scene_adaptation_frame
        scene = build_live_scene_adaptation_frame(live_session_id, fusion)
        publish_live_event(make_live_event("live_scene_adaptation_preview", {"interpretation": scene.get("change_interpretation", "")}, ctx))
    except Exception:
        pass

    live_frame = {"live_session_id": live_session_id, "guided_session_id": sid,
                  "feed_id": fid, "timestamp": datetime.now(timezone.utc).isoformat(),
                  "sqi": sq.get("overall_sqi"), "gate_state": frame.get("signal_quality", {}).get("quality_state", "unknown"),
                  "adaptive_state": state.get("state"), "state_confidence": state.get("confidence"),
                  "policy_action": policy.get("recommended_action"),
                  "scene_policy": policy.get("scene_policy", {}),
                  "safety_policy": policy.get("safety_policy", {}),
                  "scene_adaptation": {"scene_after_preview": scene.get("scene_after_preview", {}),
                                        "change_interpretation": scene.get("change_interpretation", ""),
                                        "preview_only": scene.get("preview_only", True)} if scene else {},
                  "raw_eeg_included": False, **SAFETY}
    m["n_steps"] = m.get("n_steps", 0) + 1
    _save_json(os.path.join(d, "manifest.json"), m)
    _append_jsonl(os.path.join(d, "frames.jsonl"), live_frame)
    return live_frame


def submit_live_demo_checkin(live_session_id, checkin_payload):
    m = _load_json(os.path.join(_live_dir(live_session_id), "manifest.json"))
    if not m:
        return {"error": "not_found", **SAFETY}
    sid = m["guided_session_id"]
    from app.core.imagery.guided_session_runtime import submit_guided_micro_checkin
    r = submit_guided_micro_checkin(sid, checkin_payload)
    publish_live_event(make_live_event("micro_checkin_received", {"vividness": checkin_payload.get("vividness")}, {"user_id": m["user_id"], "guided_session_id": sid}))
    return r


def complete_live_neuroadaptive_demo(live_session_id):
    d = _live_dir(live_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return {"error": "not_found", **SAFETY}
    sid = m["guided_session_id"]
    from app.core.imagery.guided_session_runtime import complete_guided_session
    complete_guided_session(sid)
    m["status"] = "completed"
    m["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(os.path.join(d, "manifest.json"), m)
    publish_live_event(make_live_event("live_session_completed", {"live_session_id": live_session_id}, {"user_id": m["user_id"]}))
    return m


def abort_live_neuroadaptive_demo(live_session_id, reason=""):
    d = _live_dir(live_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return {"error": "not_found", **SAFETY}
    m["status"] = "aborted"
    _save_json(os.path.join(d, "manifest.json"), m)
    publish_live_event(make_live_event("live_session_aborted", {"reason": reason}, {"user_id": m["user_id"]}))
    return m


def get_live_neuroadaptive_demo(live_session_id):
    d = _live_dir(live_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return None
    frames = [json.loads(line) for line in
              open(os.path.join(d, "frames.jsonl")) if line.strip()] if os.path.exists(os.path.join(d, "frames.jsonl")) else []
    m["frames"] = frames
    return m


def list_live_neuroadaptive_demos(user_id="demo_user"):
    idx = _load_json(_live_index(user_id))
    if not idx:
        return []
    results = []
    for lsid in idx.get("session_ids", []):
        m = get_live_neuroadaptive_demo(lsid)
        if m:
            results.append(m)
    return results


def build_live_control_room_summary(user_id="demo_user"):
    events = get_recent_live_events(user_id, 200)
    counts = {}
    for e in events:
        et = e.get("event_type", "unknown")
        counts[et] = counts.get(et, 0) + 1
    latest = events[-1] if events else {}
    latest_frame = None
    try:
        d = os.path.join(BASE, "live_sessions")
        if os.path.isdir(d):
            for lsid in sorted(os.listdir(d), reverse=True):
                ff = os.path.join(d, lsid, "frames.jsonl")
                if os.path.exists(ff):
                    frames = [json.loads(line) for line in open(ff) if line.strip()]
                    if frames:
                        latest_frame = frames[-1]
                        break
    except Exception:
        pass

    summary = {"control_room_id": str(uuid4()), "user_id": user_id,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "event_counts": counts, "n_events": len(events),
               "latest_event_type": latest.get("event_type", ""),
               "latest_adaptive_state": latest_frame.get("adaptive_state", "") if latest_frame else "",
               "latest_policy_action": latest_frame.get("policy_action", "") if latest_frame else "",
               "latest_sqi": latest_frame.get("sqi") if latest_frame else None,
               "raw_eeg_included": False, **SAFETY}
    d = os.path.join(BASE, "live_control_room", user_id)
    _save_json(os.path.join(d, "latest_control_room_summary.json"), summary)
    return summary


# ─── SAFE LIVE EXPORT ───────────────────────────────────────────

def export_safe_live_demo_pack(user_id="demo_user", live_session_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "live_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Safe Live Demo Export\n\nLive demo uses self-report proxies and derived biosignal summaries. No raw EEG. Not BCI. Not neurofeedback validation. Not clinical."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    summary = build_live_control_room_summary(user_id)
    sp = os.path.join(ed, "live_event_summary.json")
    _save_json(sp, summary)
    files.append(sp)

    if live_session_id:
        ls = get_live_neuroadaptive_demo(live_session_id)
        if ls:
            lp = os.path.join(ed, "live_session_manifest.json")
            _save_json(lp, ls)
            files.append(lp)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}
