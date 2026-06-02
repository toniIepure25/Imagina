"""IMAGINA Core API Routes — Production-quality endpoints using SessionManager."""

from fastapi import APIRouter, HTTPException

from app.core.sessions.session_manager import session_manager
from app.schemas.imagina.api import CompleteTaskRequest, SelfReportRequest, SignalFeaturesRequest, StartSessionRequest

router = APIRouter(prefix="/api/imagina", tags=["imagina"])


@router.get("/health")
async def health():
    return {"status": "ok", "system": "IMAGINA Core", "version": "1.0.0",
            "demo_profiles": ["stable_improving", "distracted", "fatigued",
                              "high_vividness", "low_vividness", "noisy"]}


@router.get("/tasks")
async def list_tasks():
    from app.core.tasks.imagery_task_engine import TASK_TEMPLATES
    return {"tasks": TASK_TEMPLATES}


@router.get("/demo-profiles")
async def list_demo_profiles():
    from app.core.state.simulated_signal_provider import DEMO_PROFILES
    return {"profiles": list(DEMO_PROFILES.keys())}


@router.post("/session/start")
async def start_session(req: StartSessionRequest = StartSessionRequest()):
    config = {"duration_minutes": req.duration_minutes, "user_id": req.user_id,
              "demo_mode": req.demo_mode, "demo_profile": req.demo_profile}
    result = session_manager.start_session(req.user_id, config)
    return result


