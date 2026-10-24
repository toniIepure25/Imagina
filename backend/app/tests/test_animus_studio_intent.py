"""Refinement grammar: understood sentences become validated commands."""
from __future__ import annotations

import pytest

from app.core.animus.scene.commands import apply_commands
from app.core.animus.scene.compose import compose_from_intention, shade
from app.core.animus.scene.intent import parse_intent
from app.core.animus.scene.model import SceneGraph

pytestmark = pytest.mark.core


def _scene(text: str = "a white castle above a dark ocean", seed: int = 31):
    return compose_from_intention(text, seed=seed).scene


def _castle(scene):
    return next(e for e in scene.entities if e.kind == "castle")


def test_sky_color_intent():
    scene = _scene()
    parsed = parse_intent("make the sky deep violet", scene)
    assert not parsed.needs_clarification
    assert any("Sky" in r for r in parsed.resolutions)
    updated, diff, _ = apply_commands(scene, parsed.commands)
    assert updated.atmosphere.sky_top == shade("#8a5cf0", 0.35)
    assert any("Sky color" in line for line in diff["explanation"])


def test_style_and_keep_combine():
    scene = _scene()
    parsed = parse_intent("make the castle gothic and keep the ocean", scene)
    assert not parsed.needs_clarification
    updated, _, _ = apply_commands(scene, parsed.commands)
    assert updated.style == "gothic"
    water = next(e for e in updated.entities if e.kind == "water")
    assert water.locked is True


def test_add_second_moon():
    scene = _scene()
    parsed = parse_intent("add a second moon", scene)
    updated, diff, _ = apply_commands(scene, parsed.commands)
    assert sum(1 for e in updated.entities if e.kind == "moon") == 1
    assert any(item["kind"] == "moon" for item in diff["added"])


def test_remove_fog_when_no_fog_entity():
    scene = _scene()
    assert all(e.kind != "fog" for e in scene.entities)
    parsed = parse_intent("remove the fog", scene)
    updated, _, _ = apply_commands(scene, parsed.commands)
    assert updated.atmosphere.fog_density == 0.004


def test_lock_color_then_change_is_understood_but_rejected():
    scene = _scene()
    parsed = parse_intent("lock the castle color", scene)
    locked, _, _ = apply_commands(scene, parsed.commands)
    with pytest.raises(Exception):
        apply_commands(locked, parse_intent("make the castle red", locked).commands)


def test_brighten_scene():
    scene = _scene()
    before = scene.lighting.key_intensity
    parsed = parse_intent("make it brighter", scene)
    updated, _, _ = apply_commands(scene, parsed.commands)
    assert updated.lighting.key_intensity > before


def test_unknown_request_needs_clarification():
    parsed = parse_intent("make it better somehow", _scene())
    assert parsed.needs_clarification
    assert parsed.clarification
    assert not parsed.commands


def test_add_unknown_noun_becomes_abstract_form():
    parsed = parse_intent("add a turtle", _scene())
    updated, diff, _ = apply_commands(_scene(), parsed.commands)
    assert any(e.kind == "custom" and e.label == "Turtle" for e in updated.entities)
    assert any("abstract form" in w for w in parsed.warnings)


def test_parser_output_is_deterministic():
    scene = _scene()
    first = parse_intent("make the sky deep violet and add a second moon", scene)
    second = parse_intent("make the sky deep violet and add a second moon", scene)
    assert [c.op for c in first.commands] == [c.op for c in second.commands]
    a, _, _ = apply_commands(scene, first.commands)
    b, _, _ = apply_commands(scene, second.commands)
    assert a.content_hash() == b.content_hash()
    assert SceneGraph.from_dict(a.to_dict()).content_hash() == a.content_hash()
