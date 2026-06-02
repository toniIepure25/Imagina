"""IMAGINA V30 — Multimodal Observation + Adaptive State + Policy Engine + Fusion Loop + Safe Export."""

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
    "fusion_boundary": ("Multimodal fusion uses self-report and derived engineering summaries only. "
                         "It does not infer mental content, diagnose states, decode thoughts, "
                         "or validate neurofeedback."),
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


# ─── MULTIMODAL OBSERVATION ─────────────────────────────────────

def build_multimodal_observation(guided_session_id=None, feed_id=None, user_id="demo_user"):
    biosignal = {"status": "missing"}
    signal_gate = {"gate_state": "blocked"}
    self_report = {"status": "missing"}
    session_context = {"status": "standalone"}
    scene_context = {"status": "missing"}
    protocol_context = {"status": "missing"}
    completeness = 0.0

    if feed_id:
        try:
            from app.core.biosignals.biosignal_dashboard import poll_realtime_feed
            frame = poll_realtime_feed(feed_id)
            sq = frame.get("signal_quality", {})
            biosignal = {"sqi": sq.get("overall_sqi"), "quality_state": sq.get("quality_state"),
                         "alpha_proxy": frame.get("safe_visualization", {}).get("alpha_proxy"),
                         "theta_proxy": frame.get("safe_visualization", {}).get("theta_proxy"),
                         "noise_proxy": frame.get("safe_visualization", {}).get("noise_proxy"),
                         "status": "active", "raw_samples_included": False}
            from app.core.biosignals.biosignal_dashboard import evaluate_signal_quality_gate
            signal_gate = evaluate_signal_quality_gate(sq)
            completeness += 0.3
        except Exception:
            biosignal = {"status": "error"}

    if guided_session_id:
        try:
            from app.core.imagery.guided_session_runtime import get_guided_session
            gs = get_guided_session(guided_session_id)
            if gs:
                ci = gs.get("micro_checkins", [{}])[-1] if gs.get("micro_checkins") else {}
                proxies = (gs.get("live_proxy_history") or [{}])[-1]
                session_context = {"current_phase": gs.get("current_phase", ""),
                                   "status": gs.get("status", ""),
                                   "source": gs.get("source", "")}
                self_report = {"vividness": ci.get("vividness"), "stability": ci.get("stability"),
                               "effort": ci.get("effort"), "fatigue": ci.get("fatigue"),
                               "confidence": ci.get("confidence"), "discomfort": ci.get("discomfort"),
                               "iqi_proxy": proxies.get("iqi_proxy"), "pid_proxy": proxies.get("pid_proxy"),
                               "safety_state": proxies.get("safety_state"), "status": "present"}
                completeness += 0.3
                from app.core.imagery.scene_simulator import get_latest_scene_state
                sc = get_latest_scene_state(guided_session_id)
                if sc and "error" not in sc:
                    sp = sc.get("scene_parameters", {})
                    scene_context = {"clarity": sp.get("clarity"), "fog": sp.get("fog"),
                                     "stability_anchor": sp.get("stability_anchor"),
                                     "detail_density": sp.get("detail_density"),
                                     "visual_noise": sc.get("derived_from", {}).get("pid_proxy"),
                                     "status": "present"}
                    completeness += 0.2
        except Exception:
            session_context = {"status": "error"}

    try:
        from app.core.imagery.protocol_studio import get_active_protocol_run
        pr = get_active_protocol_run(user_id)
        if pr:
            protocol_context = {"protocol_title": pr.get("protocol_title", ""),
                                "current_day": pr.get("current_day", 1),
                                "completion_rate": pr.get("progress", {}).get("completion_rate", 0),
                                "status": "active"}
            completeness += 0.1
    except Exception:
        pass

    obs = {"observation_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
           "user_id": user_id, "guided_session_id": guided_session_id, "feed_id": feed_id,
           "biosignal": biosignal, "signal_gate": signal_gate,
           "self_report": self_report, "session_context": session_context,
           "scene_context": scene_context, "protocol_context": protocol_context,
           "data_completeness": round(completeness, 3), "raw_eeg_included": False, **SAFETY}
    d = os.path.join(BASE, "multimodal_observations", user_id)
    _save_json(os.path.join(d, "latest_observation.json"), obs)
    _append_jsonl(os.path.join(d, "observations.jsonl"), obs)
    return obs


# ─── ADAPTIVE STATE ESTIMATOR ───────────────────────────────────

