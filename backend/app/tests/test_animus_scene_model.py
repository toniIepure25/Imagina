"""Scene graph invariants, composition, and belief bridge (no DB, no neural data)."""
from __future__ import annotations

import pytest

from app.core.animus.models import ImaginationBeliefState
from app.core.animus.scene.compose import compose_from_intention
from app.core.animus.scene.model import (
    PROVENANCE_NEURAL_IMAGERY_FORBIDDEN,
    PROVENANCE_USER_EXPLICIT,
    AttributeValue,
    SceneEntity,
    SceneGraph,
    SceneValidationError,
    canonical_hash,
    make_entity_id,
    make_scene_id,
    sanitize_text,
)
from app.core.animus.scene.resolve import resolve_belief_scene

pytestmark = pytest.mark.core


def test_scene_roundtrip_and_hash_are_stable():
    result = compose_from_intention("a white castle above a dark ocean at dusk", seed=11)
    scene = result.scene
    restored = SceneGraph.from_dict(scene.to_dict())
    assert restored.to_dict() == scene.to_dict()
    assert restored.content_hash() == scene.content_hash()
    assert scene.content_hash() == scene.content_hash()


def test_hash_changes_when_visible_content_changes():
    scene = compose_from_intention("a white castle above a dark ocean", seed=5).scene
    before = scene.content_hash()
    scene.entities[0].attributes["color"] = AttributeValue(
        value="#8a5cf0", provenance=PROVENANCE_USER_EXPLICIT, confidence=1.0)
    assert scene.content_hash() != before


def test_entity_ids_are_deterministic_and_unique():
    assert make_entity_id(1, "castle", 0) == make_entity_id(1, "castle", 0)
    assert make_entity_id(1, "castle", 0) != make_entity_id(1, "castle", 1)
    assert make_scene_id(1).startswith("scene_")


def test_forbidden_imagery_provenance_is_rejected():
    with pytest.raises(SceneValidationError):
        AttributeValue(value="x", provenance=PROVENANCE_NEURAL_IMAGERY_FORBIDDEN)


def test_invalid_entity_id_is_rejected():
    with pytest.raises(SceneValidationError):
        SceneEntity(id="castle-1", kind="castle", label="Castle")


def test_non_finite_numbers_are_rejected():
    with pytest.raises(SceneValidationError):
        SceneEntity(id=make_entity_id(1, "castle", 0), kind="castle", label="Castle",
                    position=[0, float("nan"), 0])


def test_text_is_sanitized_and_bounded():
    assert sanitize_text("  hello\x00   world  ") == "hello world"
    assert len(sanitize_text("x" * 5000)) == 500


def test_composition_is_deterministic():
    a = compose_from_intention("a gothic castle above a violet ocean at night", seed=9).scene
    b = compose_from_intention("a gothic castle above a violet ocean at night", seed=9).scene
    assert a.content_hash() == b.content_hash()


def test_composition_recognizes_nouns_counts_and_style():
    result = compose_from_intention("two moons over a gothic castle at night", seed=3)
    kinds = [e.kind for e in result.scene.entities]
    assert kinds.count("moon") == 2
    assert "castle" in kinds
    assert result.scene.style == "gothic"
    assert result.scene.atmosphere.time_of_day == "night"


def test_composition_unknown_noun_is_abstract_with_warning():
    result = compose_from_intention("a giant turtle beside a crystal", seed=4)
    assert any(e.kind == "custom" for e in result.scene.entities)
    assert any("abstract form" in w for w in result.warnings)


def test_composition_negative_removes_element():
    result = compose_from_intention("a castle with no fog", seed=2)
    assert all(e.kind != "fog" for e in result.scene.entities)


def test_composition_never_exceeds_entity_cap():
    text = " ".join(["castle", "moon", "tree", "water", "star", "fire", "bird", "boat", "flower"] * 4)
    scene = compose_from_intention(text, seed=1).scene
    assert len(scene.entities) <= 40


def test_belief_bridge_is_simulated_and_does_not_mutate_belief():
    belief = ImaginationBeliefState.broad_prior()
    belief.objects["castle"] = 0.9
    before = belief.history_hash()
    scene = resolve_belief_scene(belief, seed=1)
    assert scene.metadata["claim_level"] == "L0_SIMULATED"
    assert all(a.provenance == "SIMULATED" for e in scene.entities for a in e.attributes.values())
    assert belief.history_hash() == before


def test_canonical_hash_is_order_insensitive_for_objects():
    assert canonical_hash({"b": 1, "a": 2}) == canonical_hash({"a": 2, "b": 1})
