"""One-way bridge from the research belief state (IBS-v1) to a displayable SceneGraph.

Benchmark and research demos only. Nothing here writes back into a belief state, and provenance is
``SIMULATED`` so the product can never present this as user-confirmed content.
"""
from __future__ import annotations

from app.core.animus import vocab
from app.core.animus.models import ImaginationBeliefState
from app.core.animus.scene import library
from app.core.animus.scene.model import (
    PROVENANCE_SIMULATED,
    AttributeValue,
    SceneEntity,
    SceneGraph,
    SceneRelation,
    make_entity_id_unique,
    new_scene,
)

PALETTE_COLORS = {
    "cold": "#4a7cf0", "neutral": "#c9c3b5", "warm": "#f2b06a", "vivid": "#d23fa0",
}


def resolve_belief_scene(belief: ImaginationBeliefState, *, seed: int | None = None,
                         title: str = "Benchmark scene") -> SceneGraph:
    use_seed = int(seed if seed is not None else belief.iteration + 20260909)
    graph = belief.scene_graph()
    attributes = graph.get("attributes", {})
    scene = new_scene(use_seed, title)
    scene.metadata = {
        "claim_level": "L0_SIMULATED",
        "generator": "belief-resolver.v1",
        "source": "IBS-v1",
        "warnings": ["Simulated benchmark scene; not user-confirmed content"],
    }

    palette = PALETTE_COLORS.get(attributes.get("color_palette", "neutral"), "#c9c3b5")
    scene.lighting.key_intensity = {"dark": 0.4, "dim": 0.65, "medium": 1.0, "bright": 1.5}.get(
        attributes.get("brightness", "medium"), 1.0)
    scene.atmosphere.fog_density = {"flat": 0.008, "shallow": 0.02, "deep": 0.045}.get(
        attributes.get("depth", "shallow"), 0.02)
    scene.dynamics.water = 0.6 if "water" in graph.get("objects", []) else 0.1
    scene.dynamics.wind = {"still": 0.0, "slow": 0.25, "dynamic": 0.7}.get(
        attributes.get("motion", "slow"), 0.25)
    viewpoint = attributes.get("viewpoint", "medium")
    if viewpoint == "aerial":
        scene.camera.position = [0.0, 9.0, 10.0]
    elif viewpoint == "close":
        scene.camera.position = [0.0, 1.6, 4.2]
    elif viewpoint == "wide":
        scene.camera.position = [0.0, 3.2, 15.0]

    existing: set[str] = set()
    by_kind: dict[str, SceneEntity] = {}
    for index, kind in enumerate(graph.get("objects", [])):
        normalized = library.normalize_kind(str(kind))
        if normalized == "custom":
            normalized = "custom"
        entity_id = make_entity_id_unique(use_seed, normalized, index, existing)
        existing.add(entity_id)
        defaults = dict(library.KIND_DEFAULT_ATTRIBUTES.get(normalized, {}))
        defaults["color"] = palette
        attrs: dict[str, AttributeValue] = {}
        for path, value in defaults.items():
            spec = library.attribute_spec(path)
            if spec and spec["type"] == "color":
                value = library.normalize_color(str(value))
            attrs[path] = AttributeValue(value=value, confidence=0.5,
                                         provenance=PROVENANCE_SIMULATED)
        entity = SceneEntity(id=entity_id, kind=normalized,
                             label=library.kind_label(normalized),
                             role=library.default_role(normalized),
                             position=library.default_position(normalized, index),
                             attributes=attrs, confidence=0.5, provenance=PROVENANCE_SIMULATED)
        scene.entities.append(entity)
        by_kind[normalized] = entity

    entity_names = {e.kind: e.id for e in scene.entities}
    entity_names.update({e.label.lower(): e.id for e in scene.entities})
    for relation in graph.get("relations", []):
        try:
            subject, name, obj = relation
        except (TypeError, ValueError):
            continue
        subject_id = entity_names.get(str(subject).lower())
        object_id = entity_names.get(str(obj).lower())
        if not subject_id or not object_id or subject_id == object_id:
            continue
        if name not in ("above", "below", "left_of", "right_of", "behind", "in_front_of"):
            continue
        scene.relations.append(SceneRelation(subject_id=subject_id, relation=name,
                                             object_id=object_id, confidence=0.45,
                                             provenance=PROVENANCE_SIMULATED))

    if not scene.entities:
        entity_id = make_entity_id_unique(use_seed, "custom", 0, set())
        scene.entities.append(SceneEntity(
            id=entity_id, kind="custom", label="Abstract form", role="subject",
            attributes={"color": AttributeValue(value=palette, provenance=PROVENANCE_SIMULATED)},
            confidence=0.4, provenance=PROVENANCE_SIMULATED,
        ))
    if attributes.get("complexity") == "complex" and len(scene.entities) < 6:
        scene.metadata["warnings"].append(
            "The benchmark twin's complexity attribute exceeds the displayed element count")
    return scene


def belief_object_vocab() -> list[str]:
    return list(vocab.OBJECT_VOCAB)


__all__ = ["resolve_belief_scene", "belief_object_vocab"]