def estimate_adaptive_state(observation):
    obs = observation
    sd = obs.get("data_completeness", 0)
    if sd < 0.35:
        return _make_state("insufficient_data", 0.3, "low", "data_completeness", ["Insufficient data."], [])

    sr = obs.get("self_report", {})
    gate = obs.get("signal_gate", {})
    gs = gate.get("gate_state", "blocked")

    if gs == "blocked":
        return _make_state("signal_blocked", 0.5, "medium", "biosignal_quality",
                           ["Biosignal gate is blocked."], ["Cannot use biosignal for adaptation."])
    if gs == "degraded":
        return _make_state("signal_degraded", 0.4, "medium", "biosignal_quality",
                           ["Biosignal quality degraded."], ["Derived metrics may be unreliable."])

    discomfort = sr.get("discomfort", 1) or 1
    fatigue = sr.get("fatigue", 3) or 3
    effort = sr.get("effort", 5) or 5
    iqi = sr.get("iqi_proxy", 0.5) or 0.5
    pid = sr.get("pid_proxy", 0.5) or 0.5
    confidence = sr.get("confidence", 5) or 5

    if fatigue >= 8 or discomfort >= 7:
        return _make_state("pause_recommended", 0.8, "high", "self_report",
                           [f"High fatigue ({fatigue}) or discomfort ({discomfort})."], [])
    if fatigue >= 6:
        return _make_state("fatigue_risk", 0.6, "medium", "self_report",
                           [f"Elevated fatigue ({fatigue})."], ["Consider shorter sessions."])
    if effort >= 8 and iqi < 0.55:
        return _make_state("effort_overload", 0.55, "medium", "self_report",
                           ["High effort with low IQI."], ["Simplify task."])
    if discomfort >= 5:
        return _make_state("discomfort_warning", 0.55, "medium", "self_report",
                           [f"Moderate discomfort ({discomfort})."], [])
    if iqi >= 0.7 and pid <= 0.35 and fatigue < 5:
        return _make_state("deepening", 0.7, "low", "self_report",
                           ["High IQI, low PID, low fatigue."], ["Ready for deeper practice."])
    if iqi < 0.55 and fatigue <= 5:
        return _make_state("clarity_building", 0.55, "low", "self_report",
                           ["Low IQI with low fatigue."], ["Build clarity with simpler tasks."])
    if iqi >= 0.6 and pid <= 0.45 and confidence >= 6:
        return _make_state("stable_practice", 0.65, "low", "self_report",
                           ["Stable IQI/PID with good confidence."], [])
    return _make_state("ready", 0.4, "low", "data_completeness",
                       ["Sufficient data, no acute risks."], [])


def _make_state(state, conf, risk, driver, reasons, neg):
    return {"adaptive_state_id": str(uuid4()), "state": state, "confidence": round(conf, 3),
            "risk_level": risk, "primary_driver": driver, "reasons": reasons,
            "negative_evidence": neg, "not_neural_decoding": True, **SAFETY}


# ─── POLICY ENGINE ──────────────────────────────────────────────

def recommend_neuroadaptive_policy(adaptive_state, observation):
    state = adaptive_state.get("state", "ready")
    sr = observation.get("self_report", {})
    scene_action = {}
    session_action = {"pace": "normal", "difficulty_delta": 0, "next_checkin_seconds": 60}
    safety_action = {"pause_recommended": False, "stop_recommended": False, "reason": ""}

    policy_map = {
        "signal_blocked": ("hide_derived_biosignal_metrics", ["keep_biosignal_dashboard_visible_only"]),
        "signal_degraded": ("keep_biosignal_dashboard_visible_only", ["request_manual_checkin"]),
        "pause_recommended": ("suggest_short_pause", ["stop_session_safely"]),
        "fatigue_risk": ("slow_guidance_pace", ["reduce_visual_complexity"]),
        "effort_overload": ("lower_difficulty_next_block", ["reduce_visual_complexity"]),
        "discomfort_warning": ("suggest_short_pause", ["request_manual_checkin"]),
        "clarity_building": ("increase_scene_clarity", ["slow_guidance_pace"]),
        "deepening": ("continue_current_task", ["increase_scene_clarity"]),
        "stable_practice": ("continue_current_task", []),
        "ready": ("continue_current_task", []),
        "insufficient_data": ("request_manual_checkin", []),
    }
    pa = policy_map.get(state, ("continue_current_task", []))
    primary = pa[0]
    secondary = pa[1]

    if state == "pause_recommended":
        safety_action = {"pause_recommended": True, "stop_recommended": False,
                         "reason": f"High fatigue ({sr.get('fatigue')}) or discomfort ({sr.get('discomfort')})."}
    elif state == "signal_blocked":
        safety_action = {"pause_recommended": False, "stop_recommended": False,
                         "reason": "Signal quality blocked. Biosignal data not used."}

    scene_action = {"clarity_delta": 0.1 if "clarity" in primary else 0,
                    "fog_delta": -0.05 if "clarity" in primary else 0,
                    "brightness_delta": 0.05 if "clarity" in primary else 0,
                    "detail_delta": -0.05 if "reduce" in primary else 0,
                    "motion_delta": -0.1 if "slow" in primary else 0}

    return {"policy_id": str(uuid4()), "recommended_action": primary,
            "secondary_actions": secondary, "scene_policy": scene_action,
            "session_policy": session_action, "safety_policy": safety_action,
            "explainability": [f"State: {state}", f"Primary driver: {adaptive_state.get('primary_driver')}",
                              f"Confidence: {adaptive_state.get('confidence', 0):.2f}"],
            **SAFETY}


