"""Deterministic procedural candidate generation that respects locks and user edits.

No image model, no network, no hidden target. Variants are perturbations of the symbolic scene, so every
candidate is explainable and can be diffed against the scene the user just saw.
"""
from __future__ import annotations

import colorsys
import hashlib
import random
from dataclasses import dataclass, field

from app.core.animus.scene import library
from app.core.animus.scene.compose import shade
from app.core.animus.scene.diff import diff_scenes
from app.core.animus.scene.model import (
    PROVENANCE_SYSTEM_INFERRED,
    AttributeValue,
    SceneGraph,
    clamp,
)


@dataclass(frozen=True)
class RegenerationConfig:
    count: int = 3
    strength: float = 0.22
    seed: int = 0
    preserve_user_edits: bool = True
    vary_camera: bool = True


@dataclass
class Variant:
    index: int
    scene: SceneGraph
    diff: dict
    notes: list[str] = field(default_factory=list)


def scene_lock_paths(scene: SceneGraph) -> set[str]:
    """Locked entity ids and ``entity_id.attribute`` paths currently enforced by the scene."""
    locks: set[str] = set()
    for entity in scene.entities:
        if entity.locked:
            locks.add(entity.id)
            continue
        for path, attribute in entity.attributes.items():
            if attribute.locked:
                locks.add(f"{entity.id}.{path}")
    return locks


def _is_locked(entity_id: str, path: str | None, locks: set[str]) -> bool:
    if entity_id in locks:
        return True
    return path is not None and f"{entity_id}.{path}" in locks


def _rng(seed: int, scene_hash: str, index: int) -> random.Random:
    payload = f"{seed}:{scene_hash}:{index}".encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big"))


def _shift_color(hex_color: str, rng: random.Random, strength: float) -> str:
    text = library.normalize_color(hex_color).lstrip("#")
    r, g, b = (int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    hue = (hue + rng.uniform(-0.06, 0.06) * strength) % 1.0
    lightness = clamp(lightness + rng.uniform(-0.08, 0.08) * strength, 0.05, 0.95)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#" + "".join(f"{int(round(c * 255)):02x}" for c in (r, g, b))


def _vary_attribute(attribute: AttributeValue, path: str, rng: random.Random,
                    strength: float) -> AttributeValue:
    spec = library.attribute_spec(path)
    if spec is None:
        return attribute
    value = attribute.value
    if spec["type"] == "color":
        value = _shift_color(str(value), rng, strength)
    elif spec["type"] == "number":
        span = float(spec["max"]) - float(spec["min"])
        value = round(clamp(float(value) + rng.uniform(-0.5, 0.5) * span * strength,
                            float(spec["min"]), float(spec["max"])), 6)
    elif spec["type"] == "integer":
        value = int(clamp(int(value) + rng.choice([-1, 0, 1]), float(spec["min"]), float(spec["max"])))
    elif spec["type"] == "enum":
        if path == "animation":
            value = rng.choice([v for v in spec["options"] if v != value])
    return AttributeValue(value=value, confidence=0.4, provenance=PROVENANCE_SYSTEM_INFERRED,
                          locked=attribute.locked, source_text=None, renderable=attribute.renderable)


def regenerate_variants(scene: SceneGraph, config: RegenerationConfig,
                        locks: set[str] | None = None) -> list[Variant]:
    if not 1 <= config.count <= 6:
        raise ValueError("count must be between 1 and 6")
    strength = clamp(float(config.strength), 0.0, 1.0)
    effective_locks = set(locks or ()) | scene_lock_paths(scene)
    base_hash = scene.content_hash()
    user_scene_paths = set(scene.metadata.get("user_scene_paths") or [])
    variants: list[Variant] = []

    for index in range(config.count):
        rng = _rng(config.seed, base_hash, index)
        candidate = scene.copy()
        notes: list[str] = []
        changed = False

        for entity in candidate.entities:
            if entity.id in effective_locks:
                continue
            mutable_attrs = []
            for path, attribute in entity.attributes.items():
                if _is_locked(entity.id, path, effective_locks):
                    continue
                if config.preserve_user_edits and attribute.provenance == "USER_EXPLICIT":
                    continue
                mutable_attrs.append(path)
            if mutable_attrs:
                path = rng.choice(mutable_attrs)
                entity.attributes[path] = _vary_attribute(entity.attributes[path], path, rng, strength)
                changed = True
            if not entity.locked and rng.random() < 0.5:
                entity.rotation = [
                    round(entity.rotation[0] + rng.uniform(-0.2, 0.2) * strength, 6),
                    round(entity.rotation[1] + rng.uniform(-0.6, 0.6) * strength, 6),
                    round(entity.rotation[2] + rng.uniform(-0.15, 0.15) * strength, 6),
                ]
                changed = True

        if config.vary_camera and "camera" not in effective_locks:
            candidate.camera.fov = round(clamp(candidate.camera.fov + rng.uniform(-6, 6) * strength,
                                              20, 90), 6)
            candidate.camera.position[2] = round(candidate.camera.position[2] + rng.uniform(-1.2, 1.2) * strength, 6)
            changed = True
            notes.append("Camera adjusted")

        for path in ("atmosphere.fog.density", "atmosphere.sky.top", "lighting.key.intensity",
                     "lighting.ambient.intensity"):
            if path in effective_locks or (config.preserve_user_edits and path in user_scene_paths):
                continue
            if path == "atmosphere.fog.density":
                candidate.atmosphere.fog_density = round(clamp(
                    candidate.atmosphere.fog_density + rng.uniform(-0.01, 0.01) * strength, 0, 0.2), 6)
            elif path == "atmosphere.sky.top":
                candidate.atmosphere.sky_top = shade(
                    _shift_color(candidate.atmosphere.sky_top, rng, strength * 0.5), 1.0)
            elif path == "lighting.key.intensity":
                candidate.lighting.key_intensity = round(clamp(
                    candidate.lighting.key_intensity + rng.uniform(-0.2, 0.2) * strength, 0, 8), 6)
            else:
                candidate.lighting.ambient_intensity = round(clamp(
                    candidate.lighting.ambient_intensity + rng.uniform(-0.1, 0.1) * strength, 0, 4), 6)
            changed = True

        if not changed:
            notes.append("Content is fully locked or user-authored; this variant keeps the composition")
        candidate = SceneGraph.from_dict(candidate.to_dict())
        diff = diff_scenes(scene, candidate)
        preserved = sorted(effective_locks & scene_lock_paths(scene))
        if preserved:
            notes.append(f"Preserved {len(preserved)} locked path{'s' if len(preserved) != 1 else ''}")
        diff["locked_untouched"] = sorted(set(diff.get("locked_untouched", [])) | set(preserved))
        variants.append(Variant(index=index, scene=candidate, diff=diff, notes=notes))

    return variants


__all__ = ["RegenerationConfig", "Variant", "regenerate_variants", "scene_lock_paths"]
