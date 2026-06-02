"""IMAGINA Session Analytics — Extract metrics and trends from event log."""

from app.core.events.event_store import load_events


def analyze_session(session_id: str) -> dict:
    events = load_events(session_id)
    if not events:
        return {"session_id": session_id, "n_steps": 0, "error": "no_events"}

    iqi_vals = [e["payload"]["iqi_score"] for e in events if e["event_type"] == "iqi_computed"]
    pid_vals = [e["payload"]["pid_score"] for e in events if e["event_type"] == "pid_computed"]
    state_vals = [e["payload"]["state"] for e in events if e["event_type"] == "state_estimate"]
    cur_acts = [e["payload"]["action"] for e in events if e["event_type"] == "curriculum_decision"]
    saf_acts = [e["payload"]["action"] for e in events if e["event_type"] == "safety_decision"]
    fb_acts = [e["payload"] for e in events if e["event_type"] == "feedback_action"]

    fatigue_vals = [s["fatigue"] for s in state_vals]

    n = len(iqi_vals)
    if n == 0:
        return {"session_id": session_id, "n_steps": 0, "error": "no_iqi_events"}

    mean_iqi = round(sum(iqi_vals) / n, 3)
    mean_pid = round(sum(pid_vals) / len(pid_vals), 3) if pid_vals else 0.5
    best_iqi = round(max(iqi_vals), 3)
    best_step = next((i + 1 for i, v in enumerate(iqi_vals) if round(v, 3) == best_iqi), 1)

    def slope(vals):
        if len(vals) < 2:
            return 0.0
        xm = (len(vals) - 1) / 2.0
        ym = sum(vals) / len(vals)
        num = sum((i - xm) * (v - ym) for i, v in enumerate(vals))
        den = sum((i - xm) ** 2 for i in range(len(vals)))
        return round(num / max(den, 1e-10), 4)

    iqi_slope = slope(iqi_vals)
    pid_slope = slope(pid_vals) if pid_vals else 0.0
    fatigue_slope = slope(fatigue_vals) if fatigue_vals else 0.0

    # Feedback responsiveness: how much do scene params change between steps?
    fb_resp = 0.0
    if len(fb_acts) >= 2:
        diffs = []
        for i in range(1, len(fb_acts)):
            try:
                p1 = fb_acts[i - 1].get("scene_params", {})
                p2 = fb_acts[i].get("scene_params", {})
                keys = set(p1) & set(p2)
                if keys:
                    d = sum(abs(float(p1.get(k, 0)) - float(p2.get(k, 0))) for k in keys) / len(keys)
                    diffs.append(d)
            except (TypeError, ValueError):
                pass
        fb_resp = round(sum(diffs) / len(diffs), 4) if diffs else 0.0

    # Demo profile detection from config
    demo_profile = None
    for e in events:
        if e["event_type"] == "session_started":
            demo_profile = e["payload"].get("config", {}).get("demo_profile")
            break

    # Interpretation
    if iqi_slope > 0.02:
        interp = "Improving imagery quality across session."
    elif iqi_slope < -0.02:
        interp = "Declining imagery quality — consider rest or simpler task."
    elif fatigue_slope > 0.01:
        interp = "Fatigue building — session may be too long."
    else:
        interp = "Stable imagery quality throughout session."

    return {
        "session_id": session_id,
        "n_steps": n,
        "mean_iqi": mean_iqi,
        "mean_pid": mean_pid,
        "best_iqi": best_iqi,
        "best_step": best_step,
        "iqi_slope": iqi_slope,
        "pid_slope": pid_slope,
        "fatigue_slope": fatigue_slope,
        "feedback_responsiveness": fb_resp,
        "curriculum_summary": {a: cur_acts.count(a) for a in set(cur_acts)},
        "safety_summary": {a: saf_acts.count(a) for a in set(saf_acts)},
        "demo_profile": demo_profile,
        "interpretation": interp,
        "disclaimer": "Experimental proxy analytics. Not clinical or validated metrics.",
    }
