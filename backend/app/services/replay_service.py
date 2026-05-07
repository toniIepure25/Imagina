"""
Replay service — creates deterministic demo sessions and replays event streams.
"""

import asyncio

from app.schemas.session import Session, SessionCreate
from app.services.curriculum_manager import CurriculumManager
from app.services.feature_engine import FeatureEngine
from app.services.feedback_policy_engine import FeedbackPolicyEngine
from app.services.pid_iqi_engine import PIDIQIEngine
from app.services.safety_monitor import SafetyMonitor
from app.services.session_service import create_session
from app.services.signal_simulator import SignalSimulator
from app.services.state_estimator import StateEstimator
from app.storage import event_store
from app.websocket.manager import ws_manager

_replay_states: dict[str, dict] = {}


async def create_demo_session(
    scenario: str = "improving_user",
    seed: int = 42,
    duration_windows: int = 30,
) -> Session:
    """Pre-generate a complete demo session and store all events."""
    session = await create_session(
        SessionCreate(display_name="Demo", mode="replay", task_id="corridor_simple")
    )
    sid = session.session_id
    baseline = {"focus": 6, "relaxation": 5, "vividness": 5, "fatigue": 3}
    await event_store.append_event(sid, "baseline_set", baseline)

    sim = SignalSimulator(seed=seed, scenario=scenario)
    feat_engine = FeatureEngine()
    state_est = StateEstimator()
    pid_iqi = PIDIQIEngine()
    curriculum = CurriculumManager()
    safety = SafetyMonitor()
    feedback = FeedbackPolicyEngine()

    improving_sr = None
    for i in range(duration_windows):
        t = i / duration_windows
        improving_sr = {
            "vividness": min(10, int(4 + 5 * t)),
            "stability": min(10, int(4 + 4 * t)),
            "focus": min(10, int(5 + 4 * t)),
            "relaxation": min(10, int(5 + 3 * t)),
            "effort": max(1, int(6 - 2 * t)),
            "fatigue": min(10, int(2 + 3 * t)),
            "distraction": max(1, int(5 - 3 * t)),
        }

        _, fv = sim.generate_window(sid, i, improving_sr, duration_windows)
        fv = feat_engine.process(fv)
        state = state_est.estimate(sid, fv, improving_sr, baseline, i)
        pid_est, iqi_est = pid_iqi.compute(sid, state, fv, i)
        curr = curriculum.update(sid, state, pid_est, iqi_est)
        fb = feedback.compute(sid, state, pid_est, iqi_est, curr, i)
        safety_events = safety.check(sid, state, improving_sr, i * 10, fv.signal_quality)

        await event_store.append_event(sid, "self_report", improving_sr)
        await event_store.append_event(sid, "feature_vector", fv.model_dump(mode="json"))
        await event_store.append_event(sid, "state_estimate", state.model_dump(mode="json"))
        await event_store.append_event(sid, "pid_update", pid_est.model_dump(mode="json"))
        await event_store.append_event(sid, "iqi_update", iqi_est.model_dump(mode="json"))
        await event_store.append_event(sid, "curriculum_update", curr.model_dump(mode="json"))
        await event_store.append_event(sid, "feedback_action", fb.model_dump(mode="json"))
        for se in safety_events:
            await event_store.append_event(sid, "safety_event", se.model_dump(mode="json"))

    return session


async def replay_to_websocket(session_id: str, speed: float = 1.0):
    """Stream stored events to a connected WebSocket client."""
    _replay_states[session_id] = {"running": True, "paused": False}
    events = await event_store.list_events(session_id)

    replay_types = {
        "feature_vector", "state_estimate", "pid_update", "iqi_update",
        "curriculum_update", "feedback_action", "safety_event", "self_report",
    }

    try:
        for ev in events:
            state = _replay_states.get(session_id, {})
            if not state.get("running", False):
                break
            while state.get("paused", False):
                await asyncio.sleep(0.1)
                state = _replay_states.get(session_id, {})
                if not state.get("running", False):
                    return
            if ev.event_type not in replay_types:
                continue
            if not ws_manager.is_connected(session_id):
                break
            await ws_manager.send(session_id, ev.event_type, ev.payload)
            await asyncio.sleep(0.5 / speed)
    finally:
        _replay_states.pop(session_id, None)


def pause_replay(session_id: str):
    state = _replay_states.get(session_id)
    if state:
        state["paused"] = True


def resume_replay(session_id: str):
    state = _replay_states.get(session_id)
    if state:
        state["paused"] = False


def stop_replay(session_id: str):
    state = _replay_states.get(session_id)
    if state:
        state["running"] = False
