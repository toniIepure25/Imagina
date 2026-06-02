"""IMAGINA V34 — Visible Scene Dynamics Engine + Demo Scenarios + Upgraded Adaptation."""

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
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only."),
    "scene_boundary": ("Scene changes are symbolic visualization aids based on self-report proxies "
                        "and safe policy previews. They are not reconstructions of thoughts, "
                        "dreams, neural activity, or mental images."),
    "raw_eeg_export_default": False,
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def compute_scene_dynamics(adaptive_state, policy, observation=None, scene_before=None):
    obs = observation or {}
    sr = obs.get("self_report", {}) or {}
    state_name = adaptive_state.get("state", "ready")
    gate = obs.get("signal_gate", {}).get("gate_state", "open") or "open"
    vividness = sr.get("vividness") or 5
    stability = sr.get("stability") or 5
    effort = sr.get("effort") or 5
    fatigue = sr.get("fatigue") or 3
    confidence = sr.get("confidence") or 5
    discomfort = sr.get("discomfort") or 1

    deltas = {"clarity": 0.0, "fog": 0.0, "brightness": 0.0, "color_saturation": 0.0,
              "detail": 0.0, "motion": 0.0, "stability": 0.0, "visual_noise": 0.0}
    reason_parts = []

    # ─── Self-report modulation ───
    if vividness <= 3:
        deltas["clarity"] -= 0.07
        deltas["fog"] += 0.06
        reason_parts.append(f"low vividness ({vividness})")
    elif vividness >= 8:
        deltas["clarity"] += 0.06
        deltas["fog"] -= 0.05
        reason_parts.append(f"high vividness ({vividness})")

    if stability <= 3:
        deltas["stability"] -= 0.06
        deltas["visual_noise"] += 0.05
        reason_parts.append(f"low stability ({stability})")
    elif stability >= 8:
        deltas["stability"] += 0.05
        deltas["visual_noise"] -= 0.04
        reason_parts.append(f"high stability ({stability})")

    if effort >= 8:
        deltas["detail"] -= 0.06
        deltas["motion"] -= 0.05
        deltas["fog"] += 0.05
        reason_parts.append(f"high effort ({effort})")

    if fatigue >= 7:
        deltas["brightness"] -= 0.06
        deltas["motion"] -= 0.06
        deltas["detail"] -= 0.04
        reason_parts.append(f"high fatigue ({fatigue})")

    if confidence >= 8:
        deltas["clarity"] += 0.04
        deltas["fog"] -= 0.03
        reason_parts.append(f"high confidence ({confidence})")

    if discomfort >= 5:
        deltas["brightness"] -= 0.06
        deltas["motion"] -= 0.07
        reason_parts.append(f"moderate discomfort ({discomfort})")

    # ─── State-driven modulation ───
    if state_name == "clarity_building":
        deltas["clarity"] += 0.08
        deltas["fog"] -= 0.06
        deltas["stability"] += 0.03
        deltas["detail"] += 0.02
        reason_parts.append("state=clarity_building")
    elif state_name == "deepening":
        deltas["clarity"] += 0.04
        deltas["fog"] -= 0.04
        deltas["detail"] += 0.07
        deltas["color_saturation"] += 0.04
        deltas["stability"] += 0.03
        reason_parts.append("state=deepening")
    elif state_name == "stable_practice":
        deltas["clarity"] += 0.03
        deltas["fog"] -= 0.02
        deltas["stability"] += 0.04
        reason_parts.append("state=stable_practice")
    elif state_name == "effort_overload":
        deltas["fog"] += 0.06
        deltas["detail"] -= 0.06
        deltas["motion"] -= 0.06
        deltas["brightness"] -= 0.03
        reason_parts.append("state=effort_overload")
    elif state_name == "fatigue_risk":
        deltas["motion"] -= 0.08
        deltas["detail"] -= 0.05
        deltas["brightness"] -= 0.05
        deltas["fog"] += 0.04
        reason_parts.append("state=fatigue_risk")
    elif state_name == "pause_recommended":
        for k in deltas:
            deltas[k] = 0.0
        reason_parts.append("state=pause_recommended, scene frozen")

    # ─── Signal gate override ───
    if gate == "blocked":
        deltas = {k: 0.0 for k in deltas}
        reason_parts = ["signal blocked; scene adaptation disabled"]
    elif gate == "degraded":
        deltas = {k: max(-0.04, min(0.04, v)) for k, v in deltas.items()}
        reason_parts.append("signal degraded, conservative deltas only")

    final = {k: round(max(-0.15, min(0.15, v)), 3) for k, v in deltas.items()}
    reason = "; ".join(reason_parts) if reason_parts else "baseline, no significant change"

    return {
        "scene_dynamics_id": str(uuid4()),
        "adaptive_state": state_name,
        "policy_action": policy.get("recommended_action", ""),
        "base_deltas": deltas,
        "final_deltas": final,
        "dynamics_reason": reason,
        "visible_change_expected": any(abs(v) >= 0.02 for v in final.values()),
        "preview_only": True,
        **SAFETY,
    }