@router.post("/session/{session_id}/task/start")
async def start_task(session_id: str, task_id: str = "shape_stabilization"):
    result = session_manager.start_task(session_id, task_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/session/{session_id}/self-report")
async def submit_self_report(session_id: str, req: SelfReportRequest):
    return session_manager.submit_self_report(
        session_id, req.vividness, req.stability, req.effort,
        req.fatigue, req.comfort, req.task_id)


@router.post("/session/{session_id}/signal-features")
async def submit_signal_features(session_id: str, req: SignalFeaturesRequest):
    return {"session_id": session_id, "status": "received",
            "note": "Signal features stored. Use /step to trigger pipeline."}


@router.post("/session/{session_id}/step")
async def step(session_id: str):
    try:
        return session_manager.run_step(session_id)
    except Exception as e:
        raise HTTPException(500, f"Pipeline step failed: {e}")


@router.post("/session/{session_id}/complete-task")
async def complete_task(session_id: str, req: CompleteTaskRequest):
    return {"session_id": session_id, "task_id": req.task_id,
            "status": "completed", "note": "Task completion recorded."}


@router.get("/session/{session_id}/summary")
async def session_summary(session_id: str):
    result = session_manager.get_summary(session_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/session/{session_id}/events")
async def session_events(session_id: str):
    events = session_manager.get_events(session_id)
    return {"session_id": session_id, "event_count": len(events), "events": events}


@router.get("/profile/{user_id}")
async def get_profile(user_id: str):
    from app.core.personalization.user_profile import load_profile
    return load_profile(user_id)


@router.post("/profile/{user_id}/update-from-session/{session_id}")
async def update_profile_from_session(user_id: str, session_id: str):
    from app.core.personalization.user_profile import update_profile_from_session
    return update_profile_from_session(user_id, session_id)


@router.post("/profile/{user_id}/reset")
async def reset_profile(user_id: str):
    from app.core.personalization.user_profile import reset_profile
    return reset_profile(user_id)


@router.get("/session/{session_id}/analytics")
async def session_analytics(session_id: str):
    from app.core.analytics.session_analytics import analyze_session
    result = analyze_session(session_id)
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


@router.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    from app.core.personalization.recommender import generate_recommendations
    from app.core.personalization.user_profile import load_profile
    profile = load_profile(user_id)
    return {"user_id": user_id, "recommendations": generate_recommendations(profile)}


# ─── Protocol Engine ─────────────────────────────────────────────

@router.get("/protocols/templates")
async def list_protocol_templates():
    from app.core.protocols.protocol_engine import PROTOCOL_TEMPLATES
    return {"templates": PROTOCOL_TEMPLATES}


@router.post("/protocols/{user_id}/create")
async def create_protocol(user_id: str, template_name: str = "baseline_3_session"):
    from app.core.protocols.protocol_engine import create_protocol
    result = create_protocol(template_name, user_id)
    if not result:
        raise HTTPException(404, f"Template '{template_name}' not found")
    return result


@router.get("/protocols/{user_id}")
async def list_protocols(user_id: str):
    from app.core.protocols.protocol_engine import list_protocols
    return {"protocols": list_protocols(user_id)}


@router.get("/protocols/{user_id}/{protocol_id}")
async def get_protocol(user_id: str, protocol_id: str):
    from app.core.protocols.protocol_engine import load_protocol
    p = load_protocol(protocol_id, user_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    return p


@router.delete("/protocols/{user_id}/{protocol_id}")
async def delete_protocol(user_id: str, protocol_id: str):
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "protocols", user_id, f"{protocol_id}.json")
    if os.path.exists(p):
        os.remove(p)
        return {"status": "deleted"}
    raise HTTPException(404, "Protocol not found")


@router.post("/protocol-runs/{user_id}/start/{protocol_id}")
async def start_protocol_run(user_id: str, protocol_id: str):
    from app.core.protocols.protocol_engine import start_protocol_run
    r = start_protocol_run(user_id, protocol_id)
    if not r:
        raise HTTPException(404, "Protocol not found")
    return r


@router.get("/protocol-runs/{user_id}")
async def list_protocol_runs(user_id: str):
    from app.core.protocols.protocol_engine import list_protocol_runs
    return {"runs": list_protocol_runs(user_id)}


@router.get("/protocol-runs/{user_id}/{run_id}")
async def get_protocol_run(user_id: str, run_id: str):
    from app.core.protocols.protocol_engine import get_protocol_run
    r = get_protocol_run(run_id, user_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return r


@router.post("/protocol-runs/{run_id}/attach-session/{session_id}")
async def attach_session(run_id: str, session_id: str):
    from app.core.protocols.protocol_engine import attach_session_to_run
    r = attach_session_to_run(run_id, session_id, "default")
    if not r:
        raise HTTPException(404, "Run not found")
    return r


@router.get("/protocol-runs/{run_id}/next-step")
async def next_step(run_id: str):
    from app.core.protocols.protocol_engine import get_next_step
    s = get_next_step(run_id, "default")
    return {"next_step": s} if s else {"next_step": None, "status": "all_complete"}


@router.post("/protocol-runs/{run_id}/complete")
async def complete_run(run_id: str):
    from app.core.protocols.protocol_engine import complete_protocol_run
    return complete_protocol_run(run_id, "default")


@router.get("/protocol-runs/{run_id}/analysis")
async def protocol_analysis(run_id: str):
    from app.core.protocols.protocol_engine import analyze_protocol_run
    result = analyze_protocol_run(run_id, "default")
    if result.get("error"):
        raise HTTPException(404, result["error"])
    return result


# ─── Experiment Designer ────────────────────────────────────────

@router.get("/experiment-designs/templates")
async def list_experiment_templates():
    from app.core.protocols.experiment_design import DESIGN_TEMPLATES
    return {"templates": DESIGN_TEMPLATES}


@router.post("/experiment-designs/{user_id}/create")
async def create_experiment_design(user_id: str, template_id: str = None):
    from app.core.protocols.experiment_design import create_experiment_design
    result = create_experiment_design(user_id, template_id)
    if not result:
        raise HTTPException(404, "Template not found or invalid payload")
    return result


@router.get("/experiment-designs/{user_id}")
async def list_experiment_designs(user_id: str):
    from app.core.protocols.experiment_design import list_designs
    return {"designs": list_designs(user_id)}


@router.get("/experiment-designs/{user_id}/{design_id}")
async def get_experiment_design(user_id: str, design_id: str):
    from app.core.protocols.experiment_design import load_design
    d = load_design(user_id, design_id)
    if not d:
        raise HTTPException(404, "Design not found")
    return d


@router.delete("/experiment-designs/{user_id}/{design_id}")
async def delete_experiment_design(user_id: str, design_id: str):
    from app.core.protocols.experiment_design import delete_design
    delete_design(user_id, design_id)
    return {"status": "deleted"}


@router.post("/experiment-designs/{user_id}/{design_id}/validate")
async def validate_design(user_id: str, design_id: str):
    from app.core.protocols.experiment_design import load_design, validate_design
    d = load_design(user_id, design_id)
    if not d:
        raise HTTPException(404, "Design not found")
    return validate_design(d)


@router.post("/experiment-designs/{user_id}/{design_id}/compile")
async def compile_design(user_id: str, design_id: str):
    from app.core.protocols.experiment_design import compile_design_to_protocol
    result = compile_design_to_protocol(user_id, design_id)
    if not result:
        raise HTTPException(404, "Design not found")
    return result


@router.post("/protocols/{user_id}/create-from-design/{design_id}")
async def create_protocol_from_design(user_id: str, design_id: str):
    from app.core.protocols.experiment_design import compile_design_to_protocol
    result = compile_design_to_protocol(user_id, design_id)
    if not result:
        raise HTTPException(404, "Design not found")
    return result


# ─── Personal Intelligence ──────────────────────────────────────

@router.get("/personal-profile")
async def get_personal_profile():
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile, load_personal_profile
    p = load_personal_profile()
    return p if p else build_personal_imagery_profile()


@router.post("/personal-profile/rebuild")
async def rebuild_profile():
    from app.core.protocols.personal_intelligence import build_personal_imagery_profile
    return build_personal_imagery_profile()


@router.get("/imagery-gaps")
async def get_imagery_gaps():
    from app.core.protocols.personal_intelligence import analyze_imagery_gaps
    return analyze_imagery_gaps()


@router.get("/recommendation/next")
async def get_next_recommendation():
    from app.core.protocols.personal_intelligence import recommend_next_protocol
    return recommend_next_protocol()


@router.post("/recommendation/create-design")
async def create_recommended_design():
    from app.core.protocols.experiment_design import create_experiment_design
    from app.core.protocols.personal_intelligence import recommend_next_protocol
    rec = recommend_next_protocol()
    if rec.get("recommended_template_id"):
        return create_experiment_design("default", rec["recommended_template_id"])
    return {"error": "no_template_recommended"}


@router.get("/personal-report")
async def get_personal_report():
    from app.core.protocols.personal_intelligence import generate_personal_progress_report
    return generate_personal_progress_report()


# ─── PID v2 Calibration ─────────────────────────────────────────

@router.get("/calibration/reference-tasks")
async def list_ref_tasks():
    from app.core.calibration.pid_v2_calibration import list_reference_tasks
    return {"tasks": list_reference_tasks()}


@router.get("/calibration/reference-tasks/{task_id}")
async def get_ref_task(task_id: str):
    from app.core.calibration.pid_v2_calibration import get_reference_task
    t = get_reference_task(task_id)
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@router.post("/calibration/start")
async def start_calibration(user_id: str = "default", task_id: str = "simple_red_circle_reference"):
    from app.core.calibration.pid_v2_calibration import start_calibration_session
    r = start_calibration_session(user_id, task_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/calibration/{session_id}/reference-rating")
async def submit_ref_rating(session_id: str, payload: dict):
    from app.core.calibration.pid_v2_calibration import submit_reference_rating
    r = submit_reference_rating(session_id, payload)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/calibration/{session_id}/imagery-rating")
async def submit_img_rating(session_id: str, payload: dict):
    from app.core.calibration.pid_v2_calibration import submit_imagery_rating
    r = submit_imagery_rating(session_id, payload)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/calibration/{session_id}/complete")
async def complete_calibration(session_id: str):
    from app.core.calibration.pid_v2_calibration import _load_calib
    s = _load_calib(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.get("/calibration/{session_id}")
async def get_calibration(session_id: str):
    from app.core.calibration.pid_v2_calibration import get_calibration_session
    s = get_calibration_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.get("/calibration/history/{user_id}")
async def get_calibration_history(user_id: str):
    from app.core.calibration.pid_v2_calibration import list_calibration_sessions
    return {"sessions": list_calibration_sessions(user_id)}


@router.get("/calibration/pid-summary/{user_id}")
async def get_pid_summary(user_id: str):
    from app.core.calibration.pid_v2_calibration import aggregate_pid_v2_history
    return aggregate_pid_v2_history(user_id)


# ─── V14 Adaptive Training Loop ──────────────────────────────────

@router.get("/adaptive/plan/{user_id}")
async def get_adaptive_plan(user_id: str):
    from app.core.adaptive.adaptive_training_planner import load_latest_adaptive_training_plan
    plan = load_latest_adaptive_training_plan(user_id)
    if not plan:
        raise HTTPException(404, "No adaptive plan found. Generate one first.")
    return plan


@router.post("/adaptive/plan/{user_id}/generate")
async def generate_adaptive_plan(user_id: str):
    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    plan = build_adaptive_training_plan(user_id)
    if plan.get("status") == "insufficient_data":
        raise HTTPException(400, plan.get("message", "Insufficient data"))
    return plan


@router.post("/adaptive/plan/{user_id}/regenerate")
async def regenerate_adaptive_plan(user_id: str, payload: dict = None):
    from app.core.adaptive.adaptive_training_planner import build_adaptive_training_plan
    plan = build_adaptive_training_plan(user_id)
    if plan.get("status") == "insufficient_data":
        raise HTTPException(400, plan.get("message", "Insufficient data"))
    if payload:
        if payload.get("focus_override"):
            plan["training_focus"] = payload["focus_override"]
        if payload.get("difficulty"):
            plan["difficulty_level"] = payload["difficulty"]
    return plan


@router.get("/adaptive/plans/{user_id}")
async def list_adaptive_plans(user_id: str):
    from app.core.adaptive.adaptive_training_planner import (
        list_adaptive_training_plans,
        load_latest_adaptive_training_plan,
    )
    return {
        "latest": load_latest_adaptive_training_plan(user_id),
        "history": list_adaptive_training_plans(user_id),
    }


@router.get("/adaptive/improvement/{user_id}")
async def get_pid_improvement(user_id: str):
    from app.core.adaptive.pid_improvement_tracker import compute_pid_improvement
    return compute_pid_improvement(user_id)


@router.get("/adaptive/training-response/{user_id}")
async def get_training_response(user_id: str):
    from app.core.adaptive.pid_improvement_tracker import compute_training_response
    return compute_training_response(user_id)


# ─── V15 Adaptive Plan Execution ─────────────────────────────────

@router.post("/adaptive/execution/{user_id}/start")
async def start_execution(user_id: str):
    from app.core.adaptive.adaptive_plan_execution import start_plan_execution
    r = start_plan_execution(user_id)
    if r.get("error"):
        raise HTTPException(400, r.get("message", r["error"]))
    return r


@router.get("/adaptive/execution/{user_id}/latest")
async def get_latest_execution(user_id: str):
    from app.core.adaptive.adaptive_plan_execution import get_latest_plan_execution
    ex = get_latest_plan_execution(user_id)
    if not ex:
        raise HTTPException(404, "No executions found")
    return ex


@router.get("/adaptive/execution/{user_id}/{execution_id}")
async def get_execution(user_id: str, execution_id: str):
    from app.core.adaptive.adaptive_plan_execution import get_plan_execution
    ex = get_plan_execution(user_id, execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found")
    return ex


@router.get("/adaptive/executions/{user_id}")
async def list_executions(user_id: str):
    from app.core.adaptive.adaptive_plan_execution import list_plan_executions
    return {"executions": list_plan_executions(user_id)}


@router.post("/adaptive/execution/{user_id}/{execution_id}/day/{day}/complete")
async def complete_exec_day(user_id: str, execution_id: str, day: int, payload: dict):
    from app.core.adaptive.adaptive_plan_execution import complete_execution_day
    r = complete_execution_day(user_id, execution_id, day, payload)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/adaptive/execution/{user_id}/{execution_id}/day/{day}/attach-calibration")
async def attach_calib_to_exec(user_id: str, execution_id: str, day: int, payload: dict):
    from app.core.adaptive.adaptive_plan_execution import attach_calibration_to_execution_day
    r = attach_calibration_to_execution_day(
        user_id, execution_id, day, payload.get("calibration_session_id", ""))
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/adaptive/execution/{user_id}/{execution_id}/close")
async def close_execution(user_id: str, execution_id: str):
    from app.core.adaptive.adaptive_plan_execution import close_plan_execution
    r = close_plan_execution(user_id, execution_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.get("/adaptive/execution/{user_id}/{execution_id}/analysis")
async def get_execution_analysis(user_id: str, execution_id: str):
    from app.core.adaptive.adaptive_execution_analytics import analyze_plan_execution
    r = analyze_plan_execution(user_id, execution_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/adaptive/executions/{user_id}/analysis")
async def get_all_executions_analysis(user_id: str):
    from app.core.adaptive.adaptive_execution_analytics import analyze_all_executions
    return analyze_all_executions(user_id)


@router.get("/adaptive/longitudinal-report/{user_id}")
async def get_longitudinal_report(user_id: str):
    from app.core.adaptive.longitudinal_progress_report import generate_longitudinal_progress_report
    return generate_longitudinal_progress_report(user_id)


# ─── V16 Adaptive Optimization Engine ────────────────────────────

@router.get("/adaptive/optimization/response-model/{user_id}")
async def get_response_model(user_id: str):
    from app.core.adaptive.plan_response_model import build_plan_response_model
    return build_plan_response_model(user_id)


@router.get("/adaptive/optimization/fatigue-adherence/{user_id}")
async def get_fatigue_adherence(user_id: str):
    from app.core.adaptive.fatigue_adherence_model import analyze_fatigue_adherence_patterns
    return analyze_fatigue_adherence_patterns(user_id)


@router.get("/adaptive/optimization/next-plan/{user_id}")
async def get_next_plan_recommendation(user_id: str):
    from app.core.adaptive.next_plan_optimizer import recommend_optimized_next_plan
    return recommend_optimized_next_plan(user_id)


@router.post("/adaptive/optimization/generate-plan/{user_id}")
async def generate_optimized_plan(user_id: str):
    from app.core.adaptive.next_plan_optimizer import generate_optimized_adaptive_plan
    return generate_optimized_adaptive_plan(user_id)


@router.post("/adaptive/optimization/compare-executions/{user_id}")
async def compare_executions(user_id: str, payload: dict = None):
    from app.core.adaptive.plan_ab_comparator import compare_plan_executions
    eids = payload.get("execution_ids", None) if payload else None
    return compare_plan_executions(user_id, eids)


@router.get("/adaptive/optimization/compare-focuses/{user_id}")
async def compare_focuses(user_id: str):
    from app.core.adaptive.plan_ab_comparator import compare_training_focuses
    return compare_training_focuses(user_id)


# ─── V17 N-of-1 Experiment Engine ────────────────────────────────

@router.post("/adaptive/experiments/{user_id}/design")
async def design_experiment(user_id: str, payload: dict = None):
    from app.core.adaptive.n_of_1_experiment_designer import design_n_of_1_experiment
    p = payload or {}
    r = design_n_of_1_experiment(
        user_id,
        p.get("experiment_type", "baseline_vs_optimized"),
        p.get("design", "AB"),
        p.get("duration_days", 14),
    )
    if r.get("error"):
        raise HTTPException(400, r.get("reason", r["error"]))
    return r


@router.post("/adaptive/experiments/{user_id}/start")
async def start_experiment(user_id: str, payload: dict = None):
    from app.core.adaptive.n_of_1_experiment_execution import start_n_of_1_experiment
    p = payload or {}
    r = start_n_of_1_experiment(user_id, p.get("experiment_id"))
    if r.get("error"):
        raise HTTPException(400, r.get("message", r["error"]))
    return r


@router.get("/adaptive/experiments/{user_id}/latest")
async def get_latest_experiment(user_id: str):
    from app.core.adaptive.n_of_1_experiment_execution import get_latest_n_of_1_experiment
    exp = get_latest_n_of_1_experiment(user_id)
    if not exp:
        raise HTTPException(404, "No experiments found")
    return exp


@router.get("/adaptive/experiments/{user_id}/{experiment_id}")
async def get_experiment(user_id: str, experiment_id: str):
    from app.core.adaptive.n_of_1_experiment_execution import get_n_of_1_experiment
    exp = get_n_of_1_experiment(user_id, experiment_id)
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return exp


@router.get("/adaptive/experiments/{user_id}")
async def list_experiments(user_id: str):
    from app.core.adaptive.n_of_1_experiment_execution import list_n_of_1_experiments
    return {"experiments": list_n_of_1_experiments(user_id)}


@router.post("/adaptive/experiments/{user_id}/{experiment_id}/day/{day}/complete")
async def complete_experiment_day(user_id: str, experiment_id: str, day: int, payload: dict):
    from app.core.adaptive.n_of_1_experiment_execution import complete_experiment_day
    r = complete_experiment_day(user_id, experiment_id, day, payload)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/adaptive/experiments/{user_id}/{experiment_id}/day/{day}/attach-calibration")
async def attach_experiment_calibration(user_id: str, experiment_id: str, day: int, payload: dict):
    from app.core.adaptive.n_of_1_experiment_execution import attach_experiment_calibration
    r = attach_experiment_calibration(user_id, experiment_id, day,
                                       payload.get("calibration_session_id", ""))
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/adaptive/experiments/{user_id}/{experiment_id}/close")
async def close_experiment(user_id: str, experiment_id: str):
    from app.core.adaptive.n_of_1_experiment_execution import close_n_of_1_experiment
    r = close_n_of_1_experiment(user_id, experiment_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.get("/adaptive/experiments/{user_id}/{experiment_id}/analysis")
async def get_experiment_analysis(user_id: str, experiment_id: str):
    from app.core.adaptive.n_of_1_experiment_analysis import analyze_n_of_1_experiment
    r = analyze_n_of_1_experiment(user_id, experiment_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/adaptive/experiments/{user_id}/{experiment_id}/evidence-score")
async def get_experiment_evidence(user_id: str, experiment_id: str):
    from app.core.adaptive.n_of_1_experiment_analysis import compute_n_of_1_evidence_score
    return compute_n_of_1_evidence_score(user_id, experiment_id)


@router.get("/adaptive/experiments/{user_id}/{experiment_id}/report")
async def get_experiment_report(user_id: str, experiment_id: str):
    from app.core.adaptive.n_of_1_experiment_report import generate_n_of_1_experiment_report
    r = generate_n_of_1_experiment_report(user_id, experiment_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


# ─── V18 Evidence Dashboard ──────────────────────────────────────

@router.get("/evidence/{user_id}/model")
async def get_evidence_model(user_id: str):
    from app.core.evidence.imagina_evidence_model import build_unified_evidence_model
    return build_unified_evidence_model(user_id)


@router.get("/evidence/{user_id}/quality-audit")
async def get_evidence_quality(user_id: str):
    from app.core.evidence.evidence_quality_auditor import audit_imagina_evidence_quality
    return audit_imagina_evidence_quality(user_id)


@router.get("/evidence/{user_id}/timeline")
async def get_evidence_timeline(user_id: str):
    from app.core.evidence.evidence_timeline_and_recommendations import build_evidence_timeline
    return build_evidence_timeline(user_id)


@router.get("/evidence/{user_id}/recommendation")
async def get_evidence_recommendation(user_id: str):
    from app.core.evidence.evidence_timeline_and_recommendations import recommend_next_research_action
    return recommend_next_research_action(user_id)


@router.post("/evidence/{user_id}/export-pack")
async def export_evidence_pack(user_id: str):
    from app.core.evidence.research_export_pack import generate_research_export_pack
    return generate_research_export_pack(user_id)


# ─── V19 Imagery Task Battery ────────────────────────────────────

@router.get("/imagery/tasks")
async def list_imagery_tasks(category: str = None):
    from app.core.imagery.task_battery import list_imagery_tasks as lit
    return lit(category) if category else lit()


@router.get("/imagery/tasks/{task_id}")
async def get_imagery_task(task_id: str):
    from app.core.imagery.task_battery import get_imagery_task
    t = get_imagery_task(task_id)
    if t.get("error"):
        raise HTTPException(404, t.get("message", t["error"]))
    return t


@router.post("/imagery/sessions/{user_id}/start/{task_id}")
async def start_imagery_session(user_id: str, task_id: str):
    from app.core.imagery.task_session_manager import start_imagery_task_session
    r = start_imagery_task_session(user_id, task_id)
    if r.get("error"):
        raise HTTPException(400, r.get("message", r["error"]))
    return r


@router.post("/imagery/sessions/{session_id}/rating")
async def submit_imagery_rating(session_id: str, payload: dict):
    from app.core.imagery.task_session_manager import submit_imagery_task_rating
    r = submit_imagery_task_rating(session_id, payload)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/imagery/sessions/{session_id}/complete")
async def complete_imagery_session(session_id: str):
    from app.core.imagery.task_session_manager import complete_imagery_task_session
    r = complete_imagery_task_session(session_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.get("/imagery/sessions/{session_id}")
async def get_imagery_session(session_id: str):
    from app.core.imagery.task_session_manager import get_imagery_task_session
    s = get_imagery_task_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.get("/imagery/sessions/user/{user_id}")
async def list_imagery_sessions(user_id: str):
    from app.core.imagery.task_session_manager import list_imagery_task_sessions
    return {"sessions": list_imagery_task_sessions(user_id)}


@router.get("/imagery/phenotype/{user_id}")
async def get_phenotype(user_id: str):
    from app.core.imagery.imagery_phenotype import build_imagery_phenotype
    return build_imagery_phenotype(user_id)


@router.get("/imagery/gaps/{user_id}")
async def get_imagery_phenotype_gaps(user_id: str):
    from app.core.imagery.imagery_phenotype import analyze_imagery_gaps
    return analyze_imagery_gaps(user_id)


@router.post("/imagery/task-plan/{user_id}")
async def generate_task_plan(user_id: str, payload: dict = None):
    from app.core.imagery.imagery_phenotype import generate_task_based_imagery_plan
    days = (payload or {}).get("duration_days", 7)
    return generate_task_based_imagery_plan(user_id, days)


# ─── V20 Guided Imagery Session Runtime ─────────────────────────

@router.get("/guided/schema")
async def get_guided_schema():
    from app.core.imagery.guided_session_runtime import get_guided_session_schema
    return get_guided_session_schema()


@router.post("/guided/session/{user_id}/start/{task_id}")
async def start_guided_session(user_id: str, task_id: str, source: str = "manual"):
    from app.core.imagery.guided_session_runtime import start_guided_imagery_session
    r = start_guided_imagery_session(user_id, task_id, source)
    if r.get("error"):
        raise HTTPException(400, r.get("message", r["error"]))
    return r


@router.get("/guided/session/{session_id}")
async def get_guided_session(session_id: str):
    from app.core.imagery.guided_session_runtime import get_guided_session
    s = get_guided_session(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.post("/guided/session/{session_id}/advance")
async def advance_guided_phase(session_id: str):
    from app.core.imagery.guided_session_runtime import advance_guided_session_phase
    r = advance_guided_session_phase(session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/guided/session/{session_id}/checkin")
async def submit_guided_checkin(session_id: str, payload: dict):
    from app.core.imagery.guided_session_runtime import submit_guided_micro_checkin
    r = submit_guided_micro_checkin(session_id, payload)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/guided/session/{session_id}/pause")
async def pause_guided_session(session_id: str):
    from app.core.imagery.guided_session_runtime import pause_guided_session
    r = pause_guided_session(session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/guided/session/{session_id}/resume")
async def resume_guided_session(session_id: str):
    from app.core.imagery.guided_session_runtime import resume_guided_session
    r = resume_guided_session(session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/guided/session/{session_id}/complete")
async def complete_guided_session(session_id: str):
    from app.core.imagery.guided_session_runtime import complete_guided_session
    r = complete_guided_session(session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/guided/session/{session_id}/abort")
async def abort_guided_session(session_id: str, payload: dict = None):
    from app.core.imagery.guided_session_runtime import abort_guided_session
    reason = (payload or {}).get("reason", "")
    r = abort_guided_session(session_id, reason)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.get("/guided/sessions/{user_id}")
async def list_guided_sessions(user_id: str):
    from app.core.imagery.guided_session_runtime import list_guided_sessions
    return {"sessions": list_guided_sessions(user_id)}


@router.get("/guided/session/{session_id}/report")
async def get_guided_session_report(session_id: str):
    from app.core.imagery.guided_session_runtime import build_guided_session_report
    r = build_guided_session_report(session_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.post("/guided/session/{session_id}/export-task-rating")
async def export_guided_task_rating(session_id: str):
    from app.core.imagery.guided_session_runtime import export_guided_session_as_task_rating
    r = export_guided_session_as_task_rating(session_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/guided/plan/{user_id}/start-next")
async def start_next_guided_task(user_id: str):
    from app.core.imagery.guided_session_runtime import start_next_guided_task_from_plan
    return start_next_guided_task_from_plan(user_id)


@router.get("/guided/plan/{user_id}/progress")
async def get_guided_plan_progress(user_id: str):
    from app.core.imagery.guided_session_runtime import get_guided_plan_progress
    return get_guided_plan_progress(user_id)


@router.post("/guided/plan/{user_id}/complete-day/{session_id}")
async def complete_guided_plan_day(user_id: str, session_id: str):
    from app.core.imagery.guided_session_runtime import mark_guided_plan_day_completed
    r = mark_guided_plan_day_completed(user_id, session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


# ─── V21 Skill Tree & Mastery Progression ───────────────────────

@router.get("/skill-tree")
async def get_skill_tree():
    from app.core.imagery.skill_tree import get_skill_tree
    return get_skill_tree()


@router.get("/skill-tree/{dimension}")
async def get_skill_branch(dimension: str):
    from app.core.imagery.skill_tree import get_skill_branch
    r = get_skill_branch(dimension)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/skill-model/{user_id}")
async def get_skill_model(user_id: str):
    from app.core.imagery.skill_tree import build_longitudinal_skill_model
    return build_longitudinal_skill_model(user_id)


@router.get("/mastery-milestones/{user_id}")
async def get_mastery_milestones(user_id: str):
    from app.core.imagery.skill_tree import evaluate_mastery_milestones
    return evaluate_mastery_milestones(user_id)


@router.get("/plateaus/{user_id}")
async def get_plateau_analysis(user_id: str):
    from app.core.imagery.skill_tree import detect_imagery_plateaus
    return detect_imagery_plateaus(user_id)


@router.post("/difficulty-recommendation/{user_id}")
async def get_difficulty_rec(user_id: str, payload: dict = None):
    from app.core.imagery.skill_tree import recommend_next_difficulty
    p = payload or {}
    return recommend_next_difficulty(user_id, p.get("task_id"), p.get("dimension"))


@router.post("/weekly-progress/{user_id}")
async def generate_weekly_report(user_id: str, payload: dict = None):
    from app.core.imagery.skill_tree import generate_weekly_imagery_progress_report
    days = (payload or {}).get("days", 7)
    return generate_weekly_imagery_progress_report(user_id, days)


@router.get("/weekly-progress/{user_id}")
async def get_weekly_report(user_id: str):
    from app.core.imagery.skill_tree import get_weekly_progress_report
    r = get_weekly_progress_report(user_id)
    if not r:
        raise HTTPException(404, "No weekly report found")
    return r


@router.post("/curriculum-update/{user_id}")
async def trigger_curriculum_update(user_id: str):
    from app.core.imagery.skill_tree import update_imagery_curriculum
    return update_imagery_curriculum(user_id)


@router.get("/curriculum-update/{user_id}")
async def get_curriculum_update(user_id: str):
    from app.core.imagery.skill_tree import get_curriculum_update
    r = get_curriculum_update(user_id)
    if not r:
        raise HTTPException(404, "No curriculum update found")
    return r


# ─── V22 Scene Simulator & Replay ───────────────────────────────

@router.get("/scenes/templates")
async def get_scene_templates(category: str = None):
    from app.core.imagery.scene_simulator import list_scene_templates
    return list_scene_templates(category)


@router.get("/scenes/templates/{template_id}")
async def get_scene_template(template_id: str):
    from app.core.imagery.scene_simulator import get_scene_template
    t = get_scene_template(template_id)
    if t.get("error"):
        raise HTTPException(404, t["error"])
    return t


@router.get("/scenes/template-for-task/{task_id}")
async def get_scene_template_for_task(task_id: str):
    from app.core.imagery.scene_simulator import get_scene_template_for_task
    return get_scene_template_for_task(task_id)


@router.post("/scenes/session/{session_id}/update")
async def update_scene(session_id: str):
    from app.core.imagery.scene_simulator import update_scene_from_guided_session
    r = update_scene_from_guided_session(session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.get("/scenes/session/{session_id}/latest")
async def get_latest_scene(session_id: str):
    from app.core.imagery.scene_simulator import get_latest_scene_state
    r = get_latest_scene_state(session_id)
    if not r or r.get("error"):
        raise HTTPException(404, "No scene state found")
    return r


@router.get("/scenes/session/{session_id}/states")
async def list_scene_states(session_id: str):
    from app.core.imagery.scene_simulator import list_scene_states
    return {"states": list_scene_states(session_id)}


@router.get("/scenes/session/{session_id}/summary")
async def get_scene_summary(session_id: str):
    from app.core.imagery.scene_simulator import get_scene_control_summary
    return get_scene_control_summary(session_id)


@router.post("/scenes/session/{session_id}/replay/build")
async def build_replay(session_id: str):
    from app.core.imagery.scene_simulator import build_guided_session_replay
    r = build_guided_session_replay(session_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/scenes/session/{session_id}/replay")
async def get_replay(session_id: str):
    from app.core.imagery.scene_simulator import get_guided_session_replay
    r = get_guided_session_replay(session_id)
    if not r:
        raise HTTPException(404, "No replay found")
    return r


@router.get("/scenes/session/{session_id}/replay-summary")
async def get_replay_summary(session_id: str):
    from app.core.imagery.scene_simulator import export_guided_session_replay_summary
    return export_guided_session_replay_summary(session_id)


# ─── V23 Protocol Studio & Benchmark ────────────────────────────

@router.get("/protocols/builtin")
async def get_builtin_protocols():
    from app.core.imagery.protocol_library import get_builtin_protocol_library
    return get_builtin_protocol_library()


@router.get("/protocols/builtin/{template_id}")
async def get_builtin_protocol(template_id: str):
    from app.core.imagery.protocol_library import get_builtin_protocol
    r = get_builtin_protocol(template_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.post("/protocols/builtin/{user_id}/instantiate/{template_id}")
async def instantiate_protocol(user_id: str, template_id: str):
    from app.core.imagery.protocol_library import instantiate_builtin_protocol
    r = instantiate_builtin_protocol(user_id, template_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/protocols/{user_id}")
async def create_imagery_protocol_route(user_id: str, payload: dict):
    from app.core.imagery.protocol_studio import create_imagery_protocol
    return create_imagery_protocol(user_id, payload)


@router.get("/protocols/{protocol_id}")
async def get_imagery_protocol_route(protocol_id: str):
    from app.core.imagery.protocol_studio import get_imagery_protocol
    p = get_imagery_protocol(protocol_id)
    if not p:
        raise HTTPException(404, "Protocol not found")
    return p


@router.get("/protocols/user/{user_id}")
async def list_user_protocols(user_id: str):
    from app.core.imagery.protocol_studio import list_imagery_protocols
    return {"protocols": list_imagery_protocols(user_id)}


@router.delete("/protocols/{protocol_id}")
async def delete_imagery_protocol_route(protocol_id: str):
    from app.core.imagery.protocol_studio import delete_imagery_protocol
    return delete_imagery_protocol(protocol_id)


@router.post("/protocol-runs/{user_id}/start/{protocol_id}")
async def start_run(user_id: str, protocol_id: str):
    from app.core.imagery.protocol_studio import start_protocol_run
    r = start_protocol_run(user_id, protocol_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.get("/protocol-runs/{run_id}")
async def get_run(run_id: str):
    from app.core.imagery.protocol_studio import get_protocol_run
    r = get_protocol_run(run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return r


@router.get("/protocol-runs/user/{user_id}")
async def list_runs(user_id: str):
    from app.core.imagery.protocol_studio import list_protocol_runs
    return {"runs": list_protocol_runs(user_id)}


@router.get("/protocol-runs/user/{user_id}/active")
async def get_active_run(user_id: str):
    from app.core.imagery.protocol_studio import get_active_protocol_run
    r = get_active_protocol_run(user_id)
    if not r:
        raise HTTPException(404, "No active run")
    return r


@router.post("/protocol-runs/{run_id}/start-next-block")
async def start_block(run_id: str):
    from app.core.imagery.protocol_studio import start_next_protocol_block
    r = start_next_protocol_block(run_id)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.post("/protocol-runs/{run_id}/complete-block/{session_id}")
async def complete_block(run_id: str, session_id: str):
    from app.core.imagery.protocol_studio import complete_protocol_block
    r = complete_protocol_block(run_id, session_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/protocol-runs/{run_id}/pause")
async def pause_run(run_id: str):
    from app.core.imagery.protocol_studio import pause_protocol_run
    return pause_protocol_run(run_id)


@router.post("/protocol-runs/{run_id}/resume")
async def resume_run(run_id: str):
    from app.core.imagery.protocol_studio import resume_protocol_run
    return resume_protocol_run(run_id)


@router.post("/protocol-runs/{run_id}/complete")
async def complete_imagery_run(run_id: str):
    from app.core.imagery.protocol_studio import complete_protocol_run
    return complete_protocol_run(run_id)


@router.post("/protocol-runs/{run_id}/abort")
async def abort_run(run_id: str, payload: dict = None):
    from app.core.imagery.protocol_studio import abort_protocol_run
    return abort_protocol_run(run_id, (payload or {}).get("reason", ""))


@router.get("/protocol-runs/{run_id}/benchmark")
async def get_benchmark(run_id: str):
    from app.core.imagery.protocol_studio import analyze_protocol_run
    return analyze_protocol_run(run_id)


@router.post("/protocol-comparison/{user_id}")
async def compare_runs(user_id: str, payload: dict):
    from app.core.imagery.protocol_studio import compare_protocol_runs
    r = compare_protocol_runs(user_id, payload.get("run_ids", []))
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.post("/benchmark-export/{user_id}")
async def export_benchmark(user_id: str, payload: dict = None):
    from app.core.imagery.protocol_studio import export_imagina_benchmark_pack
    return export_imagina_benchmark_pack(user_id, (payload or {}).get("run_id"))


# ─── V24 SDK & Standard ─────────────────────────────────────────

@router.get("/sdk/schema")
async def get_sdk_schema():
    from app.core.imagery.protocol_sdk import get_external_protocol_schema
    return get_external_protocol_schema()


@router.get("/sdk/example")
async def get_sdk_example():
    from app.core.imagery.protocol_sdk import get_protocol_sdk_example
    return get_protocol_sdk_example()


@router.post("/sdk/validate")
async def validate_sdk_protocol(payload: dict):
    from app.core.imagery.protocol_sdk import validate_external_protocol
    return validate_external_protocol(payload)


@router.post("/sdk/import/{user_id}")
async def import_sdk_protocol(user_id: str, payload: dict):
    from app.core.imagery.protocol_sdk import import_external_protocol
    r = import_external_protocol(user_id, protocol_payload=payload)
    if r.get("error"):
        raise HTTPException(400, r.get("error", r.get("message", "")))
    return r


@router.get("/sdk/imports/{user_id}")
async def list_sdk_imports(user_id: str):
    from app.core.imagery.protocol_sdk import list_imported_protocols
    return {"imports": list_imported_protocols(user_id)}


@router.get("/sdk/export-protocol/{protocol_id}")
async def export_sdk_protocol(protocol_id: str):
    from app.core.imagery.protocol_sdk import save_protocol_sdk_file
    return save_protocol_sdk_file(protocol_id)


@router.post("/sdk/reproducibility/{user_id}")
async def build_repro_manifest(user_id: str, payload: dict = None):
    from app.core.imagery.protocol_sdk import build_reproducibility_manifest
    p = payload or {}
    return build_reproducibility_manifest(user_id, p.get("protocol_id"), p.get("run_id"))


@router.post("/sdk/demo/{user_id}")
async def seed_demo(user_id: str):
    from app.core.imagery.demo_data_seeder import seed_imagina_demo_user
    return seed_imagina_demo_user(user_id)


@router.post("/sdk/validate-pack")
async def validate_pack(payload: dict):
    import os

    from app.core.imagery.protocol_sdk import validate_benchmark_export_pack
    d = payload.get("export_dir", "")
    if not d or not os.path.exists(d):
        raise HTTPException(400, "export_dir required and must exist")
    return validate_benchmark_export_pack(d)


@router.post("/sdk/portfolio-summary/{user_id}")
async def build_portfolio(user_id: str):
    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary
    return build_portfolio_safe_summary(user_id)


@router.get("/sdk/portfolio-summary/{user_id}")
async def get_portfolio(user_id: str):
    from app.core.imagery.demo_data_seeder import get_portfolio_safe_summary
    r = get_portfolio_safe_summary(user_id)
    if not r:
        raise HTTPException(404, "No portfolio summary found")
    return r


# ─── V25 Showcase & Demo ────────────────────────────────────────

@router.get("/showcase/{user_id}")
async def get_showcase(user_id: str):
    from app.core.imagery.showcase_aggregator import get_imagina_showcase
    r = get_imagina_showcase(user_id)
    if not r:
        raise HTTPException(404, "Showcase not built. Run imagina_demo seed first.")
    return r


@router.post("/showcase/{user_id}/build")
async def build_showcase(user_id: str):
    from app.core.imagery.showcase_aggregator import build_imagina_showcase
    return build_imagina_showcase(user_id)


@router.post("/demo/{user_id}/full")
async def full_demo(user_id: str):
    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary, seed_imagina_demo_user
    from app.core.imagery.showcase_aggregator import build_imagina_showcase, build_release_manifest
    s = seed_imagina_demo_user(user_id, reset_existing=True)
    build_portfolio_safe_summary(user_id)
    sc = build_imagina_showcase(user_id)
    mf = build_release_manifest("V25")
    return {"demo": s, "showcase_id": sc.get("showcase_id", ""),
            "release_id": mf.get("release_id", ""),
            "frontend_url": "http://localhost:3000/imagina/showcase"}


# ─── V26 Release Candidate ──────────────────────────────────────

@router.get("/release/health")
async def get_release_health():
    from app.core.imagery.release_health import run_release_health_check
    return run_release_health_check()


@router.post("/release/health")
async def build_release_health():
    from app.core.imagery.release_health import run_release_health_check
    return run_release_health_check()


@router.post("/release/api-contract")
async def export_api_contract():
    from app.core.imagery.release_health import export_imagina_api_contract
    return export_imagina_api_contract()


@router.post("/release/architecture")
async def build_architecture():
    from app.core.imagery.release_health import build_imagina_architecture_map
    return build_imagina_architecture_map()


@router.post("/release/demo-script")
async def build_demo_scripts():
    from app.core.imagery.release_health import generate_reviewer_demo_script
    return generate_reviewer_demo_script()


@router.post("/release/whitepaper")
async def build_whitepaper():
    from app.core.imagery.release_health import build_imagina_technical_whitepaper
    return build_imagina_technical_whitepaper()


@router.post("/release/submission-pack/{user_id}")
async def build_submission_pack(user_id: str):
    from app.core.imagery.release_health import build_imagina_submission_pack
    return build_imagina_submission_pack(user_id)


@router.post("/release/all/{user_id}")
async def release_all(user_id: str):
    from app.core.imagery.release_health import (
        build_imagina_architecture_map,
        build_imagina_submission_pack,
        build_imagina_technical_whitepaper,
        export_imagina_api_contract,
        generate_reviewer_demo_script,
        run_release_health_check,
    )
    h = run_release_health_check()
    c = export_imagina_api_contract()
    a = build_imagina_architecture_map()
    ds = generate_reviewer_demo_script()
    w = build_imagina_technical_whitepaper()
    sp = build_imagina_submission_pack(user_id)
    return {"health": h["overall_status"], "api_contract_endpoints": c.get("total_endpoints", 0),
            "architecture_layers": len(a.get("layers", [])),
            "demo_scripts": len(ds.get("scripts_generated", [])),
            "whitepaper_sections": len(w.get("sections", [])),
            "submission_pack_files": sp.get("n_files", 0)}


# ─── V27 System Health & CI ─────────────────────────────────────

@router.get("/system/health")
async def system_health():
    import os
    dr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "imagina")
    return {"status": "ok", "service": "imagina-backend", "version": "V27",
            "data_root_exists": os.path.isdir(dr)}


@router.post("/local-ci/quick")
async def local_ci_quick():
    from app.cli.imagina_local_ci import run_local_ci
    return run_local_ci("quick")


@router.post("/local-ci/full")
async def local_ci_full():
    from app.cli.imagina_local_ci import run_local_ci
    return run_local_ci("full")


@router.post("/local-ci/release")
async def local_ci_release():
    from app.cli.imagina_local_ci import run_local_ci
    return run_local_ci("release")


@router.post("/release/artifact-index/{user_id}")
async def build_artifact_index(user_id: str):
    from app.cli.imagina_local_ci import build_release_artifact_index
    return build_release_artifact_index(user_id)


@router.get("/release/artifact-index/{user_id}")
async def get_artifact_index(user_id: str):
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "release_artifacts", "latest_artifact_index.json")
    if os.path.exists(p):
        return json.load(open(p))
    raise HTTPException(404, "Artifact index not built yet")


@router.post("/release/validate-submission-pack")
async def validate_submission(payload: dict):
    from app.cli.imagina_local_ci import validate_submission_pack
    d = payload.get("submission_dir", "")
    if not d:
        raise HTTPException(400, "submission_dir required")
    return validate_submission_pack(d)


# ─── V28 Biosignal Sandbox ──────────────────────────────────────

@router.get("/biosignals/sources")
async def list_biosignal_sources():
    from app.core.biosignals.biosignal_module import list_biosignal_sources
    return {"sources": list_biosignal_sources()}


@router.post("/biosignals/sources/simulated")
async def create_simulated_source():
    from app.core.biosignals.biosignal_module import create_simulated_eeg_source
    return create_simulated_eeg_source()


@router.get("/biosignals/sources/{source_id}")
async def get_biosignal_source(source_id: str):
    from app.core.biosignals.biosignal_module import get_biosignal_source
    r = get_biosignal_source(source_id)
    if not r:
        raise HTTPException(404, "Source not found")
    return r


@router.delete("/biosignals/sources/{source_id}")
async def delete_biosignal_source(source_id: str):
    from app.core.biosignals.biosignal_module import remove_biosignal_source
    return remove_biosignal_source(source_id)


@router.get("/biosignals/lsl/discover")
async def discover_lsl():
    from app.core.biosignals.biosignal_module import discover_lsl_streams
    return discover_lsl_streams()


@router.get("/biosignals/brainflow/status")
async def brainflow_status():
    from app.core.biosignals.biosignal_module import check_brainflow_available
    return check_brainflow_available()


@router.post("/biosignals/monitor/{guided_session_id}/start")
async def start_biosignal_monitor(guided_session_id: str, payload: dict = None):
    from app.core.biosignals.biosignal_module import start_biosignal_monitor_for_guided_session
    sid = (payload or {}).get("source_id", "simulated_eeg")
    return start_biosignal_monitor_for_guided_session(guided_session_id, sid)


@router.post("/biosignals/monitor/{monitor_id}/sample")
async def sample_monitor(monitor_id: str):
    from app.core.biosignals.biosignal_module import sample_biosignal_monitor
    return sample_biosignal_monitor(monitor_id)


@router.post("/biosignals/monitor/{monitor_id}/stop")
async def stop_monitor(monitor_id: str):
    from app.core.biosignals.biosignal_module import stop_biosignal_monitor
    return stop_biosignal_monitor(monitor_id)


@router.get("/biosignals/monitor/{monitor_id}/summary")
async def monitor_summary(monitor_id: str):
    from app.core.biosignals.biosignal_module import get_biosignal_monitor_summary
    r = get_biosignal_monitor_summary(monitor_id)
    if not r:
        raise HTTPException(404, "Monitor not found")
    return r


@router.get("/biosignals/report/{guided_session_id}")
async def biosignal_report(guided_session_id: str):
    from app.core.biosignals.biosignal_module import build_biosignal_session_report
    return build_biosignal_session_report(guided_session_id)


@router.get("/biosignals/boundaries")
async def biosignal_boundaries():
    from app.core.biosignals.biosignal_module import SAFETY
    return {"biosignal_boundary": SAFETY["biosignal_boundary"],
            "raw_eeg_export_default": SAFETY["raw_eeg_export_default"], **SAFETY}


# ─── V29 Realtime Biosignal Dashboard ───────────────────────────

@router.post("/biosignals/feed/{guided_session_id}/start")
async def start_feed(guided_session_id: str, payload: dict = None):
    from app.core.biosignals.biosignal_dashboard import create_realtime_feed_session
    sid = (payload or {}).get("source_id", "simulated_eeg")
    return create_realtime_feed_session(guided_session_id, sid)


@router.post("/biosignals/feed/{feed_id}/poll")
async def poll_feed(feed_id: str):
    from app.core.biosignals.biosignal_dashboard import poll_realtime_feed
    return poll_realtime_feed(feed_id)


@router.post("/biosignals/feed/{feed_id}/stop")
async def stop_feed(feed_id: str):
    from app.core.biosignals.biosignal_dashboard import stop_realtime_feed
    return stop_realtime_feed(feed_id)


@router.get("/biosignals/feed/{feed_id}/summary")
async def feed_summary(feed_id: str):
    from app.core.biosignals.biosignal_dashboard import get_realtime_feed_summary
    r = get_realtime_feed_summary(feed_id)
    if not r:
        raise HTTPException(404, "Feed not found")
    return r


@router.post("/biosignals/timeline/{guided_session_id}/build")
async def build_timeline(guided_session_id: str):
    from app.core.imagery.guided_session_runtime import get_guided_session
    gs = get_guided_session(guided_session_id)
    if not gs:
        raise HTTPException(404, "Session not found")
    from app.core.biosignals.biosignal_dashboard import build_biosignal_event_timeline
    return build_biosignal_event_timeline(guided_session_id,
                                           gs.get("biosignal_monitor_id"),
                                           gs.get("biosignal_marker_session_id"))


@router.get("/biosignals/timeline/{guided_session_id}")
async def get_timeline(guided_session_id: str):
    from app.core.biosignals.biosignal_dashboard import get_biosignal_event_timeline
    r = get_biosignal_event_timeline(guided_session_id)
    if not r:
        raise HTTPException(404, "Timeline not found")
    return r


@router.post("/biosignals/gate/evaluate")
async def evaluate_gate(payload: dict):
    from app.core.biosignals.biosignal_dashboard import evaluate_signal_quality_gate
    return evaluate_signal_quality_gate(payload)


@router.get("/biosignals/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    from app.core.biosignals.biosignal_dashboard import build_biosignal_dashboard_summary
    return build_biosignal_dashboard_summary(user_id)


@router.post("/biosignals/dashboard/{user_id}/build")
async def build_dashboard(user_id: str):
    from app.core.biosignals.biosignal_dashboard import build_biosignal_dashboard_summary
    return build_biosignal_dashboard_summary(user_id)


@router.post("/biosignals/export-safe/{user_id}")
async def export_safe(user_id: str, payload: dict = None):
    from app.core.biosignals.biosignal_dashboard import export_safe_biosignal_pack
    return export_safe_biosignal_pack(user_id, (payload or {}).get("guided_session_id"))


# ─── V30 Multimodal Fusion ──────────────────────────────────────

@router.post("/fusion/observation")
async def build_observation(payload: dict):
    from app.core.biosignals.fusion_multimodal import build_multimodal_observation
    p = payload or {}
    return build_multimodal_observation(p.get("guided_session_id"), p.get("feed_id"), p.get("user_id", "demo_user"))


@router.post("/fusion/state")
async def estimate_state(payload: dict):
    from app.core.biosignals.fusion_multimodal import estimate_adaptive_state
    return estimate_adaptive_state(payload)


@router.post("/fusion/policy")
async def recommend_policy(payload: dict):
    from app.core.biosignals.fusion_multimodal import recommend_neuroadaptive_policy
    return recommend_neuroadaptive_policy(payload.get("adaptive_state", {}), payload.get("observation", {}))


@router.post("/fusion/apply/{guided_session_id}")
async def apply_policy(guided_session_id: str, payload: dict):
    from app.core.biosignals.fusion_multimodal import apply_neuroadaptive_policy
    return apply_neuroadaptive_policy(guided_session_id, payload)


@router.post("/fusion/step")
async def run_fusion_step(payload: dict):
    from app.core.biosignals.fusion_multimodal import run_single_fusion_step
    p = payload or {}
    return run_single_fusion_step(p.get("user_id", "demo_user"),
                                   p.get("guided_session_id"), p.get("feed_id"))


@router.get("/fusion/summary/{user_id}")
async def get_fusion_summary(user_id: str):
    from app.core.biosignals.fusion_multimodal import build_fusion_session_summary
    return build_fusion_session_summary(user_id)


@router.post("/fusion/summary/{user_id}")
async def build_fusion_summary(user_id: str, payload: dict = None):
    from app.core.biosignals.fusion_multimodal import build_fusion_session_summary
    return build_fusion_session_summary(user_id, (payload or {}).get("guided_session_id"))


@router.post("/fusion/export-safe/{user_id}")
async def export_fusion_safe(user_id: str, payload: dict = None):
    from app.core.biosignals.fusion_multimodal import export_safe_fusion_pack
    return export_safe_fusion_pack(user_id, (payload or {}).get("guided_session_id"))


# ─── V31 Live Neuroadaptive Control Room ─────────────────────────

@router.get("/live/schema")
async def get_live_schema():
    from app.core.biosignals.live_neuroadaptive import get_live_event_schema
    return get_live_event_schema()


@router.post("/live/demo/{user_id}/start")
async def start_live_demo(user_id: str, payload: dict = None):
    from app.core.biosignals.live_neuroadaptive import start_live_neuroadaptive_demo
    p = payload or {}
    return start_live_neuroadaptive_demo(user_id, p.get("task_id", "red_circle_vividness"), p.get("source_id", "simulated_eeg"))


@router.post("/live/demo/{live_session_id}/step")
async def step_live_demo(live_session_id: str):
    from app.core.biosignals.live_neuroadaptive import step_live_neuroadaptive_demo
    return step_live_neuroadaptive_demo(live_session_id)


@router.post("/live/demo/{live_session_id}/checkin")
async def live_demo_checkin(live_session_id: str, payload: dict):
    from app.core.biosignals.live_neuroadaptive import submit_live_demo_checkin
    return submit_live_demo_checkin(live_session_id, payload)


@router.post("/live/demo/{live_session_id}/complete")
async def complete_live_demo(live_session_id: str):
    from app.core.biosignals.live_neuroadaptive import complete_live_neuroadaptive_demo
    return complete_live_neuroadaptive_demo(live_session_id)


@router.post("/live/demo/{live_session_id}/abort")
async def abort_live_demo(live_session_id: str, payload: dict = None):
    from app.core.biosignals.live_neuroadaptive import abort_live_neuroadaptive_demo
    return abort_live_neuroadaptive_demo(live_session_id, (payload or {}).get("reason", ""))


@router.get("/live/demo/{live_session_id}")
async def get_live_demo(live_session_id: str):
    from app.core.biosignals.live_neuroadaptive import get_live_neuroadaptive_demo
    r = get_live_neuroadaptive_demo(live_session_id)
    if not r:
        raise HTTPException(404, "Live demo not found")
    return r


@router.get("/live/events/{user_id}")
async def get_live_events(user_id: str):
    from app.core.biosignals.live_neuroadaptive import get_recent_live_events
    return {"events": get_recent_live_events(user_id, 100)}


@router.get("/live/summary/{user_id}")
async def get_live_summary(user_id: str):
    from app.core.biosignals.live_neuroadaptive import build_live_control_room_summary
    return build_live_control_room_summary(user_id)


@router.post("/live/export-safe/{user_id}")
async def export_live_safe(user_id: str, payload: dict = None):
    from app.core.biosignals.live_neuroadaptive import export_safe_live_demo_pack
    return export_safe_live_demo_pack(user_id, (payload or {}).get("live_session_id"))


# ─── V33 Live Scene Adaptation ──────────────────────────────────

@router.post("/live/scene/{live_session_id}/adapt")
async def build_live_scene_adaptation(live_session_id: str):
    from app.core.biosignals.scene_dynamics_engine import build_live_scene_adaptation_frame
    r = build_live_scene_adaptation_frame(live_session_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/live/scene/{live_session_id}/latest")
async def get_latest_scene_adaptation(live_session_id: str):
    from app.core.biosignals.scene_dynamics_engine import get_latest_live_scene_adaptation
    r = get_latest_live_scene_adaptation(live_session_id)
    if not r:
        raise HTTPException(404, "No scene adaptation found")
    return r


@router.post("/live/scene/{live_session_id}/replay/build")
async def build_live_scene_replay(live_session_id: str):
    from app.core.biosignals.scene_dynamics_engine import build_live_scene_replay
    r = build_live_scene_replay(live_session_id)
    if r.get("error"):
        raise HTTPException(404, r["error"])
    return r


@router.get("/live/scene/{live_session_id}/replay")
async def get_live_scene_replay(live_session_id: str):
    from app.core.biosignals.scene_dynamics_engine import get_live_scene_replay
    r = get_live_scene_replay(live_session_id)
    if not r:
        raise HTTPException(404, "Replay not found")
    return r


@router.post("/live/scene/export-safe/{user_id}")
async def export_live_scene_safe(user_id: str, payload: dict = None):
    from app.core.biosignals.scene_dynamics_engine import export_safe_live_scene_pack
    return export_safe_live_scene_pack(user_id, (payload or {}).get("live_session_id"))


@router.get("/live/scene/scenarios")
async def get_scene_scenarios():
    from app.core.biosignals.scene_dynamics_engine import get_scene_demo_scenarios
    return get_scene_demo_scenarios()


@router.post("/live/scene/scenarios/{user_id}/{scenario_id}/run")
async def run_scene_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.scene_dynamics_engine import run_scene_demo_scenario
    return run_scene_demo_scenario(user_id, scenario_id)


# ─── V35 Closed-Loop Benchmark ──────────────────────────────────

@router.get("/closed-loop/scenarios")
async def get_cl_scenarios():
    from app.core.biosignals.closed_loop_benchmark import get_closed_loop_benchmark_scenarios
    return get_closed_loop_benchmark_scenarios()


@router.get("/closed-loop/scenarios/{scenario_id}")
async def get_cl_scenario(scenario_id: str):
    from app.core.biosignals.closed_loop_benchmark import get_closed_loop_benchmark_scenario
    s = get_closed_loop_benchmark_scenario(scenario_id)
    if s.get("error"):
        raise HTTPException(404, s["error"])
    return s


@router.post("/closed-loop/run/{user_id}/{scenario_id}")
async def run_cl_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.closed_loop_benchmark import run_closed_loop_benchmark_scenario
    return run_closed_loop_benchmark_scenario(user_id, scenario_id)


@router.post("/closed-loop/run-suite/{user_id}")
async def run_cl_suite(user_id: str, payload: dict = None):
    from app.core.biosignals.closed_loop_benchmark import run_closed_loop_benchmark_suite
    return run_closed_loop_benchmark_suite(user_id, (payload or {}).get("scenario_ids"))


@router.get("/closed-loop/latest-suite/{user_id}")
async def get_latest_suite(user_id: str):
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "closed_loop_benchmarks", user_id, "latest_suite_result.json")
    if os.path.exists(p):
        return json.load(open(p))
    raise HTTPException(404, "No suite found")


@router.post("/closed-loop/metrics/{user_id}")
async def build_cl_metrics(user_id: str):
    from app.core.biosignals.closed_loop_benchmark import calculate_closed_loop_metrics
    return calculate_closed_loop_metrics()


@router.get("/closed-loop/metrics/{user_id}")
async def get_cl_metrics(user_id: str):
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "closed_loop_benchmarks", "metrics_user", "latest_metrics.json")
    if os.path.exists(p):
        return json.load(open(p))
    raise HTTPException(404, "No metrics found")


@router.post("/closed-loop/scorecard/{user_id}")
async def build_cl_scorecard(user_id: str):
    from app.core.biosignals.closed_loop_benchmark import build_neuroadaptive_ux_scorecard
    return build_neuroadaptive_ux_scorecard(user_id)


@router.get("/closed-loop/scorecard/{user_id}")
async def get_cl_scorecard(user_id: str):
    from app.core.biosignals.closed_loop_benchmark import get_neuroadaptive_ux_scorecard
    s = get_neuroadaptive_ux_scorecard(user_id)
    if not s:
        raise HTTPException(404, "No scorecard found")
    return s


@router.post("/closed-loop/export/{user_id}")
async def export_cl_benchmark(user_id: str):
    from app.core.biosignals.closed_loop_benchmark import export_closed_loop_benchmark_pack
    return export_closed_loop_benchmark_pack(user_id)


# ─── V37 Benchmark Scenario SDK ─────────────────────────────────

@router.get("/benchmark-sdk/schema")
async def get_benchmark_schema():
    from app.core.biosignals.benchmark_sdk import get_benchmark_scenario_schema
    return get_benchmark_scenario_schema()


@router.get("/benchmark-sdk/example")
async def get_benchmark_example():
    from app.core.biosignals.benchmark_sdk import get_benchmark_scenario_example
    return get_benchmark_scenario_example()


@router.post("/benchmark-sdk/validate")
async def validate_benchmark_scenario(payload: dict):
    from app.core.biosignals.benchmark_sdk import validate_benchmark_scenario_payload
    return validate_benchmark_scenario_payload(payload)


@router.post("/benchmark-sdk/import/{user_id}")
async def import_benchmark_scenario(user_id: str, payload: dict):
    from app.core.biosignals.benchmark_sdk import import_benchmark_scenario
    r = import_benchmark_scenario(user_id, payload)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.get("/benchmark-sdk/imported/{user_id}")
async def list_imported_scenarios(user_id: str):
    from app.core.biosignals.benchmark_sdk import list_imported_benchmark_scenarios
    return list_imported_benchmark_scenarios(user_id)


@router.get("/benchmark-sdk/imported/{user_id}/{scenario_id}")
async def get_imported_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.benchmark_sdk import get_imported_benchmark_scenario
    r = get_imported_benchmark_scenario(user_id, scenario_id)
    if not r:
        raise HTTPException(404, "Scenario not found")
    return r


@router.delete("/benchmark-sdk/imported/{user_id}/{scenario_id}")
async def remove_imported_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.benchmark_sdk import remove_imported_benchmark_scenario
    return remove_imported_benchmark_scenario(user_id, scenario_id)


@router.get("/benchmark-sdk/export-scenario/{user_id}/{scenario_id}")
async def export_benchmark_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.benchmark_sdk import export_benchmark_scenario
    return export_benchmark_scenario(user_id, scenario_id)


@router.post("/benchmark-sdk/run-imported/{user_id}/{scenario_id}")
async def run_imported_cl_scenario(user_id: str, scenario_id: str):
    from app.core.biosignals.benchmark_sdk import run_imported_closed_loop_scenario
    return run_imported_closed_loop_scenario(user_id, scenario_id)


@router.post("/benchmark-sdk/suite/{user_id}")
async def create_benchmark_suite(user_id: str, payload: dict):
    from app.core.biosignals.benchmark_sdk import create_custom_benchmark_suite
    return create_custom_benchmark_suite(
        user_id, payload.get("suite_name", "Custom Suite"),
        payload.get("scenario_ids", []),
        payload.get("include_built_ins", False),
    )


@router.get("/benchmark-sdk/suites/{user_id}")
async def list_benchmark_suites(user_id: str):
    from app.core.biosignals.benchmark_sdk import list_custom_benchmark_suites
    return list_custom_benchmark_suites(user_id)


@router.get("/benchmark-sdk/suites/{user_id}/{suite_id}")
async def get_benchmark_suite(user_id: str, suite_id: str):
    from app.core.biosignals.benchmark_sdk import get_custom_benchmark_suite
    r = get_custom_benchmark_suite(user_id, suite_id)
    if not r:
        raise HTTPException(404, "Suite not found")
    return r


@router.post("/benchmark-sdk/suites/{user_id}/{suite_id}/run")
async def run_benchmark_suite(user_id: str, suite_id: str):
    from app.core.biosignals.benchmark_sdk import run_custom_benchmark_suite
    return run_custom_benchmark_suite(user_id, suite_id)


@router.post("/benchmark-sdk/export/{user_id}")
async def export_benchmark_sdk(user_id: str):
    from app.core.biosignals.benchmark_sdk import export_benchmark_sdk_pack
    return export_benchmark_sdk_pack(user_id)


# ─── V40 Adaptive Policy Lab ────────────────────────────────────

@router.get("/policy-lab/schema")
async def get_policy_schema():
    from app.core.biosignals.policy_lab import get_policy_profile_schema
    return get_policy_profile_schema()


@router.get("/policy-lab/example")
async def get_policy_example():
    from app.core.biosignals.policy_lab import get_policy_profile_example
    return get_policy_profile_example()


@router.get("/policy-lab/builtins")
async def get_builtin_policies():
    from app.core.biosignals.policy_lab import get_builtin_policy_profiles
    return get_builtin_policy_profiles()


@router.post("/policy-lab/validate")
async def validate_policy(payload: dict):
    from app.core.biosignals.policy_lab import validate_policy_profile
    return validate_policy_profile(payload)


@router.post("/policy-lab/import/{user_id}")
async def import_policy(user_id: str, payload: dict):
    from app.core.biosignals.policy_lab import import_policy_profile
    r = import_policy_profile(user_id, payload)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return r


@router.get("/policy-lab/profiles/{user_id}")
async def list_policies(user_id: str):
    from app.core.biosignals.policy_lab import list_policy_profiles
    return list_policy_profiles(user_id)


@router.get("/policy-lab/profiles/{user_id}/{policy_id}")
async def get_policy(user_id: str, policy_id: str):
    from app.core.biosignals.policy_lab import get_policy_profile
    r = get_policy_profile(user_id, policy_id)
    if not r:
        raise HTTPException(404, "Policy not found")
    return r


@router.post("/policy-lab/run/{user_id}/{policy_id}")
async def run_policy_benchmark(user_id: str, policy_id: str):
    from app.core.biosignals.policy_lab import run_policy_profile_benchmark
    return run_policy_profile_benchmark(user_id, policy_id)


@router.post("/policy-lab/run-matrix/{user_id}")
async def run_policy_matrix(user_id: str, payload: dict = None):
    from app.core.biosignals.policy_lab import run_policy_profile_benchmark_matrix
    p = payload or {}
    return run_policy_profile_benchmark_matrix(user_id, p.get("policy_ids"), p.get("scenario_ids"))


@router.get("/policy-lab/latest-matrix/{user_id}")
async def get_latest_matrix(user_id: str):
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "policy_benchmarks", user_id, "latest_policy_matrix.json")
    if os.path.exists(p):
        return json.load(open(p))
    raise HTTPException(404, "No matrix found")


@router.post("/policy-lab/leaderboard/{user_id}")
async def build_leaderboard(user_id: str):
    from app.core.biosignals.policy_lab import build_policy_leaderboard
    return build_policy_leaderboard(user_id)


@router.get("/policy-lab/leaderboard/{user_id}")
async def get_leaderboard(user_id: str):
    from app.core.biosignals.policy_lab import get_policy_leaderboard
    r = get_policy_leaderboard(user_id)
    if not r:
        raise HTTPException(404, "No leaderboard found")
    return r


@router.post("/policy-lab/export/{user_id}")
async def export_policy_lab(user_id: str):
    from app.core.biosignals.policy_lab import export_policy_lab_pack
    return export_policy_lab_pack(user_id)


# ─── V43 Capstone Demo ──────────────────────────────────────────

@router.post("/capstone/demo/{user_id}/run")
async def run_capstone(user_id: str):
    from app.core.imagery.capstone_demo import run_capstone_reviewer_demo
    return run_capstone_reviewer_demo(user_id)


@router.get("/capstone/demo/{user_id}/latest")
async def get_latest_capstone(user_id: str):
    from app.core.imagery.capstone_demo import get_latest_capstone_demo
    r = get_latest_capstone_demo(user_id)
    if not r:
        raise HTTPException(404, "No capstone demo found")
    return r


@router.post("/capstone/evidence-pack/{user_id}")
async def build_capstone_evidence(user_id: str):
    from app.core.imagery.capstone_demo import build_capstone_evidence_pack
    return build_capstone_evidence_pack(user_id)


@router.get("/capstone/evidence-pack/{user_id}/latest")
async def get_capstone_evidence(user_id: str):
    import json
    import os
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "capstone_evidence_packs", user_id)
    if os.path.isdir(d):
        dirs = sorted(os.listdir(d), reverse=True)
        for dn in dirs:
            p = os.path.join(d, dn, "manifest.json")
            if os.path.exists(p):
                return json.load(open(p))
    raise HTTPException(404, "No evidence pack found")


@router.post("/capstone/narrative/{user_id}")
async def build_capstone_narrative(user_id: str):
    from app.core.imagery.capstone_demo import build_capstone_narrative
    return build_capstone_narrative(user_id)


@router.get("/capstone/narrative/{user_id}")
async def get_capstone_narrative(user_id: str):
    import os
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                     "data", "imagina", "capstone_demos", user_id, "CAPSTONE_NARRATIVE.md")
    if os.path.exists(p):
        return {"narrative": open(p).read()}
    raise HTTPException(404, "Narrative not found")


@router.post("/capstone/readiness/{user_id}")
async def build_capstone_readiness(user_id: str):
    from app.core.imagery.capstone_demo import check_capstone_readiness
    return check_capstone_readiness(user_id)


@router.get("/capstone/readiness/{user_id}")
async def get_capstone_readiness(user_id: str):
    from app.core.imagery.capstone_demo import get_capstone_readiness
    r = get_capstone_readiness(user_id)
    if not r:
        raise HTTPException(404, "Readiness not checked")
    return r


@router.get("/capstone/boundaries")
async def get_capstone_boundaries():
    from app.core.imagery.capstone_demo import SAFETY
    return {"capstone_boundary": SAFETY["capstone_boundary"],
            "raw_eeg_export_default": SAFETY["raw_eeg_export_default"], **SAFETY}
