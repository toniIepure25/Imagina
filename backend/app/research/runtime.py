"""Transport-independent research session runtime.

This is the core execution engine for research sessions. It does not depend on
FastAPI, WebSocket, or any transport layer. All dependencies are injected.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

import aiosqlite

from app.research.event_sinks import EventSink, RuntimeEvent
from app.research.id_generator import IdGenerator
from app.research.runtime_clock import RuntimeClock
from app.research.state_machines import (
    transition_session,
    transition_trial,
)

logger = logging.getLogger(__name__)


class ResearchFeedbackPolicy(Protocol):
    policy_id: str
    policy_version: str

    async def compute(self, context: "FeedbackContext") -> "FeedbackDecision": ...


class FeedbackContext:
    def __init__(
        self,
        session_id: str,
        trial_id: str | None,
        window_index: int,
        state_estimate: dict[str, float],
        feature_vector: dict[str, float],
        pid: float | None,
        iqi: float | None,
        curriculum_level: int,
        safety_context: dict[str, Any],
        seed: int,
    ):
        self.session_id = session_id
        self.trial_id = trial_id
        self.window_index = window_index
        self.state_estimate = state_estimate
        self.feature_vector = feature_vector
        self.pid = pid
        self.iqi = iqi
        self.curriculum_level = curriculum_level
        self.safety_context = safety_context
        self.seed = seed


class FeedbackDecision:
    def __init__(
        self,
        scene_params: dict[str, float],
        prompt_text: str,
        reason: str,
        policy_id: str,
        policy_version: str,
    ):
        self.scene_params = scene_params
        self.prompt_text = prompt_text
        self.reason = reason
        self.policy_id = policy_id
        self.policy_version = policy_version


class SafetyDecision:
    def __init__(self, should_stop: bool, severity: str = "none", reason_code: str = "", metric_name: str = "",
                 metric_value: float = 0.0, action: str = "continue"):
        self.should_stop = should_stop
        self.severity = severity
        self.reason_code = reason_code
        self.metric_name = metric_name
        self.metric_value = metric_value
        self.action = action


class RuntimeSafetyMonitor(Protocol):
    async def check(self, state: dict[str, float], window_index: int, elapsed_s: float) -> SafetyDecision: ...


class ResearchSessionRuntime:
    def __init__(
        self,
        db: aiosqlite.Connection,
        clock: RuntimeClock,
        id_gen: IdGenerator,
        feedback_policy: ResearchFeedbackPolicy,
        safety_monitor: RuntimeSafetyMonitor,
        event_sink: EventSink,
        signal_provider_fn: Any = None,
    ):
        self._db = db
        self._clock = clock
        self._id_gen = id_gen
        self._policy = feedback_policy
        self._safety = safety_monitor
        self._sink = event_sink
        self._signal_fn = signal_provider_fn

    async def run_session(
        self,
        research_session_id: str,
        trial_count: int = 5,
        windows_per_trial: int = 3,
    ) -> str:
        row = await (await self._db.execute(
            "SELECT status, state_version, runtime_seed FROM research_sessions "
            "WHERE research_session_id = ?",
            (research_session_id,),
        )).fetchone()

        if not row:
            raise ValueError(f"Session {research_session_id} not found")

        status = row["status"]
        version = row["state_version"]
        seed = row["runtime_seed"]

        if status == "planned":
            version = await transition_session(
                self._db, research_session_id, "planned", version, "ready",
                actor="runtime", timestamp=self._clock.utc_now(),
            )
            await self._db.commit()
            await self._sink.publish(RuntimeEvent(
                "session_ready", research_session_id, {"state_version": version},
                self._clock.utc_now(),
            ))

        if status in ("planned", "ready"):
            version = await transition_session(
                self._db, research_session_id, "ready", version, "running",
                actor="runtime", timestamp=self._clock.utc_now(),
            )
            await self._db.commit()
            await self._sink.publish(RuntimeEvent(
                "session_started", research_session_id, {"state_version": version},
                self._clock.utc_now(),
            ))

        session_start_mono = self._clock.monotonic()
        terminal_reason = "completed"

        for trial_idx in range(trial_count):
            trial_id = self._id_gen.generate("trial", research_session_id, trial_idx)

            existing = await (await self._db.execute(
                "SELECT trial_id FROM trials WHERE research_session_id = ? AND trial_index = ?",
                (research_session_id, trial_idx),
            )).fetchone()

            if not existing:
                await self._db.execute(
                    "INSERT INTO trials (trial_id, research_session_id, trial_index, "
                    "stimulus_id, status, state_version, planned_at) "
                    "VALUES (?, ?, ?, ?, 'planned', 0, ?)",
                    (trial_id, research_session_id, trial_idx,
                     f"corridor_stim_{trial_idx}", self._clock.utc_now().isoformat()),
                )
                await self._db.commit()
            else:
                trial_id = existing["trial_id"]

            trial_row = await (await self._db.execute(
                "SELECT status, state_version FROM trials WHERE trial_id = ?", (trial_id,)
            )).fetchone()
            tv = trial_row["state_version"]

            if trial_row["status"] == "planned":
                tv = await transition_trial(
                    self._db, trial_id, "planned", tv, "ready",
                    actor="runtime", timestamp=self._clock.utc_now(),
                )
                await self._db.commit()

            tv = await transition_trial(
                self._db, trial_id, "ready", tv, "running",
                actor="runtime", timestamp=self._clock.utc_now(),
            )
            trial_mono_start = self._clock.monotonic()
            await self._db.commit()

            safety_stopped = False
            for window_idx in range(windows_per_trial):
                elapsed = self._clock.monotonic() - session_start_mono

                features = self._generate_features(seed, trial_idx, window_idx)
                state_est = self._estimate_state(features)
                pid_val = self._compute_pid(state_est)
                iqi_val = self._compute_iqi(state_est)

                safety = await self._safety.check(state_est, window_idx, elapsed)

                ctx = FeedbackContext(
                    session_id=research_session_id,
                    trial_id=trial_id,
                    window_index=(trial_idx * windows_per_trial) + window_idx,
                    state_estimate=state_est,
                    feature_vector=features,
                    pid=pid_val,
                    iqi=iqi_val,
                    curriculum_level=1,
                    safety_context={"fatigue": state_est.get("fatigue", 0)},
                    seed=seed,
                )

                if safety.should_stop:
                    decision = FeedbackDecision(
                        scene_params={}, prompt_text="", reason="safety_override",
                        policy_id=self._policy.policy_id, policy_version=self._policy.policy_version,
                    )
                else:
                    decision = await self._policy.compute(ctx)

                import json
                fb_id = self._id_gen.generate("feedback", research_session_id,
                                              (trial_idx * windows_per_trial) + window_idx)
                await self._db.execute(
                    "INSERT INTO feedback_records "
                    "(feedback_record_id, research_session_id, trial_id, window_index, "
                    "condition, policy_id, policy_version, pid_value, iqi_value, "
                    "scene_params_json, reason_code, safety_override, timestamp_utc, mono_elapsed) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        fb_id, research_session_id, trial_id,
                        (trial_idx * windows_per_trial) + window_idx,
                        (await (await self._db.execute(
                            "SELECT condition FROM research_sessions WHERE research_session_id=?",
                            (research_session_id,)
                        )).fetchone())["condition"],
                        decision.policy_id, decision.policy_version,
                        pid_val, iqi_val,
                        json.dumps(decision.scene_params, sort_keys=True),
                        decision.reason, int(safety.should_stop),
                        self._clock.utc_now().isoformat(), elapsed,
                    ),
                )

                if safety.should_stop:
                    await self._db.execute(
                        "INSERT INTO safety_events "
                        "(safety_event_id, research_session_id, trial_id, severity, "
                        "reason_code, metric_name, metric_value, action_taken, timestamp_utc, mono_elapsed) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            self._id_gen.generate("safety", research_session_id, trial_idx),
                            research_session_id, trial_id, safety.severity,
                            safety.reason_code, safety.metric_name, safety.metric_value,
                            safety.action, self._clock.utc_now().isoformat(), elapsed,
                        ),
                    )
                    await self._db.commit()
                    await transition_trial(
                        self._db, trial_id, "running", tv, "safety_stopped",
                        reason_code=safety.reason_code, actor="safety_monitor",
                        timestamp=self._clock.utc_now(),
                    )
                    await self._db.commit()
                    safety_stopped = True
                    break

                await self._db.commit()
                await self._clock.sleep(0.1)

            if safety_stopped:
                row2 = await (await self._db.execute(
                    "SELECT state_version FROM research_sessions WHERE research_session_id=?",
                    (research_session_id,)
                )).fetchone()
                await transition_session(
                    self._db, research_session_id, "running", row2["state_version"],
                    "safety_stopped", reason_code="trial_safety_stop",
                    actor="safety_monitor", timestamp=self._clock.utc_now(),
                )
                await self._db.commit()
                terminal_reason = "safety_stopped"
                break

            if not safety_stopped:
                trial_mono_end = self._clock.monotonic()
                await self._db.execute(
                    "UPDATE trials SET mono_start=?, mono_end=? WHERE trial_id=?",
                    (trial_mono_start, trial_mono_end, trial_id),
                )

                response_id = self._id_gen.generate("response", trial_id, 0)
                await self._db.execute(
                    "INSERT INTO trial_responses "
                    "(trial_response_id, trial_id, vividness, confidence, effort, "
                    "imagery_formation_latency_ms, rating_completion_latency_ms, "
                    "response_source, recorded_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'synthetic', ?)",
                    (
                        response_id, trial_id,
                        0.5 + 0.1 * (trial_idx % 3),
                        0.6 + 0.05 * (trial_idx % 4),
                        0.3 + 0.1 * (trial_idx % 2),
                        800.0 + trial_idx * 50,
                        400.0 + trial_idx * 30,
                        self._clock.utc_now().isoformat(),
                    ),
                )

                trial_row2 = await (await self._db.execute(
                    "SELECT state_version FROM trials WHERE trial_id=?", (trial_id,)
                )).fetchone()
                await transition_trial(
                    self._db, trial_id, "running", trial_row2["state_version"],
                    "completed", actor="runtime", timestamp=self._clock.utc_now(),
                )
                await self._db.commit()

                await self._sink.publish(RuntimeEvent(
                    "trial_completed", research_session_id,
                    {"trial_id": trial_id, "trial_index": trial_idx},
                    self._clock.utc_now(), trial_id=trial_id,
                ))

        if terminal_reason == "completed":
            session_row = await (await self._db.execute(
                "SELECT state_version FROM research_sessions WHERE research_session_id=?",
                (research_session_id,)
            )).fetchone()
            await transition_session(
                self._db, research_session_id, "running", session_row["state_version"],
                "completed", actor="runtime", timestamp=self._clock.utc_now(),
            )
            await self._db.commit()

        await self._sink.publish(RuntimeEvent(
            "session_ended", research_session_id,
            {"terminal_reason": terminal_reason},
            self._clock.utc_now(),
        ))
        await self._sink.flush()

        return terminal_reason

    def _generate_features(self, seed: int, trial_idx: int, window_idx: int) -> dict[str, float]:
        import math
        t = (trial_idx * 10 + window_idx + seed) * 0.1
        return {
            "alpha": 0.5 + 0.2 * math.sin(t),
            "beta": 0.4 + 0.15 * math.cos(t * 1.3),
            "theta": 0.3 + 0.1 * math.sin(t * 0.7),
            "gamma": 0.2 + 0.1 * math.cos(t * 2.1),
        }

    def _estimate_state(self, features: dict[str, float]) -> dict[str, float]:
        alpha = features.get("alpha", 0.5)
        beta = features.get("beta", 0.4)
        theta = features.get("theta", 0.3)
        gamma = features.get("gamma", 0.2)
        return {
            "attention": min(1.0, max(0.0, beta / (theta + 0.01))),
            "relaxation": min(1.0, max(0.0, alpha * 1.5)),
            "engagement": min(1.0, max(0.0, gamma * 2.0)),
            "fatigue": min(1.0, max(0.0, theta * 1.2)),
        }

    def _compute_pid(self, state: dict[str, float]) -> float:
        attention = state.get("attention", 0.5)
        return max(0.0, min(1.0, 1.0 - attention * 0.7))

    def _compute_iqi(self, state: dict[str, float]) -> float:
        attention = state.get("attention", 0.5)
        engagement = state.get("engagement", 0.3)
        relaxation = state.get("relaxation", 0.5)
        return max(0.0, min(1.0, 0.35 * attention + 0.30 * engagement + 0.20 * relaxation + 0.15 * 0.5))
