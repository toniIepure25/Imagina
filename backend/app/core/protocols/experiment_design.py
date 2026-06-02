"""IMAGINA V11 — Experiment Designer + Protocol Studio.

Custom experiment design, validation, compilation, and templates.
Builds on V10 protocol engine.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
DESIGNS_DIR = os.path.join(BASE, "experiment_designs")

FORBIDDEN_TERMS = ["mind-reading", "therapy", "clinical", "diagnosis", "dream decoding",
                   "cure", "BCI-ready", "production BCI", "decode thoughts",
                   "read mind", "consciousness measurement"]


# ─── DESIGN TEMPLATES ──────────────────────────────────────────

DESIGN_TEMPLATES = [
    {"id": "prompt_vividness_ab", "name": "Prompt Vividness A/B",
     "hypothesis": "Vivid narrative prompts improve imagery vividness compared to minimal prompts.",
     "design_type": "ab_test",
     "independent_variable": "prompt_style",
     "dependent_metrics": ["iqi", "vividness", "stability"],
     "conditions": {"A": {"prompt_style": "minimal"}, "B": {"prompt_style": "vivid"}},
     "sessions": [
         {"session_index": 1, "condition": "A", "task_id": "scene_construction", "difficulty": 4},
         {"session_index": 2, "condition": "B", "task_id": "scene_construction", "difficulty": 4},
         {"session_index": 3, "condition": "A", "task_id": "scene_construction", "difficulty": 4},
         {"session_index": 4, "condition": "B", "task_id": "scene_construction", "difficulty": 4},
     ],
     "planned_n_sessions": 4},
    {"id": "feedback_intensity_ab", "name": "Feedback Intensity A/B",
     "hypothesis": "Subtle visual feedback improves stability with less fatigue than strong feedback.",
     "design_type": "ab_test",
     "independent_variable": "feedback_intensity",
     "dependent_metrics": ["iqi", "pid", "fatigue", "stability"],
     "conditions": {"A": {"feedback_mode": "calm"}, "B": {"feedback_mode": "strong"}},
     "sessions": [
         {"session_index": 1, "condition": "A", "task_id": "object_detail", "difficulty": 3},
         {"session_index": 2, "condition": "B", "task_id": "object_detail", "difficulty": 3},
         {"session_index": 3, "condition": "A", "task_id": "object_detail", "difficulty": 3},
         {"session_index": 4, "condition": "B", "task_id": "object_detail", "difficulty": 3},
     ],
     "planned_n_sessions": 4},
    {"id": "baseline_intervention_stabilization", "name": "Baseline + Stabilization",
     "hypothesis": "Daily stabilization practice improves IQI over baseline.",
     "design_type": "baseline_intervention",
     "independent_variable": "phase",
     "dependent_metrics": ["iqi", "pid", "stability"],
     "conditions": {"baseline": {"phase": "baseline"}, "intervention": {"phase": "treatment"}},
     "sessions": [
         {"session_index": 1, "condition": "baseline", "task_id": "shape_stabilization", "difficulty": 1},
         {"session_index": 2, "condition": "baseline", "task_id": "color_stabilization", "difficulty": 1},
         {"session_index": 3, "condition": "intervention", "task_id": "spatial_position", "difficulty": 3},
         {"session_index": 4, "condition": "intervention", "task_id": "object_detail", "difficulty": 3},
         {"session_index": 5, "condition": "intervention", "task_id": "scene_construction", "difficulty": 4},
         {"session_index": 6, "condition": "intervention", "task_id": "stable_return", "difficulty": 6},
     ],
     "planned_n_sessions": 6},
    {"id": "fatigue_mapping", "name": "Fatigue Mapping",
     "hypothesis": "IQI decreases and fatigue rises after a personal threshold number of steps.",
     "design_type": "fatigue_mapping",
     "independent_variable": "steps",
     "dependent_metrics": ["fatigue", "iqi", "attention"],
     "sessions": [
         {"session_index": 1, "condition": "single", "task_id": "shape_stabilization", "difficulty": 1},
     ],
     "planned_n_sessions": 1},
    {"id": "complexity_progression", "name": "Complexity Progression",
     "hypothesis": "Gradual complexity progression improves stability compared to jumping.",
     "design_type": "progression",
     "independent_variable": "difficulty",
     "dependent_metrics": ["iqi", "stability", "fatigue"],
     "sessions": [
         {"session_index": 1, "condition": "gradual", "task_id": "shape_stabilization", "difficulty": 1},
         {"session_index": 2, "condition": "gradual", "task_id": "color_stabilization", "difficulty": 1},
         {"session_index": 3, "condition": "gradual", "task_id": "brightness_contrast", "difficulty": 2},
         {"session_index": 4, "condition": "gradual", "task_id": "motion", "difficulty": 2},
         {"session_index": 5, "condition": "gradual", "task_id": "object_detail", "difficulty": 3},
         {"session_index": 6, "condition": "gradual", "task_id": "scene_construction", "difficulty": 4},
     ],
     "planned_n_sessions": 6},
]


# ─── DESIGN CRUD ────────────────────────────────────────────────

def create_experiment_design(user_id: str, template_id: str = None, payload: dict = None) -> dict:
    if template_id:
        template = next((t for t in DESIGN_TEMPLATES if t["id"] == template_id), None)
        if not template:
            return {}
        design = dict(template)
    elif payload:
        design = payload
    else:
        return {}
    design["design_id"] = str(uuid4())
    design["user_id"] = user_id
    design["created_at"] = datetime.now(timezone.utc).isoformat()
    design["scientific_boundary"] = ("Experimental self-training design. "
                                      "Not therapy, diagnosis, or clinical treatment.")
    if "name" not in design:
        design["name"] = design.get("hypothesis", "Custom Design")[:60]
    _save_design(user_id, design)
    return design


def _save_design(user_id: str, design: dict):
    d = os.path.join(DESIGNS_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{design['design_id']}.json"), "w") as f:
        json.dump(design, f, indent=2, default=str)


def load_design(user_id: str, design_id: str) -> dict | None:
    p = os.path.join(DESIGNS_DIR, user_id, f"{design_id}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def list_designs(user_id: str = "default") -> list[dict]:
    d = os.path.join(DESIGNS_DIR, user_id)
    if not os.path.exists(d):
        return []
    return [json.load(open(os.path.join(d, f))) for f in os.listdir(d) if f.endswith(".json")]


def delete_design(user_id: str, design_id: str):
    p = os.path.join(DESIGNS_DIR, user_id, f"{design_id}.json")
    if os.path.exists(p):
        os.remove(p)


# ─── VALIDATOR ──────────────────────────────────────────────────

def validate_design(design: dict) -> dict:
    score = 0
    warnings, errors = [], []

    # Hypothesis
    hyp = design.get("hypothesis", "").lower()
    if hyp:
        score += 20
    else:
        errors.append("Missing hypothesis")
    for term in FORBIDDEN_TERMS:
        if term in hyp:
            errors.append(f"Forbidden term in hypothesis: '{term}'")
            score -= 30

    # Sessions
    sessions = design.get("sessions", [])
    n = len(sessions)
    if n >= 6:
        score += 20
    elif n >= 3:
        score += 15
        warnings.append("Few sessions — confidence will be low")
    else:
        errors.append("Need at least 2 sessions")
        score += 5

    # Balanced conditions
    conditions = design.get("conditions", {})
    if len(conditions) >= 2:
        counts = {}
        for s in sessions:
            c = s.get("condition", "unknown")
            counts[c] = counts.get(c, 0) + 1
        vals = list(counts.values())
        if vals and max(vals) - min(vals) > 2:
            warnings.append("Unbalanced conditions — A/B comparison may be unreliable")
            score += 10
        else:
            score += 20
    else:
        score += 15

    # Metrics
    metrics = design.get("dependent_metrics", [])
    if len(metrics) >= 2:
        score += 15
    else:
        warnings.append("Few dependent metrics tracked")

    # Fatigue safety
    high_diff = sum(1 for s in sessions if s.get("difficulty", 1) >= 5)
    if high_diff > n * 0.5:
        warnings.append("Many high-difficulty tasks — fatigue risk")
        score += 5
    else:
        score += 15

    # Scientific boundary
    boundary = design.get("scientific_boundary", "")
    if boundary and any(t in boundary.lower() for t in FORBIDDEN_TERMS):
        errors.append("Scientific boundary contains forbidden claims")
        score -= 20
    elif boundary:
        score += 10
    else:
        score += 5

    valid = len(errors) == 0
    conf = "high" if n >= 6 else "medium" if n >= 3 else "low"

    return {
        "valid": valid,
        "quality_score": max(0, min(100, score)),
        "confidence_level": conf,
        "warnings": warnings,
        "errors": errors,
        "scientific_boundary_ok": len([e for e in errors if "Forbidden term" in e]) == 0,
    }


# ─── COMPILER ───────────────────────────────────────────────────

def compile_design_to_protocol(user_id: str, design_id: str) -> dict:
    design = load_design(user_id, design_id)
    if not design:
        return {}
    validation = validate_design(design)
    protocol = {
        "protocol_id": str(uuid4()),
        "name": design.get("name", "Compiled Design"),
        "description": design.get("hypothesis", ""),
        "protocol_type": design.get("design_type", "custom"),
        "design_id": design_id,
        "duration_days": design.get("planned_n_sessions", 4),
        "steps_per_session": 8,
        "task_sequence": [
            {"day": s["session_index"], "task_id": s["task_id"],
             "difficulty": s["difficulty"],
             "condition": s.get("condition", "single")}
            for s in design.get("sessions", [])
        ],
        "conditions": design.get("conditions", {}),
        "metrics": design.get("dependent_metrics", []),
        "success_criteria": {"min_sessions_completed": design.get("planned_n_sessions", 4)},
        "design_quality": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scientific_boundary": design.get("scientific_boundary", ""),
    }
    # Save as protocol
    from app.core.protocols.protocol_engine import _save_protocol as sp
    sp(user_id, protocol)
    return protocol
