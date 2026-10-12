"""Closed-loop feedback controller.

State machine: IDLE -> CALIBRATION -> BASELINE -> ACTIVE_SHADOW | FEEDBACK_RESEARCH, plus PAUSED, SAFE_FALLBACK and
TERMINATED. ACTIVE_SHADOW computes and logs every decision without delivering it. FEEDBACK_RESEARCH delivers
feedback and requires a complete ``FeedbackAuthorization`` whenever any REAL_SENSOR stream is involved; synthetic
and replay sessions may use it so the full control path can be exercised in simulation.

Safety gates always run before the policy and can only make feedback more conservative. The controller never
optimizes the perception-imagination distance, arousal, or any measure of reality confusion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import numpy as np
from pydantic import BaseModel, Field

from app.multimodal.estimator import ImageryState
from app.multimodal.schemas import SourceKind, stable_hash
from app.services.safety_monitor import DISSOCIATION_KEYWORDS


class ControllerState(str, Enum):
    IDLE = "IDLE"
    CALIBRATION = "CALIBRATION"
    BASELINE = "BASELINE"
    ACTIVE_SHADOW = "ACTIVE_SHADOW"
    FEEDBACK_RESEARCH = "FEEDBACK_RESEARCH"
    PAUSED = "PAUSED"
    SAFE_FALLBACK = "SAFE_FALLBACK"
    TERMINATED = "TERMINATED"


S = ControllerState
TRANSITIONS: dict[ControllerState, set[ControllerState]] = {
    S.IDLE: {S.CALIBRATION, S.TERMINATED},
    S.CALIBRATION: {S.BASELINE, S.PAUSED, S.SAFE_FALLBACK, S.TERMINATED},
    S.BASELINE: {S.ACTIVE_SHADOW, S.FEEDBACK_RESEARCH, S.PAUSED, S.SAFE_FALLBACK, S.TERMINATED},
    S.ACTIVE_SHADOW: {S.FEEDBACK_RESEARCH, S.PAUSED, S.SAFE_FALLBACK, S.TERMINATED},
    S.FEEDBACK_RESEARCH: {S.ACTIVE_SHADOW, S.PAUSED, S.SAFE_FALLBACK, S.TERMINATED},
    S.PAUSED: {S.CALIBRATION, S.BASELINE, S.ACTIVE_SHADOW, S.FEEDBACK_RESEARCH, S.SAFE_FALLBACK, S.TERMINATED},
    S.SAFE_FALLBACK: {S.PAUSED, S.ACTIVE_SHADOW, S.TERMINATED},
    S.TERMINATED: set(),
}
ADAPTIVE_STATES = {S.ACTIVE_SHADOW, S.FEEDBACK_RESEARCH}


class TransitionError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


class FeedbackAuthorization(BaseModel):
    protocol_id: str = ""
    ethics_approval_ref: str = ""
    supervisor_id: str = ""
    signal_validation_ref: str = ""
    safety_review_ref: str = ""
    allow_real_sensor: bool = False

    def check(self, source_kinds: set[str]) -> tuple[bool, str]:
        if SourceKind.REAL_SENSOR.value not in source_kinds:
            return True, "simulation/replay only"
        missing = [k for k in ("protocol_id", "ethics_approval_ref", "supervisor_id", "signal_validation_ref",
                               "safety_review_ref") if not getattr(self, k)]
        if missing:
            return False, f"real-sensor feedback requires: {', '.join(missing)}"
        if not self.allow_real_sensor:
            return False, "authorization does not permit real-sensor feedback"
        return True, "authorized"


PARAMS = ("scene_complexity", "visual_cue_strength", "audio_guidance", "ambient_audio", "rest_cue")


class FeedbackParams(BaseModel):
    scene_complexity: float = Field(default=0.3, ge=0, le=1)
    visual_cue_strength: float = Field(default=0.5, ge=0, le=1)
    audio_guidance: float = Field(default=0.5, ge=0, le=1)
    ambient_audio: float = Field(default=0.3, ge=0, le=1)
    rest_cue: float = Field(default=0.0, ge=0, le=1)
    prompt_key: str = "default"

    def vector(self) -> np.ndarray:
        return np.array([getattr(self, p) for p in PARAMS])

    @classmethod
    def from_vector(cls, v: np.ndarray, prompt_key: str = "default") -> FeedbackParams:
        return cls(**{p: float(np.clip(x, 0, 1)) for p, x in zip(PARAMS, v)}, prompt_key=prompt_key)


NEUTRAL = FeedbackParams()
REST = FeedbackParams(scene_complexity=0.1, visual_cue_strength=0.2, audio_guidance=0.6, ambient_audio=0.2,
                      rest_cue=1.0, prompt_key="breathing")
UPPER_BOUNDS = {"scene_complexity": 0.85, "visual_cue_strength": 0.9, "audio_guidance": 0.8, "ambient_audio": 0.6,
                "rest_cue": 1.0}


class Policy(Protocol):
    name: str
    version: str
    objective: str

    def propose(self, state: ImageryState, ctx: dict) -> FeedbackParams: ...

    def update(self, outcome: dict) -> None: ...


class NoFeedbackPolicy:
    name, version, objective = "no_feedback", "1.0", "none"

    def propose(self, state, ctx):
        return NEUTRAL

    def update(self, outcome):
        pass


class BoundedRulePolicy:
    """Small, interpretable rules on calibrated proxies. Cue strength is capped by the curriculum fade level."""

    name, version, objective = "bounded_rules", "1.0", "support_attention_and_comfort"

    def propose(self, state, ctx):
        att = state.value("sustained_attention")
        effort = state.value("mental_effort")
        p = NEUTRAL.model_copy()
        key = "default"
        if att is not None:
            p.scene_complexity = 0.2 + 0.5 * att
            p.audio_guidance = 0.7 - 0.4 * att
            key = "good" if att > 0.6 else "low_attention"
        if effort is not None and effort > 0.7:
            p.scene_complexity = min(p.scene_complexity, 0.3)
            p.audio_guidance = max(p.audio_guidance, 0.6)
            key = "unstable"
        p.visual_cue_strength = min(p.visual_cue_strength, ctx.get("cue_cap", 1.0))
        p.prompt_key = key
        return p

    def update(self, outcome):
        pass


class PIDControllerPolicy:
    """Proportional-integral-derivative control of scene complexity toward an IQI setpoint (experimental proxy).
    Unrelated to the Perception-Imagination Distance metric."""

    name, version, objective = "pid_controller_iqi", "1.0", "iqi_setpoint_tracking"

    def __init__(self, setpoint: float = 0.6, kp: float = 0.6, ki: float = 0.05, kd: float = 0.1,
                 integral_limit: float = 2.0):
        self.setpoint, self.kp, self.ki, self.kd = setpoint, kp, ki, kd
        self.integral_limit = integral_limit
        self._i = 0.0
        self._prev: float | None = None

    def propose(self, state, ctx):
        p = NEUTRAL.model_copy()
        if state.iqi is None:
            return p
        err = state.iqi - self.setpoint
        self._i = float(np.clip(self._i + err, -self.integral_limit, self.integral_limit))
        d = 0.0 if self._prev is None else err - self._prev
        self._prev = err
        u = self.kp * err + self.ki * self._i + self.kd * d
        p.scene_complexity = float(np.clip(0.4 + u, 0, 1))
        p.visual_cue_strength = float(np.clip(0.5 - 0.5 * u, 0, ctx.get("cue_cap", 1.0)))
        p.prompt_key = "good" if err >= 0 else "building"
        return p

    def update(self, outcome):
        pass


class ShamPolicy:
    """Replays a yoked action sequence recorded from another session, independent of the current state."""

    name, version, objective = "sham_yoked", "1.0", "none"

    def __init__(self, yoked: list[dict]):
        self.yoked = yoked
        self._k = 0

    def propose(self, state, ctx):
        if not self.yoked:
            return NEUTRAL
        p = FeedbackParams(**self.yoked[self._k % len(self.yoked)])
        self._k += 1
        return p

    def update(self, outcome):
        pass


POLICY_REGISTRY: dict[str, Any] = {
    "no_feedback": NoFeedbackPolicy, "bounded_rules": BoundedRulePolicy, "pid_controller_iqi": PIDControllerPolicy,
    "sham_yoked": ShamPolicy,
}
FORBIDDEN_OBJECTIVES = {"perception_imagination_distance", "minimize_pid_metric", "maximize_arousal",
                        "reality_confusion", "dissociation"}


def register_policy(name: str, cls: Any) -> None:
    if getattr(cls, "objective", None) in FORBIDDEN_OBJECTIVES:
        raise ValueError(f"policy objective '{cls.objective}' is not permitted")
    POLICY_REGISTRY[name] = cls


class ControllerConfig(BaseModel):
    confidence_threshold: float = 0.3
    min_quality: float = 0.25
    max_alignment_uncertainty_s: float = 0.05
    require_known_alignment: bool = True
    ema_alpha: float = 0.3
    hysteresis: float = 0.05
    max_step: float = 0.1
    min_action_interval_s: float = 4.0
    session_limit_s: float = 1200.0
    fatigue_threshold: float = 0.80
    fatigue_consecutive: int = 2
    discomfort_threshold: float = 0.6
    min_reality_orientation: float = 0.5
    hold_ticks_before_fallback: int = 5
    allow_policy_update: bool = False


class GateInputs(BaseModel):
    usable_streams: int
    stale_streams: list[str] = Field(default_factory=list)
    disconnected_streams: list[str] = Field(default_factory=list)
    max_alignment_uncertainty_s: float | None = None
    mean_quality: float = 0.0
    source_kinds: list[str] = Field(default_factory=list)
    self_report_text: str = ""
    discomfort: float | None = None


class Decision(BaseModel):
    tick: int
    t: float
    controller_state: ControllerState
    policy: str
    policy_version: str
    estimate_summary: dict
    confidence: float
    safety_findings: list[dict]
    gates_passed: bool
    hold_reason: str = ""
    adaptation_note: str = ""
    proposed: dict | None = None
    applied: dict
    delivered: bool
    action_id: str
    input_hash: str
    prev_hash: str
    hash: str = ""


@dataclass
class SafetyFinding:
    code: str
    severity: str
    detail: str

    def as_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "detail": self.detail}


@dataclass
class FeedbackController:
    policy: Any
    config: ControllerConfig = field(default_factory=ControllerConfig)
    authorization: FeedbackAuthorization | None = None
    state: ControllerState = ControllerState.IDLE
    trace: list[Decision] = field(default_factory=list)
    transitions: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if getattr(self.policy, "objective", "") in FORBIDDEN_OBJECTIVES:
            raise ValueError(f"policy objective '{self.policy.objective}' is not permitted")
        self._ema: np.ndarray | None = None
        self._applied = NEUTRAL.model_copy()
        self._last_change_t = -np.inf
        self._fatigue_run = 0
        self._hold_run = 0
        self._tick = 0
        self._start_t: float | None = None
        self._estop = False
        self._prev_hash = "0" * 64
        self._delivering = False

    def transition(self, new: ControllerState, t: float, reason: str, source_kinds: set[str] | None = None) -> None:
        if new not in TRANSITIONS[self.state]:
            raise TransitionError(f"{self.state.value} -> {new.value} not allowed")
        if new == S.FEEDBACK_RESEARCH:
            ok, why = (self.authorization or FeedbackAuthorization()).check(source_kinds or set())
            if not ok:
                raise AuthorizationError(why)
        self.transitions.append({"t": t, "from": self.state.value, "to": new.value, "reason": reason})
        self.state = new
        if new == S.FEEDBACK_RESEARCH:
            self._delivering = True
        elif new in (S.ACTIVE_SHADOW, S.CALIBRATION, S.BASELINE):
            self._delivering = False
        if new == S.CALIBRATION and self._start_t is None:
            self._start_t = t

    def restore_state(self, state: ControllerState) -> None:
        """Replay only: re-apply a runtime-initiated transition that was recorded in the session log."""
        if state != self.state:
            self.state = state
            if state == S.FEEDBACK_RESEARCH:
                self._delivering = True
            elif state in (S.ACTIVE_SHADOW, S.CALIBRATION, S.BASELINE):
                self._delivering = False

    def emergency_stop(self, t: float, reason: str = "manual emergency stop") -> None:
        self._estop = True
        if self.state != S.TERMINATED:
            self.transitions.append({"t": t, "from": self.state.value, "to": S.TERMINATED.value, "reason": reason})
            self.state = S.TERMINATED
            self._applied = REST.model_copy()

    def pause(self, t: float, reason: str = "manual pause") -> None:
        if self.state not in (S.PAUSED, S.TERMINATED):
            self.transition(S.PAUSED, t, reason)

    def _safety(self, t: float, st: ImageryState, g: GateInputs) -> list[SafetyFinding]:
        c = self.config
        out = []
        if self._start_t is not None and t - self._start_t > c.session_limit_s:
            out.append(SafetyFinding("session_time_limit", "stop", f"> {c.session_limit_s:.0f}s"))
        if g.self_report_text and DISSOCIATION_KEYWORDS.search(g.self_report_text):
            out.append(SafetyFinding("dissociation_keyword", "fallback", "self-report contains distress keyword"))
        ro = st.value("reality_orientation")
        if ro is not None and ro < c.min_reality_orientation:
            out.append(SafetyFinding("reality_orientation_low", "fallback", f"reported {ro:.2f}"))
        if g.discomfort is not None and g.discomfort > c.discomfort_threshold:
            out.append(SafetyFinding("discomfort_reported", "fallback", f"reported {g.discomfort:.2f}"))
        fat = st.value("fatigue")
        self._fatigue_run = self._fatigue_run + 1 if fat is not None and fat > c.fatigue_threshold else 0
        if self._fatigue_run >= c.fatigue_consecutive:
            out.append(SafetyFinding("fatigue_high", "fallback", f"{self._fatigue_run} consecutive ticks"))
        if g.disconnected_streams:
            out.append(SafetyFinding("sensor_disconnected", "hold", ",".join(g.disconnected_streams)))
        if g.stale_streams:
            out.append(SafetyFinding("stale_data", "hold", ",".join(g.stale_streams)))
        if g.usable_streams == 0:
            out.append(SafetyFinding("no_usable_stream", "hold", ""))
        if g.mean_quality < c.min_quality:
            out.append(SafetyFinding("low_signal_quality", "hold", f"{g.mean_quality:.2f}"))
        if g.max_alignment_uncertainty_s is None and c.require_known_alignment:
            out.append(SafetyFinding("alignment_unknown", "hold", "sync uncertainty not observable"))
        elif g.max_alignment_uncertainty_s is not None and g.max_alignment_uncertainty_s > c.max_alignment_uncertainty_s:
            out.append(SafetyFinding("alignment_uncertain", "hold", f"{g.max_alignment_uncertainty_s * 1e3:.1f} ms"))
        if st.overall_confidence < c.confidence_threshold:
            out.append(SafetyFinding("low_confidence", "hold", f"{st.overall_confidence:.2f}"))
        return out

    def _bounded(self, proposed: FeedbackParams, t: float) -> tuple[FeedbackParams, str]:
        c = self.config
        v = proposed.vector()
        self._ema = v if self._ema is None else c.ema_alpha * v + (1 - c.ema_alpha) * self._ema
        cur = self._applied.vector()
        delta = self._ema - cur
        if np.max(np.abs(delta)) < c.hysteresis:
            return self._applied, "within_hysteresis"
        if t - self._last_change_t < c.min_action_interval_s:
            return self._applied, "rate_limited"
        new = cur + np.clip(delta, -c.max_step, c.max_step)
        new = np.minimum(new, [UPPER_BOUNDS[p] for p in ("scene_complexity", "visual_cue_strength", "audio_guidance",
                                                         "ambient_audio", "rest_cue")])
        self._last_change_t = t
        return FeedbackParams.from_vector(new, proposed.prompt_key), ""

    def tick(self, t: float, st: ImageryState, g: GateInputs, ctx: dict | None = None) -> Decision:
        ctx = ctx or {}
        self._tick += 1
        findings = self._safety(t, st, g) if self.state != S.TERMINATED else []
        sev = {f.severity for f in findings}
        proposed = None
        hold = ""
        note = ""
        if self.state != S.TERMINATED and "stop" in sev:
            self.transition(S.TERMINATED, t, "safety stop: " + ",".join(f.code for f in findings if f.severity == "stop"))
            self._applied = REST.model_copy()
        elif self.state in ADAPTIVE_STATES | {S.PAUSED} and "fallback" in sev:
            self.transition(S.SAFE_FALLBACK, t, ",".join(f.code for f in findings if f.severity == "fallback"))
            self._applied = REST.model_copy()
        elif self.state in ADAPTIVE_STATES:
            if "hold" in sev:
                self._hold_run += 1
                hold = ",".join(f.code for f in findings if f.severity == "hold")
                if self._hold_run >= self.config.hold_ticks_before_fallback:
                    self.transition(S.SAFE_FALLBACK, t, f"persistent hold: {hold}")
                    self._applied = REST.model_copy()
            else:
                self._hold_run = 0
                proposed = self.policy.propose(st, ctx)
                if getattr(proposed, "prompt_key", None) is None:
                    proposed.prompt_key = "default"
                self._applied, note = self._bounded(proposed, t)
        delivered = self.state == S.FEEDBACK_RESEARCH and not hold and proposed is not None and not note
        if self.state == S.SAFE_FALLBACK:
            delivered = self._delivering
        summary = {k: (None if d.value is None else round(d.value, 4), d.evidence_class.value)
                   for k, d in st.dimensions.items()}
        input_hash = stable_hash({"t": round(t, 6), "state": st.model_dump(mode="json"),
                                  "gates": g.model_dump(mode="json")})
        dec = Decision(
            tick=self._tick, t=t, controller_state=self.state, policy=self.policy.name,
            policy_version=self.policy.version, estimate_summary={"dimensions": summary, "iqi": st.iqi},
            confidence=st.overall_confidence, safety_findings=[f.as_dict() for f in findings],
            gates_passed=not findings or sev <= {"info"}, hold_reason=hold, adaptation_note=note,
            proposed=None if proposed is None else proposed.model_dump(), applied=self._applied.model_dump(),
            delivered=delivered, action_id=f"a{self._tick:05d}", input_hash=input_hash, prev_hash=self._prev_hash,
        )
        dec.hash = stable_hash(dec.model_dump(mode="json", exclude={"hash"}))
        self._prev_hash = dec.hash
        self.trace.append(dec)
        if self.config.allow_policy_update and self.state == S.FEEDBACK_RESEARCH and "outcome" in ctx:
            self.policy.update(ctx["outcome"])
        return dec


def verify_trace(trace: list[Decision]) -> bool:
    prev = "0" * 64
    for d in trace:
        if d.prev_hash != prev or stable_hash(d.model_dump(mode="json", exclude={"hash"})) != d.hash:
            return False
        prev = d.hash
    return True
