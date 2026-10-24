"""Epistemic reconstruction interview (ERI) for the ANIMUS instrument.

The interview is a behavioural belief-elicitation method. It asks binary questions about a hidden
symbolic scene, updates a mean-field Beta posterior, and chooses the next question by expected
information gain. It does not decode imagery, measure a neural signal, or expose the target answer.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Any

from app.core.animus.scene.library import KIND_LABELS, OBJECT_KINDS
from app.core.animus.scene.model import SceneGraph, SceneValidationError

ERI_PROTOCOL_VERSION = "eri-v1"
ERI_SCORING_VERSION = "eri-v1"
ERI_TASK_FAMILY = "epistemic_interview"
ERI_RESPONSE_KIND = "probability_choice"
PROBE_TYPES = ("object_presence", "spatial_relation")
EPISTEMIC_TASK_TYPES = ("epistemic_object_probe", "epistemic_spatial_probe")
FORM_IDS = ("A", "B", "C")
DEFAULT_MAX_PROBES = 12
MIN_MAX_PROBES = 6
MAX_MAX_PROBES = 20
DEFAULT_SENSITIVITY = 0.8


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _digest(*parts: Any) -> str:
    material = "|".join(str(part) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _entropy(probability: float) -> float:
    p = max(1e-9, min(1.0 - 1e-9, float(probability)))
    return float(-(p * math.log(p) + (1.0 - p) * math.log(1.0 - p)))


def _beta_mean(alpha: float, beta: float) -> float:
    total = max(1e-9, alpha + beta)
    return max(0.0, min(1.0, alpha / total))


def _beta_entropy(alpha: float, beta: float) -> float:
    return _entropy(_beta_mean(alpha, beta))


def information_gain(before_probability: float, after_probability: float) -> float:
    return round(max(0.0, _entropy(before_probability) - _entropy(after_probability)), 6)


def expected_information_gain(alpha: float, beta: float,
                              sensitivity: float = DEFAULT_SENSITIVITY) -> float:
    """Expected reduction in binary entropy for one probe.

    ``sensitivity`` is the assumed probability of a correct answer used only for selection. The
    posterior update uses the reported confidence, not this value. The result ranks probes; it is not
    a learning rate or an ability estimate.
    """
    prior = _beta_mean(alpha, beta)
    s = _clamp(sensitivity, 0.51, 0.99)
    p_yes = prior * s + (1.0 - prior) * (1.0 - s)
    post_yes = (alpha + s) / (alpha + beta + 1.0)
    post_no = (alpha + (1.0 - s)) / (alpha + beta + 1.0)
    expected_after = p_yes * _entropy(post_yes) + (1.0 - p_yes) * _entropy(post_no)
    return round(max(0.0, _entropy(prior) - expected_after), 6)


def _normalized_positions(scene: SceneGraph) -> dict[str, tuple[float, float]]:
    if len(scene.entities) < 2:
        return {}
    xs = [entity.position[0] for entity in scene.entities]
    zs = [entity.position[2] for entity in scene.entities]
    x_span = max(xs) - min(xs)
    z_span = max(zs) - min(zs)
    if max(x_span, z_span) < 1e-6:
        return {}
    x_center = (max(xs) + min(xs)) / 2.0
    z_center = (max(zs) + min(zs)) / 2.0
    x_scale = max(x_span / 2.0, 1e-6)
    z_scale = max(z_span / 2.0, 1e-6)
    return {
        entity.id: (
            round(_clamp((entity.position[0] - x_center) / x_scale, -1.0, 1.0), 4),
            round(_clamp((entity.position[2] - z_center) / z_scale, -1.0, 1.0), 4),
        )
        for entity in scene.entities
    }


def _unique_labels(scene: SceneGraph) -> dict[str, str]:
    labels: dict[str, str] = {}
    seen: dict[str, int] = {}
    for entity in scene.entities:
        base = entity.label.strip() or KIND_LABELS.get(entity.kind, entity.kind.title())
        count = seen.get(base, 0) + 1
        seen[base] = count
        labels[entity.id] = base if count == 1 else f"{base} ({count})"
    return labels


@dataclass(frozen=True)
class EpistemicProbe:
    probe_id: str
    task_id: str
    probe_type: str
    prompt: str
    options: tuple[dict[str, str], ...]
    dimension: str
    difficulty: float
    preview_seconds: int
    variable_id: str
    answer: dict[str, str] = field(default_factory=dict, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def task_type(self) -> str:
        return ("epistemic_object_probe" if self.probe_type == "object_presence"
                else "epistemic_spatial_probe")

    def public_payload(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "task_id": self.task_id,
            "probe_type": self.probe_type,
            "prompt": self.prompt,
            "options": [dict(option) for option in self.options],
            "dimension": self.dimension,
            "difficulty": self.difficulty,
            "preview_seconds": self.preview_seconds,
        }


@dataclass
class EpistemicBelief:
    objects: dict[str, tuple[float, float]] = field(default_factory=dict)
    relations: dict[str, tuple[float, float]] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)

    def probability(self, variable_id: str) -> float:
        alpha, beta = self.objects.get(variable_id) or self.relations.get(variable_id) or (1.0, 1.0)
        return _beta_mean(alpha, beta)

    def with_probe(self, probe: EpistemicProbe) -> "EpistemicBelief":
        objects = dict(self.objects)
        relations = dict(self.relations)
        if probe.probe_type == "object_presence":
            objects.setdefault(probe.variable_id, (1.0, 1.0))
        else:
            relations.setdefault(probe.variable_id, (1.0, 1.0))
        return EpistemicBelief(objects=objects, relations=relations, asked=list(self.asked))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "eri-belief-v1",
            "objects": {key: [round(value[0], 6), round(value[1], 6)]
                        for key, value in sorted(self.objects.items())},
            "relations": {key: [round(value[0], 6), round(value[1], 6)]
                          for key, value in sorted(self.relations.items())},
            "asked": list(self.asked),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EpistemicBelief":
        if not isinstance(payload, dict):
            return cls()
        objects = _parse_beta_map(payload.get("objects"))
        relations = _parse_beta_map(payload.get("relations"))
        asked = payload.get("asked")
        return cls(
            objects=objects,
            relations=relations,
            asked=[item for item in asked if isinstance(item, str)] if isinstance(asked, list) else [],
        )


def _parse_beta_map(raw: Any) -> dict[str, tuple[float, float]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[float, float]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, (list, tuple)) or len(value) != 2:
            continue
        try:
            alpha = max(0.001, min(1000.0, float(value[0])))
            beta = max(0.001, min(1000.0, float(value[1])))
        except (TypeError, ValueError):
            continue
        out[key] = (alpha, beta)
    return out


def _object_probe(scene_hash: str, seed: int, form_id: str, index: int, *,
                  variable_id: str, label: str, kind: str, present: bool,
                  difficulty: float) -> EpistemicProbe:
    answer = "present" if present else "absent"
    prompt = f"Was the {label} present in the hidden scene?"
    options = (
        {"id": "present", "label": "Present"},
        {"id": "absent", "label": "Absent"},
    )
    probe_id = "pr_" + _digest(scene_hash, form_id, "object", variable_id, index)[:14]
    task_id = "eri_" + _digest(scene_hash, form_id, seed, "object", variable_id,
                                round(_clamp(difficulty), 3))[:18]
    return EpistemicProbe(
        probe_id=probe_id,
        task_id=task_id,
        probe_type="object_presence",
        prompt=prompt,
        options=options,
        dimension="stability",
        difficulty=round(_clamp(difficulty), 3),
        preview_seconds=4,
        variable_id=variable_id,
        answer={"choice": answer},
        metadata={"label": label, "kind": kind, "variable_kind": "object"},
    )


def _spatial_probe(scene_hash: str, seed: int, form_id: str, index: int, *,
                   subject_id: str, object_id: str, subject_label: str, object_label: str,
                   relation: str, difficulty: float) -> EpistemicProbe:
    variable_id = f"rel:{subject_id}:{object_id}:x"
    prompt = f"Was the {subject_label} to the left or right of the {object_label}?"
    options = (
        {"id": "left", "label": "Left"},
        {"id": "right", "label": "Right"},
    )
    probe_id = "pr_" + _digest(scene_hash, form_id, "spatial", variable_id, index)[:14]
    task_id = "eri_" + _digest(scene_hash, form_id, seed, "spatial", variable_id,
                                round(_clamp(difficulty), 3))[:18]
    return EpistemicProbe(
        probe_id=probe_id,
        task_id=task_id,
        probe_type="spatial_relation",
        prompt=prompt,
        options=options,
        dimension="spatial",
        difficulty=round(_clamp(difficulty), 3),
        preview_seconds=4,
        variable_id=variable_id,
        answer={"choice": relation},
        metadata={
            "subject_id": subject_id,
            "object_id": object_id,
            "subject_label": subject_label,
            "object_label": object_label,
            "relation": "left_of" if relation == "left" else "right_of",
            "variable_kind": "relation",
        },
    )


def build_probe_pool(scene: SceneGraph, *, seed: int, form_id: str = "A",
                     difficulty: float = 0.45) -> tuple[EpistemicProbe, ...]:
    """Build a deterministic pool of object and spatial probes for one scene."""
    if form_id not in FORM_IDS:
        raise SceneValidationError("form_id must be A, B, or C")
    difficulty = float(difficulty)
    if not math.isfinite(difficulty):
        raise SceneValidationError("difficulty must be finite")
    difficulty = round(_clamp(difficulty), 3)
    scene_hash = scene.content_hash()
    rng = random.Random(f"{seed}:{form_id}:{scene_hash}:{difficulty}")
    labels = _unique_labels(scene)
    entities = list(scene.entities)
    if not entities:
        return ()
    object_limit = min(len(entities), 2 + int(round(difficulty * 3)))
    target_order = list(entities)
    rng.shuffle(target_order)
    targets = target_order[:object_limit]
    probes: list[EpistemicProbe] = []
    for index, entity in enumerate(targets):
        probes.append(_object_probe(
            scene_hash, seed, form_id, index,
            variable_id=f"obj:{entity.id}",
            label=labels[entity.id],
            kind=entity.kind,
            present=True,
            difficulty=difficulty,
        ))
    blocked = {entity.kind for entity in entities}
    used_labels = set(labels.values())
    decoy_count = 1 + int(round(difficulty * 3))
    for index in range(decoy_count):
        kinds = [kind for kind in OBJECT_KINDS if kind not in blocked]
        if not kinds:
            break
        kind = kinds[rng.randrange(len(kinds))]
        blocked.add(kind)
        base_label = KIND_LABELS.get(kind, kind.title())
        label = base_label
        suffix = 2
        while label in used_labels:
            label = f"{base_label} {suffix}"
            suffix += 1
        used_labels.add(label)
        probes.append(_object_probe(
            scene_hash, seed, form_id, len(targets) + index,
            variable_id=f"decoy:{kind}:{index}",
            label=label,
            kind=kind,
            present=False,
            difficulty=difficulty,
        ))
    positions = _normalized_positions(scene)
    pairs: list[tuple[Any, Any, str]] = []
    for left_index, left in enumerate(entities):
        for right in entities[left_index + 1:]:
            if left.id not in positions or right.id not in positions:
                continue
            left_x = positions[left.id][0]
            right_x = positions[right.id][0]
            if abs(left_x - right_x) < 0.15:
                continue
            pairs.append((left, right, "left" if left_x < right_x else "right"))
    rng.shuffle(pairs)
    pair_limit = min(len(pairs), 3 + int(round(difficulty * 4)))
    for index, (subject, obj, relation) in enumerate(pairs[:pair_limit]):
        probes.append(_spatial_probe(
            scene_hash, seed, form_id, len(targets) + decoy_count + index,
            subject_id=subject.id,
            object_id=obj.id,
            subject_label=labels[subject.id],
            object_label=labels[obj.id],
            relation=relation,
            difficulty=difficulty,
        ))
    return tuple(probes)


def init_belief(probes: tuple[EpistemicProbe, ...]) -> EpistemicBelief:
    belief = EpistemicBelief()
    for probe in probes:
        belief = belief.with_probe(probe)
    return belief


def _asked_types(probes: tuple[EpistemicProbe, ...], asked: list[str]) -> set[str]:
    by_id = {probe.probe_id: probe for probe in probes}
    return {by_id[item].probe_type for item in asked if item in by_id}


def select_probe(probes: tuple[EpistemicProbe, ...], belief: EpistemicBelief, *,
                 asked: list[str] | None = None) -> EpistemicProbe | None:
    """Choose the next probe with a coverage floor and expected information gain."""
    asked_ids = list(asked if asked is not None else belief.asked)
    asked_set = set(asked_ids)
    available = [probe for probe in probes if probe.probe_id not in asked_set]
    if not available:
        return None
    asked_types = _asked_types(probes, asked_ids)
    for probe_type in PROBE_TYPES:
        if probe_type not in asked_types:
            candidates = [probe for probe in available if probe.probe_type == probe_type]
            if candidates:
                return candidates[0]

    def score(probe: EpistemicProbe) -> tuple[float, str]:
        alpha, beta = (belief.objects.get(probe.variable_id)
                       or belief.relations.get(probe.variable_id)
                       or (1.0, 1.0))
        return expected_information_gain(alpha, beta), probe.probe_id

    return max(available, key=score)


def update_belief(belief: EpistemicBelief, probe: EpistemicProbe, *,
                  choice: str, confidence: float, abstained: bool = False) -> EpistemicBelief:
    """Update the Beta posterior after one answer.

    A correct answer with confidence ``c`` contributes likelihood ``c`` to the hidden state and
    ``1 - c`` to the other state, whether the hidden state is the positive or negative option. An
    abstention records the probe without changing the posterior.
    """
    if abstained:
        return EpistemicBelief(objects=dict(belief.objects), relations=dict(belief.relations),
                               asked=list(belief.asked) + [probe.probe_id])
    if choice not in {option["id"] for option in probe.options}:
        raise SceneValidationError("choice is not one of the probe options")
    confidence = float(confidence)
    if not math.isfinite(confidence):
        raise SceneValidationError("confidence must be finite")
    confidence = _clamp(confidence, 0.5, 1.0)
    truth = probe.answer.get("choice")
    correct = choice == truth
    support_truth = confidence if correct else 1.0 - confidence
    positive_option = ("present" if probe.probe_type == "object_presence" else "left")
    if truth == positive_option:
        support_positive = support_truth
    else:
        support_positive = 1.0 - support_truth
    variable_id = probe.variable_id
    source = belief.objects if probe.probe_type == "object_presence" else belief.relations
    alpha, beta = source.get(variable_id) or (1.0, 1.0)
    updated = (alpha + support_positive, beta + (1.0 - support_positive))
    objects = dict(belief.objects)
    relations = dict(belief.relations)
    if probe.probe_type == "object_presence":
        objects[variable_id] = updated
    else:
        relations[variable_id] = updated
    return EpistemicBelief(objects=objects, relations=relations,
                           asked=list(belief.asked) + [probe.probe_id])


def score_probe(probe: EpistemicProbe, *, choice: str, confidence: float,
                abstained: bool = False) -> dict[str, Any]:
    if abstained:
        return {
            "correct": None,
            "accuracy": None,
            "brier": None,
            "abstained": True,
            "response_kind": ERI_RESPONSE_KIND,
        }
    if choice not in {option["id"] for option in probe.options}:
        raise SceneValidationError("choice is not one of the probe options")
    confidence = float(confidence)
    if not math.isfinite(confidence):
        raise SceneValidationError("confidence must be finite")
    confidence = _clamp(confidence, 0.5, 1.0)
    correct = choice == probe.answer.get("choice")
    return {
        "correct": bool(correct),
        "accuracy": 1.0 if correct else 0.0,
        "brier": round((confidence - (1.0 if correct else 0.0)) ** 2, 6),
        "abstained": False,
        "response_kind": ERI_RESPONSE_KIND,
    }


def summarize_interview(records: list[dict[str, Any]]) -> dict[str, Any]:
    answered = [record for record in records if not record.get("abstained")]
    object_records = [record for record in answered
                      if (record.get("probe_type") == "object_presence")]
    spatial_records = [record for record in answered
                       if (record.get("probe_type") == "spatial_relation")]
    brier_values = [float(record["brier"]) for record in answered
                    if record.get("brier") is not None]
    confidences = [float(record.get("confidence") or 0.0) for record in answered]
    gains = [float(record.get("information_gain") or 0.0) for record in records
             if record.get("information_gain") is not None]

    def _accuracy(items: list[dict[str, Any]]) -> float | None:
        if not items:
            return None
        return round(sum(1.0 for item in items if item.get("correct")) / len(items), 6)

    accuracy = _accuracy(answered)
    overconfidence = None
    if accuracy is not None and confidences:
        overconfidence = round(sum(confidences) / len(confidences) - accuracy, 6)
    total = len(records)
    return {
        "n_probes": total,
        "n_answered": len(answered),
        "object_accuracy": _accuracy(object_records),
        "spatial_accuracy": _accuracy(spatial_records),
        "mean_brier": round(sum(brier_values) / len(brier_values), 6) if brier_values else None,
        "coverage": round(len(answered) / total, 6) if total else 0.0,
        "abstention_rate": round((total - len(answered)) / total, 6) if total else 0.0,
        "overconfidence": overconfidence,
        "mean_information_gain": round(sum(gains) / len(gains), 6) if gains else None,
    }


def build_reconstruction(belief: EpistemicBelief, probes: tuple[EpistemicProbe, ...],
                         records: list[dict[str, Any]]) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for probe in probes:
        if probe.probe_type == "object_presence":
            probability = belief.probability(probe.variable_id)
            objects.append({
                "label": probe.metadata.get("label") or "object",
                "kind": probe.metadata.get("kind") or "custom",
                "probability": round(probability, 4),
                "status": _status(probability),
            })
        else:
            probability = belief.probability(probe.variable_id)
            relations.append({
                "subject": probe.metadata.get("subject_label") or "subject",
                "relation": "left_of" if probability >= 0.5 else "right_of",
                "object": probe.metadata.get("object_label") or "object",
                "probability": round(probability, 4),
                "status": ("likely_left" if probability >= 0.65
                           else "likely_right" if probability <= 0.35 else "uncertain"),
            })
    object_entropy = _mean_entropy(belief.objects)
    relation_entropy = _mean_entropy(belief.relations)
    return {
        "objects": objects,
        "relations": relations,
        "uncertainty": {
            "object_entropy": object_entropy,
            "relation_entropy": relation_entropy,
        },
        "scores": summarize_interview(records),
        "protocol_version": ERI_PROTOCOL_VERSION,
        "scoring_version": ERI_SCORING_VERSION,
    }


def _mean_entropy(values: dict[str, tuple[float, float]]) -> float:
    if not values:
        return 0.0
    return round(sum(_beta_entropy(alpha, beta) for alpha, beta in values.values()) / len(values), 6)


def _status(probability: float) -> str:
    if probability >= 0.65:
        return "likely_present"
    if probability <= 0.35:
        return "likely_absent"
    return "uncertain"


__all__ = [
    "ERI_PROTOCOL_VERSION",
    "ERI_SCORING_VERSION",
    "ERI_TASK_FAMILY",
    "ERI_RESPONSE_KIND",
    "PROBE_TYPES",
    "EPISTEMIC_TASK_TYPES",
    "FORM_IDS",
    "DEFAULT_MAX_PROBES",
    "MIN_MAX_PROBES",
    "MAX_MAX_PROBES",
    "EpistemicProbe",
    "EpistemicBelief",
    "build_probe_pool",
    "init_belief",
    "select_probe",
    "update_belief",
    "score_probe",
    "summarize_interview",
    "build_reconstruction",
    "information_gain",
    "expected_information_gain",
]
