import uuid

from app.core.time import utcnow
from app.schemas.experiments import ExperimentProtocol, ExperimentRun, ExperimentRunCreate
from app.schemas.session import Session, SessionCreate
from app.services.report_service import generate_summary
from app.storage import repository

PROTOCOLS = [
    ExperimentProtocol(
        protocol_id="adaptive_guided_v1",
        name="Adaptive guided corridor",
        description="Default closed-loop curriculum with guided prompts and simulated-signal-assisted metrics.",
        condition="adaptive_curriculum",
        task_sequence=["corridor_simple", "corridor_doors"],
        duration_minutes=12,
        feedback_mode="guided_prompt_feedback",
        curriculum_mode="adaptive",
        catch_trial_rate=0.0,
        safety_limits={"max_fatigue": 0.8, "max_duration_minutes": 20},
        metrics_to_collect=["iqi", "pid", "fatigue", "uncertainty", "curriculum_level"],
    ),
    ExperimentProtocol(
        protocol_id="fixed_visual_control_v1",
        name="Fixed visual feedback control",
        description="Fixed curriculum and visual-only feedback for comparison against adaptive guidance.",
        condition="visual_feedback_only",
        task_sequence=["corridor_simple"],
        duration_minutes=10,
        feedback_mode="visual_only",
        curriculum_mode="fixed",
        catch_trial_rate=0.0,
        safety_limits={"max_fatigue": 0.75, "max_duration_minutes": 15},
        metrics_to_collect=["iqi", "pid", "fatigue", "self_report"],
    ),
    ExperimentProtocol(
        protocol_id="catch_trial_validation_v1",
        name="Catch-trial validation",
        description=(
            "Research-mode protocol where some trials may hold feedback constant "
            "to validate closed-loop effects."
        ),
        condition="catch_trial_control",
        task_sequence=["corridor_simple", "corridor_simple"],
        duration_minutes=12,
        feedback_mode="guided_prompt_feedback",
        curriculum_mode="adaptive",
        catch_trial_rate=0.15,
        safety_limits={"max_fatigue": 0.75, "max_duration_minutes": 15},
        metrics_to_collect=["iqi", "pid", "fatigue", "uncertainty", "catch_trial_flag"],
    ),
]


def list_protocols() -> list[ExperimentProtocol]:
    return PROTOCOLS


def get_protocol(protocol_id: str) -> ExperimentProtocol | None:
    return next((p for p in PROTOCOLS if p.protocol_id == protocol_id), None)


def _catch_trials(protocol: ExperimentProtocol) -> list[int]:
    if protocol.catch_trial_rate <= 0:
        return []
    total = max(1, len(protocol.task_sequence) * 10)
    step = max(1, round(1 / protocol.catch_trial_rate))
    return [i for i in range(step - 1, total, step)]


def _planned_sessions(protocol: ExperimentProtocol) -> list[dict]:
    scenario_by_condition = {
        "adaptive_curriculum": "improving_user",
        "fixed_curriculum": "unstable_user",
        "visual_feedback_only": "high_vividness_low_stability",
        "guided_prompt_feedback": "improving_user",
        "self_report_only": "low_vividness_improving",
        "simulated_signal_assisted": "improving_user",
        "catch_trial_control": "noisy_signal",
    }
    scenario = scenario_by_condition.get(protocol.condition, "improving_user")
    return [
        {
            "step": index,
            "task_id": task_id,
            "signal_provider_id": "simulated.default",
            "scenario": scenario,
            "duration_minutes": protocol.duration_minutes,
            "feedback_mode": protocol.feedback_mode,
            "curriculum_mode": protocol.curriculum_mode,
            "condition": protocol.condition,
            "catch_trial": bool(protocol.catch_trial_rate and index in _catch_trials(protocol)),
        }
        for index, task_id in enumerate(protocol.task_sequence)
    ]


async def create_run(data: ExperimentRunCreate) -> ExperimentRun:
    protocol = get_protocol(data.protocol_id)
    if not protocol:
        raise ValueError("Unknown protocol")
    run = ExperimentRun(
        run_id=str(uuid.uuid4()),
        protocol_id=data.protocol_id,
        participant_label=data.participant_label,
        planned_sessions=_planned_sessions(protocol),
        condition=protocol.condition,
        started_at=utcnow(),
        status="running",
        notes=data.notes,
        catch_trials=_catch_trials(protocol),
    )
    await save_run(run)
    return run


async def save_run(run: ExperimentRun) -> None:
    await repository.upsert_json(
        "experiment_runs",
        "run_id",
        run.run_id,
        run.model_dump(mode="json"),
        {
            "protocol_id": run.protocol_id,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "status": run.status,
        },
    )


