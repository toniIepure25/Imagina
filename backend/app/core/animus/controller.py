"""ANIMUS controllers — the active decision layer.

The controller chooses WHAT TO DO NEXT to converge on the user's imagined content: generate a candidate or
contrast pair, probe an uncertain attribute/object, ask for re-imagination, hold, or complete. The
reference ``AnimusActiveController`` scores each action by expected information gain and belief contraction
minus effort/fatigue cost, with all coefficients frozen in ``AnimusPolicyConfig`` (exposed in the Policy
Lab). Baselines (static / random / greedy) exist so any improvement is measured, not assumed.

This is an engineering controller, NOT a validated cognitive model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from app.core.animus.models import ImaginationBeliefState

# Action space.
GENERATE_SINGLE = "GENERATE_SINGLE"
GENERATE_CONTRAST_PAIR = "GENERATE_CONTRAST_PAIR"
PROBE_ATTRIBUTE = "PROBE_ATTRIBUTE"
PROBE_OBJECT = "PROBE_OBJECT"
PROBE_SPATIAL_RELATION = "PROBE_SPATIAL_RELATION"
ZOOM_REGION = "ZOOM_REGION"
SIMPLIFY_SCENE = "SIMPLIFY_SCENE"
INCREASE_DETAIL = "INCREASE_DETAIL"
REACTIVATE_REFERENCE = "REACTIVATE_REFERENCE"
ASK_REIMAGINE = "ASK_REIMAGINE"
HOLD_STABLE = "HOLD_STABLE"
COOLDOWN = "COOLDOWN"
COMPLETE = "COMPLETE"

ACTION_SPACE = [
    GENERATE_SINGLE, GENERATE_CONTRAST_PAIR, PROBE_ATTRIBUTE, PROBE_OBJECT, PROBE_SPATIAL_RELATION,
    ZOOM_REGION, SIMPLIFY_SCENE, INCREASE_DETAIL, REACTIVATE_REFERENCE, ASK_REIMAGINE, HOLD_STABLE,
    COOLDOWN, COMPLETE,
]

POLICY_VERSION = "animus-policy-v1"


@dataclass(frozen=True)
class AnimusPolicyConfig:
    """Frozen, named policy coefficients (Policy Lab surface).

    Actions are scored by *expected similarity gain* — the product objective decomposes as
    w_visual/w_attr/w_object (design constants the controller may know; NOT the hidden target) — minus
    effort and fatigue. This makes the high-weight visual channel compete fairly with the many small
    per-attribute gains, so the controller interleaves embedding refinement and attribute/object probing.
    """
    version: str = POLICY_VERSION
    w_visual: float = 0.40              # objective weight of the visual-embedding channel
    w_attribute: float = 0.35           # objective weight of all scene attributes (shared)
    w_object: float = 0.25              # objective weight of all objects (shared)
    k_contrast: float = 1.0             # gain factor for a visual-refinement action
    vis_norm_floor: float = 0.5         # normalizer for visual-uncertainty -> expected gain
    effort_generate: float = 0.02
    effort_probe: float = 0.01
    effort_reimagine: float = 0.20
    fatigue_weight: float = 0.20
    convergence_uncertainty: float = 0.18   # global-uncertainty threshold to allow COMPLETE
    min_iterations: int = 2
    reimagine_fatigue_trigger: float = 0.75
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in (
            "version", "w_visual", "w_attribute", "w_object", "k_contrast", "vis_norm_floor",
            "effort_generate", "effort_probe", "effort_reimagine", "fatigue_weight",
            "convergence_uncertainty", "min_iterations", "reimagine_fatigue_trigger")}


@dataclass
class ControlContext:
    iteration: int
    max_iterations: int
    fatigue: float = 0.0
    neural_available: bool = True
    behavioral_available: bool = True
    rng: np.random.Generator | None = None


def _attr_entropies(belief: ImaginationBeliefState) -> dict[str, float]:
    return {a: cb.entropy() for a, cb in belief.global_scene_attributes.items()}


def _most_uncertain_object(belief: ImaginationBeliefState) -> tuple[str, float]:
    items = [(o, 1.0 - abs(p - 0.5) * 2) for o, p in belief.objects.items()]
    o, u = max(items, key=lambda kv: kv[1])
    return o, u


class BaseController(ABC):
    name: str

    @abstractmethod
    def select_action(self, belief: ImaginationBeliefState, ctx: ControlContext) -> dict:
        ...

    @staticmethod
    def _terminal(action, params=None, scores=None, rationale=""):
        return {"action": action, "params": params or {}, "scores": scores or {}, "rationale": rationale}


class StaticController(BaseController):
    """Baseline: always present the same single candidate; never probe, never adapt."""
    name = "STATIC"

    def select_action(self, belief, ctx):
        if ctx.iteration >= ctx.max_iterations:
            return self._terminal(COMPLETE, rationale="max iterations")
        return self._terminal(GENERATE_SINGLE, {"static": True}, rationale="static: fixed candidate")


class RandomController(BaseController):
    """Baseline: pick a random (non-terminal) action; generate with large jitter."""
    name = "RANDOM"
    _choices = [GENERATE_SINGLE, GENERATE_CONTRAST_PAIR, PROBE_ATTRIBUTE, PROBE_OBJECT, ASK_REIMAGINE]

    def select_action(self, belief, ctx):
        if ctx.iteration >= ctx.max_iterations:
            return self._terminal(COMPLETE, rationale="max iterations")
        rng = ctx.rng or np.random.default_rng(ctx.iteration)
        a = self._choices[int(rng.integers(len(self._choices)))]
        params = {"jitter": 1.2}
        if a == PROBE_ATTRIBUTE:
            attrs = list(belief.global_scene_attributes.keys())
            params = {"attribute": attrs[int(rng.integers(len(attrs)))]}
        elif a == PROBE_OBJECT:
            objs = list(belief.objects.keys())
            params = {"object": objs[int(rng.integers(len(objs)))]}
        return self._terminal(a, params, rationale="random policy")


class GreedyUserFeedbackController(BaseController):
    """Baseline: always request a belief-guided contrast pair; exploit comparative feedback only."""
    name = "GREEDY_USER_FEEDBACK"

    def select_action(self, belief, ctx):
        if ctx.iteration >= ctx.max_iterations:
            return self._terminal(COMPLETE, rationale="max iterations")
        return self._terminal(GENERATE_CONTRAST_PAIR, {"jitter": 0.4},
                              rationale="greedy: comparative feedback only")


class GreedyNeuralOnlyController(BaseController):
    """Baseline: rely on neural observation via reactivation; ignore attribute/object structure."""
    name = "GREEDY_NEURAL_ONLY"

    def select_action(self, belief, ctx):
        if ctx.iteration >= ctx.max_iterations:
            return self._terminal(COMPLETE, rationale="max iterations")
        if not ctx.neural_available:
            return self._terminal(GENERATE_SINGLE, rationale="neural unavailable -> present")
        return self._terminal(REACTIVATE_REFERENCE, rationale="greedy neural: gather observation")


class AnimusActiveController(BaseController):
    """Reference active-inference controller: pick the action with the best expected information gain per
    unit effort, balancing embedding uncertainty, attribute entropy, object ambiguity, and fatigue."""
    name = "ANIMUS_ACTIVE"

    def __init__(self, config: AnimusPolicyConfig | None = None):
        self.config = config or AnimusPolicyConfig()

    def select_action(self, belief, ctx):
        cfg = self.config
        gu = belief.global_uncertainty()
        if ctx.iteration >= ctx.max_iterations:
            return self._terminal(COMPLETE, rationale="max iterations")
        if ctx.iteration >= cfg.min_iterations and gu < cfg.convergence_uncertainty:
            return self._terminal(COMPLETE, {"global_uncertainty": round(gu, 4)},
                                  rationale="converged")

        vis_u = belief.visual_embedding.scalar_uncertainty()
        ents = _attr_entropies(belief)
        n_attr = len(ents)
        n_obj = len(belief.objects)
        best_attr, best_attr_ent = max(ents.items(), key=lambda kv: kv[1])
        obj, obj_u = _most_uncertain_object(belief)
        fat = ctx.fatigue

        # expected similarity gain per action (objective-weighted marginals). Visual gain scales with the
        # remaining visual uncertainty and saturates as the embedding converges.
        vis_gain = cfg.w_visual * cfg.k_contrast * float(min(1.0, vis_u))
        attr_gain = cfg.w_attribute * (1.0 / n_attr) * (best_attr_ent / np.log(4))
        obj_gain = cfg.w_object * (1.0 / n_obj) * obj_u

        scores = {}
        scores[GENERATE_CONTRAST_PAIR] = vis_gain - cfg.effort_generate - cfg.fatigue_weight * fat
        scores[PROBE_ATTRIBUTE] = attr_gain - cfg.effort_probe - cfg.fatigue_weight * 0.3 * fat
        scores[PROBE_OBJECT] = obj_gain - cfg.effort_probe - cfg.fatigue_weight * 0.3 * fat
        if ctx.neural_available:
            scores[REACTIVATE_REFERENCE] = 0.9 * vis_gain - cfg.effort_generate - cfg.fatigue_weight * fat
        if fat >= cfg.reimagine_fatigue_trigger:
            scores[ASK_REIMAGINE] = 0.5 * cfg.w_visual - cfg.effort_reimagine  # a reset when fatigued

        action = max(scores.items(), key=lambda kv: kv[1])[0]
        params = {}
        if action == PROBE_ATTRIBUTE:
            params = {"attribute": best_attr, "entropy": round(best_attr_ent, 4)}
        elif action == PROBE_OBJECT:
            params = {"object": obj, "uncertainty": round(obj_u, 4)}
        elif action == GENERATE_CONTRAST_PAIR:
            params = {"jitter": 0.4}
        return self._terminal(action, params,
                              scores={k: round(float(v), 4) for k, v in scores.items()},
                              rationale=f"max EIG/effort; gu={gu:.3f}")


CONTROLLERS = {
    StaticController.name: StaticController,
    RandomController.name: RandomController,
    GreedyUserFeedbackController.name: GreedyUserFeedbackController,
    GreedyNeuralOnlyController.name: GreedyNeuralOnlyController,
    AnimusActiveController.name: AnimusActiveController,
}


def build_controller(name: str, policy: AnimusPolicyConfig | None = None) -> BaseController:
    if name == AnimusActiveController.name:
        return AnimusActiveController(policy)
    if name not in CONTROLLERS:
        raise ValueError(f"unknown controller: {name!r}")
    return CONTROLLERS[name]()