# ─── UPGRADED LIVE SCENE ADAPTATION ────────────────────────────

def build_live_scene_adaptation_frame(live_session_id, fusion_step=None, latest_scene_state=None):
    from app.core.biosignals.live_neuroadaptive import get_live_neuroadaptive_demo
    live = get_live_neuroadaptive_demo(live_session_id)
    if not live:
        return {"error": "live_session_not_found", **SAFETY}

    if not fusion_step:
        from app.core.biosignals.fusion_multimodal import run_single_fusion_step
        fusion_step = run_single_fusion_step(live.get("user_id", "demo_user"),
                                              live.get("guided_session_id"),
                                              live.get("feed_id"))

    frames = live.get("frames", []) or []
    scene_before = None
    for f in reversed(frames):
        sa = f.get("scene_adaptation", {})
        if sa.get("scene_after_preview"):
            scene_before = sa["scene_after_preview"]
            break
    if not scene_before:
        scene_before = {"clarity": 0.6, "fog": 0.4, "brightness": 0.6, "color_saturation": 0.5,
                        "motion_speed": 0.2, "stability_anchor": 0.6, "detail_density": 0.4, "visual_noise": 0.3}

    dynamics = compute_scene_dynamics(
        fusion_step.get("adaptive_state", {}),
        fusion_step.get("policy", {}),
        fusion_step.get("observation", {}),
        scene_before,
    )

    fd = dynamics["final_deltas"]
    scene_after = {
        "clarity": round(max(0.0, min(1.0, scene_before.get("clarity", 0.5) + fd["clarity"])), 3),
        "fog": round(max(0.0, min(1.0, scene_before.get("fog", 0.5) + fd["fog"])), 3),
        "brightness": round(max(0.0, min(1.0, scene_before.get("brightness", 0.5) + fd["brightness"])), 3),
        "color_saturation": round(max(0.0, min(1.0, scene_before.get("color_saturation", 0.5) + fd["color_saturation"])), 3),
        "motion_speed": round(max(0.0, min(1.0, scene_before.get("motion_speed", 0.2) + fd["motion"])), 3),
        "stability_anchor": round(max(0.0, min(1.0, scene_before.get("stability_anchor", 0.6) + fd["stability"])), 3),
        "detail_density": round(max(0.0, min(1.0, scene_before.get("detail_density", 0.4) + fd["detail"])), 3),
        "visual_noise": round(max(0.0, min(1.0, scene_before.get("visual_noise", 0.3) + fd["visual_noise"])), 3),
    }

    frame = {
        "live_scene_frame_id": str(uuid4()),
        "live_session_id": live_session_id,
        "guided_session_id": live.get("guided_session_id", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "adaptive_state": dynamics["adaptive_state"],
        "policy_action": dynamics["policy_action"],
        "scene_dynamics": dynamics,
        "scene_before": scene_before,
        "scene_after_preview": scene_after,
        "visible_change_expected": dynamics["visible_change_expected"],
        "change_interpretation": dynamics["dynamics_reason"],
        "preview_only": True,
        "requires_user_confirmation": dynamics["adaptive_state"] == "pause_recommended",
        "raw_eeg_included": False,
        **SAFETY,
    }

    d = os.path.join(BASE, "live_scene_adaptation", live_session_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "frames.jsonl"), "a") as f:
        f.write(json.dumps(frame, default=str) + "\n")
    _save_json(os.path.join(d, "latest_frame.json"), frame)
    return frame


