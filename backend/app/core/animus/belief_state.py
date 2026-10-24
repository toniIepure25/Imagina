"""ANIMUS multi-source belief fusion (IBS-v1 reference method).

Combines a prior ``ImaginationBeliefState`` with new evidence — simulated/future neural observations and
normalized behavioral feedback — using explicit, defensible update rules:

* continuous channels (visual/semantic embeddings): precision-weighted Gaussian update
  (posterior of a Gaussian prior + Gaussian observation);
* comparative feedback (closer/farther, pairwise): a bounded step of the mean toward the preferred
  candidate embedding, with a matched variance contraction;
* structured attributes: Bayesian categorical update (multiply by a soft likelihood, renormalize);
* objects: log-odds update of P(present).

Every coefficient lives in ``FusionConfig`` — named, documented, versioned. No hidden magic weights.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.animus.models import (
    FB_ATTRIBUTE,
    FB_CLOSER_FARTHER,
    FB_CONFIDENCE,
    FB_OBJECT,
    FB_PAIRWISE,
    FB_REIMAGINE,
    CategoricalBelief,
    FeedbackEvidence,
    ImaginationBeliefState,
    ObservationEnvelope,
)

FUSION_METHOD_VERSION = "animus-fusion-v1"


@dataclass(frozen=True)
class FusionConfig:
    """Named, versioned fusion coefficients (exposed in the Policy Lab)."""
    version: str = FUSION_METHOD_VERSION
    comparative_step: float = 0.35          # fraction of the way to move mean toward a preferred candidate
    comparative_var_contract: float = 0.85  # variance multiplier after an informative comparative step
    farther_step: float = 0.18              # weaker push AWAY when a candidate is judged farther
    attribute_likelihood_strength: float = 2.2   # soft-likelihood peakiness for attribute corrections
    object_logodds_step: float = 1.4        # log-odds increment for an add/remove/replace correction
    confidence_var_contract: float = 0.8    # variance multiplier when user confirms closeness
    reimagine_var_inflate: float = 1.12     # mild variance inflation when the user re-imagines
    min_variance: float = 1e-3
    max_variance: float = 4.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"version": self.version, "comparative_step": self.comparative_step,
                "comparative_var_contract": self.comparative_var_contract, "farther_step": self.farther_step,
                "attribute_likelihood_strength": self.attribute_likelihood_strength,
                "object_logodds_step": self.object_logodds_step,
                "confidence_var_contract": self.confidence_var_contract,
                "reimagine_var_inflate": self.reimagine_var_inflate,
                "min_variance": self.min_variance, "max_variance": self.max_variance}


def _clip_var(v: np.ndarray, cfg: FusionConfig) -> np.ndarray:
    return np.clip(v, cfg.min_variance, cfg.max_variance)


def _gaussian_update(mean, var, obs, obs_var, cfg: FusionConfig):
    """Precision-weighted posterior of N(mean,var) given observation obs with variance obs_var."""
    var = _clip_var(np.asarray(var, float), cfg)
    obs_var = np.clip(np.asarray(obs_var, float), cfg.min_variance, None)
    prec = 1.0 / var
    obs_prec = 1.0 / obs_var
    post_var = 1.0 / (prec + obs_prec)
    post_mean = post_var * (mean / var + np.asarray(obs, float) / obs_var)
    return post_mean, _clip_var(post_var, cfg)


class BeliefFusionEngine:
    """Deterministic evidence combination. Pure functions of (belief, evidence, config)."""

    def __init__(self, config: FusionConfig | None = None):
        self.config = config or FusionConfig()

    # --- neural / future-neural observation -----------------------------------
    def apply_observation(self, belief: ImaginationBeliefState,
                          obs: ObservationEnvelope) -> ImaginationBeliefState:
        cfg = self.config
        rep, unc = obs.representation, obs.uncertainty
        # reject non-finite observations (fail-safe: ignore rather than corrupt the belief)
        for ch in ("visual", "semantic"):
            if ch in rep and not np.all(np.isfinite(np.asarray(rep[ch], float))):
                return belief
        if "visual" in rep:
            m, v = _gaussian_update(belief.visual_embedding.mean, belief.visual_embedding.variance,
                                    rep["visual"], unc.get("visual", 1.0), cfg)
            belief.visual_embedding.mean, belief.visual_embedding.variance = m, v
        if "semantic" in rep:
            m, v = _gaussian_update(belief.semantic_embedding.mean, belief.semantic_embedding.variance,
                                    rep["semantic"], unc.get("semantic", 1.0), cfg)
            belief.semantic_embedding.mean, belief.semantic_embedding.variance = m, v
        if obs.source_type not in belief.evidence_sources:
            belief.evidence_sources.append(obs.source_type)
        return belief

    # --- behavioral feedback ---------------------------------------------------
    def apply_feedback(self, belief: ImaginationBeliefState,
                       fb: FeedbackEvidence) -> ImaginationBeliefState:
        cfg = self.config
        ch, c = fb.channel, fb.content
        if ch in (FB_CLOSER_FARTHER, FB_PAIRWISE):
            self._apply_comparative(belief, c, cfg)
        elif ch == FB_ATTRIBUTE:
            self._apply_attribute(belief, c, cfg)
        elif ch == FB_OBJECT:
            self._apply_object(belief, c, cfg)
        elif ch == FB_CONFIDENCE:
            self._apply_confidence(belief, c, cfg)
        elif ch == FB_REIMAGINE:
            belief.visual_embedding.variance = _clip_var(
                belief.visual_embedding.variance * cfg.reimagine_var_inflate, cfg)
        if f"feedback:{ch}" not in belief.evidence_sources:
            belief.evidence_sources.append(f"feedback:{ch}")
        return belief

    def _apply_comparative(self, belief, c, cfg):
        pref = c.get("preferred_embedding")
        if pref is None:
            return
        pref = np.asarray(pref, float)
        mean = belief.visual_embedding.mean
        if c.get("closer", True):
            belief.visual_embedding.mean = mean + cfg.comparative_step * (pref - mean)
            belief.visual_embedding.variance = _clip_var(
                belief.visual_embedding.variance * cfg.comparative_var_contract, cfg)
        else:
            belief.visual_embedding.mean = mean - cfg.farther_step * (pref - mean)

    def _apply_attribute(self, belief, c, cfg):
        attr, target = c.get("attribute"), c.get("target_option")
        if attr not in belief.global_scene_attributes or target is None:
            return
        cb = belief.global_scene_attributes[attr]
        strength = float(c.get("strength", 1.0)) * cfg.attribute_likelihood_strength
        like = {o: (np.exp(strength) if o == target else 1.0) for o in cb.probs}
        post = {o: cb.probs[o] * like[o] for o in cb.probs}
        belief.global_scene_attributes[attr] = CategoricalBelief(post).normalized()

    def _apply_object(self, belief, c, cfg):
        obj, op = c.get("object"), c.get("op", "add")
        if obj not in belief.objects:
            return
        p = min(max(belief.objects[obj], 1e-4), 1 - 1e-4)
        lo = np.log(p / (1 - p))
        if op in ("add", "replace_in"):
            lo += cfg.object_logodds_step
        elif op in ("remove", "replace_out"):
            lo -= cfg.object_logodds_step
        belief.objects[obj] = float(1.0 / (1.0 + np.exp(-lo)))

    def _apply_confidence(self, belief, c, cfg):
        if float(c.get("confidence", 0.0)) >= 0.5:
            belief.visual_embedding.variance = _clip_var(
                belief.visual_embedding.variance * cfg.confidence_var_contract, cfg)
            belief.semantic_embedding.variance = _clip_var(
                belief.semantic_embedding.variance * cfg.confidence_var_contract, cfg)
