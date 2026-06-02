"""IMAGINA V18 — Unified Evidence Model.

Collects all personal evidence across calibration, adaptive plans, optimized plans,
executions, N-of-1 experiments, fatigue/adherence, and PID trends into a single model.
"""

from datetime import datetime, timezone

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}

FORBIDDEN_CLAIMS = [
    "No clinical improvement can be claimed from this data.",
    "No diagnosis or therapeutic conclusion is possible.",
    "This is not brain-computer interface (BCI) validation.",
    "No mind-reading or dream decoding was performed.",
    "Results are personal exploratory observations, not generalizable findings.",
    "No causal mechanism has been established or claimed.",
]


def build_unified_evidence_model(user_id="default") -> dict:
    data = _inventory(user_id)

    evidence_status = _compute_status(data)

    pid = _pid_section(user_id)
    training = _training_section(user_id)
    experiments = _experiment_section(user_id)
    limitations = _collect_limitations(data, pid, experiments)

    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_status": evidence_status,
        "data_inventory": data,
        "pid_summary": pid,
        "training_summary": training,
        "experiment_summary": experiments,
        "main_limitations": limitations if limitations else [
            "Not enough data to assess limitations. Continue collecting evidence."],
        "safe_claims": [
            "Local-first exploratory mental imagery training system.",
            "Adaptive plan optimization based on personal check-ins and PID checkpoints.",
            "Controlled personal N-of-1 evidence scoring.",
            "Non-clinical personal experimentation framework.",
        ],
        "forbidden_claims": FORBIDDEN_CLAIMS,
        **SAFETY,
    }


def _inventory(user_id):
    try:
        from app.core.calibration.pid_v2_calibration import list_calibration_sessions
        n_calib = len([s for s in list_calibration_sessions(user_id) if s.get("status") == "completed"])
    except Exception:
        n_calib = 0
    try:
        from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
        has_plan = load_latest_adaptive_training_plan(user_id) is not None
    except Exception:
        has_plan = False
    try:
        from app.core.adaptive.adaptive_plan_execution import list_plan_executions
        execs = list_plan_executions(user_id)
        n_execs = len(execs)
        n_completed = len([e for e in execs if e.get("status") == "completed"])
    except Exception:
        n_execs = 0
        n_completed = 0
    try:
        from app.core.adaptive.next_plan_optimizer import load_latest_optimized_plan
        has_opt = load_latest_optimized_plan(user_id) is not None
    except Exception:
        has_opt = False
    try:
        from app.core.adaptive.n_of_1_experiment_execution import list_n_of_1_experiments
        exps = list_n_of_1_experiments(user_id)
        n_exps = len(exps)
        n_exp_completed = len([e for e in exps if e.get("status") == "completed"])
    except Exception:
        n_exps = 0
        n_exp_completed = 0

    return {
        "n_calibrations": n_calib,
        "n_adaptive_plans": 1 if has_plan else 0,
        "n_executions": n_execs,
        "n_completed_executions": n_completed,
        "n_optimized_plans": 1 if has_opt else 0,
        "n_n_of_1_experiments": n_exps,
        "n_completed_experiments": n_exp_completed,
    }


def _compute_status(data):
    if data.get("n_calibrations", 0) < 3 or data.get("n_completed_executions", 0) < 1:
        return "insufficient"
    if data.get("n_completed_experiments", 0) < 1:
        return "exploratory"
    try:
        from app.core.adaptive.n_of_1_experiment_analysis import compute_n_of_1_evidence_score
        score = compute_n_of_1_evidence_score("default").get("evidence_score", 0)
    except Exception:
        score = 0
    if score >= 70 and data.get("n_completed_experiments", 0) >= 2:
        return "strong_personal"
    if score >= 50:
        return "promising_personal"
    return "exploratory"


def _pid_section(user_id):
    try:
        from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement
        imp = compute_pid_improvement(user_id)
        return {
            "first_pid": imp.get("first_pid"),
            "latest_pid": imp.get("latest_pid"),
            "absolute_change": imp.get("absolute_change"),
            "trend": imp.get("trend", "insufficient"),
        }
    except Exception:
        return {"trend": "insufficient"}


def _training_section(user_id):
    try:
        from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
        from app.core.adaptive.next_plan_optimizer import recommend_optimized_next_plan
        from app.core.adaptive.plan_response_model import build_plan_response_model
        rm = build_plan_response_model(user_id)
        fa = analyze_fatigue_adherence_patterns(user_id)
        rec = recommend_optimized_next_plan(user_id)
        return {
            "best_focus": rm.get("best_focus", ""),
            "worst_focus": rm.get("worst_focus", ""),
            "recommended_next_focus": rec.get("recommended_focus", ""),
            "fatigue_risk": fa.get("fatigue", {}).get("risk_level", "unknown"),
            "adherence_risk": fa.get("adherence", {}).get("risk_level", "unknown"),
        }
    except Exception:
        return {}


def _experiment_section(user_id):
    try:
        from app.core.adaptive.n_of_1_experiment_analysis import (
            analyze_n_of_1_experiment,
            compute_n_of_1_evidence_score,
        )
        from app.core.adaptive.n_of_1_experiment_execution import (
            get_latest_n_of_1_experiment,
            list_n_of_1_experiments,
        )
        latest = get_latest_n_of_1_experiment(user_id)
        exps = list_n_of_1_experiments(user_id)
        n_opt = sum(1 for e in exps if e.get("status") == "completed")
        n_inconclusive = n_opt
        if latest and latest.get("status") == "completed":
            a = analyze_n_of_1_experiment(user_id, latest.get("experiment_id"))
            direction = a.get("primary_result", {}).get("direction", "")
            if "optimized_better" in direction:
                n_opt = 1
                n_inconclusive = 0
            ev = compute_n_of_1_evidence_score(user_id, latest.get("experiment_id"))
            return {
                "latest_experiment_id": latest.get("experiment_id", ""),
                "latest_direction": direction,
                "latest_evidence_score": ev.get("evidence_score", 0),
                "latest_evidence_category": ev.get("category", ""),
                "n_experiments_optimized_better": n_opt,
                "n_experiments_inconclusive": n_inconclusive,
            }
        return {"n_experiments_optimized_better": 0, "n_experiments_inconclusive": 0}
    except Exception:
        return {}


def _collect_limitations(data, pid, experiments):
    lims = []
    if data.get("n_calibrations", 0) < 4:
        lims.append("Fewer than 4 calibration sessions. More data would increase confidence.")
    if data.get("n_completed_executions", 0) < 2:
        lims.append("Fewer than 2 completed plan executions. Limited training data.")
    if data.get("n_completed_experiments", 0) < 1:
        lims.append("No completed N-of-1 experiments. Cannot assess optimized vs baseline.")
    if experiments.get("latest_evidence_score", 0) < 50:
        lims.append("Latest experiment evidence score < 50. Results are exploratory.")
    if pid.get("trend") == "insufficient":
        lims.append("Insufficient PID data for trend detection.")
    return lims
