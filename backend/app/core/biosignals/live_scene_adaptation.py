"""IMAGINA V33 — Live Scene Adaptation + Replay + Safe Export."""

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
    "biosignal_boundary": "Biosignal streaming is optional and exploratory.",
    "fusion_boundary": "Multimodal fusion uses self-report and derived engineering summaries only.",
    "scene_boundary": ("Scene changes are symbolic visualization aids based on self-report proxies "
                        "and safe policy previews. They are not reconstructions of thoughts, "
                        "dreams, neural activity, or mental images."),
    "live_dashboard_boundary": "Live dashboard events are local engineering telemetry.",
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


def _default_scene():
    return {"clarity": 0.6, "fog": 0.4, "brightness": 0.6, "color_saturation": 0.5,
            "motion_speed": 0.2, "stability_anchor": 0.6, "detail_density": 0.4, "visual_noise": 0.3}


# ─── SCENE ADAPTATION ───────────────────────────────────────────

def build_live_scene_adaptation_frame(live_session_id, fusion_step=None, latest_scene_state=None):
    from app.core.biosignals.live_neuroadaptive import get_live_neuroadaptive_demo
    live = get_live_neuroadaptive_demo(live_session_id)
    if not live:
        return {"error": "live_session_not_found", **SAFETY}

    frames = live.get("frames", [])
    if not frames:
        scene_before = _default_scene()
    else:
        # Use last frame's scene_after_preview or default
        sf = frames[-1].get("scene_adaptation", {}).get("scene_after_preview")
        scene_before = sf if sf else _default_scene()

    policy = (fusion_step or {}).get("policy", {})
    state = (fusion_step or {}).get("adaptive_state", {})

    scene_action = policy.get("scene_policy", {})
    deltas = {
        "clarity_delta": scene_action.get("clarity_delta", 0) * 0.1,
        "fog_delta": scene_action.get("fog_delta", 0) * 0.1,
        "brightness_delta": scene_action.get("brightness_delta", 0) * 0.1,
        "detail_delta": scene_action.get("detail_delta", 0) * 0.1,
        "motion_delta": scene_action.get("motion_delta", 0) * 0.1,
    }

    if state.get("state") == "fatigue_risk":
        deltas["motion_delta"] = -0.05
        deltas["detail_delta"] = -0.03
    elif state.get("state") == "clarity_building":
        deltas["clarity_delta"] = 0.05
        deltas["fog_delta"] = -0.03
    elif state.get("state") == "effort_overload":
        deltas["detail_delta"] = -0.05
        deltas["motion_delta"] = -0.05
    elif state.get("state") == "signal_blocked":
        deltas = {k: 0 for k in deltas}

    scene_after = {
        "clarity": round(max(0.0, min(1.0, scene_before.get("clarity", 0.5) + deltas["clarity_delta"])), 3),
        "fog": round(max(0.0, min(1.0, scene_before.get("fog", 0.5) + deltas["fog_delta"])), 3),
        "brightness": round(max(0.0, min(1.0, scene_before.get("brightness", 0.5) + deltas["brightness_delta"])), 3),
        "color_saturation": scene_before.get("color_saturation", 0.5),
        "motion_speed": round(max(0.0, min(1.0, scene_before.get("motion_speed", 0.2) + deltas["motion_delta"])), 3),
        "stability_anchor": scene_before.get("stability_anchor", 0.6),
        "detail_density": round(max(0.0, min(1.0, scene_before.get("detail_density", 0.4) + deltas["detail_delta"])), 3),
        "visual_noise": scene_before.get("visual_noise", 0.3),
    }

    interpret = _interpret(deltas, state)
    frame = {"live_scene_frame_id": str(uuid4()), "live_session_id": live_session_id,
             "guided_session_id": live.get("guided_session_id", ""),
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "adaptive_state": state.get("state", ""),
             "policy_action": policy.get("recommended_action", ""),
             "scene_before": scene_before, "scene_policy_delta": deltas,
             "scene_after_preview": scene_after,
             "change_interpretation": interpret,
             "preview_only": True, "requires_user_confirmation": False,
             "raw_eeg_included": False, **SAFETY}

    d = os.path.join(BASE, "live_scene_adaptation", live_session_id)
    _append_jsonl(os.path.join(d, "frames.jsonl"), frame)
    _save_json(os.path.join(d, "latest_frame.json"), frame)
    return frame


def _interpret(deltas, state):
    if state.get("state") == "signal_blocked":
        return "Signal quality degraded; scene adaptation remains self-report only."
    if state.get("state") == "fatigue_risk":
        return "Scene simplified to reduce cognitive load."
    if deltas.get("clarity_delta", 0) > 0:
        return "Scene clarity scaffold increased."
    if deltas.get("fog_delta", 0) > 0:
        return "Scene became foggier due to lower confidence or higher effort."
    if deltas.get("motion_delta", 0) < 0:
        return "Motion reduced to stabilize scene."
    return "Scene preview adapted based on policy preview."


