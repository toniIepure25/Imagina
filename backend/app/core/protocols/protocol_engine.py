"""IMAGINA V10 — Protocol Model + Templates + Runner + Analytics + API.

Structured N-of-1 experiment protocols for mental imagery training.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina")
PROTOCOLS_DIR = os.path.join(BASE, "protocols")
RUNS_DIR = os.path.join(BASE, "protocol_runs")

# ─── TEMPLATES ────────────────────────────────────────────────

PROTOCOL_TEMPLATES = [
    {"id": "baseline_3_session", "name": "Baseline (3 Sessions)",
     "description": "3 sessions of simple shape/color tasks to estimate starting IQI/PID.",
     "protocol_type": "baseline", "duration_days": 3, "sessions_per_day": 1,
     "steps_per_session": 6,
     "task_sequence": [
         {"day": 1, "task_id": "shape_stabilization", "difficulty": 1},
         {"day": 2, "task_id": "color_stabilization", "difficulty": 1},
         {"day": 3, "task_id": "brightness_contrast", "difficulty": 2},
     ],
     "metrics": ["iqi", "pid", "fatigue", "attention"],
     "success_criteria": {"min_sessions_completed": 3},
    },
    {"id": "stabilization_7_day", "name": "Stabilization Training (7 Days)",
     "description": "Progresses from simple shapes to scene maintenance. Target: reduce imagery drift.",
     "protocol_type": "stabilization", "duration_days": 7, "sessions_per_day": 1,
     "steps_per_session": 8,
     "task_sequence": [
         {"day": 1, "task_id": "shape_stabilization", "difficulty": 1},
         {"day": 2, "task_id": "spatial_position", "difficulty": 3},
         {"day": 3, "task_id": "object_detail", "difficulty": 3},
         {"day": 4, "task_id": "scene_construction", "difficulty": 4},
         {"day": 5, "task_id": "perspective_viewpoint", "difficulty": 4},
         {"day": 6, "task_id": "multisensory_scene", "difficulty": 5},
         {"day": 7, "task_id": "stable_return", "difficulty": 6},
     ],
     "metrics": ["iqi", "pid", "fatigue", "stability", "vividness"],
     "success_criteria": {"min_iqi_improvement": 0.03, "max_fatigue_increase": 0.15},
    },
    {"id": "vividness_7_day", "name": "Vividness Training (7 Days)",
     "description": "Gradually increases complexity to test if vividness improves.",
     "protocol_type": "vividness_training", "duration_days": 7,
     "steps_per_session": 8,
     "task_sequence": [
         {"day": 1, "task_id": "shape_stabilization", "difficulty": 1},
         {"day": 2, "task_id": "color_stabilization", "difficulty": 1},
         {"day": 3, "task_id": "brightness_contrast", "difficulty": 2},
         {"day": 4, "task_id": "motion", "difficulty": 2},
         {"day": 5, "task_id": "object_detail", "difficulty": 3},
         {"day": 6, "task_id": "scene_construction", "difficulty": 4},
         {"day": 7, "task_id": "symbolic_scene", "difficulty": 6},
     ],
     "metrics": ["iqi", "pid", "fatigue", "vividness"],
     "success_criteria": {"min_iqi_improvement": 0.05},
    },
    {"id": "fatigue_threshold_test", "name": "Fatigue Threshold Test",
     "description": "Repeated low-complexity steps to find your fatigue limit.",
     "protocol_type": "fatigue_test", "duration_days": 1,
     "steps_per_session": 15,
     "task_sequence": [
         {"day": 1, "task_id": "shape_stabilization", "difficulty": 1},
     ],
     "metrics": ["fatigue", "iqi", "attention"],
     "success_criteria": {"fatigue_threshold_found": True},
    },
    {"id": "prompt_style_ab", "name": "Prompt Style A/B",
     "description": "Compare minimal vs. vivid narrative prompts.",
     "protocol_type": "ab_test", "duration_days": 2,
     "steps_per_session": 6,
     "task_sequence": [
         {"day": 1, "task_id": "scene_construction", "difficulty": 4, "condition": "A"},
         {"day": 2, "task_id": "scene_construction", "difficulty": 4, "condition": "B"},
     ],
     "conditions": {"A": {"prompt_style": "minimal"}, "B": {"prompt_style": "vivid"}},
     "metrics": ["iqi", "pid", "vividness", "stability"],
     "success_criteria": {"min_effect_size": 0.2},
    },
]

# ─── MODEL ─────────────────────────────────────────────────────

def create_protocol(template_name: str, user_id: str) -> dict:
    template = next((t for t in PROTOCOL_TEMPLATES if t["id"] == template_name), None)
    if not template:
        return {}
    proto = dict(template)
    proto["protocol_id"] = str(uuid4())
    proto["user_id"] = user_id
    proto["created_at"] = datetime.now(timezone.utc).isoformat()
    proto["version"] = "1.0"
    proto["scientific_boundary"] = (
        "Experimental self-training protocol. Not therapy, diagnosis, or clinical treatment.")
    _save_protocol(user_id, proto)
    return proto


def _save_protocol(user_id: str, protocol: dict):
    d = os.path.join(PROTOCOLS_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{protocol['protocol_id']}.json"), "w") as f:
        json.dump(protocol, f, indent=2, default=str)


def load_protocol(protocol_id: str, user_id: str = "default") -> dict | None:
    p = os.path.join(PROTOCOLS_DIR, user_id, f"{protocol_id}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def list_protocols(user_id: str = "default") -> list[dict]:
    d = os.path.join(PROTOCOLS_DIR, user_id)
    if not os.path.exists(d):
        return []
    return [json.load(open(os.path.join(d, f))) for f in os.listdir(d) if f.endswith(".json")]


# ─── RUNNER ─────────────────────────────────────────────────────

def start_protocol_run(user_id: str, protocol_id: str) -> dict:
    protocol = load_protocol(protocol_id, user_id)
    if not protocol:
        return {}
    run = {
        "run_id": str(uuid4()),
        "protocol_id": protocol_id,
        "user_id": user_id,
        "status": "active",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "session_ids": [],
        "completed_steps": [],
        "current_step_index": 0,
        "protocol_name": protocol.get("name", ""),
        "task_sequence": protocol.get("task_sequence", []),
        "summary": {},
    }
    _save_run(user_id, run)
    return run


def _save_run(user_id: str, run: dict):
    d = os.path.join(RUNS_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{run['run_id']}.json"), "w") as f:
        json.dump(run, f, indent=2, default=str)


def get_protocol_run(run_id: str, user_id: str = "default") -> dict | None:
    p = os.path.join(RUNS_DIR, user_id, f"{run_id}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def list_protocol_runs(user_id: str = "default") -> list[dict]:
    d = os.path.join(RUNS_DIR, user_id)
    if not os.path.exists(d):
        return []
    return [json.load(open(os.path.join(d, f))) for f in os.listdir(d) if f.endswith(".json")]


def attach_session_to_run(run_id: str, session_id: str, user_id: str = "default") -> dict:
    run = get_protocol_run(run_id, user_id)
    if not run:
        return {}
    run["session_ids"].append(session_id)
    idx = run["current_step_index"]
    if idx < len(run["task_sequence"]):
        step = run["task_sequence"][idx]
        run["completed_steps"].append({
            "day": step["day"], "task_id": step["task_id"], "session_id": session_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        run["current_step_index"] = idx + 1
    _save_run(user_id, run)
    return run


def get_next_step(run_id: str, user_id: str = "default") -> dict | None:
    run = get_protocol_run(run_id, user_id)
    if not run:
        return None
    seq = run.get("task_sequence", [])
    idx = run.get("current_step_index", 0)
    return seq[idx] if idx < len(seq) else None


def complete_protocol_run(run_id: str, user_id: str = "default") -> dict:
    run = get_protocol_run(run_id, user_id)
    if not run:
        return {}
    run["status"] = "completed"
    run["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save_run(user_id, run)
    return run


# ─── ANALYTICS ──────────────────────────────────────────────────

def analyze_protocol_run(run_id: str, user_id: str = "default") -> dict:
    run = get_protocol_run(run_id, user_id)
    if not run:
        return {"error": "run_not_found"}
    session_ids = run.get("session_ids", [])
    if len(session_ids) < 2:
        return {"run_id": run_id, "status": "insufficient_data", "confidence": "low",
                "n_sessions": len(session_ids),
                "message": "Need at least 2 attached sessions for analysis."}

    from app.core.analytics.session_analytics import analyze_session

    analyses = []
    iqi_vals_all, pid_vals_all = [], []
    for sid in session_ids:
        try:
            a = analyze_session(sid)
        except Exception:
            continue
        if a and a.get("n_steps", 0) > 0:
            analyses.append(a)
            iqi_vals_all.append(a.get("mean_iqi", 0.5))
            pid_vals_all.append(a.get("mean_pid", 0.5))

    n = len(analyses)
    if n < 2:
        return {"run_id": run_id, "status": "insufficient_data", "confidence": "low"}

    # Pre/post: first vs last session
    first = analyses[0]
    last = analyses[-1]
    pre_post = {
        "iqi_delta": round(last["mean_iqi"] - first["mean_iqi"], 4),
        "pid_delta": round(last["mean_pid"] - first["mean_pid"], 4),
        "first_iqi": first["mean_iqi"], "last_iqi": last["mean_iqi"],
    }

    # Stability: mean of fold scores variation
    def _slope(vals):
        if len(vals) < 2:
            return 0.0
        nv = len(vals)
        xm = (nv - 1) / 2.0
        ym = sum(vals) / nv
        num = sum((i - xm) * (v - ym) for i, v in enumerate(vals))
        den = sum((i - xm) ** 2 for i in range(nv))
        return round(num / max(den, 1e-10), 4)

    iqi_slope = _slope(iqi_vals_all)
    pid_slope = _slope(pid_vals_all)

    success = pre_post["iqi_delta"] > 0.02 and iqi_slope > 0.001
    confidence = "high" if n >= 5 else "medium" if n >= 3 else "low"

    result = {
        "run_id": run_id, "protocol_id": run["protocol_id"],
        "n_sessions": n, "n_steps_total": sum(a["n_steps"] for a in analyses),
        "pre_post": pre_post,
        "iqi_slope": iqi_slope, "pid_slope": pid_slope,
        "stability_score": round(1.0 - abs(iqi_slope) * 5, 4) if abs(iqi_slope) < 0.2 else 0.5,
        "confidence": confidence,
        "success": success,
        "interpretation": (
            f"IQI {'improved' if pre_post['iqi_delta'] > 0 else 'did not improve'} "
            f"({pre_post['iqi_delta']:+.4f}) over {n} sessions. "
            f"{'Promising' if success else 'Inconclusive'} result. "
            f"Confidence: {confidence}."
        ),
        "disclaimer": "Experimental self-training analysis. Not clinical or validated evidence.",
    }
    _save_report(run_id, result)
    return result


def _save_report(run_id: str, analysis: dict):
    d = os.path.join(BASE, "reports")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{run_id}.json"), "w") as f:
        json.dump(analysis, f, indent=2, default=str)
