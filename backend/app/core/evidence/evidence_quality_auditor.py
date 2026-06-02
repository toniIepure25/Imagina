"""IMAGINA V18 — Evidence Quality Auditor.

Audits the completeness and quality of a user's IMAGINA evidence.
Checks calibrations, executions, experiments, checkpoints, fatigue, safety.
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


def audit_imagina_evidence_quality(user_id="default") -> dict:
    data = _get_data(user_id)
    passed, warnings, critical = _run_checks(data, user_id)
    score = _compute_score(passed, warnings, critical)
    quality_cat = ("strong" if score >= 75 else "good" if score >= 55
                   else "usable" if score >= 35 else "weak")

    return {
        "user_id": user_id,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "quality_score": score,
        "quality_category": quality_cat,
        "passed_checks": passed,
        "warnings": warnings,
        "critical_issues": critical,
        "recommended_next_actions": _actions(passed, warnings, critical),
        **SAFETY,
    }


def _get_data(user_id):
    from app.core.evidence.imagina_evidence_model import _inventory
    inv = _inventory(user_id)
    pid = {"trend": "insufficient"}
    try:
        from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement
        pid = compute_pid_improvement(user_id)
    except Exception:
        pass

    fatigue = {"fatigue": {"risk_level": "unknown"}}
    try:
        from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
        fatigue = analyze_fatigue_adherence_patterns(user_id)
    except Exception:
        pass

    exp_data = {}
    try:
        from app.core.adaptive.n_of_1_experiment_execution import list_n_of_1_experiments
        exps = list_n_of_1_experiments(user_id)
        completed = [e for e in exps if e.get("status") == "completed"]
        exp_data["n_completed"] = len(completed)
        checkpoint_count = 0
        for e in completed:
            for d in e.get("days", []):
                if d.get("calibration_session_id"):
                    checkpoint_count += 1
        exp_data["checkpoints"] = checkpoint_count
    except Exception:
        exp_data = {}

    return {"inventory": inv, "pid": pid, "fatigue": fatigue, "experiments": exp_data}


def _run_checks(data, user_id):
    passed, warnings, critical = [], [], []
    inv = data.get("inventory", {})
    pid = data.get("pid", {})
    fatigue = data.get("fatigue", {})
    exps = data.get("experiments", {})

    if inv.get("n_calibrations", 0) >= 4:
        passed.append("sufficient_calibrations")
    elif inv.get("n_calibrations", 0) >= 2:
        warnings.append("minimal_calibrations")
    else:
        critical.append("no_calibration_data")

    if inv.get("n_completed_executions", 0) >= 2:
        passed.append("sufficient_executions")
    elif inv.get("n_completed_executions", 0) >= 1:
        warnings.append("minimal_executions")
    else:
        critical.append("no_completed_execution")

    if pid.get("n_sessions", 0) >= 1:
        passed.append("pid_values_present")
    else:
        critical.append("no_pid_values")

    if fatigue.get("fatigue", {}).get("risk_level") == "high":
        warnings.append("fatigue_confound_possible")
    else:
        passed.append("fatigue_controlled")

    adh_risk = fatigue.get("adherence", {}).get("risk_level", "")
    if adh_risk == "high":
        warnings.append("adherence_confound_possible")
    elif adh_risk == "medium":
        warnings.append("adherence_moderate")

    if exps.get("n_completed", 0) >= 1:
        if exps.get("checkpoints", 0) >= 2:
            passed.append("experiment_checkpoints_complete")
        else:
            warnings.append("experiment_checkpoints_missing")
        passed.append("experiment_completed")
    else:
        warnings.append("no_completed_experiment")

    all_modules = [
        ("plan_response_model", "app.core.adaptive.plan_response_model"),
        ("fatigue_adherence_model", "app.core.adaptive.fatigue_adherence_model"),
        ("next_plan_optimizer", "app.core.adaptive.next_plan_optimizer"),
    ]
    for name, mod_path in all_modules:
        try:
            __import__(mod_path)
        except Exception:
            pass

    return passed, warnings, critical


def _compute_score(passed, warnings, critical):
    base = 0
    base += min(20, len([p for p in passed if "calibrat" in p or "execut" in p]) * 10)
    base += min(25, len([p for p in passed if "experiment" in p]) * 25)
    base += min(15, len([p for p in passed if "checkpoint" in p]) * 15)
    base += min(10, len([p for p in passed if "fatigue" in p or "pid" in p]) * 5)
    base += min(10, 5 * (1 if any("report" in p for p in passed) else 0))

    base -= len(warnings) * 5
    if critical:
        base = min(50, base)
    return max(0, min(100, base))


def _actions(passed, warnings, critical):
    actions = []
    if "no_calibration_data" in critical:
        actions.append("Complete at least 2 PID v2 calibration sessions.")
    if "no_completed_execution" in critical:
        actions.append("Run and complete at least one adaptive plan execution.")
    if "no_pid_values" in critical:
        actions.append("Attach calibration checkpoints to execution days.")
    if "no_completed_experiment" in warnings:
        actions.append("Design and run an N-of-1 experiment to compare plans.")
    if "experiment_checkpoints_missing" in warnings:
        actions.append("Attach calibration checkpoints to experiment checkpoint days.")
    if not critical and len(warnings) <= 2:
        actions.append("Evidence quality is good — consider exporting your research pack.")
    if not actions:
        actions.append("Continue training and calibrating to build stronger personal evidence.")
    return actions
