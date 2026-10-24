"""ANIMUS structured-attribute vocabulary (IBS-v1).

The fixed, versioned option sets for the structured part of the imagination belief state. Kept tiny and
explicit so categorical Bayesian updates and scene-graph edit distance are well defined and testable. The
digital twin and the belief state share this vocabulary; changing it is a schema-version change.
"""
from __future__ import annotations

VOCAB_VERSION = "IBS-v1"

# Global scene attributes: name -> ordered list of mutually-exclusive options.
SCENE_ATTRIBUTES: dict[str, list[str]] = {
    "brightness": ["dark", "dim", "medium", "bright"],
    "color_palette": ["cold", "neutral", "warm", "vivid"],
    "depth": ["flat", "shallow", "deep"],
    "texture": ["smooth", "detailed", "rough"],
    "motion": ["still", "slow", "dynamic"],
    "complexity": ["minimal", "moderate", "complex"],
    "realism": ["abstract", "stylized", "realistic"],
    "viewpoint": ["close", "medium", "wide", "aerial"],
}

# Candidate objects that may or may not be present in an imagined scene.
OBJECT_VOCAB: list[str] = [
    "castle", "moon", "fog", "tree", "mountain", "water", "person", "road",
    "star", "cloud", "fire", "bird", "building", "flower", "boat", "bridge",
]

# Spatial relations between object pairs (used for scene-graph structure).
SPATIAL_RELATIONS: list[str] = ["above", "below", "left_of", "right_of", "behind", "in_front_of"]

# Embedding dimensions for the two continuous belief channels.
VISUAL_EMBED_DIM = 16
SEMANTIC_EMBED_DIM = 16


def uniform_categorical(options: list[str]) -> dict[str, float]:
    p = 1.0 / len(options)
    return {o: p for o in options}
