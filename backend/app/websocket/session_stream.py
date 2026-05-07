"""
Main real-time session loop.

Every ~2 seconds: simulator -> feature -> state -> PID/IQI -> curriculum -> feedback -> safety.
All events are emitted via WebSocket and persisted to the event store.
"""

import asyncio

from app.core.config import settings
from app.core.time import utcnow
from app.services import session_service
from app.services.curriculum_manager import CurriculumManager
from app.services.feature_engine import FeatureEngine
from app.services.feedback_policy_engine import FeedbackPolicyEngine
from app.services.pid_iqi_engine import PIDIQIEngine
from app.services.safety_monitor import SafetyMonitor
from app.services.signal_simulator import SignalSimulator
from app.services.state_estimator import StateEstimator
from app.storage import event_store
from app.websocket.manager import ws_manager

_session_states: dict[str, dict] = {}


def get_session_state(session_id: str) -> dict:
    return _session_states.get(session_id, {})


def is_session_loop_running(session_id: str) -> bool:
    return bool(_session_states.get(session_id, {}).get("running"))


def set_self_report(session_id: str, report: dict):
    state = _session_states.setdefault(session_id, {})
    state["self_report"] = report


async def _persist(sid: str, etype: str, payload):
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    await event_store.append_event(sid, etype, data)


async def _emit(sid: str, etype: str, payload):
    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    await ws_manager.send(sid, etype, data)


async def run_session_loop(
    session_id: str,
    scenario: str = "improving_user",
    seed: int = 42,
    baseline: dict | None = None,
    total_windows: int = 60,
):
    if is_session_loop_running(session_id):
        await _emit(session_id, "session_error", {"message": "Session loop is already running"})
        return

    if baseline is None:
        baseline = await session_service.get_baseline(session_id)

    sim = SignalSimulator(seed=seed, scenario=scenario)
    feat_engine = FeatureEngine()
    state_est = StateEstimator()
    pid_iqi = PIDIQIEngine()
    curriculum = CurriculumManager(starting_level=1)
    safety = SafetyMonitor(max_duration_s=settings.max_session_duration_seconds)
    feedback_engine = FeedbackPolicyEngine()

    _session_states[session_id] = {"self_report": None, "running": True, "stop_reason": None}
    start_time = utcnow()

    window_index = 0
    terminal_reason = None
    try:
        while _session_states.get(session_id, {}).get("running", False):
            if not ws_manager.is_connected(session_id):
                break

            sr = _session_states.get(session_id, {}).get("self_report")
            eeg, raw_fv = sim.generate_window(
                session_id, window_index, sr, total_windows
            )
            fv = feat_engine.process(raw_fv, sr)
            state = state_est.estimate(
                session_id, fv, sr, baseline, window_index
            )
            pid_est, iqi_est = pid_iqi.compute(
                session_id, state, fv, window_index
            )
            curr = curriculum.update(session_id, state, pid_est, iqi_est)
            fb = feedback_engine.compute(
                session_id, state, pid_est, iqi_est, curr, window_index
            )

            elapsed = (utcnow() - start_time).total_seconds()
            safety_events = safety.check(
                session_id, state, sr, elapsed, fv.signal_quality
            )

            await _persist(sid=session_id, etype="feature_vector", payload=fv)
            await _persist(sid=session_id, etype="state_estimate", payload=state)
            await _persist(sid=session_id, etype="pid_update", payload=pid_est)
            await _persist(sid=session_id, etype="iqi_update", payload=iqi_est)
            await _persist(sid=session_id, etype="curriculum_update", payload=curr)
            await _persist(sid=session_id, etype="feedback_action", payload=fb)
            for se in safety_events:
                await _persist(sid=session_id, etype="safety_event", payload=se)

            try:
                await _emit(session_id, "feature_vector", fv)
                await _emit(session_id, "state_estimate", state)
                await _emit(session_id, "pid_update", pid_est)
                await _emit(session_id, "iqi_update", iqi_est)
                await _emit(session_id, "curriculum_update", curr)
                await _emit(session_id, "feedback_action", fb)
                for se in safety_events:
                    await _emit(session_id, "safety_event", se)
            except Exception:
                break

            if any(se.severity == "stop" for se in safety_events):
                terminal_reason = "safety"
                break

            window_index += 1
            if window_index >= total_windows:
                terminal_reason = "completed"
                break
            await asyncio.sleep(settings.window_interval_seconds)
    finally:
        state = _session_states.get(session_id, {})
        terminal_reason = terminal_reason or state.get("stop_reason")
        if terminal_reason in {"completed", "safety", "user_stop"}:
            try:
                await session_service.complete_session(session_id, reason=terminal_reason)
            except Exception:
                pass
            await _emit(session_id, "session_stopped", {"reason": terminal_reason})
        _session_states.pop(session_id, None)


def stop_session_loop(session_id: str, reason: str = "user_stop"):
    state = _session_states.get(session_id)
    if state:
        state["running"] = False
        state["stop_reason"] = reason
