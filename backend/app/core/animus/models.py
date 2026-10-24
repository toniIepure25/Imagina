"""ANIMUS core data models (IBS-v1).

Model-independent representation of the system's *belief* about a user's imagined content, plus the typed
envelopes that flow through the loop (observations, feedback, candidates). Nothing here assumes a specific
generative model or embedding (e.g. CLIP); an ``EmbeddingSpec`` records which model produced a vector so a
future decoder can be swapped in without redesign.

All structures serialize to plain JSON via ``to_dict`` and hash deterministically via ``canonical_hash`` so
sessions replay bit-exactly under a fixed seed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.animus import vocab
from app.core.animus.claims import L0_SIMULATED

IBS_VERSION = "IBS-v1"

# Observation source modes (see ObservationProvider). No silent fallback between them.
SOURCE_BEHAVIORAL = "BEHAVIORAL"
SOURCE_SIMULATED_NEURAL = "SIMULATED_NEURAL"
SOURCE_REPLAY = "REPLAY"
SOURCE_VALIDATED_NEURAL_FUTURE = "VALIDATED_NEURAL_FUTURE"
SOURCE_VALIDATED_PERCEPTION_NEURAL = "VALIDATED_PERCEPTION_NEURAL"  # P2: real, validated perception content


def _round_list(x: np.ndarray, nd: int = 6) -> list[float]:
    return [round(float(v), nd) for v in np.asarray(x, dtype=float).ravel()]


def canonical_hash(obj: Any) -> str:
    """Deterministic sha256 over a JSON-canonicalized object (sorted keys, rounded floats upstream)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class EmbeddingSpec:
    dimension: int
    model_id: str = "animus-synthetic-embed"
    model_hash: str = "synthetic-v1"
    normalization: str = "unit_l2"

    def to_dict(self) -> dict:
        return {"dimension": self.dimension, "model_id": self.model_id,
                "model_hash": self.model_hash, "normalization": self.normalization}


@dataclass
class GaussianBelief:
    """Diagonal-covariance Gaussian belief over a continuous embedding channel."""
    mean: np.ndarray
    variance: np.ndarray
    spec: EmbeddingSpec

    @classmethod
    def broad(cls, dim: int, var: float = 1.0, model_id: str = "animus-synthetic-embed") -> "GaussianBelief":
        return cls(mean=np.zeros(dim), variance=np.full(dim, float(var)),
                   spec=EmbeddingSpec(dimension=dim, model_id=model_id))

    def scalar_uncertainty(self) -> float:
        return float(np.mean(self.variance))

    def to_dict(self) -> dict:
        return {"mean": _round_list(self.mean), "variance": _round_list(self.variance),
                "spec": self.spec.to_dict()}


@dataclass
class CategoricalBelief:
    """Probability distribution over a fixed option set."""
    probs: dict[str, float]

    @classmethod
    def uniform(cls, options: list[str]) -> "CategoricalBelief":
        return cls(vocab.uniform_categorical(options))

    def normalized(self) -> "CategoricalBelief":
        s = sum(self.probs.values())
        if s <= 0:
            n = len(self.probs)
            return CategoricalBelief({k: 1.0 / n for k in self.probs})
        return CategoricalBelief({k: v / s for k, v in self.probs.items()})

    def argmax(self) -> str:
        return max(self.probs.items(), key=lambda kv: kv[1])[0]

    def confidence(self) -> float:
        return max(self.probs.values()) if self.probs else 0.0

    def entropy(self) -> float:
        e = 0.0
        for p in self.probs.values():
            if p > 0:
                e -= p * np.log(p)
        return float(e)

    def to_dict(self) -> dict:
        return {k: round(float(v), 6) for k, v in self.probs.items()}


