"""Scene command semantics: validation, locks, diffs, relations."""
from __future__ import annotations

import pytest

from app.core.animus.scene.commands import (
    LockedContentError,
    UnknownEntityError,
    apply_commands,
    parse_command,
)
from app.core.animus.scene.compose import compose_from_intention
from app.core.animus.scene.model import SceneValidationError

pytestmark = pytest.mark.core


def _scene(text: str = "a white castle above a dark ocean", seed: int = 7):
    return compose_from_intention(text, seed=seed).scene


def _castle(scene):
    return next(e for e in scene.entities if e.kind == "castle")


def test_set_entity_attribute_changes_only_target():
    scene = _scene()
    castle = _castle(scene)
    before_water = next(e for e in scene.entities if e.kind == "water").attributes["color"].value
    updated, diff, warnings = apply_commands(scene, [parse_command({
        "op": "set_entity_attribute", "entity_id": castle.id, "path": "color", "value": "violet",
        "lock": True})])
    assert _castle(updated).attributes["color"].value == "#8a5cf0"
    assert _castle(updated).attributes["color"].locked is True
    assert next(e for e in updated.entities if e.kind == "water").attributes["color"].value == before_water
    assert any("Color" in line for line in diff["explanation"])
    assert warnings == []
    assert updated.version == scene.version
    assert scene.content_hash() != updated.content_hash()


def test_locked_attribute_cannot_be_changed():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "path": "color", "locked": True})])
    with pytest.raises(LockedContentError):
        apply_commands(scene, [parse_command({
            "op": "set_entity_attribute", "entity_id": castle.id, "path": "color", "value": "black"})])


def test_unlock_then_change():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "path": "color", "locked": True})])
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "path": "color", "locked": False})])
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "set_entity_attribute", "entity_id": castle.id, "path": "color", "value": "black"})])
    assert _castle(scene).attributes["color"].value == "#080a12"


def test_entity_lock_blocks_transform_and_remove():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [parse_command({"op": "lock", "entity_id": castle.id,
                                                        "path": "", "locked": True})])
    with pytest.raises(LockedContentError):
        apply_commands(scene, [parse_command({"op": "remove_entity", "entity_id": castle.id})])
    with pytest.raises(LockedContentError):
        apply_commands(scene, [parse_command({"op": "set_entity_transform", "entity_id": castle.id,
                                              "position": [1, 0, 0]})])


def test_add_and_remove_entity_cleans_relations():
    scene = _scene()
    added, diff, _ = apply_commands(scene, [parse_command({
        "op": "add_entity", "kind": "moon", "label": "second moon", "position": [3, 4, -2]})])
    assert sum(1 for e in added.entities if e.kind == "moon") == 1
    assert diff["added"]
    moon = next(e for e in added.entities if e.kind == "moon")
    added, _, _ = apply_commands(added, [parse_command({
        "op": "set_relation", "subject_id": moon.id, "relation": "above",
        "object_id": _castle(added).id})])
    assert any(r.subject_id == moon.id for r in added.relations)
    updated, _, _ = apply_commands(added, [parse_command({"op": "remove_entity", "entity_id": moon.id})])
    assert all(r.subject_id != moon.id and r.object_id != moon.id for r in updated.relations)


def test_unknown_entity_is_reported():
    scene = _scene()
    with pytest.raises(UnknownEntityError):
        apply_commands(scene, [parse_command({"op": "set_entity_transform",
                                              "entity_id": "ent_deadbeef", "position": [0, 0, 0]})])


def test_scene_attributes_and_validation():
    scene = _scene()
    updated, diff, _ = apply_commands(scene, [
        parse_command({"op": "set_scene_attribute", "path": "style", "value": "surreal"}),
        parse_command({"op": "set_scene_attribute", "path": "camera.fov", "value": 62}),
        parse_command({"op": "set_scene_attribute", "path": "atmosphere.sky.top", "value": "#8a5cf0"}),
    ])
    assert updated.style == "surreal"
    assert updated.camera.fov == 62
    assert updated.atmosphere.sky_top == "#8a5cf0"
    assert diff["changed"]
    with pytest.raises(SceneValidationError):
        apply_commands(scene, [parse_command({"op": "set_scene_attribute", "path": "style",
                                              "value": "not-a-style"})])
    with pytest.raises(SceneValidationError):
        apply_commands(scene, [parse_command({"op": "set_scene_attribute", "path": "camera.nope",
                                              "value": 1})])


def test_custom_attribute_is_stored_not_rendered():
    scene = _scene()
    castle = _castle(scene)
    updated, _, warnings = apply_commands(scene, [parse_command({
        "op": "set_entity_attribute", "entity_id": castle.id, "path": "mood_note", "value": "lonely"})])
    attr = _castle(updated).attributes["mood_note"]
    assert attr.value == "lonely"
    assert attr.renderable is False
    assert any("not rendered" in w for w in warnings)


def test_command_schema_rejects_extra_fields_and_bad_ops():
    with pytest.raises(SceneValidationError):
        parse_command({"op": "set_entity_attribute", "entity_id": "ent_1234abcd",
                       "path": "color", "value": "red", "oops": 1})
    with pytest.raises(SceneValidationError):
        parse_command({"op": "explode"})
    with pytest.raises(SceneValidationError):
        apply_commands(_scene(), [parse_command({"op": "set_scene_attribute", "path": "camera.fov",
                                                  "value": float("inf")})])


def test_empty_batch_is_rejected():
    with pytest.raises(SceneValidationError):
        apply_commands(_scene(), [])


def test_no_change_is_reported():
    scene = _scene()
    castle = _castle(scene)
    color = castle.attributes["color"].value
    _, _, warnings = apply_commands(scene, [parse_command({
        "op": "set_entity_attribute", "entity_id": castle.id, "path": "color", "value": color})])
    assert any("No change" in warning for warning in warnings)


def test_element_level_lock_without_path_blocks_edits_and_survives_unlock():
    scene = _scene()
    castle = _castle(scene)
    updated, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "locked": True})])
    assert _castle(updated).locked is True
    assert _castle(updated).attributes["color"].locked is False
    with pytest.raises(LockedContentError):
        apply_commands(updated, [parse_command({
            "op": "set_entity_attribute", "entity_id": castle.id, "path": "color", "value": "black"})])
    unlocked, _, _ = apply_commands(updated, [parse_command({
        "op": "lock", "entity_id": castle.id, "locked": False})])
    assert _castle(unlocked).locked is False
    assert updated.content_hash() != scene.content_hash()
