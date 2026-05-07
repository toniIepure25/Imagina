from app.core.constants import DISCLAIMER
from app.schemas.reports import SessionSummary
from app.services import calibration_service, experiment_service, session_service
from app.storage import event_store

TIMELINE_TYPES = {
    "iqi_update", "pid_update", "state_estimate",
    "curriculum_update", "feedback_action",
}


async def generate_json_report(session_id: str, summary: SessionSummary) -> dict:
    events = await event_store.list_events(session_id)
    session = await session_service.get_session(session_id)
    calibration = await calibration_service.get_calibration(session_id)
    experiment = (
        await experiment_service.run_progress(session.experiment_run_id)
        if session.experiment_run_id
        else None
    )
    iqi_rows = [ev.payload for ev in events if ev.event_type == "iqi_update"]
    pid_rows = [ev.payload for ev in events if ev.event_type == "pid_update"]
    state_rows = [ev.payload for ev in events if ev.event_type == "state_estimate"]
    curriculum_rows = [ev.payload for ev in events if ev.event_type == "curriculum_update"]
    self_report_rows = [ev.payload for ev in events if ev.event_type == "self_report"]

    def slope(rows: list[dict], key: str) -> float:
        values = [row.get(key) for row in rows if isinstance(row.get(key), (int, float))]
        if len(values) < 2:
            return 0.0
        return round((values[-1] - values[0]) / (len(values) - 1), 5)

    levels = [row.get("current_level") for row in curriculum_rows if isinstance(row.get("current_level"), int)]
    timeline = [
        {
            "event_type": ev.event_type,
            "timestamp": ev.timestamp.isoformat(),
            "payload": ev.payload,
        }
        for ev in events
        if ev.event_type in TIMELINE_TYPES
    ]
    return {
        "disclaimer": DISCLAIMER,
        "session_id": session_id,
        "metadata": {
            "user_id": session.user_id,
            "display_name": session.display_name,
            "mode": session.mode,
            "task_id": session.task_id,
            "signal_provider_id": session.signal_provider_id,
            "scenario": session.scenario,
            "experiment_run_id": session.experiment_run_id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        },
        "calibration": calibration.model_dump(mode="json") if calibration else None,
        "experiment": experiment,
        "summary": summary.model_dump(mode="json"),
        "analysis": {
            "iqi_slope": slope(iqi_rows, "iqi"),
            "pid_slope": slope(pid_rows, "pid"),
            "uncertainty_peak": max(
                [row.get("uncertainty", 0.0) for row in state_rows if isinstance(row.get("uncertainty"), (int, float))],
                default=0.0,
            ),
            "level_advances": sum(1 for prev, curr in zip(levels, levels[1:]) if curr > prev),
            "level_regressions": sum(1 for prev, curr in zip(levels, levels[1:]) if curr < prev),
            "self_report_count": len(self_report_rows),
        },
        "timeline": timeline,
        "exports": {
            "json_report": f"/api/reports/{session_id}",
            "html_report": f"/api/reports/{session_id}/html",
            "events_jsonl": f"/api/exports/session/{session_id}/events.jsonl",
            "timeline_csv": f"/api/exports/session/{session_id}/timeline.csv",
            "self_reports_csv": f"/api/exports/session/{session_id}/self_reports.csv",
            "summary_csv": f"/api/exports/session/{session_id}/summary.csv",
        },
        "event_count": len(events),
    }
