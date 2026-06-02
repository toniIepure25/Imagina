"""IMAGINA Core Domain Events — Deterministic replay-friendly event schema."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


class ImaginaEventType:
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    SELF_REPORT = "self_report"
    SIGNAL_FEATURE = "signal_feature"
    STATE_ESTIMATE = "state_estimate"
    IQI_COMPUTED = "iqi_computed"
    PID_COMPUTED = "pid_computed"
    CURRICULUM_DECISION = "curriculum_decision"
    FEEDBACK_ACTION = "feedback_action"
    PERSONALIZATION_UPDATE = "personalization_update"
    SAFETY_DECISION = "safety_decision"
    SESSION_SUMMARY = "session_summary"
    METADATA_PREFLIGHT_RESULT = "metadata_preflight_result"


def create_event(
    event_type: ImaginaEventType,
    payload: dict[str, Any],
    session_id: str,
    user_id: str = "default",
    producer: str = "imagina_core",
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": payload,
        "producer": producer,
        "schema_version": "1.0",
    }


# Pre-built event factories for each domain event type

def session_started(session_id: str, config: dict, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.SESSION_STARTED, {"config": config}, session_id, user_id)


def task_started(session_id: str, task_id: str, task_config: dict,
                 user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.TASK_STARTED,
                        {"task_id": task_id, "task_config": task_config},
                        session_id, user_id)


def self_report(session_id: str, task_id: str, vividness: float, stability: float, effort: float,
                optional: Optional[dict] = None, user_id: str = "default") -> dict:
    payload = {"task_id": task_id, "vividness": vividness, "stability": stability, "effort": effort}
    if optional:
        payload.update(optional)
    return create_event(ImaginaEventType.SELF_REPORT, payload, session_id, user_id)


def signal_feature(session_id: str, features: dict, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.SIGNAL_FEATURE, {"features": features}, session_id, user_id)


def state_estimate(session_id: str, state: dict, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.STATE_ESTIMATE, {"state": state}, session_id, user_id)


def iqi_computed(session_id: str, iqi_score: float, confidence: float, components: dict,
                 user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.IQI_COMPUTED,
                        {"iqi_score": iqi_score, "confidence": confidence, "components": components},
                        session_id, user_id)


def pid_computed(session_id: str, pid_score: float, confidence: float, components: dict,
                 user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.PID_COMPUTED,
                        {"pid_score": pid_score, "confidence": confidence, "components": components},
                        session_id, user_id)


def curriculum_decision(session_id: str, action: str, next_task_id: str, reason: str,
                        user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.CURRICULUM_DECISION,
                        {"action": action, "next_task_id": next_task_id, "reason": reason},
                        session_id, user_id)


def feedback_action(session_id: str, scene_params: dict, prompt: str, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.FEEDBACK_ACTION,
                        {"scene_params": scene_params, "prompt": prompt}, session_id, user_id)


def personalization_update(session_id: str, profile_updates: dict, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.PERSONALIZATION_UPDATE,
                        {"profile_updates": profile_updates}, session_id, user_id)


def safety_decision(session_id: str, action: str, message: str, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.SAFETY_DECISION,
                        {"action": action, "message": message}, session_id, user_id)


def session_summary(session_id: str, summary: dict, user_id: str = "default") -> dict:
    return create_event(ImaginaEventType.SESSION_SUMMARY, {"summary": summary}, session_id, user_id)
