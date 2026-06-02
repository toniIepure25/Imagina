"""IMAGINA V17 — N-of-1 Experiment Designer.

Generates controlled personal experiments comparing two mental imagery
training plans under structured N-of-1 designs.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina")
EXPERIMENT_DIR = os.path.join(BASE, "n_of_1_experiments")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

DESIGN_STRENGTHS = {"AB": 6, "BA": 6, "ABAB": 12, "randomized_blocks": 15, "dose_response": 10}

INCLUSION_CRITERIA = [
    "At least 2 completed PID v2 calibration sessions",
    "At least 1 generated optimized adaptive plan",
    "At least 1 baseline adaptive plan (V14 or optimized)",
    "Average fatigue < 8/10",
]

EXCLUSION_CRITERIA = [
    "Average fatigue > 8/10",
    "Missing checkpoint calibrations in prior executions",
    "Average adherence < 0.4 in prior executions",
]

FORBIDDEN_CLAIMS = [
    "This is not a clinical trial.",
    "This is not diagnostic or therapeutic.",
    "This is not brain-computer interface (BCI) validation.",
    "This is not mind-reading or dream decoding.",
    "Results are personal exploratory observations only.",
]


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _get_baseline_plan(user_id):
    from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
    return load_latest_adaptive_training_plan(user_id)


def _get_optimized_plan(user_id):
    from app.core.adaptive.next_plan_optimizer import load_latest_optimized_plan
    p = load_latest_optimized_plan(user_id)
    if not p:
        from app.core.adaptive.next_plan_optimizer import generate_optimized_adaptive_plan
        p = generate_optimized_adaptive_plan(user_id)
    return p


def _check_eligibility(user_id):
    from app.core.adaptive.adaptive_execution_analytics import analyze_all_executions
    from app.core.calibration.pid_v2_calibration import list_calibration_sessions

    sessions = [s for s in list_calibration_sessions(user_id) if s.get("status") == "completed"]
    if len(sessions) < 2:
        return False, "Need at least 2 completed calibration sessions."

    baseline = _get_baseline_plan(user_id)
    if not baseline:
        return False, "No baseline adaptive plan found. Generate one first."

    optimized = _get_optimized_plan(user_id)
    if not optimized:
        return False, "No optimized plan found. Generate one first."

    exec_analysis = analyze_all_executions(user_id)
    if exec_analysis.get("n_completed", 0) >= 1:
        avg_fatigue = exec_analysis.get("average_fatigue", 0)
        avg_adh = exec_analysis.get("average_adherence", 0)
        if avg_fatigue > 8:
            return False, f"Average fatigue ({avg_fatigue:.1f}) too high."
        if avg_adh < 0.4:
            return False, f"Average adherence ({avg_adh:.0%}) too low."

    return True, "eligible"


def design_n_of_1_experiment(user_id="default", experiment_type="baseline_vs_optimized",
                              design="AB", duration_days=14) -> dict:
    eligible, reason = _check_eligibility(user_id)
    if not eligible:
        return {"error": "not_eligible", "reason": reason, **SAFETY}

    baseline = _get_baseline_plan(user_id)
    optimized = _get_optimized_plan(user_id)

    blocks = _build_blocks(design, duration_days, baseline, optimized)

    experiment_id = str(uuid4())
    experiment = {
        "experiment_id": experiment_id,
        "user_id": user_id,
        "designed_at": datetime.now(timezone.utc).isoformat(),
        "design_type": design,
        "experiment_type": experiment_type,
        "hypothesis": ("The optimized plan will result in a greater PID v2 decrease "
                       "compared with the baseline plan."),
        "primary_metric": "pid_v2_change",
        "secondary_metrics": ["adherence_rate", "fatigue_rating", "clarity_rating",
                               "focus_quality", "confidence_rating"],
        "inclusion_criteria": INCLUSION_CRITERIA,
        "exclusion_criteria": EXCLUSION_CRITERIA,
        "baseline_plan": {
            "plan_id": baseline.get("adaptive_plan_id", ""),
            "title": baseline.get("plan_title", ""),
            "focus": baseline.get("training_focus", ""),
        },
        "optimized_plan": {
            "plan_id": optimized.get("adaptive_plan_id", ""),
            "title": optimized.get("plan_title", ""),
            "focus": optimized.get("training_focus", ""),
        },
        "blocks": blocks,
        "days": _flatten_blocks_to_days(blocks),
        "checkpoint_schedule": _checkpoint_schedule(blocks),
        "design_strength_score": DESIGN_STRENGTHS.get(design, 6),
        "expected_interpretation_limits": [
            "Personal exploratory observation, not causal proof.",
            "Not a randomized controlled trial (RCT).",
            "Results may reflect practice effects, fatigue, or context.",
            "Cannot be generalized to other users.",
        ],
        "status": "designed",
        **SAFETY,
    }

    _save_manifest(user_id, experiment_id, experiment)
    _save_latest(user_id, experiment)
    return experiment


def _build_blocks(design, duration_days, baseline, optimized):
    block_days = max(2, duration_days // 2) if design in ("AB", "BA") else max(3, duration_days // 4)

    def make_block(block_id, condition, plan, num_days, calib_task_id):
        daily_exercises = plan.get("daily_plan", [])
        ex_list = daily_exercises[:num_days]
        while len(ex_list) < num_days:
            ex_list.append(ex_list[0] if ex_list else {"title": "Focus Practice", "duration_minutes": 10})
        return {
            "block_id": block_id,
            "condition": condition,
            "plan_title": plan.get("plan_title", ""),
            "calibration_task_id": calib_task_id,
            "days": [
                {
                    "day_in_block": i + 1,
                    "condition": condition,
                    "exercise": {
                        "title": ex_list[i].get("title", ""),
                        "duration_minutes": ex_list[i].get("duration_minutes", 10),
                    },
                    "requires_calibration": i == 0,
                }
                for i in range(num_days)
            ],
        }

    calib_task = baseline.get("daily_plan", [{}])[0].get("calibration_task_id",
        "simple_red_circle_reference") if baseline.get("daily_plan") else "simple_red_circle_reference"

    if design == "AB":
        return [
            make_block(1, "baseline", baseline, block_days, calib_task),
            make_block(2, "optimized", optimized, block_days, calib_task),
        ]
    elif design == "BA":
        return [
            make_block(1, "optimized", optimized, block_days, calib_task),
            make_block(2, "baseline", baseline, block_days, calib_task),
        ]
    elif design == "ABAB":
        return [
            make_block(1, "baseline", baseline, block_days, calib_task),
            make_block(2, "optimized", optimized, block_days, calib_task),
            make_block(3, "baseline", baseline, block_days, calib_task),
            make_block(4, "optimized", optimized, block_days, calib_task),
        ]
    elif design == "randomized_blocks":
        import random
        pairs = [
            ("baseline", baseline), ("optimized", optimized),
            ("optimized", optimized), ("baseline", baseline),
        ]
        random.shuffle(pairs)
        return [
            make_block(i + 1, c, p, block_days, calib_task)
            for i, (c, p) in enumerate(pairs)
        ]
    elif design == "dose_response":
        return [
            make_block(1, "low_intensity", baseline, block_days, calib_task),
            make_block(2, "normal_intensity", optimized, block_days, calib_task),
            make_block(3, "high_intensity", optimized, block_days, calib_task),
        ]
    else:
        return _build_blocks("AB", duration_days, baseline, optimized)


def _flatten_blocks_to_days(blocks):
    days = []
    day_num = 1
    for block in blocks:
        for d in block["days"]:
            days.append({
                "day": day_num,
                "block_id": block["block_id"],
                "condition": d["condition"],
                "exercise": d["exercise"],
                "requires_calibration": d.get("requires_calibration", False),
                "calibration_task_id": block.get("calibration_task_id"),
                "status": "pending",
                "checkin": None,
                "calibration_session_id": None,
                "checkpoint_pid": None,
            })
            day_num += 1
    return days


def _checkpoint_schedule(blocks):
    schedule = []
    day_num = 1
    for block in blocks:
        schedule.append({
            "block_id": block["block_id"],
            "condition": block["condition"],
            "day": day_num,
            "type": "block_start_calibration",
            "task_id": block.get("calibration_task_id", ""),
        })
        day_num += len(block["days"])
    schedule.append({
        "block_id": "final",
        "day": day_num,
        "type": "final_calibration",
        "task_id": blocks[-1].get("calibration_task_id", "") if blocks else "",
    })
    return schedule


def _save_manifest(user_id, experiment_id, data):
    d = os.path.join(EXPERIMENT_DIR, user_id, experiment_id)
    _save_json(os.path.join(d, "manifest.json"), data)


def _save_latest(user_id, data):
    d = os.path.join(EXPERIMENT_DIR, user_id)
    _save_json(os.path.join(d, "latest_experiment.json"), data)


def get_n_of_1_experiment(user_id, experiment_id):
    p = os.path.join(EXPERIMENT_DIR, user_id, experiment_id, "manifest.json")
    return _load_json(p)


def get_latest_n_of_1_experiment(user_id="default"):
    p = os.path.join(EXPERIMENT_DIR, user_id, "latest_experiment.json")
    return _load_json(p)


def list_n_of_1_experiments(user_id="default"):
    d = os.path.join(EXPERIMENT_DIR, user_id)
    if not os.path.isdir(d):
        return []
    results = []
    for eid in os.listdir(d):
        mp = os.path.join(d, eid, "manifest.json")
        m = _load_json(mp)
        if m:
            results.append(m)
    return sorted(results, key=lambda x: x.get("designed_at", ""), reverse=True)
