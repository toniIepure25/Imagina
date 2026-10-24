"""ANIMUS-P2 frozen target representation (the neural output space ANIMUS consumes).

The decoder predicts a representation derived from the ACTUAL visual stimulus (not a caption). The exact
encoder is chosen on NON-neural criteria and pinned (name, weights hash, preprocessing, dim, normalization)
in a seal BEFORE any BOLD outcome. In this environment the real encoder (a frozen open vision/vision-language
model) is loaded on the cluster; the local synthetic embedder is a deterministic stand-in used ONLY for
method validation and clearly labelled as such.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

PRIMARY_ENCODER = {
    "family": "frozen_vision_language_embedding",
    "model_id": "open_clip:ViT-B-32",              # pinned exact model/version at staging
    "pretrained": "laion2b_s34b_b79k",
    "embedding_dim": 512,
    "input_preprocessing": "clip_bicubic_224_center_crop_openai_norm",
    "normalization": "unit_l2",
    "derived_from": "visual_stimulus_image (NOT caption)",
    "weights_hash": "TO_PIN_AT_STAGING",
    "code_version": "open_clip_torch (pinned at staging)",
}
SECONDARY_ENCODER = {
    "family": "self_supervised_visual_embedding",
    "model_id": "dinov2:vitb14",
    "embedding_dim": 768,
    "normalization": "unit_l2",
    "role": "SECONDARY (descriptive only)",
    "weights_hash": "TO_PIN_AT_STAGING",
}


def unit_l2(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.clip(n, 1e-9, None)


@dataclass
class SyntheticStimulusEncoder:
    """Deterministic per-identity embedding stand-in for METHOD VALIDATION ONLY (no real images)."""
    dim: int = 512
    seed: int = 20260909

    def embed(self, stimulus_id: str) -> np.ndarray:
        h = hashlib.sha256(f"{self.seed}:{stimulus_id}".encode()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
        return unit_l2(rng.standard_normal(self.dim))

    def embed_many(self, stimulus_ids) -> np.ndarray:
        return np.stack([self.embed(s) for s in stimulus_ids])


def target_representation_seal(primary=PRIMARY_ENCODER, secondary=SECONDARY_ENCODER) -> dict:
    body = {"artifact": "ANIMUS_P2_TARGET_REPRESENTATION_SEAL", "milestone": "ANIMUS-P2",
            "primary_encoder": primary, "secondary_encoder": secondary,
            "primary_target_is_visual_stimulus_not_caption": True,
            "caption_targets_role": "SECONDARY only (never primary; prevents semantic-annotation shortcut)",
            "chosen_on_non_neural_criteria": True}
    body["self_hash"] = hashlib.sha256(
        __import__("json").dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return body
