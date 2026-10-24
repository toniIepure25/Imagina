"""ANIMUS session service — in-process session registry for the API/SDK.

Manages live sessions in two product modes:

* **MODE_A amplifier (interactive):** no hidden target; the real user drives via ``apply_feedback`` /
  ``observe`` and the service generates the next candidate from the belief. No ground-truth similarity.
* **MODE_B blind benchmark / synthetic demo:** a server-side digital twin holds a hidden target (never
  exposed to the controller or the client) and ``step`` advances the closed loop automatically.

Everything is deterministic under a session seed and fully event-logged for replay. No raw neural data or
identifiers ever leave via candidates (enforced by the generation privacy boundary).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.animus import claims, metrics
from app.core.animus.belief_state import BeliefFusionEngine
from app.core.animus.benchmark import TwinRespondent, make_target
from app.core.animus.candidate_generator import DeterministicSceneGenerator
from app.core.animus.controller import AnimusPolicyConfig, ControlContext, build_controller
from app.core.animus.feedback import normalize_feedback, parse_freetext
from app.core.animus.loop_runtime import AnimusLoop, LoopConfig
from app.core.animus.models import SOURCE_SIMULATED_NEURAL, Candidate, ImaginationBeliefState
from app.core.animus.synthetic_imaginer import ImaginerParams, SyntheticImaginer
from app.core.time import utcnow

MODE_AMPLIFIER = "amplifier"        # interactive, no hidden target (MODE A)
MODE_BENCHMARK = "benchmark"        # twin-driven, hidden target (MODE B / synthetic demo)


class AnimusSessionError(RuntimeError):
    pass


@dataclass
class SessionState:
    session_id: str
    mode: str
    config: LoopConfig
    belief: ImaginationBeliefState
    generator: DeterministicSceneGenerator
    fusion: BeliefFusionEngine
    controller_name: str
    events: list[dict] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    loop: AnimusLoop | None = None          # for benchmark/synthetic mode
    twin: SyntheticImaginer | None = None
    iteration: int = 0
    active: bool = True
    clarity_series: list[float] = field(default_factory=list)
    uncertainty_series: list[float] = field(default_factory=list)
    initial_uncertainty: float = 0.0

    def _emit(self, etype: str, payload: dict):
        ev = {"seq": len(self.events), "event_type": etype, "timestamp": utcnow().isoformat(),
              "iteration": self.iteration, "claim_level": self.config.claim_ceiling, "payload": payload}
        self.events.append(ev)
        return ev


class AnimusService:
    def __init__(self):
        self._sessions: dict[str, SessionState] = {}

    # --- creation --------------------------------------------------------------
    def create_session(self, mode: str = MODE_AMPLIFIER, controller: str = "ANIMUS_ACTIVE",
                       seed: int = 20260909, max_iterations: int = 8,
                       observation_mode: str | None = None, target_index: int | None = None) -> dict:
        if mode not in (MODE_AMPLIFIER, MODE_BENCHMARK):
            raise AnimusSessionError(f"unknown mode {mode!r}")
        sid = f"animus-{seed}-{len(self._sessions)}-{mode}"
        obs_mode = observation_mode if mode == MODE_BENCHMARK else observation_mode
        cfg = LoopConfig(session_id=sid, seed=seed, controller=controller,
                         max_iterations=max_iterations, observation_mode=obs_mode, persist=False)
        belief = ImaginationBeliefState.broad_prior(provenance={"session_id": sid, "mode": mode})
        st = SessionState(session_id=sid, mode=mode, config=cfg, belief=belief,
                          generator=DeterministicSceneGenerator(),
                          fusion=BeliefFusionEngine(cfg.fusion), controller_name=controller)
        st.initial_uncertainty = belief.global_uncertainty()
        st.uncertainty_series.append(st.initial_uncertainty)
        if mode == MODE_BENCHMARK:
            target = make_target(target_index if target_index is not None else 0, seed)
            twin = SyntheticImaginer(target, ImaginerParams(),
                                     np.random.default_rng(seed * 6151 + 17))
            st.twin = twin
            st.loop = AnimusLoop(LoopConfig(session_id=sid, seed=seed, controller=controller,
                                            max_iterations=max_iterations,
                                            observation_mode=obs_mode or SOURCE_SIMULATED_NEURAL,
                                            persist=False),
                                 TwinRespondent(twin), imaginer=twin, belief=belief)
            st.loop.initialize()
            st.events = st.loop.events
        st._emit("animus.session.started", {"mode": mode, "controller": controller,
                                            "claim_label": claims.label_for(cfg.claim_ceiling)})
        self._sessions[sid] = st
        return self.state(sid)

    def _get(self, sid: str) -> SessionState:
        if sid not in self._sessions:
            raise AnimusSessionError(f"unknown session {sid!r}")
        return self._sessions[sid]

    # --- benchmark/synthetic stepping -----------------------------------------
    def step(self, sid: str) -> dict:
        st = self._get(sid)
        if not st.active:
            raise AnimusSessionError("session not active")
        if st.mode != MODE_BENCHMARK or st.loop is None:
            raise AnimusSessionError("step() is for benchmark/synthetic sessions; use feedback() for MODE_A")
        cont = st.loop.step()
        st.belief = st.loop.belief
        st.candidates = st.loop.candidates
        st.iteration = st.loop._iter
        st.uncertainty_series.append(st.belief.global_uncertainty())
        if not cont:
            st.active = False
            st.loop._result(final_state="COMPLETE")
        return self.state(sid)

    # --- interactive amplifier -------------------------------------------------
    def next_action(self, sid: str) -> dict:
        """MODE_A: controller proposes the next action (what to present/ask)."""
        st = self._get(sid)
        ctrl = build_controller(st.controller_name, AnimusPolicyConfig())
        ctx = ControlContext(iteration=st.iteration, max_iterations=st.config.max_iterations,
                             fatigue=0.0, neural_available=False, behavioral_available=True,
                             rng=np.random.default_rng(st.config.seed * 7919 + st.iteration))
        decision = ctrl.select_action(st.belief, ctx)
        st._emit("animus.controller.action", {"decision": decision})
        return decision

    def generate_candidate(self, sid: str, n: int = 1, jitter: float = 0.0) -> dict:
        st = self._get(sid)
        cset = st.generator.generate(st.belief, {"seed": st.config.seed, "n": n, "jitter": jitter})
        for c in cset.candidates:
            st.candidates.append(c)
            st._emit("animus.candidate.generated", {"candidate": c.to_dict()})
        st._emit("animus.candidate.presented", {"candidate_ids": [c.candidate_id for c in cset.candidates]})
        return {"candidates": [c.to_dict() for c in cset.candidates]}

    def apply_feedback(self, sid: str, raw: dict) -> dict:
        """MODE_A: apply one real user feedback event, updating the belief and advancing the iteration."""
        st = self._get(sid)
        if not st.active:
            raise AnimusSessionError("session not active")
        # resolve candidate reference to embedding for comparative channels
        if raw.get("channel") in ("closer_farther", "pairwise") and "candidate_id" in raw:
            emb = self._candidate_embedding(st, raw["candidate_id"])
            raw = {**raw, "preferred_embedding": emb}
        if raw.get("channel") == "freetext":
            for sub in parse_freetext(raw.get("text", "")):
                fb = normalize_feedback(sub, claim_level=st.config.claim_ceiling)
                st.fusion.apply_feedback(st.belief, fb)
                st._emit("animus.feedback.received", {"feedback": fb.to_dict()})
        else:
            fb = normalize_feedback(raw, claim_level=st.config.claim_ceiling)
            st.fusion.apply_feedback(st.belief, fb)
            st._emit("animus.feedback.received", {"feedback": fb.to_dict()})
        st.iteration += 1
        st.belief.iteration = st.iteration
        gu = st.belief.global_uncertainty()
        st.uncertainty_series.append(gu)
        st._emit("animus.belief.updated", {"belief_hash": st.belief.history_hash(),
                                           "global_uncertainty": round(gu, 6)})
        st._emit("animus.convergence.updated", {"global_uncertainty": round(gu, 6)})
        return self.state(sid)

    def _candidate_embedding(self, st: SessionState, cid: str):
        for c in st.candidates:
            if c.candidate_id == cid:
                return c.visual_embedding
        raise AnimusSessionError(f"unknown candidate {cid!r}")

    def stop(self, sid: str) -> dict:
        st = self._get(sid)
        st.active = False
        st._emit("animus.session.completed", {"iterations": st.iteration,
                                               "final_belief_hash": st.belief.history_hash()})
        return self.state(sid)

    def delete(self, sid: str) -> dict:
        self._get(sid)
        del self._sessions[sid]
        return {"deleted": sid}

    # --- reads -----------------------------------------------------------------
    def state(self, sid: str) -> dict:
        st = self._get(sid)
        return {"session_id": sid, "mode": st.mode, "controller": st.controller_name,
                "active": st.active, "iteration": st.iteration,
                "claim_level": st.config.claim_ceiling,
                "claim_label": claims.label_for(st.config.claim_ceiling),
                "global_uncertainty": round(st.belief.global_uncertainty(), 6),
                "scene_graph": st.belief.scene_graph(),
                "n_candidates": len(st.candidates), "n_events": len(st.events)}

    def belief(self, sid: str) -> dict:
        return self._get(sid).belief.to_dict()

    def candidates(self, sid: str) -> dict:
        st = self._get(sid)
        return {"candidates": [c.to_dict() for c in st.candidates]}

    def timeline(self, sid: str) -> dict:
        st = self._get(sid)
        return {"events": st.events, "uncertainty_series": [round(x, 6) for x in st.uncertainty_series]}

    def replay(self, sid: str) -> dict:
        st = self._get(sid)
        from app.core.animus.replay import AnimusReplayManifest
        man = AnimusReplayManifest.from_config(st.config)
        return {"manifest": man.to_dict(), "n_events": len(st.events),
                "final_belief_hash": st.belief.history_hash()}

    def amplification_summary(self, sid: str) -> dict:
        st = self._get(sid)
        cl = st.clarity_series or [0.0, 0.0]
        summary = metrics.AmplificationSessionSummary(
            clarity_before=cl[0], clarity_after=cl[-1],
            confidence_before=0.0, confidence_after=0.0,
            uncertainty_before=st.initial_uncertainty, uncertainty_after=st.belief.global_uncertainty(),
            candidate_closeness_progression=[],
            stability_across_reimagination=0.0, iterations=st.iteration,
            claim_level=st.config.claim_ceiling)
        return summary.to_dict()


animus_service = AnimusService()
