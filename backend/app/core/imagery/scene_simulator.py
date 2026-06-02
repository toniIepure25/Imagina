"""IMAGINA V22 — Scene Template Registry + Scene State Model + Adaptive Controller + Replay Engine."""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
SCENE_DIR = os.path.join(BASE, "scene_states")
REPLAY_DIR = os.path.join(BASE, "session_replays")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

VIZ_BOUNDARY = ("Scene visualization is a symbolic training aid based on self-report proxies. "
                "It is not a reconstruction of mental imagery, neural activity, dreams, or thoughts.")


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


# ─── SCENE TEMPLATE REGISTRY ────────────────────────────────────

SCENE_TEMPLATES = [
    {"template_id": "red_circle_field", "title": "Red Circle Field",
     "category": "basic", "compatible_task_ids": ["red_circle_vividness"],
     "base_scene": {"background_type": "dark", "primary_object": "circle",
                    "base_colors": ["#cc0000", "#220000", "#440000"],
                    "default_clarity": 0.5, "default_fog": 0.5, "default_brightness": 0.5,
                    "default_color_saturation": 0.5, "default_motion_speed": 0.2,
                    "default_stability_anchor": 0.5, "default_detail_density": 0.3},
     "render_hints": {"layout": "centered_single", "animation_type": "breathing",
                      "symbolic_elements": ["glow_ring", "anchor_marker"]}},
    {"template_id": "blue_cube_space", "title": "Blue Cube Space",
     "category": "spatial", "compatible_task_ids": ["blue_cube_vividness", "static_cube_stability",
                                                      "rotating_cube_stability", "room_layout_stability"],
     "base_scene": {"background_type": "grid", "primary_object": "cube",
                    "base_colors": ["#0033cc", "#000022", "#334488"],
                    "default_clarity": 0.5, "default_fog": 0.3, "default_brightness": 0.6,
                    "default_color_saturation": 0.6, "default_motion_speed": 0.3,
                    "default_stability_anchor": 0.6, "default_detail_density": 0.4},
     "render_hints": {"layout": "perspective_grid", "animation_type": "rotate_slow",
                      "symbolic_elements": ["grid_lines", "depth_indicator"]}},
    {"template_id": "candle_flame_room", "title": "Candle Flame Room",
     "category": "basic", "compatible_task_ids": ["candle_flame_vividness"],
     "base_scene": {"background_type": "dark", "primary_object": "flame",
                    "base_colors": ["#ffcc00", "#002200", "#886600"],
                    "default_clarity": 0.6, "default_fog": 0.2, "default_brightness": 0.3,
                    "default_color_saturation": 0.8, "default_motion_speed": 0.4,
                    "default_stability_anchor": 0.5, "default_detail_density": 0.5},
     "render_hints": {"layout": "centered_light_source", "animation_type": "flicker",
                      "symbolic_elements": ["flame_particles", "glow_halo"]}},
    {"template_id": "apple_detail_table", "title": "Apple Detail Table",
     "category": "object", "compatible_task_ids": ["apple_detail_generation"],
     "base_scene": {"background_type": "room", "primary_object": "sphere",
                    "base_colors": ["#cc2200", "#ffffcc", "#336622"],
                    "default_clarity": 0.5, "default_fog": 0.1, "default_brightness": 0.7,
                    "default_color_saturation": 0.7, "default_motion_speed": 0,
                    "default_stability_anchor": 0.7, "default_detail_density": 0.8},
     "render_hints": {"layout": "table_surface", "animation_type": "none",
                      "symbolic_elements": ["highlight_dots", "texture_patch"]}},
    {"template_id": "forest_scene", "title": "Forest Scene",
     "category": "nature", "compatible_task_ids": ["forest_scene_detail", "walking_path_simulation"],
     "base_scene": {"background_type": "nature", "primary_object": "path",
                    "base_colors": ["#226622", "#88aa44", "#443322"],
                    "default_clarity": 0.4, "default_fog": 0.6, "default_brightness": 0.5,
                    "default_color_saturation": 0.5, "default_motion_speed": 0.2,
                    "default_stability_anchor": 0.5, "default_detail_density": 0.7},
     "render_hints": {"layout": "horizon_with_path", "animation_type": "gentle_sway",
                      "symbolic_elements": ["light_rays", "fog_layers", "path_markers"]}},
    {"template_id": "beach_scene", "title": "Beach Scene",
     "category": "nature", "compatible_task_ids": ["beach_scene_construction", "visual_plus_sound_scene",
                                                     "multisensory_beach_reference"],
     "base_scene": {"background_type": "beach", "primary_object": "horizon",
                    "base_colors": ["#ffcc88", "#4488cc", "#886644"],
                    "default_clarity": 0.5, "default_fog": 0.4, "default_brightness": 0.8,
                    "default_color_saturation": 0.7, "default_motion_speed": 0.15,
                    "default_stability_anchor": 0.5, "default_detail_density": 0.5},
     "render_hints": {"layout": "horizon_wide", "animation_type": "wave_motion",
                      "symbolic_elements": ["wave_lines", "sun_glow", "sand_gradient"]}},
    {"template_id": "doorway_symbol", "title": "Symbolic Doorway",
     "category": "symbolic", "compatible_task_ids": ["symbolic_doorway_scene", "emotional_tone_imagery"],
     "base_scene": {"background_type": "symbolic", "primary_object": "doorway",
                    "base_colors": ["#442244", "#ffddaa", "#224488"],
                    "default_clarity": 0.4, "default_fog": 0.5, "default_brightness": 0.4,
                    "default_color_saturation": 0.5, "default_motion_speed": 0,
                    "default_stability_anchor": 0.6, "default_detail_density": 0.4},
     "render_hints": {"layout": "centered_arch", "animation_type": "glow_pulse",
                      "symbolic_elements": ["door_arch", "glow_behind", "particles_float"]}},
    {"template_id": "falling_leaf_scene", "title": "Falling Leaf",
     "category": "nature", "compatible_task_ids": ["falling_leaf"],
     "base_scene": {"background_type": "nature", "primary_object": "leaf",
                    "base_colors": ["#cc8800", "#88cc44", "#aaccff"],
                    "default_clarity": 0.5, "default_fog": 0.3, "default_brightness": 0.7,
                    "default_color_saturation": 0.6, "default_motion_speed": 0.7,
                    "default_stability_anchor": 0.3, "default_detail_density": 0.5},
     "render_hints": {"layout": "vertical_drift", "animation_type": "drift_sway",
                      "symbolic_elements": ["leaf_path", "wind_lines", "ground_marker"]}},
    {"template_id": "walking_path_scene", "title": "Walking Path",
     "category": "nature", "compatible_task_ids": ["walking_path_simulation"],
     "base_scene": {"background_type": "nature", "primary_object": "path",
                    "base_colors": ["#886644", "#448822", "#ccbb88"],
                    "default_clarity": 0.5, "default_fog": 0.5, "default_brightness": 0.6,
                    "default_color_saturation": 0.5, "default_motion_speed": 0.6,
                    "default_stability_anchor": 0.4, "default_detail_density": 0.5},
     "render_hints": {"layout": "horizon_with_path", "animation_type": "forward_scroll",
                      "symbolic_elements": ["motion_lines", "horizon_marker"]}},
    {"template_id": "multisensory_food", "title": "Multisensory Food",
     "category": "object", "compatible_task_ids": ["visual_plus_smell_food", "visual_plus_touch_object"],
     "base_scene": {"background_type": "room", "primary_object": "sphere",
                    "base_colors": ["#ff8800", "#ffffaa", "#88dd44"],
                    "default_clarity": 0.5, "default_fog": 0.1, "default_brightness": 0.7,
                    "default_color_saturation": 0.7, "default_motion_speed": 0,
                    "default_stability_anchor": 0.7, "default_detail_density": 0.6},
     "render_hints": {"layout": "table_surface", "animation_type": "pulse",
                      "symbolic_elements": ["aroma_lines", "warmth_glow", "texture_dots"]}},
    {"template_id": "default_dark_field", "title": "Default Dark Field",
     "category": "basic", "compatible_task_ids": [],
     "base_scene": {"background_type": "dark", "primary_object": "circle",
                    "base_colors": ["#884488", "#220022", "#442244"],
                    "default_clarity": 0.5, "default_fog": 0.5, "default_brightness": 0.5,
                    "default_color_saturation": 0.5, "default_motion_speed": 0.2,
                    "default_stability_anchor": 0.5, "default_detail_density": 0.3},
     "render_hints": {"layout": "centered_single", "animation_type": "breathing",
                      "symbolic_elements": ["glow_ring"]}},
]