@dataclass
class ImaginationBeliefState:
    """IBS-v1 — the central, model-independent belief about imagined content."""
    visual_embedding: GaussianBelief
    semantic_embedding: GaussianBelief
    objects: dict[str, float]                        # object -> P(present)
    global_scene_attributes: dict[str, CategoricalBelief]
    spatial_relations: list[dict]                    # [{"subject","relation","object","confidence"}]
    iteration: int = 0
    evidence_sources: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    version: str = IBS_VERSION

    @classmethod
    def broad_prior(cls, provenance: dict | None = None) -> "ImaginationBeliefState":
        return cls(
            visual_embedding=GaussianBelief.broad(vocab.VISUAL_EMBED_DIM, var=1.0, model_id="animus-visual"),
            semantic_embedding=GaussianBelief.broad(vocab.SEMANTIC_EMBED_DIM, var=1.0,
                                                    model_id="animus-semantic"),
            # absent-leaning prior: a scene contains only a few of the candidate objects
            objects={o: 0.3 for o in vocab.OBJECT_VOCAB},
            global_scene_attributes={a: CategoricalBelief.uniform(opts)
                                     for a, opts in vocab.SCENE_ATTRIBUTES.items()},
            spatial_relations=[],
            provenance=provenance or {},
        )

    # --- uncertainty summaries -------------------------------------------------
    def confidence_by_component(self) -> dict[str, float]:
        out = {"visual_embedding": 1.0 / (1.0 + self.visual_embedding.scalar_uncertainty()),
               "semantic_embedding": 1.0 / (1.0 + self.semantic_embedding.scalar_uncertainty())}
        for a, cb in self.global_scene_attributes.items():
            out[f"attr:{a}"] = round(cb.confidence(), 6)
        # object confidence = distance of P(present) from 0.5 (decided-ness)
        out["objects"] = round(float(np.mean([abs(p - 0.5) * 2 for p in self.objects.values()])), 6)
        return out

    def global_uncertainty(self) -> float:
        vis = self.visual_embedding.scalar_uncertainty()
        sem = self.semantic_embedding.scalar_uncertainty()
        attr_ent = float(np.mean([cb.entropy() for cb in self.global_scene_attributes.values()]))
        obj_unc = float(np.mean([1.0 - abs(p - 0.5) * 2 for p in self.objects.values()]))
        return float(0.4 * (vis + sem) / 2 + 0.3 * (attr_ent / np.log(4)) + 0.3 * obj_unc)

    # --- serialization / hashing ----------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "iteration": self.iteration,
            "visual_embedding": self.visual_embedding.to_dict(),
            "semantic_embedding": self.semantic_embedding.to_dict(),
            "objects": {k: round(float(v), 6) for k, v in self.objects.items()},
            "global_scene_attributes": {a: cb.to_dict() for a, cb in self.global_scene_attributes.items()},
            "spatial_relations": self.spatial_relations,
            "confidence_by_component": self.confidence_by_component(),
            "global_uncertainty": round(self.global_uncertainty(), 6),
            "evidence_sources": list(self.evidence_sources),
            "provenance": self.provenance,
            "constraints": self.constraints,
        }

    def history_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def scene_graph(self) -> dict:
        """Discrete MAP scene graph used for edit-distance and generation specs."""
        return {
            "objects": sorted([o for o, p in self.objects.items() if p >= 0.5]),
            "attributes": {a: cb.argmax() for a, cb in self.global_scene_attributes.items()},
            "relations": [(r["subject"], r["relation"], r["object"]) for r in self.spatial_relations],
        }


@dataclass
class ObservationEnvelope:
    """Everything an ObservationProvider returns for one measurement."""
    source_type: str
    representation: dict                 # channel -> value (e.g. {"visual": [...]})
    uncertainty: dict                    # channel -> variance/quality
    signal_quality: float
    measurement_id: str
    timestamp: str
    provenance: dict
    scientific_authorization: str
    claim_level: str = L0_SIMULATED

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type, "representation": self.representation,
            "uncertainty": self.uncertainty, "signal_quality": round(float(self.signal_quality), 6),
            "measurement_id": self.measurement_id, "timestamp": self.timestamp,
            "provenance": self.provenance, "scientific_authorization": self.scientific_authorization,
            "claim_level": self.claim_level,
        }


# Feedback channel identifiers (see feedback.py).
FB_CLOSER_FARTHER = "closer_farther"
FB_PAIRWISE = "pairwise"
FB_ATTRIBUTE = "attribute_correction"
FB_OBJECT = "object_correction"
FB_FREETEXT = "freetext"
FB_CONFIDENCE = "confidence"
FB_REIMAGINE = "reimagine"


@dataclass
class FeedbackEvidence:
    """Normalized user feedback with uncertainty + provenance."""
    channel: str
    content: dict
    uncertainty: float
    provenance: dict
    claim_level: str = L0_SIMULATED

    def to_dict(self) -> dict:
        return {"channel": self.channel, "content": self.content,
                "uncertainty": round(float(self.uncertainty), 6),
                "provenance": self.provenance, "claim_level": self.claim_level}


@dataclass
class Candidate:
    """One immutable, versioned candidate produced by a CandidateGenerator."""
    candidate_id: str
    iteration: int
    visual_embedding: list[float]
    scene_graph: dict
    description: str
    generator: str
    seed: int
    modality: str = "scene"            # scene | image | text | future_video | future_3d
    asset_ref: str | None = None       # opaque ref (mock/local generator); never raw signal

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id, "iteration": self.iteration,
            "visual_embedding": [round(float(v), 6) for v in self.visual_embedding],
            "scene_graph": self.scene_graph, "description": self.description,
            "generator": self.generator, "seed": self.seed, "modality": self.modality,
            "asset_ref": self.asset_ref,
        }


@dataclass
class CandidateSet:
    candidates: list[Candidate]
    request: dict

    def to_dict(self) -> dict:
        return {"candidates": [c.to_dict() for c in self.candidates], "request": self.request}
