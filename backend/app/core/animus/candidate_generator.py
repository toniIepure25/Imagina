"""ANIMUS candidate generation + the belief->generation privacy boundary.

A ``CandidateGenerator`` turns a belief state into concrete candidates. Crucially, a generator receives only
a SANITIZED ``GenerationSpec`` built by ``BeliefToGenerationSpec`` — a semantic/structured description plus
approved (small, synthetic) embeddings and a seed. Raw neural arrays, participant identifiers, and raw
biosignal time series can never reach a generator (enforced here and by a privacy test).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from app.core.animus.models import Candidate, CandidateSet, ImaginationBeliefState

# Keys that must NEVER appear in a generation spec/payload.
FORBIDDEN_PAYLOAD_KEYS = (
    "raw_neural", "neural_timeseries", "eeg", "fmri", "bold", "raw_signal",
    "participant_id", "subject_id", "mrn", "medical", "dob", "date_of_birth",
    "forward_operator", "raw_measurement",
)


class PrivacyViolation(RuntimeError):
    pass


@dataclass
class GenerationSpec:
    semantic_summary: str
    scene_graph: dict
    visual_attributes: dict
    approved_embedding: list[float]      # small synthetic embedding, allowed
    seed: int
    modality: str = "scene"

    def to_payload(self) -> dict:
        payload = {"semantic_summary": self.semantic_summary, "scene_graph": self.scene_graph,
                   "visual_attributes": self.visual_attributes,
                   "approved_embedding": [round(float(v), 6) for v in self.approved_embedding],
                   "seed": self.seed, "modality": self.modality}
        assert_no_forbidden_content(payload)
        return payload


def assert_no_forbidden_content(payload: dict) -> None:
    """Recursively verify a payload carries no raw neural data / identifiers. Fail-closed."""
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if any(bad in kl for bad in FORBIDDEN_PAYLOAD_KEYS):
                    raise PrivacyViolation(f"forbidden key in generation payload: {path}{k}")
                walk(v, f"{path}{k}.")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                walk(v, f"{path}{i}.")
            # a large raw array masquerading as an embedding is rejected
            if len(obj) > 512:
                raise PrivacyViolation(f"payload array too large (possible raw signal) at {path}")
    walk(payload)


class BeliefToGenerationSpec:
    """Builds a sanitized generation spec from a belief state (the ONLY bridge to a generator)."""

    def build(self, belief: ImaginationBeliefState, seed: int, modality: str = "scene") -> GenerationSpec:
        sg = belief.scene_graph()
        attrs = sg["attributes"]
        summary = self._describe(sg)
        spec = GenerationSpec(
            semantic_summary=summary, scene_graph=sg, visual_attributes=attrs,
            approved_embedding=[round(float(v), 6) for v in belief.visual_embedding.mean],
            seed=seed, modality=modality)
        assert_no_forbidden_content(spec.to_payload())
        return spec

    @staticmethod
    def _describe(sg: dict) -> str:
        objs = ", ".join(sg["objects"]) or "an abstract scene"
        a = sg["attributes"]
        return (f"A {a.get('brightness','')} {a.get('color_palette','')} scene with {objs}; "
                f"{a.get('texture','')} texture, {a.get('depth','')} depth, {a.get('motion','')} motion, "
                f"{a.get('realism','')} style, {a.get('viewpoint','')} viewpoint").replace("  ", " ").strip()


class CandidateGenerator(ABC):
    name: str

    @abstractmethod
    def generate(self, belief: ImaginationBeliefState, request: dict) -> CandidateSet:
        ...

    @staticmethod
    def _cid(seed: int, iteration: int, k: int) -> str:
        return "cand-" + hashlib.sha256(f"{seed}:{iteration}:{k}".encode()).hexdigest()[:12]


class DeterministicSceneGenerator(CandidateGenerator):
    """Deterministic scene-graph candidate at the belief mean (+ optional seeded jitter for alternatives).
    CI-safe: no model weights, no network."""
    name = "deterministic-scene"

    def __init__(self):
        self._spec_builder = BeliefToGenerationSpec()

    def generate(self, belief: ImaginationBeliefState, request: dict) -> CandidateSet:
        seed = int(request.get("seed", 0))
        n = int(request.get("n", 1))
        jitter = float(request.get("jitter", 0.0))
        it = belief.iteration
        base = np.asarray(belief.visual_embedding.mean, float)
        cands = []
        for k in range(n):
            rng = np.random.default_rng(seed * 1000003 + it * 101 + k)
            emb = base + (jitter * rng.standard_normal(base.shape) if (jitter and k > 0) else 0.0)
            spec = self._spec_builder.build(belief, seed=seed + k, modality=request.get("modality", "scene"))
            cands.append(Candidate(
                candidate_id=self._cid(seed, it, k), iteration=it, visual_embedding=list(emb),
                scene_graph=spec.scene_graph, description=spec.semantic_summary,
                generator=self.name, seed=seed + k, modality=spec.modality,
                asset_ref=None))
        return CandidateSet(cands, request={"generator": self.name, "n": n, "jitter": jitter, "seed": seed})


class MockImageGenerator(CandidateGenerator):
    """Deterministic mock 'image' generator: emits a stable asset_ref hash instead of pixels (CI-safe)."""
    name = "mock-image"

    def __init__(self):
        self._spec_builder = BeliefToGenerationSpec()

    def generate(self, belief: ImaginationBeliefState, request: dict) -> CandidateSet:
        seed = int(request.get("seed", 0))
        spec = self._spec_builder.build(belief, seed=seed, modality="image")
        payload = spec.to_payload()
        ref = "mockimg-" + hashlib.sha256(str(payload).encode()).hexdigest()[:16]
        c = Candidate(candidate_id=self._cid(seed, belief.iteration, 0), iteration=belief.iteration,
                      visual_embedding=list(np.asarray(belief.visual_embedding.mean, float)),
                      scene_graph=spec.scene_graph, description=spec.semantic_summary,
                      generator=self.name, seed=seed, modality="image", asset_ref=ref)
        return CandidateSet([c], request={"generator": self.name, "seed": seed})


class LocalGenerativeAdapter(CandidateGenerator):
    """Boundary for a REAL local generator (e.g. Diffusers/ComfyUI local API). Never used in CI: if no
    local backend is wired it falls back to a deterministic asset_ref so the interface stays exercised,
    and it only ever receives a sanitized GenerationSpec. No cloud API, no weights in CI."""
    name = "local-generative"

    def __init__(self, backend=None):
        self._backend = backend
        self._spec_builder = BeliefToGenerationSpec()

    def generate(self, belief: ImaginationBeliefState, request: dict) -> CandidateSet:
        seed = int(request.get("seed", 0))
        spec = self._spec_builder.build(belief, seed=seed, modality=request.get("modality", "image"))
        payload = spec.to_payload()                 # sanitized; privacy-checked
        if self._backend is not None:               # pragma: no cover - real local backend
            ref = self._backend.render(payload)
        else:
            ref = "localgen-stub-" + hashlib.sha256(str(payload).encode()).hexdigest()[:16]
        c = Candidate(candidate_id=self._cid(seed, belief.iteration, 0), iteration=belief.iteration,
                      visual_embedding=list(np.asarray(belief.visual_embedding.mean, float)),
                      scene_graph=spec.scene_graph, description=spec.semantic_summary,
                      generator=self.name, seed=seed, modality=spec.modality, asset_ref=ref)
        return CandidateSet([c], request={"generator": self.name, "seed": seed})
