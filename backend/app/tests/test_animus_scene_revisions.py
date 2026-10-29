"""Versioning, branching, undo/redo, and lock-respecting regeneration."""
from __future__ import annotations

import pytest

from app.core.animus.scene.commands import apply_commands, parse_command
from app.core.animus.scene.compose import compose_from_intention
from app.core.animus.scene.model import SceneGraph
from app.core.animus.scene.regenerate import (
    RegenerationConfig,
    regenerate_variants,
    scene_lock_paths,
)
from app.core.animus.scene.revisions import MAIN_BRANCH, RevisionError, RevisionStore

pytestmark = pytest.mark.core


def _scene(seed: int = 21):
    return compose_from_intention("a white castle above a dark ocean at night", seed=seed).scene


def _castle(scene):
    return next(e for e in scene.entities if e.kind == "castle")


def test_commit_undo_redo_preserves_hashes():
    root = _scene()
    store = RevisionStore.with_root(root, intention="castle over ocean")
    v1 = store.head()
    assert v1.number == 1
    updated, diff, _ = apply_commands(root, [parse_command({
        "op": "set_scene_attribute", "path": "style", "value": "surreal"})])
    v2 = store.commit(MAIN_BRANCH, updated, commands=[{"op": "set_scene_attribute",
                                                       "path": "style", "value": "surreal"}],
                      diff=diff, source="refine", label="Make it surreal")
    assert v2.number == 2
    assert v2.parent_version_id == v1.version_id
    undone = store.undo()
    assert undone.content_hash == v1.content_hash
    assert store.head().content_hash == v1.content_hash
    redone = store.redo()
    assert redone.content_hash == v2.content_hash
    assert store.head().version_id == v2.version_id


def test_undo_root_is_rejected():
    store = RevisionStore.with_root(_scene())
    with pytest.raises(RevisionError):
        store.undo()


def test_scoped_stores_do_not_share_version_ids():
    first = RevisionStore.with_root(_scene(), scope="ast_first")
    second = RevisionStore.with_root(_scene(), scope="ast_second")
    assert first.head().content_hash == second.head().content_hash
    assert first.head().version_id != second.head().version_id


def test_branch_is_isolated_and_history_is_lineage():
    root = _scene()
    store = RevisionStore.with_root(root)
    root_version = store.head()
    branch = store.branch_from(root_version.version_id, "violet sky")
    violet, diff, _ = apply_commands(root, [parse_command({
        "op": "set_scene_attribute", "path": "atmosphere.sky.top", "value": "#6c3bb5"})])
    store.commit(branch.branch_id, violet, diff=diff, source="branch", label="Violet sky")
    assert store.head(MAIN_BRANCH).content_hash == root.content_hash()
    assert store.head(branch.branch_id).content_hash == violet.content_hash()
    assert store.head().content_hash == root.content_hash()
    assert [v.version_id for v in store.history(branch.branch_id)] == [
        root_version.version_id, store.head(branch.branch_id).version_id]


def test_versions_are_immutable_copies():
    scene = _scene()
    store = RevisionStore.with_root(scene)
    version = store.head()
    leaked = version.scene
    leaked.entities[0].label = "Mutated"
    assert store.head().scene.entities[0].label != "Mutated"


def test_snapshot_roundtrip():
    store = RevisionStore.with_root(_scene())
    updated, diff, _ = apply_commands(store.head().scene, [parse_command({
        "op": "set_scene_attribute", "path": "style", "value": "minimal"})])
    store.commit(MAIN_BRANCH, updated, diff=diff, label="Minimal")
    restored = RevisionStore.from_snapshot(store.snapshot())
    assert restored.head().content_hash == store.head().content_hash
    assert len(restored.versions()) == len(store.versions())
    assert restored.snapshot()["next_number"] == store.snapshot()["next_number"]


def test_scene_lock_paths_reports_entity_and_attribute_locks():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [
        parse_command({"op": "lock", "entity_id": castle.id, "path": "color", "locked": True}),
        parse_command({"op": "lock", "entity_id": scene.entities[1].id, "path": "", "locked": True}),
    ])
    locks = scene_lock_paths(scene)
    assert f"{castle.id}.color" in locks
    assert scene.entities[1].id in locks


def test_regeneration_respects_locked_color_and_is_deterministic():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "path": "color", "locked": True})])
    color = _castle(scene).attributes["color"].value

    config = RegenerationConfig(count=3, seed=7, strength=0.3)
    first = regenerate_variants(scene, config)
    second = regenerate_variants(scene, config)
    assert [v.scene.content_hash() for v in first] == [v.scene.content_hash() for v in second]
    for variant in first:
        assert _castle(variant.scene).attributes["color"].value == color
        assert f"{castle.id}.color" in variant.diff["locked_untouched"]


def test_regeneration_preserves_user_explicit_attributes_and_scene_paths():
    scene = _scene()
    castle = _castle(scene)
    scene, _, _ = apply_commands(scene, [
        parse_command({"op": "set_entity_attribute", "entity_id": castle.id,
                       "path": "size", "value": 2.0}),
        parse_command({"op": "set_scene_attribute", "path": "atmosphere.sky.top",
                       "value": "#6c3bb5"}),
    ])
    variants = regenerate_variants(scene, RegenerationConfig(count=2, seed=3, strength=0.5))
    for variant in variants:
        assert _castle(variant.scene).attributes["size"].value == 2.0
        assert variant.scene.atmosphere.sky_top == "#6c3bb5"


def test_regeneration_never_changes_locked_entity_transform():
    scene = _scene()
    castle = _castle(scene)
    original = list(castle.position)
    scene, _, _ = apply_commands(scene, [parse_command({
        "op": "lock", "entity_id": castle.id, "path": "", "locked": True})])
    for variant in regenerate_variants(scene, RegenerationConfig(count=2, seed=9, strength=0.6)):
        assert _castle(variant.scene).position == original


def test_regeneration_returns_valid_scene_graphs():
    scene = _scene()
    for variant in regenerate_variants(scene, RegenerationConfig(count=2, seed=1)):
        assert SceneGraph.from_dict(variant.scene.to_dict()).content_hash() == variant.scene.content_hash()
        assert variant.diff["before_hash"] == scene.content_hash()
