"""IMAGINA V18 — Evidence Timeline Builder + Recommendation Engine."""


SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def build_evidence_timeline(user_id="default") -> dict:
    events = []

    try:
        from app.core.calibration.pid_v2_calibration import list_calibration_sessions
        for s in list_calibration_sessions(user_id):
            if s.get("status") == "completed" and s.get("pid_v2"):
                events.append({
                    "timestamp": s.get("started_at", ""),
                    "event_type": "calibration_completed",
                    "title": "PID v2 Calibration",
                    "summary": f"PID={s['pid_v2'].get('pid_v2', 0):.3f}",
                    "source_id": s.get("session_id", ""),
                    "metric_snapshot": {"pid_v2": s["pid_v2"].get("pid_v2")},
                })
    except Exception:
        pass

    try:
        from app.core.adaptive.adaptive_training_planner import list_adaptive_training_plans
        for p in list_adaptive_training_plans(user_id):
            events.append({
                "timestamp": p.get("generated_at", ""),
                "event_type": "adaptive_plan_generated",
                "title": p.get("plan_title", "Adaptive Plan"),
                "summary": f"Focus: {p.get('training_focus', '')}",
                "source_id": p.get("adaptive_plan_id", ""),
                "metric_snapshot": {"mean_pid": p.get("source", {}).get("mean_pid_v2")},
            })
    except Exception:
        pass

    try:
        from app.core.adaptive.adaptive_plan_execution import list_plan_executions
        for e in list_plan_executions(user_id):
            status = e.get("status", "")
            events.append({
                "timestamp": e.get("started_at", ""),
                "event_type": f"plan_execution_{status}",
                "title": e.get("plan_title", "Execution"),
                "summary": f"Status: {status}, Adherence: {e.get('summary', {}).get('adherence_rate', 0):.0%}",
                "source_id": e.get("execution_id", ""),
                "metric_snapshot": {
                    "adherence": e.get("summary", {}).get("adherence_rate"),
                    "completed_days": e.get("summary", {}).get("completed_days"),
                },
            })
    except Exception:
        pass

    try:
        from app.core.adaptive.n_of_1_experiment_execution import list_n_of_1_experiments
        for e in list_n_of_1_experiments(user_id):
            status = e.get("status", "")
            if status == "designed":
                etype = "n_of_1_experiment_designed"
            elif status == "active":
                etype = "n_of_1_experiment_started"
            else:
                etype = "n_of_1_experiment_closed"
            events.append({
                "timestamp": e.get("designed_at") or e.get("started_at", ""),
                "event_type": etype,
                "title": f"N-of-1 {e.get('design_type', '')}",
                "summary": f"Status: {status}, Days: {len(e.get('days', []))}",
                "source_id": e.get("experiment_id", ""),
                "metric_snapshot": {"design": e.get("design_type")},
            })
    except Exception:
        pass

    try:
        from app.core.adaptive.next_plan_optimizer import load_latest_optimized_plan
        opt = load_latest_optimized_plan(user_id)
        if opt:
            events.append({
                "timestamp": opt.get("generated_at", ""),
                "event_type": "optimized_plan_generated",
                "title": opt.get("plan_title", "Optimized Plan"),
                "summary": f"Focus: {opt.get('training_focus', '')}",
                "source_id": opt.get("adaptive_plan_id", ""),
                "metric_snapshot": {},
            })
    except Exception:
        pass

    events.sort(key=lambda x: x.get("timestamp", ""))

    return {
        "user_id": user_id,
        "n_events": len(events),
        "timeline": events,
        **SAFETY,
    }


def recommend_next_research_action(user_id="default") -> dict:
    from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
    from app.core.evidence.imagina_evidence_model import build_unified_evidence_model

    model = build_unified_evidence_model(user_id)
    quality = audit_imagina_evidence_quality(user_id)

    data = model.get("data_inventory", {})
    critical = quality.get("critical_issues", [])
    experiments = model.get("experiment_summary", {})

    if "no_calibration_data" in critical or "no_completed_execution" in critical:
        return {
            "recommended_action": "complete_more_calibrations",
            "priority": "high",
            "why": ["No calibration or execution data found. Start with PID v2 calibrations and adaptive plan execution."],
            "next_steps": ["Run PID v2 calibration sessions", "Generate an adaptive plan", "Execute the plan for 7 days"],
            "blocks_export": True, **SAFETY,
        }

    if data.get("n_completed_experiments", 0) < 1:
        return {
            "recommended_action": "run_first_n_of_1_experiment",
            "priority": "high",
            "why": ["No completed N-of-1 experiment.", "Experiments compare baseline vs optimized plans under controlled conditions."],
            "next_steps": ["Design an AB experiment", "Execute and calibrate both blocks", "Close and analyze the experiment"],
            "blocks_export": True, **SAFETY,
        }

    direction = experiments.get("latest_direction", "")
    score = experiments.get("latest_evidence_score", 0)

    if "fatigue_confound_possible" in quality.get("warnings", []):
        return {
            "recommended_action": "reduce_fatigue_before_experiment",
            "priority": "medium",
            "why": ["High fatigue detected. Rest before repeating the experiment for cleaner results."],
            "next_steps": ["Take a rest day", "Reduce session duration", "Re-attempt experiment with lower intensity"],
            "blocks_export": False, **SAFETY,
        }

    if "optimized_better" in direction and data.get("n_completed_experiments", 0) < 2:
        return {
            "recommended_action": "repeat_n_of_1_experiment",
            "priority": "medium",
            "why": ["One experiment showed optimized_better.", "Repeating confirms the pattern and increases evidence quality."],
            "next_steps": ["Re-run the same experiment design", "Try ABAB for stronger design", "Compare results across experiments"],
            "blocks_export": False, **SAFETY,
        }

    if score >= 50 and "no_completed_experiment" not in quality.get("warnings", []):
        return {
            "recommended_action": "export_research_pack",
            "priority": "medium",
            "why": ["Evidence quality is sufficient for personal portfolio/demo export.",
                     f"Evidence score: {score}/100, category: {experiments.get('latest_evidence_category', '')}."],
            "next_steps": ["Generate research export pack", "Review exported evidence files", "Share or archive for personal reference"],
            "blocks_export": False, **SAFETY,
        }

    return {
        "recommended_action": "evidence_sufficient_for_portfolio_demo",
        "priority": "low",
        "why": ["Evidence is strong enough for a personal portfolio demo.",
                 "Continue practicing to strengthen and diversify evidence."],
        "next_steps": ["Export research pack", "Archive evidence", "Continue training for stronger longitudinal data"],
        "blocks_export": False, **SAFETY,
    }