def get_scene_template_registry():
    return {"templates": SCENE_TEMPLATES, "n_templates": len(SCENE_TEMPLATES),
            "visualization_boundary": VIZ_BOUNDARY, **SAFETY}


def get_scene_template(template_id):
    for t in SCENE_TEMPLATES:
        if t["template_id"] == template_id:
            return {**t, "visualization_boundary": VIZ_BOUNDARY, **SAFETY}
    return {"error": "template_not_found", "template_id": template_id, **SAFETY}


def get_scene_template_for_task(task_id):
    for t in SCENE_TEMPLATES:
        if task_id in t["compatible_task_ids"]:
            return {**t, "visualization_boundary": VIZ_BOUNDARY, **SAFETY}
    return {**SCENE_TEMPLATES[-1], "visualization_boundary": VIZ_BOUNDARY, **SAFETY}


def list_scene_templates(category=None):
    if category:
        filtered = [t for t in SCENE_TEMPLATES if t["category"] == category]
    else:
        filtered = SCENE_TEMPLATES
    return {"templates": [{**t, "visualization_boundary": VIZ_BOUNDARY} for t in filtered],
            "n_templates": len(filtered), "visualization_boundary": VIZ_BOUNDARY, **SAFETY}


# ─── SCENE STATE MODEL ──────────────────────────────────────────

