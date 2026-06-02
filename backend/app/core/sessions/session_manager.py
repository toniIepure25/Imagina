"""IMAGINA Session Manager — Main orchestration layer for closed-loop imagery training."""

import os
from uuid import uuid4

from app.core.curriculum.curriculum_manager import decide_curriculum_action
from app.core.events.domain_events import (
    curriculum_decision,
    feedback_action,
    iqi_computed,
    pid_computed,
    safety_decision,
    self_report,
    session_started,
    state_estimate,
    task_started,
)
from app.core.events.event_store import append_event, load_events, write_session_manifest
from app.core.feedback.feedback_policy import compute_scene_params
from app.core.metrics.imagery_quality_index import compute_iqi
from app.core.metrics.perception_imagination_distance import compute_pid
from app.core.safety.safety_monitor import check_safety
from app.core.tasks.imagery_task_engine import get_task

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "..", "data", "imagina", "sessions")


class SessionManager:
    """Manages an IMAGINA training session with event sourcing."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def start_session(self, user_id: str = "default", config: dict | None = None) -> dict:
        cfg = config or {"duration_minutes": 15, "user_id": user_id, "demo_mode": False}
        sid = str(uuid4())
        os.makedirs(os.path.join(SESSIONS_DIR, sid), exist_ok=True)

        ev = session_started(sid, cfg, user_id)
        append_event(sid, ev)
        write_session_manifest(sid, cfg)

        self._cache[sid] = {"config": cfg, "current_task_id": None,
                            "last_self_report": None, "demo_mode": cfg.get("demo_mode", False)}
        return {"session_id": sid, "user_id": user_id, "event": ev}

    def start_task(self, session_id: str, task_id: str = "shape_stabilization") -> dict:
        task = get_task(task_id)
        if not task:
            return {"error": f"Task '{task_id}' not found"}
        ev = task_started(session_id, task_id, task)
        append_event(session_id, ev)
        self._cache.setdefault(session_id, {})
        self._cache[session_id]["current_task_id"] = task_id
        return {"session_id": session_id, "task": task, "event": ev}

    def submit_self_report(self, session_id: str, vividness: float = 5.0,
                           stability: float = 5.0, effort: float = 5.0,
                           fatigue: float = 3.0, comfort: float = 7.0,
                           task_id: str = "unknown") -> dict:
        extra = {"fatigue_self": fatigue, "comfort": comfort}
        ev = self_report(session_id, task_id, vividness, stability, effort, extra)
        append_event(session_id, ev)
        self._cache.setdefault(session_id, {})
        self._cache[session_id]["last_self_report"] = {
            "vividness": vividness, "stability": stability, "effort": effort,
            "fatigue": fatigue, "comfort": comfort,
        }
        return {"session_id": session_id, "event": ev}

    def run_step(self, session_id: str) -> dict:
        """Execute one full pipeline step: state → IQI → PID → safety → curriculum → feedback."""
        ses = self._cache.get(session_id, {})
        events = load_events(session_id)
        is_demo = ses.get("demo_mode", False)

        # Gather latest self-report
        sr = ses.get("last_self_report", {"vividness": 5, "stability": 5, "effort": 5,
                                           "fatigue": 3, "comfort": 7})

        # Simulated or real features
        if is_demo:
            from app.core.state.simulated_signal_provider import get_demo_features
            feats = get_demo_features(ses.get("demo_profile", "stable_improving"), len(events))
        else:
            feats = {"attention_stability": 0.6, "relaxation": 0.5, "imagery_engagement": 0.55,
                     "fatigue_proxy": 0.2, "stress": 0.2, "uncertainty": 0.3}

        attn = feats.get("attention_stability", 0.6)
        relax = feats.get("relaxation", 0.5)
        engage = feats.get("imagery_engagement", 0.55)
        f_proxy = feats.get("fatigue_proxy", 0.2)
        stress = feats.get("stress", 0.2)
        uncertainty = feats.get("uncertainty", 0.3)

        # Self-report fatigue override
        f_combined = max(f_proxy, sr.get("fatigue", 3.0) / 10.0)

        # State estimate
        state = {"attention_stability": attn, "relaxation": relax,
                 "imagery_engagement": engage, "fatigue": f_combined,
                 "stress": stress, "uncertainty": uncertainty}
        append_event(session_id, state_estimate(session_id, state))

        # IQI
        iqi = compute_iqi(sr["vividness"], sr["stability"], sr["effort"],
                          attn, relax, engage, f_combined, uncertainty)
        append_event(session_id, iqi_computed(session_id, iqi["iqi_score"],
                                               iqi["confidence"], iqi["components"]))

        # PID
        pid = compute_pid(attn, relax, engage, f_combined, uncertainty,
                          sr["vividness"], sr["stability"])
        append_event(session_id, pid_computed(session_id, pid["pid_score"],
                                               pid["confidence"], pid["components"]))

        # Safety
        duration = len(events) * 0.5  # rough estimate: 30s per step
        safe = check_safety(fatigue=f_combined, attention_stability=attn,
                            discomfort_report=10 - sr.get("comfort", 7),
                            session_duration_minutes=duration)
        append_event(session_id, safety_decision(session_id, safe["action"], safe["message"]))

        # Curriculum
        iqi_hist = [e["payload"]["iqi_score"] for e in events if e["event_type"] == "iqi_computed"]
        cur = decide_curriculum_action(ses.get("current_level", 1),
                                       iqi_hist[-5:] if iqi_hist else [0.5],
                                       fatigue=f_combined, attention_stability=attn)
        append_event(session_id, curriculum_decision(session_id, cur["action"],
                                                      cur.get("next_task_id", ""), cur["reason"]))

        # Feedback
        fb = compute_scene_params(iqi["iqi_score"], pid["pid_score"], attn, relax,
                                  f_combined, uncertainty, engage,
                                  ses.get("current_level", 1))
        append_event(session_id, feedback_action(session_id, fb, fb["prompt"]))

        return {
            "session_id": session_id,
            "iqi_score": iqi["iqi_score"],
            "pid_score": pid["pid_score"],
            "safety_action": safe["action"],
            "curriculum_action": cur["action"],
            "scene_params": {k: v for k, v in fb.items() if k != "prompt"},
            "prompt": fb["prompt"],
            "state": state,
            "iqi_interpretation": iqi["interpretation"],
            "pid_interpretation": pid["interpretation"],
            "safety_message": safe["message"],
            "curriculum_message": cur["message"],
        }

    def get_summary(self, session_id: str) -> dict:
        events = load_events(session_id)
        if not events:
            return {"error": "No events found for this session"}
        iqi_scores = [e["payload"]["iqi_score"] for e in events
                      if e["event_type"] == "iqi_computed"]
        pid_scores = [e["payload"]["pid_score"] for e in events
                      if e["event_type"] == "pid_computed"]
        safety_actions = [e["payload"]["action"] for e in events
                          if e["event_type"] == "safety_decision"]
        cur_actions = [e["payload"]["action"] for e in events
                       if e["event_type"] == "curriculum_decision"]
        tasks_done = list(set(e["payload"].get("task_id", "") for e in events
                              if e["event_type"] == "task_started"))
        return {
            "session_id": session_id,
            "total_steps": len(events),
            "mean_iqi": round(sum(iqi_scores) / max(len(iqi_scores), 1), 3),
            "mean_pid": round(sum(pid_scores) / max(len(pid_scores), 1), 3),
            "tasks_completed": tasks_done,
            "curriculum_actions": {a: cur_actions.count(a) for a in set(cur_actions)},
            "safety_actions": {a: safety_actions.count(a) for a in set(safety_actions)},
            "disclaimer": "Experimental proxy metrics. Not clinical or validated neural measures.",
        }

    def get_events(self, session_id: str) -> list[dict]:
        return load_events(session_id)

    def replay_session(self, session_id: str) -> list[dict]:
        return load_events(session_id)


# Singleton
session_manager = SessionManager()
