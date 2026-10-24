"""ANIMUS metrics.

Two strictly separated families:

* **benchmark-only** (require a hidden ground-truth target; evaluator context only) — visual similarity,
  attribute/object accuracy, scene-graph edit distance, loop_gain. These MUST NOT surface in real-user mode
  because a real imagined target is unknown.
* **real-user observable** — uncertainty reduction, self-reported clarity/confidence progression, candidate
  change magnitude, controller action entropy, stability across re-imagination. Safe to show any user.

``loop_gain = final_similarity - initial_similarity`` (benchmark-only).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.animus import vocab
from app.core.animus.models import ImaginationBeliefState
from app.core.animus.synthetic_imaginer import TargetScene


def _cos01(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    if d < 1e-9:
        return 0.5
    return float((float(a @ b) / d + 1.0) / 2.0)


# ---------------------------------------------------------------- benchmark-only
def attribute_accuracy(belief: ImaginationBeliefState, target: TargetScene) -> float:
    hits = 0
    for a, cb in belief.global_scene_attributes.items():
        if cb.argmax() == target.attributes.get(a):
            hits += 1
    return hits / len(belief.global_scene_attributes)


def object_accuracy(belief: ImaginationBeliefState, target: TargetScene) -> float:
    hits = 0
    for o in vocab.OBJECT_VOCAB:
        pred = belief.objects[o] >= 0.5
        truth = o in target.objects
        if pred == truth:
            hits += 1
    return hits / len(vocab.OBJECT_VOCAB)


def benchmark_similarity(belief: ImaginationBeliefState, target: TargetScene) -> float:
    """Evaluator-only similarity in [0,1]. Never call in real-user mode."""
    vis = _cos01(belief.visual_embedding.mean, target.visual)
    attr = attribute_accuracy(belief, target)
    obj = object_accuracy(belief, target)
    return float(0.40 * vis + 0.35 * attr + 0.25 * obj)


def scene_graph_edit_distance(belief: ImaginationBeliefState, target: TargetScene) -> int:
    """Simple edit distance: object set symmetric difference + attribute mismatches."""
    b_objs = {o for o, p in belief.objects.items() if p >= 0.5}
    obj_edits = len(b_objs.symmetric_difference(target.objects))
    attr_edits = sum(1 for a, cb in belief.global_scene_attributes.items()
                     if cb.argmax() != target.attributes.get(a))
    return int(obj_edits + attr_edits)


# ------------------------------------------------------------ real-user metrics
def uncertainty_reduction(initial_gu: float, final_gu: float) -> float:
    return float(initial_gu - final_gu)


def candidate_change_magnitude(prev_emb, cur_emb) -> float:
    return float(np.linalg.norm(np.asarray(cur_emb, float) - np.asarray(prev_emb, float)))


def action_entropy(action_counts: dict[str, int]) -> float:
    total = sum(action_counts.values())
    if total == 0:
        return 0.0
    e = 0.0
    for c in action_counts.values():
        if c > 0:
            p = c / total
            e -= p * np.log(p)
    return float(e)


@dataclass
class AmplificationSessionSummary:
    """Real-user-safe summary of an amplification session. No ground-truth target used."""
    clarity_before: float
    clarity_after: float
    confidence_before: float
    confidence_after: float
    uncertainty_before: float
    uncertainty_after: float
    candidate_closeness_progression: list[float]
    stability_across_reimagination: float
    iterations: int
    claim_level: str
    notes: list[str] = field(default_factory=list)

    @property
    def clarity_gain(self) -> float:
        return float(self.clarity_after - self.clarity_before)

    @property
    def stabilized(self) -> bool:
        return self.uncertainty_after < self.uncertainty_before

    def to_dict(self) -> dict:
        return {
            "clarity_before": round(self.clarity_before, 4), "clarity_after": round(self.clarity_after, 4),
            "clarity_gain": round(self.clarity_gain, 4),
            "confidence_before": round(self.confidence_before, 4),
            "confidence_after": round(self.confidence_after, 4),
            "uncertainty_before": round(self.uncertainty_before, 4),
            "uncertainty_after": round(self.uncertainty_after, 4),
            "stabilized": self.stabilized,
            "candidate_closeness_progression": [round(x, 4) for x in self.candidate_closeness_progression],
            "stability_across_reimagination": round(self.stability_across_reimagination, 4),
            "iterations": self.iterations, "claim_level": self.claim_level, "notes": self.notes,
        }

    def message(self) -> str:
        """A user-facing sentence, gated by claim level (never implies decoded thoughts)."""
        if self.stabilized:
            return "Your representation became more stable and clarified across this session."
        return "This session explored several candidates; the representation did not fully stabilize."
