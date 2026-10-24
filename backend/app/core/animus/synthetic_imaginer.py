"""ANIMUS SyntheticImaginer — the closed-loop digital twin.

A hidden synthetic user with a target internal representation ``z_target`` (visual + semantic embeddings,
true scene attributes and objects). The ANIMUS controller NEVER receives ``z_target``; it only receives the
twin's *responses* to candidates and probes — noisy comparative feedback, attribute/object evidence, and
(when a neural provider is used) a raw neural measurement to be decoded. This lets the entire loop be
validated before any real content decoder exists.

Behaviour is fully deterministic given a seeded ``numpy`` Generator.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.animus import vocab


@dataclass
class TargetScene:
    """The hidden ground-truth imagined content (evaluator-only)."""
    visual: np.ndarray                  # unit vector, dim VISUAL_EMBED_DIM
    semantic: np.ndarray                # unit vector, dim SEMANTIC_EMBED_DIM
    attributes: dict[str, str]          # attribute -> true option
    objects: set[str]                   # present objects
    relations: list[tuple] = field(default_factory=list)
    label: str = ""

    def to_public_label(self) -> str:
        return self.label

    def to_evaluator_dict(self) -> dict:
        return {"label": self.label, "attributes": self.attributes,
                "objects": sorted(self.objects),
                "visual_norm": round(float(np.linalg.norm(self.visual)), 6)}


@dataclass
class ImaginerParams:
    imagery_strength: float = 0.8       # how strongly the target is expressed in neural signal
    neural_noise: float = 0.35
    feedback_noise: float = 0.12        # prob of flipping a comparative judgment
    attention_drift: float = 0.03       # slow random drift of expressed target
    fatigue: float = 0.0                # accumulates, degrades signal
    fatigue_rate: float = 0.015
    memory_decay: float = 0.01          # target expression decays toward prior over time
    response_bias: float = 0.0          # systematic "everything feels closer/farther" bias

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in
                ("imagery_strength", "neural_noise", "feedback_noise", "attention_drift",
                 "fatigue", "fatigue_rate", "memory_decay", "response_bias")}


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class SyntheticImaginer:
    """Hidden-target respondent. Deterministic given ``rng``."""

    def __init__(self, target: TargetScene, params: ImaginerParams, rng: np.random.Generator):
        self.target = target
        self.params = params
        self.rng = rng
        self._expressed = np.array(target.visual, dtype=float)   # drifts over time
        self._t = 0

    # --- internal expressed target (with drift / fatigue / decay) --------------
    def _step_internal(self):
        p = self.params
        p.fatigue = min(1.0, p.fatigue + p.fatigue_rate)
        drift = p.attention_drift * self.rng.standard_normal(self._expressed.shape)
        decayed = (1 - p.memory_decay) * self._expressed + p.memory_decay * np.zeros_like(self._expressed)
        self._expressed = _unit(decayed + drift)
        self._t += 1

    def _effective_strength(self) -> float:
        return float(np.clip(self.params.imagery_strength * (1 - 0.5 * self.params.fatigue), 0.05, 1.0))

    # --- neural measurement (raw; to be decoded) -------------------------------
    def raw_neural_measurement(self, forward_operator: np.ndarray) -> np.ndarray:
        """Return A @ (strength * expressed_visual) + noise. This is the RAW signal a decoder consumes;
        it is never exposed to a generator."""
        self._step_internal()
        s = self._effective_strength()
        clean = forward_operator @ (s * self._expressed)
        noise = self.params.neural_noise * self.rng.standard_normal(clean.shape)
        return clean + noise

    def semantic_measurement(self) -> tuple[np.ndarray, float]:
        s = self._effective_strength()
        obs = s * np.array(self.target.semantic, float) + \
            self.params.neural_noise * self.rng.standard_normal(self.target.semantic.shape)
        return obs, float(self.params.neural_noise ** 2 + (1 - s))

    # --- comparative behavioral feedback ---------------------------------------
    def compare(self, cand_current: np.ndarray, cand_previous: np.ndarray | None) -> dict:
        """Judge whether the current candidate is closer to the target than the previous one."""
        tgt = self.target.visual
        d_cur = float(np.linalg.norm(np.asarray(cand_current, float) - tgt))
        if cand_previous is None:
            closer = d_cur < np.linalg.norm(tgt)     # vs the origin/broad prior
            d_prev = float(np.linalg.norm(tgt))
        else:
            d_prev = float(np.linalg.norm(np.asarray(cand_previous, float) - tgt))
            closer = d_cur < d_prev
        # response bias + noise flip
        if self.params.response_bias:
            closer = closer if self.rng.random() > abs(self.params.response_bias) else (
                self.params.response_bias > 0)
        if self.rng.random() < self.params.feedback_noise:
            closer = not closer
        return {"closer": bool(closer), "d_current": d_cur, "d_previous": d_prev}

    def prefer(self, cand_a: np.ndarray, cand_b: np.ndarray) -> str:
        """Pairwise: return 'A' or 'B' for whichever is closer to target (noisy)."""
        da = float(np.linalg.norm(np.asarray(cand_a, float) - self.target.visual))
        db = float(np.linalg.norm(np.asarray(cand_b, float) - self.target.visual))
        winner = "A" if da < db else "B"
        if self.rng.random() < self.params.feedback_noise:
            winner = "B" if winner == "A" else "A"
        return winner

    # --- attribute / object probes ---------------------------------------------
    def probe_attribute(self, attr: str) -> dict:
        """Noisy evidence about the true option of a scene attribute."""
        options = vocab.SCENE_ATTRIBUTES[attr]
        true_opt = self.target.attributes.get(attr, options[len(options) // 2])
        if self.rng.random() < self.params.feedback_noise:
            reported = options[int(self.rng.integers(len(options)))]
        else:
            reported = true_opt
        strength = float(np.clip(1.0 - self.params.feedback_noise - 0.3 * self.params.fatigue, 0.2, 1.0))
        return {"attribute": attr, "target_option": reported, "strength": strength}

    def probe_object(self, obj: str) -> dict:
        present = obj in self.target.objects
        if self.rng.random() < self.params.feedback_noise:
            present = not present
        return {"object": obj, "op": "add" if present else "remove"}

    # --- self report -----------------------------------------------------------
    def clarity(self, cand_current: np.ndarray) -> float:
        """User-reported closeness ('this is close to what I imagined'), in [0,1], noisy."""
        d = float(np.linalg.norm(np.asarray(cand_current, float) - self.target.visual))
        base = float(np.clip(1.0 - d / (np.linalg.norm(self.target.visual) + 1e-9), 0.0, 1.0))
        return float(np.clip(base + 0.05 * self.rng.standard_normal(), 0.0, 1.0))