def get_latest_live_scene_adaptation(live_session_id):
    p = os.path.join(BASE, "live_scene_adaptation", live_session_id, "latest_frame.json")
    return _load_json(p)


# ─── SCENE REPLAY ───────────────────────────────────────────────

def build_live_scene_replay(live_session_id):
    from app.core.biosignals.live_neuroadaptive import get_live_neuroadaptive_demo
    live = get_live_neuroadaptive_demo(live_session_id)
    if not live:
        return {"error": "live_session_not_found", **SAFETY}

    adaptation_frames = []
    dp = os.path.join(BASE, "live_scene_adaptation", live_session_id, "frames.jsonl")
    if os.path.exists(dp):
        adaptation_frames = [json.loads(line) for line in open(dp) if line.strip()]

    live_frames = live.get("frames", [])
    replay_frames = []
    for i in range(max(len(live_frames), len(adaptation_frames))):
        lf = live_frames[i] if i < len(live_frames) else {}
        af = adaptation_frames[i] if i < len(adaptation_frames) else {}
        scene = af.get("scene_after_preview") if af else _default_scene()
        replay_frames.append({
            "frame_index": i,
            "timestamp": af.get("timestamp", lf.get("timestamp", "")),
            "adaptive_state": lf.get("adaptive_state", ""),
            "policy_action": lf.get("policy_action", ""),
            "scene_after_preview": scene,
            "sqi": lf.get("sqi"), "gate_state": lf.get("gate_state", ""),
            "caption": af.get("change_interpretation", ""),
        })

    first_scene = replay_frames[0]["scene_after_preview"] if replay_frames else _default_scene()
    last_scene = replay_frames[-1]["scene_after_preview"] if replay_frames else _default_scene()
    states = [f.get("adaptive_state", "") for f in replay_frames]
    dominant_state = max(set(states), key=states.count) if states else ""

    replay = {
        "live_scene_replay_id": str(uuid4()),
        "live_session_id": live_session_id,
        "guided_session_id": live.get("guided_session_id", ""),
        "n_frames": len(replay_frames),
        "frames": replay_frames,
        "summary": {
            "clarity_change": round(last_scene.get("clarity", 0) - first_scene.get("clarity", 0), 3),
            "fog_change": round(last_scene.get("fog", 0) - first_scene.get("fog", 0), 3),
            "detail_change": round(last_scene.get("detail_density", 0) - first_scene.get("detail_density", 0), 3),
            "motion_change": round(last_scene.get("motion_speed", 0) - first_scene.get("motion_speed", 0), 3),
            "dominant_adaptive_state": dominant_state,
            "dominant_policy_action": "",
            "safety_events": [],
            "raw_eeg_included": False,
        }, **SAFETY,
    }
    d = os.path.join(BASE, "live_scene_replays", live_session_id)
    _save_json(os.path.join(d, "replay.json"), replay)
    return replay


def get_live_scene_replay(live_session_id):
    p = os.path.join(BASE, "live_scene_replays", live_session_id, "replay.json")
    return _load_json(p)


# ─── SAFE EXPORT ────────────────────────────────────────────────

def export_safe_live_scene_pack(user_id="demo_user", live_session_id=None):
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")[:19]
    ed = os.path.join(BASE, "live_scene_exports", user_id, f"{ts}")
    os.makedirs(ed, exist_ok=True)
    files = []

    for name, content in [
        ("manifest.json", json.dumps({"export_id": str(uuid4()), "user_id": user_id, "raw_eeg_included": False, "safe_to_share": True}, indent=2)),
        ("safety_boundaries.json", json.dumps(SAFETY, indent=2)),
        ("README.md", "# Safe Live Scene Export\n\nSymbolic scene previews only. Self-report proxy + safe policy preview. No raw EEG. Not neural decoding. Not BCI. Not neurofeedback validation."),
    ]:
        p = os.path.join(ed, name)
        with open(p, "w") as f:
            f.write(content)
        files.append(p)

    if live_session_id:
        replay = build_live_scene_replay(live_session_id)
        if replay and "error" not in replay:
            rp = os.path.join(ed, "live_scene_replay.json")
            _save_json(rp, replay)
            files.append(rp)
        latest = get_latest_live_scene_adaptation(live_session_id)
        if latest:
            lp = os.path.join(ed, "latest_scene_adaptation_frame.json")
            _save_json(lp, latest)
            files.append(lp)

    return {"export_id": str(uuid4()), "export_dir": ed, "files": files,
            "n_files": len(files), "raw_eeg_included": False, "safe_to_share": True, **SAFETY}
