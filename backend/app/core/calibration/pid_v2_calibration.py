"""IMAGINA V13 — Perception Reference Calibration + PID v2.

Reference task templates, calibration session model, PID v2 metric.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
CALIB_DIR = os.path.join(BASE, "calibration_sessions")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory perception-imagination calibration only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

# ─── REFERENCE TASKS ────────────────────────────────────────────

REFERENCE_TASKS = [
    {"id": "simple_red_circle_reference", "name": "Simple Red Circle",
     "modality": "visual_text",
     "reference_prompt": "Look at this description: a bright red circle, smooth edges, centered in your visual field.",
     "perception_phase": "Take 60 seconds to build a clear mental model of the red circle as described.",
     "imagery_phase": "Close your eyes. Reconstruct the red circle from memory. Hold it as clearly as possible for 90 seconds.",
     "target_dimensions": ["color", "shape", "spatial_position"],
     "self_report_questions": ["clarity", "detail", "color_strength", "spatial_stability"],
     "difficulty_level": 1,
    },
    {"id": "blue_square_position_reference", "name": "Blue Square Position",
     "modality": "visual_text",
     "reference_prompt": "Visualize a dark blue square positioned slightly to the upper-left of center.",
     "perception_phase": "Study the description. Note the exact color shade and spatial position for 60 seconds.",
     "imagery_phase": "Close your eyes and reconstruct the blue square in the exact described position. Hold for 90 seconds.",
     "target_dimensions": ["color", "shape", "spatial_position"],
     "self_report_questions": ["clarity", "color_strength", "spatial_stability"],
     "difficulty_level": 1,
    },
    {"id": "textured_object_reference", "name": "Textured Object",
     "modality": "visual_text",
     "reference_prompt": "Imagine a rough-textured wooden sphere, about the size of an orange, with visible grain patterns.",
     "perception_phase": "Study the texture and shape description for 60 seconds.",
     "imagery_phase": "Reconstruct the textured wooden sphere mentally. Focus on the grain pattern. Hold for 120s.",
     "target_dimensions": ["shape", "texture", "detail"],
     "self_report_questions": ["clarity", "detail", "spatial_stability"],
     "difficulty_level": 2,
    },
    {"id": "rotating_shape_reference", "name": "Rotating Shape",
     "modality": "visual_text",
     "reference_prompt": "A silver geometric pyramid slowly rotating clockwise at a steady pace.",
     "perception_phase": "Build a mental model of the pyramid's shape and rotation for 60 seconds.",
     "imagery_phase": "Close your eyes. Visualize the rotating pyramid. Maintain smooth motion for 120s.",
     "target_dimensions": ["shape", "motion", "spatial_position"],
     "self_report_questions": ["clarity", "detail", "spatial_stability"],
     "difficulty_level": 2,
    },
    {"id": "small_scene_reference", "name": "Small Scene",
     "modality": "visual_text",
     "reference_prompt": "A wooden bench under a tree, with dappled sunlight filtering through leaves above.",
     "perception_phase": "Study this small scene for 90 seconds. Note the elements and their relationships.",
     "imagery_phase": "Reconstruct the entire scene mentally. Hold the bench, tree, and lighting. 120s.",
     "target_dimensions": ["detail", "spatial_position", "brightness"],
     "self_report_questions": ["clarity", "detail", "spatial_stability", "color_strength"],
     "difficulty_level": 3,
    },
    {"id": "multisensory_beach_reference", "name": "Multisensory Beach",
     "modality": "multisensory_text",
     "reference_prompt": "A beach at sunset: orange-pink sky, gentle waves sound, warm sand feeling underfoot.",
     "perception_phase": "Build the multisensory model: visual colors, auditory waves, tactile warmth. 90s.",
     "imagery_phase": "Reconstruct the beach scene with all sensory dimensions. Hold for 120s.",
     "target_dimensions": ["color", "detail", "multisensory_features"],
     "self_report_questions": ["clarity", "detail", "color_strength", "spatial_stability"],
     "difficulty_level": 4,
    },
    {"id": "memory_room_reference", "name": "Memory Room",
     "modality": "memory_like",
     "reference_prompt": "Recall a familiar room from your past. Focus on the furniture arrangement and lighting.",
     "perception_phase": "Study the memory. Note 3 specific details you can visualize. 90s.",
     "imagery_phase": "Reconstruct the room as vividly as possible from memory. Hold for 120s.",
     "target_dimensions": ["detail", "spatial_position", "emotional_tone"],
     "self_report_questions": ["clarity", "detail", "spatial_stability", "emotional_tone"],
     "difficulty_level": 5,
     "safety_note": "Choose an emotionally neutral room. Stop if memory becomes distressing.",
    },
    {"id": "symbolic_dream_scene_reference", "name": "Symbolic Dream Scene",
     "modality": "visual_text",
     "reference_prompt": "A floating golden orb above a calm purple sea under a starry night sky.",
     "perception_phase": "Build the symbolic scene: the orb, the sea, the stars. Let it feel dream-like. 90s.",
     "imagery_phase": "Reconstruct the dream-like scene. Allow it to feel fluid but recognizable. 150s.",
     "target_dimensions": ["color", "detail", "emotional_tone", "spatial_position"],
     "self_report_questions": ["clarity", "detail", "color_strength", "emotional_tone"],
     "difficulty_level": 6,
    },
]


def list_reference_tasks():
    return REFERENCE_TASKS


def get_reference_task(task_id):
    return next((t for t in REFERENCE_TASKS if t["id"] == task_id), None)


def get_tasks_by_difficulty(level):
    return [t for t in REFERENCE_TASKS if t["difficulty"] == level]


# ─── CALIBRATION SESSION ────────────────────────────────────────

def start_calibration_session(user_id="default", task_id="simple_red_circle_reference"):
    task = get_reference_task(task_id)
    if not task:
        return {"error": "task_not_found"}
    sid = str(uuid4())
    session = {
        "session_id": sid, "user_id": user_id, "task": task,
        "status": "reference_phase", "started_at": datetime.now(timezone.utc).isoformat(),
        "reference_rating": None, "imagery_rating": None, "pid_v2": None,
        **SAFETY,
    }
    _save_calib(sid, session)
    return session


def _save_calib(sid, data):
    d = os.path.join(CALIB_DIR, sid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "manifest.json"), "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_calib(sid):
    p = os.path.join(CALIB_DIR, sid, "manifest.json")
    return json.load(open(p)) if os.path.exists(p) else None


def submit_reference_rating(session_id, payload):
    s = _load_calib(session_id)
    if not s:
        return {"error": "session_not_found"}
    if s["status"] != "reference_phase":
        return {"error": f"Invalid transition from {s['status']}"}
    s["reference_rating"] = payload
    s["status"] = "imagery_phase"
    _save_calib(session_id, s)
    return s


def submit_imagery_rating(session_id, payload):
    s = _load_calib(session_id)
    if not s:
        return {"error": "session_not_found"}
    if s["status"] != "imagery_phase":
        return {"error": f"Invalid transition from {s['status']}"}
    s["imagery_rating"] = payload
    s["status"] = "completed"
    # Compute PID v2
    s["pid_v2"] = compute_pid_v2(s["reference_rating"], payload, s.get("task", {}))
    _save_calib(session_id, s)
    return s


def get_calibration_session(session_id):
    return _load_calib(session_id)


def list_calibration_sessions(user_id="default"):
    sessions = []
    if not os.path.isdir(CALIB_DIR):
        return sessions
    for sid in os.listdir(CALIB_DIR):
        s = _load_calib(sid)
        if s and s.get("user_id") == user_id:
            sessions.append(s)
    return sorted(sessions, key=lambda x: x.get("started_at", ""), reverse=True)


def aggregate_pid_v2_history(user_id="default"):
    sessions = list_calibration_sessions(user_id)
    completed = [s for s in sessions if s.get("status") == "completed" and s.get("pid_v2")]
    if not completed:
        return {"n_sessions": 0, "status": "no_data", **SAFETY}

    pids = [s["pid_v2"]["pid_v2"] for s in completed]
    mean_pid = round(sum(pids) / len(pids), 3)
    best_pid = min(pids)
    worst_pid = max(pids)
    trend = "improving" if len(pids) >= 3 and pids[-1] < pids[0] - 0.01 else (
        "declining" if len(pids) >= 3 and pids[-1] > pids[0] + 0.01 else "stable")

    # Per-dimension gaps from last 5
    dims = {}
    for s in completed[-5:]:
        for k, v in s["pid_v2"].get("subscores", {}).items():
            dims.setdefault(k, []).append(v)
    dim_means = {k: round(sum(vals) / len(vals), 3) for k, vals in dims.items()}
    sorted_dims = sorted(dim_means.items(), key=lambda x: x[1], reverse=True)

    return {
        "user_id": user_id, "n_sessions": len(completed),
        "mean_pid_v2": mean_pid, "best_pid_v2": best_pid, "worst_pid_v2": worst_pid,
        "trend": trend,
        "strongest_dimensions": [k for k, v in sorted_dims[-3:] if v < 0.3],
        "weakest_dimensions": [k for k, v in sorted_dims[:3] if v > 0.2],
        **SAFETY,
    }


# ─── PID v2 ─────────────────────────────────────────────────────

def compute_pid_v2(ref: dict, img: dict, task: dict) -> dict:
    """Compute perception-imagination distance from reference vs imagery ratings."""

    def gap(k, a=None, b=None):
        a_val = a or ref
        b_val = b or img
        return abs(float(a_val.get(k, 5)) - float(b_val.get(k, 5))) / 10.0

    subscores = {
        "clarity_gap": round(gap("clarity"), 3),
        "detail_gap": round(gap("detail"), 3),
        "color_gap": round(gap("color_strength"), 3),
        "spatial_gap": round(gap("spatial_stability"), 3),
        "emotional_gap": round(gap("emotional_tone"), 3),
    }

    # Weighted by task target dimensions
    targets = task.get("target_dimensions", [])
    target_weights = {"color": 0.20, "shape": 0.15, "spatial_position": 0.20,
                      "texture": 0.15, "detail": 0.15, "motion": 0.10,
                      "brightness": 0.10, "emotional_tone": 0.10, "multisensory_features": 0.15}

    weighted = 0
    total_w = 0
    for dim in targets:
        key = {
            "color": "color_gap", "spatial_position": "spatial_gap",
            "detail": "detail_gap", "texture": "detail_gap",
            "shape": "spatial_gap", "motion": "spatial_gap",
            "brightness": "detail_gap", "emotional_tone": "emotional_gap",
            "multisensory_features": "detail_gap",
        }.get(dim, "detail_gap")
        w = target_weights.get(dim, 0.15)
        weighted += subscores.get(key, 0.3) * w
        total_w += w

    pid = round(min(1.0, weighted / max(total_w, 0.01)), 3)

    confidence = float(img.get("confidence", 5)) / 10.0
    fatigue = float(img.get("fatigue", 3)) / 10.0
    reliability = max(0.1, min(1.0, confidence - fatigue * 0.3))

    return {
        "pid_v2": pid,
        "perception_similarity_score": round(1.0 - pid, 3),
        "subscores": subscores,
        "reliability": {"confidence": reliability, "reason": f"Confidence {confidence:.1f}, fatigue {fatigue:.1f}"},
        "interpretation": _pid_interpretation(pid),
        "scientific_boundary": SAFETY["scientific_boundary"],
        **SAFETY,
    }


def _pid_interpretation(pid):
    if pid < 0.2:
        return "Imagined reconstruction is very close to the perceived reference."
    if pid < 0.4:
        return "Imagined reconstruction is close, with minor gaps."
    if pid < 0.6:
        return "Moderate distance between perception and imagination."
    if pid < 0.8:
        return "Significant gap — reconstruction differs notably from reference."
    return "Large perception-imagination gap — reconstruction is very different."