def get_latest_live_scene_adaptation(live_session_id):
    p = os.path.join(BASE, "live_scene_adaptation", live_session_id, "latest_frame.json")
    return _load_json(p)


def build_live_scene_replay(live_session_id):
    from app.core.biosignals.live_neuroadaptive import get_live_neuroadaptive_demo
    live = get_live_neuroadaptive_demo(live_session_id)
    if not live:
        return {"error": "live_session_not_found", **SAFETY}

    fp = os.path.join(BASE, "live_scene_adaptation", live_session_id, "frames.jsonl")
    frames = []
    if os.path.exists(fp):
        frames = [json.loads(line) for line in open(fp) if line.strip()]

    replay_frames = []
    for i, f in enumerate(frames):
        scene = f.get("scene_after_preview", {})
        replay_frames.append({
            "frame_index": i,
            "timestamp": f.get("timestamp", ""),
            "adaptive_state": f.get("adaptive_state", ""),
            "policy_action": f.get("policy_action", ""),
            "scene_after_preview": scene,
            "change_interpretation": f.get("change_interpretation", ""),
            "visible_change_expected": f.get("visible_change_expected", False),
        })

    if replay_frames:
        first = replay_frames[0]["scene_after_preview"]
        last = replay_frames[-1]["scene_after_preview"]
        visible_count = sum(1 for f in replay_frames if f.get("visible_change_expected"))
        states = [f.get("adaptive_state", "") for f in replay_frames]
        dominant_state = max(set(states), key=states.count) if states else ""
        summary = {
            "clarity_start": first.get("clarity"), "clarity_end": last.get("clarity"),
            "clarity_change": round(last.get("clarity", 0) - first.get("clarity", 0), 3),
            "fog_start": first.get("fog"), "fog_end": last.get("fog"),
            "fog_change": round(last.get("fog", 0) - first.get("fog", 0), 3),
            "detail_change": round(last.get("detail_density", 0) - first.get("detail_density", 0), 3),
            "motion_change": round(last.get("motion_speed", 0) - first.get("motion_speed", 0), 3),
            "stability_change": round(last.get("stability_anchor", 0) - first.get("stability_anchor", 0), 3),
            "visual_noise_change": round(last.get("visual_noise", 0) - first.get("visual_noise", 0), 3),
            "n_visible_changes": visible_count,
            "dominant_adaptive_state": dominant_state,
            "raw_eeg_included": False,
        }
    else:
        summary = {"n_frames": 0}

    replay = {"live_scene_replay_id": str(uuid4()), "live_session_id": live_session_id,
              "n_frames": len(replay_frames), "frames": replay_frames,
              "summary": summary, **SAFETY}
    d = os.path.join(BASE, "live_scene_replays", live_session_id)
    _save_json(os.path.join(d, "replay.json"), replay)
    return replay


def get_live_scene_replay(live_session_id):
    return _load_json(os.path.join(BASE, "live_scene_replays", live_session_id, "replay.json"))