def _get_template(task_id):
    t = get_scene_template_for_task(task_id)
    if t.get("error"):
        return SCENE_TEMPLATES[-1]
    return t


def _derive_scene_params(feedback, checkin, proxies):
    sf = (feedback or {}).get("scene_feedback", {})
    c = (checkin or {})
    px = (proxies or {})
    return {
        "clarity": sf.get("clarity", 0.5),
        "fog": sf.get("fog", 0.5),
        "brightness": sf.get("brightness", 0.5),
        "color_saturation": sf.get("color_saturation", 0.5),
        "motion_speed": sf.get("motion_speed", 0.2),
        "stability_anchor": sf.get("stability_anchor", 0.5),
        "detail_density": sf.get("detail_density", 0.5),
        "object_scale": 0.7,
        "object_sharpness": round(sf.get("clarity", 0.5) * sf.get("stability_anchor", 0.5), 3),
        "background_complexity": round(sf.get("detail_density", 0.3) * sf.get("clarity", 0.5), 3),
        "particle_density": round(sf.get("detail_density", 0.3) * 0.7, 3),
        "visual_noise": round(px.get("pid_proxy", 0.5), 3),
        "breathing_rate": round(1.0 - (c.get("fatigue", 3) / 10), 3),
        "calmness": round(sf.get("audio_calmness", 1.0 - c.get("fatigue", 3) / 10), 3),
    }