# ─── APPLICATION LAYER ──────────────────────────────────────────

def apply_neuroadaptive_policy(guided_session_id, policy):
    applied = {"application_id": str(uuid4()), "mode": "preview",
               "guided_session_id": guided_session_id,
               "policy_id": policy.get("policy_id", ""),
               "scene_adjustment_preview": policy.get("scene_policy", {}),
               "session_adjustment_preview": policy.get("session_policy", {}),
               "timeline_event_written": True,
               "requires_user_confirmation": policy.get("safety_policy", {}).get("pause_recommended", False),
               **SAFETY}
    try:
        from app.core.biosignals.biosignal_dashboard import append_biosignal_timeline_event
        append_biosignal_timeline_event(guided_session_id, "policy_applied",
                                         {"policy_id": policy.get("policy_id"),
                                          "action": policy.get("recommended_action")})
    except Exception:
        pass
    return applied


# ─── FUSION LOOP ────────────────────────────────────────────────

def run_single_fusion_step(user_id="demo_user", guided_session_id=None, feed_id=None):
    obs = build_multimodal_observation(guided_session_id, feed_id, user_id)
    state = estimate_adaptive_state(obs)
    policy = recommend_neuroadaptive_policy(state, obs)
    app = apply_neuroadaptive_policy(guided_session_id, policy) if guided_session_id else {}
    step = {"fusion_step_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observation": obs, "adaptive_state": state,
            "policy": policy, "application": app,
            "safe_to_display": True, "raw_eeg_included": False, **SAFETY}
    d = os.path.join(BASE, "fusion_steps", user_id)
    _save_json(os.path.join(d, "latest_fusion_step.json"), step)
    _append_jsonl(os.path.join(d, "fusion_steps.jsonl"), step)
    return step


# ─── FUSION SUMMARY ─────────────────────────────────────────────

def build_fusion_session_summary(user_id="demo_user", guided_session_id=None):
    d = os.path.join(BASE, "fusion_steps", user_id, "fusion_steps.jsonl")
    steps = []
    if os.path.exists(d):
        steps = [json.loads(line) for line in open(d) if line.strip()]
    if not steps:
        return {"user_id": user_id, "n_fusion_steps": 0, "status": "no_data", **SAFETY}

    states = {}
    policies = {}
    risks = {}
    confs = []
    for s in steps:
        st = s.get("adaptive_state", {}).get("state", "unknown")
        states[st] = states.get(st, 0) + 1
        pa = s.get("policy", {}).get("recommended_action", "unknown")
        policies[pa] = policies.get(pa, 0) + 1
        ri = s.get("adaptive_state", {}).get("risk_level", "unknown")
        risks[ri] = risks.get(ri, 0) + 1
        confs.append(s.get("adaptive_state", {}).get("confidence", 0))

    summary = {"fusion_summary_id": str(uuid4()), "user_id": user_id,
               "guided_session_id": guided_session_id,
               "n_fusion_steps": len(steps),
               "state_distribution": states, "policy_distribution": policies,
               "risk_distribution": risks,
               "avg_confidence": round(sum(confs) / len(confs), 3) if confs else 0,
               "biosignal_quality_impact": "derived_summaries_only",
               "primary_adaptation_driver": max(states.items(), key=lambda x: x[1])[0] if states else "",
               "safe_interpretation": "Fusion states use self-report proxies and derived engineering summaries only.",
               **SAFETY}
    sd = os.path.join(BASE, "fusion_summaries", user_id)
    _save_json(os.path.join(sd, "latest_fusion_summary.json"), summary)
    return summary


# ─── SAFE FUSION EXPORT ─────────────────────────────────────────

def export_safe_fusion_pack(user_id="demo_user", guided_session_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "fusion_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []
    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id,
                                       "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Safe Fusion Export\n\nFusion uses self-report proxies and derived "
         "engineering summaries. Not neural decoding. Not BCI. Not neurofeedback validation. "
         "Not clinical. Not mind-reading."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    summary = build_fusion_session_summary(user_id, guided_session_id)
    fp = os.path.join(ed, "fusion_summary.json")
    _save_json(fp, summary)
    files.append(fp)

    obs_p = os.path.join(BASE, "multimodal_observations", user_id, "latest_observation.json")
    if os.path.exists(obs_p):
        files.append(obs_p)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}