async def get_run(run_id: str) -> ExperimentRun | None:
    payload = await repository.get_json("experiment_runs", "run_id", run_id)
    if not payload:
        return None
    run = ExperimentRun(**payload)
    protocol = get_protocol(run.protocol_id)
    if protocol and not run.planned_sessions:
        run.planned_sessions = _planned_sessions(protocol)
    if protocol and not run.condition:
        run.condition = protocol.condition
    return run


async def next_session(run_id: str, user_id: str | None = None) -> Session | None:
    run = await get_run(run_id)
    if not run:
        return None
    protocol = get_protocol(run.protocol_id)
    planned = run.planned_sessions or (_planned_sessions(protocol) if protocol else [])
    from app.services import session_service

    pending = [sid for sid in run.session_ids if sid not in run.completed_session_ids]
    if pending:
        try:
            return await session_service.get_session(pending[-1])
        except Exception:
            pass

    next_index = max(run.current_step, len(run.session_ids), len(run.completed_session_ids))
    if next_index >= len(planned):
        return None
    step = planned[next_index]

    session = await session_service.create_session(
        SessionCreate(
            user_id=user_id,
            display_name=run.participant_label,
            task_id=step.get("task_id", "corridor_simple"),
            mode="simulated",
            signal_provider_id=step.get("signal_provider_id", "simulated"),
            scenario=step.get("scenario", "improving_user"),
            experiment_run_id=run_id,
            safety_disclaimer_acknowledged=True,
        )
    )
    await attach_session(run_id, session.session_id, completed=False)
    return session


async def attach_session(run_id: str, session_id: str, completed: bool = False) -> ExperimentRun | None:
    run = await get_run(run_id)
    if not run:
        return None
    if session_id not in run.session_ids:
        run.session_ids.append(session_id)
    if completed and session_id not in run.completed_session_ids:
        run.completed_session_ids.append(session_id)
        run.current_step = min(len(run.planned_sessions), max(run.current_step, len(run.completed_session_ids)))
    elif not completed:
        run.current_step = max(run.current_step, len(run.completed_session_ids))
    if run.planned_sessions and len(run.completed_session_ids) >= len(run.planned_sessions):
        run.status = "completed"
        run.completed_at = run.completed_at or utcnow()
    await save_run(run)
    return run


async def run_progress(run_id: str) -> dict | None:
    run = await get_run(run_id)
    if not run:
        return None
    protocol = get_protocol(run.protocol_id)
    planned_count = len(run.planned_sessions)
    return {
        "run": run.model_dump(mode="json"),
        "protocol": protocol.model_dump(mode="json") if protocol else None,
        "planned_count": planned_count,
        "completed_count": len(run.completed_session_ids),
        "current_step": run.current_step,
        "next_step": run.planned_sessions[run.current_step] if run.current_step < planned_count else None,
        "percent_complete": round((len(run.completed_session_ids) / planned_count), 4) if planned_count else 0.0,
    }


async def complete_run(run_id: str) -> ExperimentRun | None:
    run = await get_run(run_id)
    if not run:
        return None
    run.status = "completed"
    run.completed_at = utcnow()
    await save_run(run)
    return run


async def run_summary(run_id: str) -> dict | None:
    run = await get_run(run_id)
    if not run:
        return None
    protocol = get_protocol(run.protocol_id)
    session_summaries = []
    for session_id in run.session_ids:
        try:
            session_summaries.append((await generate_summary(session_id)).model_dump(mode="json"))
        except Exception:
            continue
    avg_iqi = (
        round(sum(s["average_iqi"] for s in session_summaries) / len(session_summaries), 4)
        if session_summaries
        else 0.0
    )
    avg_pid = (
        round(sum(s["average_pid"] for s in session_summaries) / len(session_summaries), 4)
        if session_summaries
        else 1.0
    )
    return {
        "run": run.model_dump(mode="json"),
        "protocol": protocol.model_dump(mode="json") if protocol else None,
        "session_count": len(run.session_ids),
        "completed_session_count": len(run.completed_session_ids),
        "session_summaries": session_summaries,
        "aggregate_metrics": {
            "average_iqi": avg_iqi,
            "average_pid": avg_pid,
            "max_level_reached": max([s["max_level_reached"] for s in session_summaries], default=1),
            "fatigue_peak": max([s["fatigue_peak"] for s in session_summaries], default=0.0),
        },
        "catch_trial_count": len(run.catch_trials),
        "catch_trials": run.catch_trials,
        "limitations": "Research mode may include control feedback; disclose protocol conditions to participants.",
    }
