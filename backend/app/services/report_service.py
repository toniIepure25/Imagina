"""
Generates session summary reports from event store data.
"""

import logging

from app.core.time import utcnow
from app.schemas.reports import SessionSummary
from app.storage import event_store


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


async def generate_summary(session_id: str) -> SessionSummary:
    events = await event_store.list_events(session_id)

    iqi_values = []
    pid_values = []
    fatigue_values = []
    attention_values = []
    max_level = 1
    safety_count = 0
    first_ts = None
    last_ts = None

    for ev in events:
        if first_ts is None:
            first_ts = ev.timestamp
        last_ts = ev.timestamp

        if ev.event_type == "iqi_update":
            iqi_values.append(_safe_float(ev.payload.get("iqi")))
        elif ev.event_type == "pid_update":
            pid_values.append(_safe_float(ev.payload.get("pid"), 1.0))
        elif ev.event_type == "state_estimate":
            fatigue_values.append(_safe_float(ev.payload.get("fatigue")))
            attention_values.append(_safe_float(ev.payload.get("attention_stability")))
        elif ev.event_type == "curriculum_update":
            lvl = ev.payload.get("current_level", 1)
            if isinstance(lvl, (int, float)) and lvl > max_level:
                max_level = int(lvl)
        elif ev.event_type == "safety_event":
            safety_count += 1

    duration = (last_ts - first_ts).total_seconds() if first_ts and last_ts else 0.0
    avg_iqi = sum(iqi_values) / len(iqi_values) if iqi_values else 0.0
    best_iqi = max(iqi_values) if iqi_values else 0.0
    avg_pid = sum(pid_values) / len(pid_values) if pid_values else 1.0
    best_pid = min(pid_values) if pid_values else 1.0
    fatigue_peak = max(fatigue_values) if fatigue_values else 0.0

    # Best stability streak: consecutive windows with IQI > 0.6
    streak = 0
    best_streak = 0
    window_duration = 2.0
    for v in iqi_values:
        if v > 0.6:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0

    recommendation = _build_recommendation(avg_iqi, avg_pid, fatigue_peak, max_level)

    signal_provider_id = None
    scenario = None
    experiment_run_id = None
    calibration_quality_score = None
    real_signal = None
    provider_type = None

    try:
        from app.services import calibration_service, session_service

        session = await session_service.get_session(session_id)
        signal_provider_id = session.signal_provider_id
        scenario = session.scenario
        experiment_run_id = session.experiment_run_id

        if signal_provider_id:
            provider_type = signal_provider_id.split(".", 1)[0]
            real_signal = provider_type == "lsl"

        calibration = await calibration_service.get_calibration(session_id)
        if calibration:
            calibration_quality_score = calibration.calibration_quality_score
    except Exception:
        logging.getLogger(__name__).warning(
            "Could not attach V2 context to summary for session %s", session_id, exc_info=True
        )

    return SessionSummary(
        session_id=session_id,
        duration_seconds=round(duration, 1),
        average_pid=round(avg_pid, 4),
        best_pid=round(best_pid, 4),
        average_iqi=round(avg_iqi, 4),
        best_iqi=round(best_iqi, 4),
        max_level_reached=max_level,
        best_stability_streak_seconds=round(best_streak * window_duration, 1),
        fatigue_peak=round(fatigue_peak, 4),
        safety_events_count=safety_count,
        recommendation=recommendation,
        generated_at=utcnow(),
        signal_provider_id=signal_provider_id,
        scenario=scenario,
        experiment_run_id=experiment_run_id,
        calibration_quality_score=calibration_quality_score,
        real_signal=real_signal,
        provider_type=provider_type,
    )


def _build_recommendation(avg_iqi: float, avg_pid: float, fatigue_peak: float, max_level: int) -> str:
    parts = []
    if fatigue_peak > 0.75:
        parts.append("Use shorter sessions and more baseline breathing exercises.")
    if avg_iqi < 0.45:
        parts.append("Repeat early levels (1-2) with lower scene complexity to build stability.")
    if avg_iqi > 0.60 and avg_pid > 0.45:
        parts.append(
            "Stability is promising but vividness distance is high. "
            "Train stable geometry before adding detail."
        )
    if avg_iqi > 0.70 and avg_pid < 0.35:
        parts.append("Excellent progress. Continue at current level or advance to add more scene elements.")
    if max_level >= 6:
        parts.append("Try the Memory Room Return task for deeper imagery training.")
    if not parts:
        parts.append("Continue regular practice sessions. Consistency is more important than intensity.")
    return " ".join(parts)