def export_safe_live_scene_pack(user_id="demo_user", live_session_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "live_scene_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []
    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Safe Live Scene Export\n\nSymbolic scene previews only. Self-report proxy + safe policy preview. No raw EEG. Not neural decoding. Not BCI."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)
    if live_session_id:
        replay = build_live_scene_replay(live_session_id)
        if replay and "error" not in replay:
            files.append(os.path.join(ed, "live_scene_replay.json") if not os.path.exists(os.path.join(ed, "live_scene_replay.json")) else "")
            _save_json(os.path.join(ed, "live_scene_replay.json"), replay)
    return {"export_id": str(uuid4()), "export_dir": ed, "files": [f for f in files if f],
            "n_files": len([f for f in files if f]), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}


# ─── DEMO SCENARIOS ─────────────────────────────────────────────

SCENARIOS = {
    "clarity_success": {
        "title": "Clarity Success",
        "description": "Low vividness → high vividness: clarity should increase, fog should decrease.",
        "checkins": [
            {"vividness": 4, "stability": 5, "effort": 4, "fatigue": 2, "confidence": 6, "discomfort": 1},
            {"vividness": 8, "stability": 7, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1},
        ],
        "expected": {"clarity_direction": "up", "fog_direction": "down"},
    },
    "effort_overload": {
        "title": "Effort Overload",
        "description": "High effort → detail and motion should decrease.",
        "checkins": [
            {"vividness": 4, "stability": 4, "effort": 8, "fatigue": 6, "confidence": 4, "discomfort": 2},
            {"vividness": 3, "stability": 3, "effort": 9, "fatigue": 7, "confidence": 3, "discomfort": 2},
        ],
        "expected": {"detail_direction": "down", "motion_direction": "down"},
    },
    "deepening": {
        "title": "Deepening",
        "description": "High vividness + confidence → detail increases, fog decreases.",
        "checkins": [
            {"vividness": 8, "stability": 7, "effort": 3, "fatigue": 2, "confidence": 9, "discomfort": 1},
            {"vividness": 9, "stability": 8, "effort": 2, "fatigue": 1, "confidence": 9, "discomfort": 1},
        ],
        "expected": {"detail_direction": "up", "fog_direction": "down"},
    },
}


def get_scene_demo_scenarios():
    return {"scenarios": SCENARIOS, "n_scenarios": len(SCENARIOS), **SAFETY}


def run_scene_demo_scenario(user_id="demo_user", scenario_id="clarity_success"):
    sc = SCENARIOS.get(scenario_id)
    if not sc:
        return {"error": "scenario_not_found", **SAFETY}

    from app.core.biosignals.live_neuroadaptive import (
        complete_live_neuroadaptive_demo,
        start_live_neuroadaptive_demo,
        step_live_neuroadaptive_demo,
        submit_live_demo_checkin,
    )
    live = start_live_neuroadaptive_demo(user_id)
    lsid = live["live_session_id"]

    scenes = []
    for ci in sc["checkins"]:
        submit_live_demo_checkin(lsid, ci)
        f = step_live_neuroadaptive_demo(lsid)
        sa = f.get("scene_adaptation", {})
        scenes.append(sa.get("scene_after_preview", {}))

    complete_live_neuroadaptive_demo(lsid)

    if len(scenes) >= 2:
        first = scenes[0]
        last = scenes[-1]
        observed = {
            "clarity_change": round(last.get("clarity", first.get("clarity", 0.5)) - first.get("clarity", 0.5), 3),
            "fog_change": round(last.get("fog", first.get("fog", 0.5)) - first.get("fog", 0.5), 3),
            "detail_change": round(last.get("detail_density", first.get("detail_density", 0.4)) - first.get("detail_density", 0.4), 3),
            "motion_change": round(last.get("motion_speed", first.get("motion_speed", 0.2)) - first.get("motion_speed", 0.2), 3),
        }
        passed = True
        failures = []
        exp = sc["expected"]
        cd = exp.get("clarity_direction")
        if cd == "up" and observed["clarity_change"] < 0.01:
            passed = False
            failures.append(f"clarity change {observed['clarity_change']} not up")
        if cd == "down" and observed["clarity_change"] > -0.01:
            passed = False
        fd = exp.get("fog_direction")
        if fd == "down" and observed["fog_change"] > -0.01:
            passed = False
            failures.append(f"fog change {observed['fog_change']} not down")
        dd = exp.get("detail_direction")
        if dd == "down" and observed["detail_change"] > -0.01:
            passed = False
            failures.append(f"detail change {observed['detail_change']} not down")
        if dd == "up" and observed["detail_change"] < 0.01:
            passed = False
        md = exp.get("motion_direction")
        if md == "down" and observed["motion_change"] > -0.01:
            passed = False
            failures.append(f"motion change {observed['motion_change']} not down")
    else:
        passed = False
        observed = {}
        failures = ["not enough frames"]

    result = {"scenario_id": scenario_id, "passed": passed, "n_steps": len(sc.get("checkins", [])),
              "expected": sc["expected"], "observed": observed, "failure_reasons": failures, **SAFETY}
    sd = os.path.join(BASE, "live_scene_scenarios", user_id)
    _save_json(os.path.join(sd, f"{scenario_id}_result.json"), result)
    return result
