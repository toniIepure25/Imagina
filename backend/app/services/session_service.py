import uuid

from app.core.errors import SessionNotFoundError, SessionStateError
from app.core.time import utcnow
from app.schemas.session import Session, SessionCreate
from app.storage import event_store, repository


async def create_session(data: SessionCreate) -> Session:
    session = Session(
        session_id=str(uuid.uuid4()),
        user_id=data.user_id or str(uuid.uuid4()),
        display_name=data.display_name,
        mode=data.mode,
        status="created",
        task_id=data.task_id,
        signal_provider_id=data.signal_provider_id,
        scenario=data.scenario,
        experiment_run_id=data.experiment_run_id,
        created_at=utcnow(),
        safety_disclaimer_acknowledged=data.safety_disclaimer_acknowledged,
    )
    await repository.create_session(session)
    await event_store.append_event(
        session.session_id, "session_created", session.model_dump(mode="json")
    )
    return session


async def get_session(session_id: str) -> Session:
    session = await repository.get_session(session_id)
    if not session:
        raise SessionNotFoundError(session_id)
    return session


async def start_session(session_id: str) -> Session:
    session = await get_session(session_id)
    if session.status not in ("created", "calibrating"):
        raise SessionStateError(f"Cannot start session in status {session.status}")
    if not await get_baseline(session_id):
        raise SessionStateError("Baseline is required before starting session")
    now = utcnow()
    await repository.update_session_status(session_id, "running", started_at=now)
    await event_store.append_event(session_id, "session_started", {"started_at": now.isoformat()})
    session.status = "running"
    session.started_at = now
    return session


async def stop_session(session_id: str) -> Session:
    return await complete_session(session_id)


async def complete_session(session_id: str, reason: str = "user_stop") -> Session:
    session = await get_session(session_id)
    if session.status not in ("running", "paused", "calibrating"):
        raise SessionStateError(f"Cannot stop session in status {session.status}")
    now = utcnow()
    await repository.update_session_status(session_id, "completed", ended_at=now)
    await event_store.append_event(session_id, "session_stopped", {"ended_at": now.isoformat(), "reason": reason})
    session.status = "completed"
    session.ended_at = now
    try:
        from app.services.personalization_service import update_profile_after_summary
        from app.services.report_service import generate_summary

        summary = await generate_summary(session_id)
        await update_profile_after_summary(session.user_id, summary)
        if session.experiment_run_id:
            from app.services.experiment_service import attach_session

            await attach_session(session.experiment_run_id, session_id, completed=True)
    except Exception:
        pass
    return session


async def store_baseline(session_id: str, baseline: dict) -> None:
    await get_session(session_id)
    await repository.set_baseline(session_id, baseline)
    await repository.update_session_status(session_id, "calibrating")
    await event_store.append_event(session_id, "baseline_set", baseline)


async def store_self_report(session_id: str, report: dict) -> None:
    await get_session(session_id)
    await event_store.append_event(session_id, "self_report", report)


async def get_baseline(session_id: str) -> dict | None:
    return await repository.get_baseline(session_id)