def build_scene_state(session_id, feedback=None, checkin=None):
    from app.core.imagery.guided_session_runtime import get_guided_session
    s = get_guided_session(session_id)
    if not s:
        return {"error": "session_not_found", **SAFETY}

    task_id = s.get("task_id", "")
    tpl = _get_template(task_id)
    checkins = s.get("micro_checkins", [])
    latest_checkin = checkins[-1] if checkins else checkin

    if not feedback:
        from app.core.imagery.guided_session_runtime import _generate_adaptive_feedback_inner
        feedback = _generate_adaptive_feedback_inner(s)

    from app.core.imagery.guided_session_runtime import _compute_live_proxies
    proxies = _compute_live_proxies(s) if checkins else {}

    scene = {
        "scene_state_id": str(uuid4()), "session_id": session_id,
        "task_id": task_id, "template_id": tpl["template_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": s.get("current_phase", ""),
        "scene_parameters": _derive_scene_params(feedback, latest_checkin, proxies),
        "derived_from": {
            "iqi_proxy": proxies.get("iqi_proxy"),
            "pid_proxy": proxies.get("pid_proxy"),
            "fatigue_risk": proxies.get("fatigue_risk"),
            "safety_state": proxies.get("safety_state"),
            "feedback_type": feedback.get("feedback_type"),
        },
        "render_instruction": (f"Template: {tpl['title']} | Phase: {s.get('current_phase')} | "
                               f"IQI={proxies.get('iqi_proxy', 0.5):.2f}"),
        "visualization_boundary": VIZ_BOUNDARY, **SAFETY,
    }

    d = os.path.join(SCENE_DIR, session_id)
    os.makedirs(d, exist_ok=True)
    _append_jsonl(os.path.join(d, "states.jsonl"), scene)
    _save_json(os.path.join(d, "latest_scene_state.json"), scene)
    return scene


def get_latest_scene_state(session_id):
    p = os.path.join(SCENE_DIR, session_id, "latest_scene_state.json")
    s = _load_json(p)
    if s:
        return s
    return build_scene_state(session_id)


def list_scene_states(session_id):
    p = os.path.join(SCENE_DIR, session_id, "states.jsonl")
    if not os.path.exists(p):
        return []
    states = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                states.append(json.loads(line))
    return states


def get_scene_control_summary(session_id):
    states = list_scene_states(session_id)
    if not states:
        latest = get_latest_scene_state(session_id)
        states = [latest] if latest and "error" not in latest else []
    if not states:
        return {"session_id": session_id, "n_scene_states": 0, "scene_trend": {}, **SAFETY}

    first = states[0]["scene_parameters"]
    last = states[-1]["scene_parameters"]
    return {
        "session_id": session_id, "n_scene_states": len(states),
        "latest_template_id": states[-1].get("template_id", ""),
        "latest_phase": states[-1].get("phase", ""),
        "latest_iqi_proxy": states[-1].get("derived_from", {}).get("iqi_proxy"),
        "latest_pid_proxy": states[-1].get("derived_from", {}).get("pid_proxy"),
        "scene_trend": {
            "clarity_delta": round(last["clarity"] - first["clarity"], 3),
            "fog_delta": round(last["fog"] - first["fog"], 3),
            "stability_delta": round(last["stability_anchor"] - first["stability_anchor"], 3),
            "detail_delta": round(last["detail_density"] - first["detail_density"], 3),
        },
        "interpretation": _scene_trend_text(last, first),
        "visualization_boundary": VIZ_BOUNDARY, **SAFETY,
    }


def _scene_trend_text(last, first):
    parts = []
    if last["clarity"] > first["clarity"] + 0.1:
        parts.append("Scene became clearer.")
    if last["fog"] < first["fog"] - 0.1:
        parts.append("Fog decreased.")
    if last["stability_anchor"] > first["stability_anchor"] + 0.1:
        parts.append("Stability improved.")
    if not parts:
        parts.append("Scene parameters remained relatively stable.")
    return " ".join(parts)


# ─── ADAPTIVE SCENE CONTROLLER ──────────────────────────────────

def update_scene_from_guided_session(session_id):
    from app.core.imagery.guided_session_runtime import get_guided_session
    s = get_guided_session(session_id)
    if not s or s.get("status") not in ("active", "paused"):
        return {"error": "session_not_active", **SAFETY}
    return build_scene_state(session_id)


def update_scene_after_checkin(session_id, checkin_result):
    feedback = checkin_result.get("feedback") if isinstance(checkin_result, dict) else None
    checkin = (checkin_result.get("session", {}).get("micro_checkins", [{}])[-1]
               if isinstance(checkin_result, dict) else None)
    return build_scene_state(session_id, feedback, checkin)


# ─── SESSION REPLAY ENGINE ──────────────────────────────────────

def build_guided_session_replay(session_id):
    from app.core.imagery.guided_session_runtime import get_guided_session
    s = get_guided_session(session_id)
    if not s:
        return {"error": "session_not_found", **SAFETY}

    states = list_scene_states(session_id)
    if not states:
        latest = get_latest_scene_state(session_id)
        states = [latest] if latest and "error" not in latest else []

    frames = []
    for i, st in enumerate(states):
        params = st.get("scene_parameters", {})
        px = st.get("derived_from", {})
        caption = ""
        if params.get("clarity", 0.5) > 0.7 and params.get("fog", 0.5) < 0.3:
            caption = "Scene became clearer and easier to hold."
        elif params.get("fog", 0.5) > 0.7 and px.get("pid_proxy", 0.5) > 0.5:
            caption = "Scene was harder to stabilize here."
        elif px.get("fatigue_risk") == "high":
            caption = "Fatigue increased; session should slow down."
        elif px.get("safety_state") in ("stop", "pause"):
            caption = f"Safety {px.get('safety_state')} event."
        else:
            caption = f"Phase: {st.get('phase', '')}, IQI={px.get('iqi_proxy', 0.5):.2f}"
        frames.append({
            "frame_index": i, "timestamp": st.get("timestamp", ""),
            "phase": st.get("phase", ""), "scene_parameters": params,
            "iqi_proxy": px.get("iqi_proxy"), "pid_proxy": px.get("pid_proxy"),
            "safety_state": px.get("safety_state"), "caption": caption,
        })

    first_p = frames[0]["scene_parameters"] if frames else {}
    last_p = frames[-1]["scene_parameters"] if frames else {}
    best_phase = ""
    hardest_phase = ""
    safety_events = []
    if frames:
        best_idx = max(range(len(frames)), key=lambda i: frames[i]["scene_parameters"].get("clarity", 0))
        hardest_idx = min(range(len(frames)), key=lambda i: frames[i]["scene_parameters"].get("clarity", 0))
        best_phase = frames[best_idx].get("phase", "")
        hardest_phase = frames[hardest_idx].get("phase", "")
        safety_events = [f for f in frames if f["safety_state"] in ("stop", "pause")]

    replay = {
        "replay_id": str(uuid4()), "session_id": session_id,
        "task_id": s.get("task_id", ""), "template_id": states[-1].get("template_id", "") if states else "",
        "duration_estimate_seconds": s.get("task_metadata", {}).get("duration_seconds", 60) if s else 60,
        "n_frames": len(frames), "frames": frames,
        "summary": {
            "clarity_change": round(last_p.get("clarity", 0) - first_p.get("clarity", 0), 3) if frames else 0,
            "fog_change": round(last_p.get("fog", 0) - first_p.get("fog", 0), 3) if frames else 0,
            "stability_change": round(last_p.get("stability_anchor", 0) - first_p.get("stability_anchor", 0), 3) if frames else 0,
            "detail_change": round(last_p.get("detail_density", 0) - first_p.get("detail_density", 0), 3) if frames else 0,
            "best_phase": best_phase, "hardest_phase": hardest_phase,
            "safety_events": [{"frame": f["frame_index"], "phase": f["phase"], "state": f["safety_state"]}
                              for f in safety_events],
        },
        "visualization_boundary": VIZ_BOUNDARY, **SAFETY,
    }

    d = os.path.join(REPLAY_DIR, session_id)
    os.makedirs(d, exist_ok=True)
    _save_json(os.path.join(d, "replay.json"), replay)
    _save_json(os.path.join(d, "replay_summary.md"), _replay_md(replay))
    return replay


def _replay_md(replay):
    sm = replay.get("summary", {})
    return f"""# Session Replay

**Frames**: {replay.get('n_frames', 0)}

## Scene Changes
- Clarity: {sm.get('clarity_change', 0):+.3f}
- Fog: {sm.get('fog_change', 0):+.3f}
- Stability: {sm.get('stability_change', 0):+.3f}
- Detail: {sm.get('detail_change', 0):+.3f}

## Phases
- Best visual phase: {sm.get('best_phase', '')}
- Hardest visual phase: {sm.get('hardest_phase', '')}

{VIZ_BOUNDARY}
"""


def get_guided_session_replay(session_id):
    p = os.path.join(REPLAY_DIR, session_id, "replay.json")
    return _load_json(p)


def export_guided_session_replay_summary(session_id):
    replay = get_guided_session_replay(session_id)
    if not replay:
        return build_guided_session_replay(session_id).get("summary", {})
    return replay.get("summary", {})
