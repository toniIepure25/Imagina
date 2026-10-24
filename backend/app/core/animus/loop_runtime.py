"""ANIMUS closed-loop runtime — the first-class state machine.

Drives INITIALIZE -> CALIBRATE -> (OBSERVE -> INFER -> GENERATE -> PRESENT -> COLLECT_FEEDBACK ->
UPDATE_BELIEF -> SELECT_NEXT_ACTION -> CHECK_CONVERGENCE -> CONTINUE)* -> COMPLETE | ABORT. Every transition
is typed, timestamped, persisted (optionally), and deterministic under a fixed seed, so a session replays
bit-exactly. Evidence is gathered from a ``RespondentSource`` (the digital twin in benchmark/demo mode, or
injected user feedback in interactive mode) — the controller never sees the hidden target.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from app.core.animus import claims
from app.core.animus.belief_state import BeliefFusionEngine, FusionConfig
from app.core.animus.candidate_generator import DeterministicSceneGenerator
from app.core.animus.controller import (
    ASK_REIMAGINE,
    COMPLETE,
    GENERATE_CONTRAST_PAIR,
    GENERATE_SINGLE,
    HOLD_STABLE,
    PROBE_ATTRIBUTE,
    PROBE_OBJECT,
    REACTIVATE_REFERENCE,
    AnimusPolicyConfig,
    ControlContext,
    build_controller,
)
from app.core.animus.feedback import normalize_feedback, twin_confidence_feedback
from app.core.animus.models import (
    FB_CLOSER_FARTHER,
    FB_OBJECT,
    SOURCE_SIMULATED_NEURAL,
    Candidate,
    ImaginationBeliefState,
    canonical_hash,
)
from app.core.animus.observation import ProviderUnavailableError, build_provider
from app.core.time import utcnow

# States.
INITIALIZE = "INITIALIZE"
CALIBRATE = "CALIBRATE"
OBSERVE = "OBSERVE"
INFER = "INFER"
GENERATE = "GENERATE"
PRESENT = "PRESENT"
COLLECT_FEEDBACK = "COLLECT_FEEDBACK"
UPDATE_BELIEF = "UPDATE_BELIEF"
SELECT_NEXT_ACTION = "SELECT_NEXT_ACTION"
CHECK_CONVERGENCE = "CHECK_CONVERGENCE"
CONTINUE = "CONTINUE"
COMPLETE_STATE = "COMPLETE"
ABORT = "ABORT"

# Event types (section 25).
EV_SESSION_STARTED = "animus.session.started"
EV_OBSERVATION = "animus.observation.received"
EV_BELIEF_UPDATED = "animus.belief.updated"
EV_CANDIDATE_GENERATED = "animus.candidate.generated"
EV_CANDIDATE_PRESENTED = "animus.candidate.presented"
EV_FEEDBACK = "animus.feedback.received"
EV_CONTROLLER_ACTION = "animus.controller.action"
EV_CONVERGENCE = "animus.convergence.updated"
EV_SAFETY = "animus.safety.event"
EV_SESSION_COMPLETED = "animus.session.completed"
EV_ABORT = "animus.session.aborted"


class RespondentSource(Protocol):
    """What the loop needs from whatever is answering (twin or injected user feedback)."""
    def neural_context(self) -> dict: ...
    def comparative(self, cur_emb, prev_emb) -> dict: ...
    def prefer(self, a_emb, b_emb) -> str: ...
    def probe_attribute(self, attr: str) -> dict: ...
    def probe_object(self, obj: str) -> dict: ...
    def clarity(self, emb) -> float: ...
    def fatigue(self) -> float: ...


@dataclass
class LoopConfig:
    session_id: str
    seed: int = 20260909
    controller: str = "ANIMUS_ACTIVE"
    max_iterations: int = 8
    observation_mode: str | None = SOURCE_SIMULATED_NEURAL   # None => behavioral only
    calibration_seed: int = 7
    fatigue_budget: float = 1.0
    max_loop_seconds: float = 0.0                            # 0 => unbounded (benchmark)
    claim_ceiling: str = claims.MAX_AUTHORIZED_LEVEL
    persist: bool = False
    policy: AnimusPolicyConfig = field(default_factory=AnimusPolicyConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)

    def to_dict(self) -> dict:
        return {"session_id": self.session_id, "seed": self.seed, "controller": self.controller,
                "max_iterations": self.max_iterations, "observation_mode": self.observation_mode,
                "calibration_seed": self.calibration_seed, "fatigue_budget": self.fatigue_budget,
                "claim_ceiling": self.claim_ceiling, "policy": self.policy.to_dict(),
                "fusion": self.fusion.to_dict()}


class AnimusAbort(RuntimeError):
    def __init__(self, reason: str, state: str, recoverable: bool):
        super().__init__(reason)
        self.reason, self.state, self.recoverable = reason, state, recoverable


@dataclass
class LoopResult:
    session_id: str
    final_state: str
    belief: ImaginationBeliefState
    events: list[dict]
    candidates: list[Candidate]
    iterations: int
    action_counts: dict[str, int]
    uncertainty_series: list[float]
    clarity_series: list[float]
    belief_hashes: list[str]
    aborted: bool = False
    abort_reason: str | None = None

    def replay_hash(self) -> str:
        return canonical_hash({"belief_hashes": self.belief_hashes,
                               "actions": sorted(self.action_counts.items()),
                               "final": self.belief.history_hash()})


class AnimusLoop:
    """Deterministic closed-loop runtime."""

    def __init__(self, config: LoopConfig, respondent: RespondentSource,
                 imaginer=None, belief: ImaginationBeliefState | None = None):
        self.cfg = config
        self.auth = claims.ClaimAuthorization(max_level=config.claim_ceiling)
        self.respondent = respondent
        self.imaginer = imaginer
        self.belief = belief or ImaginationBeliefState.broad_prior(
            provenance={"session_id": config.session_id, "seed": config.seed})
        self.fusion = BeliefFusionEngine(config.fusion)
        self.controller = build_controller(config.controller, config.policy)
        self.generator = DeterministicSceneGenerator()
        self.rng = np.random.default_rng(config.seed)
        self._provider = None
        if config.observation_mode == SOURCE_SIMULATED_NEURAL and imaginer is not None:
            self._provider = build_provider(SOURCE_SIMULATED_NEURAL, imaginer=imaginer,
                                             calibration_seed=config.calibration_seed,
                                             dim=len(self.belief.visual_embedding.mean))
        self.events: list[dict] = []
        self.candidates: list[Candidate] = []
        self.action_counts: dict[str, int] = {}
        self.uncertainty_series: list[float] = []
        self.clarity_series: list[float] = []
        self.belief_hashes: list[str] = []
        self.state = INITIALIZE
        self._prev_candidate_emb: list[float] | None = None
        self._iter = 0

    # --- event helper ---------------------------------------------------------
    def _emit(self, etype: str, payload: dict):
        ev = {"event_id": hashlib.sha256(f"{self.cfg.session_id}:{len(self.events)}".encode()).hexdigest()[:16],
              "session_id": self.cfg.session_id, "seq": len(self.events), "event_type": etype,
              "timestamp": utcnow().isoformat(), "iteration": self._iter,
              "claim_level": self.auth.max_level, "payload": payload}
        self.events.append(ev)
        if self.cfg.persist:
            from app.core.events.event_store import append_event
            append_event(f"animus-{self.cfg.session_id}", ev)
        return ev

    # --- lifecycle ------------------------------------------------------------
    def initialize(self):
        self.state = INITIALIZE
        self.auth.enforce(self.auth.max_level)
        self._emit(EV_SESSION_STARTED, {"config": self.cfg.to_dict(),
                                        "claim_label": claims.label_for(self.auth.max_level)})
        self.state = CALIBRATE
        self.uncertainty_series.append(self.belief.global_uncertainty())
        self.belief_hashes.append(self.belief.history_hash())

    def run(self) -> LoopResult:
        self.initialize()
        try:
            while True:
                cont = self.step()
                if not cont:
                    break
        except AnimusAbort as ab:
            self._emit(EV_ABORT, {"reason": ab.reason, "state": ab.state, "recoverable": ab.recoverable})
            return self._result(final_state=ABORT, aborted=True, abort_reason=ab.reason)
        return self._result(final_state=COMPLETE_STATE)

    def step(self) -> bool:
        """One full loop iteration. Returns False when the loop should stop."""
        # SELECT_NEXT_ACTION
        self.state = SELECT_NEXT_ACTION
        ctx = ControlContext(iteration=self._iter, max_iterations=self.cfg.max_iterations,
                             fatigue=self.respondent.fatigue(),
                             neural_available=self._provider is not None,
                             behavioral_available=True,
                             rng=np.random.default_rng(self.cfg.seed * 7919 + self._iter))
        decision = self.controller.select_action(self.belief, ctx)
        action = decision["action"]
        self._emit(EV_CONTROLLER_ACTION, {"decision": decision, "fatigue": round(ctx.fatigue, 4)})
        if action == COMPLETE:
            return False
        self.action_counts[action] = self.action_counts.get(action, 0) + 1

        # safety: fatigue budget
        if ctx.fatigue > self.cfg.fatigue_budget:
            self._emit(EV_SAFETY, {"type": "fatigue_budget_exceeded", "fatigue": round(ctx.fatigue, 4)})
            raise AnimusAbort("fatigue budget exceeded", COLLECT_FEEDBACK, recoverable=True)

        gathered = self._execute_action(action, decision.get("params", {}))
        self._apply_evidence(gathered)

        # CHECK_CONVERGENCE
        self.state = CHECK_CONVERGENCE
        gu = self.belief.global_uncertainty()
        self.uncertainty_series.append(gu)
        self.belief.iteration = self._iter + 1
        self.belief_hashes.append(self.belief.history_hash())
        self._emit(EV_CONVERGENCE, {"global_uncertainty": round(gu, 6),
                                    "confidence_by_component": self.belief.confidence_by_component()})
        self._iter += 1
        if self._iter >= self.cfg.max_iterations:
            return False
        return True

    # --- action execution -----------------------------------------------------
    def _execute_action(self, action: str, params: dict) -> dict:
        gathered: dict = {"observations": [], "feedback": []}
        if action in (GENERATE_SINGLE, GENERATE_CONTRAST_PAIR):
            self.state = GENERATE
            n = 2 if action == GENERATE_CONTRAST_PAIR else 1
            req = {"seed": self.cfg.seed, "n": n, "jitter": params.get("jitter", 0.0),
                   "static": params.get("static", False)}
            cset = self.generator.generate(self.belief, req)
            for c in cset.candidates:
                self.candidates.append(c)
                self._emit(EV_CANDIDATE_GENERATED, {"candidate": c.to_dict()})
            self.state = PRESENT
            self._emit(EV_CANDIDATE_PRESENTED, {"candidate_ids": [c.candidate_id for c in cset.candidates]})
            self.state = COLLECT_FEEDBACK
            if action == GENERATE_CONTRAST_PAIR and len(cset.candidates) == 2:
                a_emb = cset.candidates[0].visual_embedding
                b_emb = cset.candidates[1].visual_embedding
                winner = self.respondent.prefer(a_emb, b_emb)
                pref = a_emb if winner == "A" else b_emb
                gathered["feedback"].append({"channel": FB_CLOSER_FARTHER,
                                             "preferred_embedding": pref, "closer": True,
                                             "origin": "respondent"})
                self._prev_candidate_emb = pref
            else:
                cur = cset.candidates[0].visual_embedding
                cmp = self.respondent.comparative(cur, self._prev_candidate_emb)
                gathered["feedback"].append({"channel": FB_CLOSER_FARTHER,
                                             "preferred_embedding": cur,
                                             "closer": cmp["closer"], "origin": "respondent"})
                self._prev_candidate_emb = cur
            self._collect_neural(gathered, cset.candidates[0].visual_embedding)
            self.clarity_series.append(self.respondent.clarity(cset.candidates[0].visual_embedding))
        elif action == PROBE_ATTRIBUTE:
            self.state = COLLECT_FEEDBACK
            attr = params.get("attribute") or next(iter(self.belief.global_scene_attributes))
            resp = self.respondent.probe_attribute(attr)
            gathered["feedback"].append({"channel": "attribute_correction", **resp, "origin": "respondent"})
        elif action == PROBE_OBJECT:
            self.state = COLLECT_FEEDBACK
            obj = params.get("object") or next(iter(self.belief.objects))
            resp = self.respondent.probe_object(obj)
            gathered["feedback"].append({"channel": FB_OBJECT, **resp, "origin": "respondent"})
        elif action == REACTIVATE_REFERENCE:
            self.state = OBSERVE
            emb = self._prev_candidate_emb or list(self.belief.visual_embedding.mean)
            self._collect_neural(gathered, emb)
        elif action == ASK_REIMAGINE:
            self.state = COLLECT_FEEDBACK
            gathered["feedback"].append({"channel": "reimagine", "origin": "respondent"})
            self._collect_neural(gathered, list(self.belief.visual_embedding.mean))
        elif action == HOLD_STABLE:
            self.state = COLLECT_FEEDBACK
            conf = self.respondent.clarity(list(self.belief.visual_embedding.mean))
            gathered["feedback"].append({"channel": "confidence", "confidence": conf, "origin": "respondent"})
        return gathered

    def _collect_neural(self, gathered: dict, cur_emb):
        if self._provider is None:
            return
        try:
            obs = self._provider.observe({"previous_belief": self.belief.to_dict(),
                                          "current_candidate_embedding": cur_emb,
                                          "measurement_id": f"m{self._iter}"})
        except ProviderUnavailableError as exc:
            self._emit(EV_SAFETY, {"type": "observation_unavailable", "detail": str(exc)})
            return
        self.auth.enforce(obs.claim_level)
        gathered["observations"].append(obs)
        self._emit(EV_OBSERVATION, {"observation": obs.to_dict()})

    def _apply_evidence(self, gathered: dict):
        self.state = UPDATE_BELIEF
        for obs in gathered["observations"]:
            self.fusion.apply_observation(self.belief, obs)
        for raw in gathered["feedback"]:
            if raw.get("channel") == "confidence":
                fb = twin_confidence_feedback(float(raw.get("confidence", 0.0)))
            else:
                fb = normalize_feedback(raw, claim_level=self.auth.max_level)
            self.fusion.apply_feedback(self.belief, fb)
            self._emit(EV_FEEDBACK, {"feedback": fb.to_dict()})
        self._emit(EV_BELIEF_UPDATED, {"belief_hash": self.belief.history_hash(),
                                       "global_uncertainty": round(self.belief.global_uncertainty(), 6)})

    def _result(self, final_state: str, aborted: bool = False, abort_reason: str | None = None):
        if not aborted:
            self._emit(EV_SESSION_COMPLETED, {"iterations": self._iter,
                                              "final_belief_hash": self.belief.history_hash()})
        return LoopResult(
            session_id=self.cfg.session_id, final_state=final_state, belief=self.belief,
            events=self.events, candidates=self.candidates, iterations=self._iter,
            action_counts=self.action_counts, uncertainty_series=self.uncertainty_series,
            clarity_series=self.clarity_series, belief_hashes=self.belief_hashes,
            aborted=aborted, abort_reason=abort_reason)
