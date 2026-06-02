"""IMAGINA V29 — Biosignal Timeline + Realtime Feed + Quality Gate + Dashboard + Safe Export."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina", "biosignals")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "not_neurofeedback_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, validated BCI, or validated neurofeedback."),
    "biosignal_boundary": ("Biosignal streaming is optional and exploratory. Signal quality summaries "
                            "are engineering diagnostics, not neural decoding, diagnosis, treatment, "
                            "or validated neurofeedback."),
    "visualization_boundary": ("Biosignal visualizations show derived quality summaries and "
                                "simulated/demo signals only unless explicitly connected. "
                                "They are not neural decoding or mental image reconstruction."),
    "raw_eeg_export_default": False,
}


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


# ─── TIMELINE ───────────────────────────────────────────────────

def _timeline_dir(guided_session_id):
    return os.path.join(BASE, "timelines", guided_session_id)


def append_biosignal_timeline_event(guided_session_id, event_type, payload=None):
    evt = {"event_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
           "event_type": event_type, "payload": payload or {}, "raw_eeg_included": False, **SAFETY}
    d = _timeline_dir(guided_session_id)
    _append_jsonl(os.path.join(d, "timeline_events.jsonl"), evt)
    return evt


def build_biosignal_event_timeline(guided_session_id, monitor_id=None, marker_session_id=None):
    from app.core.biosignals.biosignal_module import list_markers
    from app.core.imagery.guided_session_runtime import get_guided_session

    gs = get_guided_session(guided_session_id)

    events = []
    if gs:
        for ph in gs.get("phase_history", []):
            events.append({"event_id": str(uuid4()),
                           "timestamp": ph.get("entered_at", ""),
                           "event_type": "phase_started",
                           "phase": ph.get("phase", ""), "summary": f"Entered {ph.get('phase', '')}",
                           "raw_eeg_included": False, **SAFETY})
        for ci in gs.get("micro_checkins", []):
            events.append({"event_id": str(uuid4()),
                           "timestamp": ci.get("timestamp", ""),
                           "event_type": "micro_checkin",
                           "phase": ci.get("phase", ""),
                           "summary": f"Vivid={ci.get('vividness')}, Stab={ci.get('stability')}",
                           "raw_eeg_included": False, **SAFETY})

    if marker_session_id:
        for m in list_markers(marker_session_id):
            events.append({"event_id": str(uuid4()),
                           "timestamp": m.get("timestamp", ""),
                           "event_type": m.get("event_type", "marker"),
                           "raw_eeg_included": False, **SAFETY})

    if monitor_id:
        try:
            dp = os.path.join(BASE, "monitors", monitor_id, "derived_samples.jsonl")
            if os.path.exists(dp):
                for line in open(dp):
                    s = json.loads(line.strip())
                    sq = s.get("signal_quality", {})
                    events.append({"event_id": str(uuid4()),
                                   "timestamp": s.get("timestamp", ""),
                                   "event_type": "signal_quality_sample",
                                   "monitor_id": monitor_id,
                                   "sqi": sq.get("overall_sqi"),
                                   "quality_state": sq.get("quality_state"),
                                   "raw_eeg_included": False, **SAFETY})
        except Exception:
            pass

    events.sort(key=lambda x: x.get("timestamp", ""))
    timeline = {"guided_session_id": guided_session_id, "n_events": len(events),
                "events": events, "raw_eeg_included": False, **SAFETY}
    d = _timeline_dir(guided_session_id)
    _save_json(os.path.join(d, "timeline.json"), timeline)
    return timeline


def get_biosignal_event_timeline(guided_session_id):
    p = os.path.join(_timeline_dir(guided_session_id), "timeline.json")
    return _load_json(p)


# ─── REALTIME FEED ──────────────────────────────────────────────

def _feed_dir(feed_id):
    return os.path.join(BASE, "realtime_feeds", feed_id)


def create_realtime_feed_session(guided_session_id, source_id="simulated_eeg"):
    from app.core.biosignals.biosignal_module import start_biosignal_monitor_for_guided_session
    mon = start_biosignal_monitor_for_guided_session(guided_session_id, source_id)
    monitor_id = mon.get("monitor_id", "")
    feed_id = str(uuid4())
    manifest = {"feed_id": feed_id, "guided_session_id": guided_session_id,
                "source_id": source_id, "monitor_id": monitor_id, "status": "active",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "n_frames": 0, "raw_eeg_included": False, **SAFETY}
    d = _feed_dir(feed_id)
    _save_json(os.path.join(d, "manifest.json"), manifest)
    return manifest


def poll_realtime_feed(feed_id):
    d = _feed_dir(feed_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m or m.get("status") != "active":
        return {"error": "feed_not_active", **SAFETY}

    from app.core.biosignals.biosignal_module import sample_biosignal_monitor
    sample = sample_biosignal_monitor(m["monitor_id"])
    ws = sample.get("window_summary", {})

    from app.core.imagery.guided_session_runtime import get_guided_session
    gs = get_guided_session(m.get("guided_session_id"))
    phase = gs.get("current_phase", "") if gs else "standalone"

    frame = {"feed_id": feed_id, "timestamp": datetime.now(timezone.utc).isoformat(),
             "guided_session_id": m["guided_session_id"], "source_id": m["source_id"],
             "phase": phase, "window_summary": ws,
             "signal_quality": sample.get("signal_quality", {}),
             "safe_visualization": {
                 "sqi": sample.get("signal_quality", {}).get("overall_sqi", 0.5),
                 "alpha_proxy": ws.get("estimated_alpha_power", 0),
                 "theta_proxy": ws.get("estimated_theta_power", 0),
                 "beta_proxy": ws.get("estimated_beta_power", 0),
                 "noise_proxy": round(1.0 - (sample.get("signal_quality", {}).get("overall_sqi", 0.5)), 3),
                 "stability_proxy": round(1.0 - abs(ws.get("variance", 0) * 100), 3),
             },
             "raw_samples_included": False, **SAFETY}

    _append_jsonl(os.path.join(d, "frames.jsonl"), frame)
    m["n_frames"] = m.get("n_frames", 0) + 1
    _save_json(os.path.join(d, "manifest.json"), m)
    return frame


def stop_realtime_feed(feed_id):
    d = _feed_dir(feed_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if m:
        m["status"] = "stopped"
        m["stopped_at"] = datetime.now(timezone.utc).isoformat()
        _save_json(os.path.join(d, "manifest.json"), m)
    return m


def get_realtime_feed_summary(feed_id):
    d = _feed_dir(feed_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return None
    frames = [json.loads(line) for line in
              open(os.path.join(d, "frames.jsonl")) if line.strip()] if os.path.exists(os.path.join(d, "frames.jsonl")) else []
    sqis = [f.get("signal_quality", {}).get("overall_sqi", 0.5) for f in frames]
    summ = {"feed_id": feed_id, "n_frames": len(frames),
            "avg_sqi": round(sum(sqis) / max(len(sqis), 1), 3) if sqis else 0.5,
            "raw_eeg_included": False, **SAFETY}
    _save_json(os.path.join(d, "summary.json"), summ)
    return summ


# ─── QUALITY GATE ───────────────────────────────────────────────

def evaluate_signal_quality_gate(signal_quality, guided_session_state=None):
    sqi = signal_quality.get("overall_sqi", 0.5)
    state = signal_quality.get("quality_state", "usable")
    gate = "open" if state in ("excellent", "good") else \
           "caution" if state == "usable" else \
           "degraded" if state == "poor" else "blocked"
    can_show = gate != "blocked"
    can_use = gate in ("open", "caution")
    return {"gate_state": gate, "can_show_derived_metrics": can_show,
            "can_use_for_exploratory_feedback": can_use,
            "warning": f"Signal quality is {state} (SQI={sqi:.2f})." if gate != "open" else "",
            "recommended_action": "Proceed normally." if gate == "open" else (
                "Monitor signal quality but continue." if gate == "caution" else
                "Check connections and environment."), **SAFETY}


# ─── DASHBOARD SUMMARY ──────────────────────────────────────────

def build_biosignal_dashboard_summary(user_id="demo_user"):
    from app.core.biosignals.biosignal_module import (
        discover_lsl_streams,
        list_biosignal_sources,
    )
    sources = list_biosignal_sources()
    lsl = discover_lsl_streams()
    bf = check_biosignal_available()
    # Find latest monitor
    monitors_dir = os.path.join(BASE, "monitors")
    latest_monitor = {}
    if os.path.isdir(monitors_dir):
        for mid in sorted(os.listdir(monitors_dir), reverse=True):
            sm = _load_json(os.path.join(monitors_dir, mid, "summary.json"))
            if sm:
                latest_monitor = sm
                break
    # Find latest feed
    feeds_dir = os.path.join(BASE, "realtime_feeds")
    latest_feed = {}
    if os.path.isdir(feeds_dir):
        for fid in sorted(os.listdir(feeds_dir), reverse=True):
            fs = get_realtime_feed_summary(fid)
            if fs:
                latest_feed = fs
                break

    dash = {"dashboard_id": str(uuid4()), "user_id": user_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": list(sources.keys()), "latest_monitor": latest_monitor,
            "latest_feed": latest_feed, "lsl_status": lsl, "brainflow_status": bf,
            "raw_eeg_export_default": False, "public_export_safe": True,
            "recommended_demo_action": "Start a guided session with simulated EEG to see the dashboard.",
            **SAFETY}
    d = os.path.join(BASE, "dashboard", user_id)
    _save_json(os.path.join(d, "latest_dashboard_summary.json"), dash)
    return dash


def check_biosignal_available():
    try:
        import importlib.util
        return {"available": importlib.util.find_spec("brainflow") is not None}
    except Exception:
        return {"available": False, "reason": "brainflow_not_installed"}


# ─── SAFE EXPORT ────────────────────────────────────────────────

def export_safe_biosignal_pack(user_id="demo_user", guided_session_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "safe_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id,
                                       "generated_at": ts, "raw_eeg_included": False,
                                       "safe_to_share": True}, indent=2)),
        ("biosignal_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Safe Biosignal Export\n\nDerived summaries only. "
         "No raw EEG. No neural decoding. No BCI. No neurofeedback validation. "
         "Not clinical. Personal exploratory engineering demo only."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    dash = build_biosignal_dashboard_summary(user_id)
    bp = os.path.join(ed, "dashboard_summary.json")
    _save_json(bp, dash)
    files.append(bp)

    if guided_session_id:
        from app.core.biosignals.biosignal_module import build_biosignal_session_report
        br = build_biosignal_session_report(guided_session_id)
        if not br.get("error"):
            brp = os.path.join(ed, "biosignal_report.json")
            _save_json(brp, br)
            files.append(brp)

        timeline = build_biosignal_event_timeline(guided_session_id)
        tp = os.path.join(ed, "timeline_summary.json")
        _save_json(tp, {"n_events": timeline.get("n_events", 0), "raw_eeg_included": False})
        files.append(tp)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}
