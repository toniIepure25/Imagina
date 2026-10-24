from __future__ import annotations

import pytest

from app.core.animus.scene.model import SceneEntity, SceneGraph, SceneValidationError
from app.core.animus.studio.reconstruction import (
    OBJECT_TASK,
    SPATIAL_TASK,
    build_reconstruction_plan,
    score_spatial_placement,
    score_token_selection,
)
from app.core.animus.studio.tasks import build_task, score_response

pytestmark = pytest.mark.core


def _scene(*, entities: int = 5, same_position: bool = False) -> SceneGraph:
    items = [
        SceneEntity(
            id=f"ent_{index:08x}",
            kind=("castle", "tree", "moon", "water", "rock")[index % 5],
            label=f"Item {index}",
            role="subject" if index == 0 else "prop",
            position=[0.0 if same_position else float(index), 0.0, 0.0 if same_position else float(index)],
        )
        for index in range(entities)
    ]
    return SceneGraph(scene_id="scene_12345678", seed=7, title="Reconstruction test", entities=items)


def test_object_reconstruction_is_deterministic_and_hides_the_answer():
    scene = _scene()
    first = build_task(scene, OBJECT_TASK, seed=11, difficulty=0.5)
    second = build_task(scene, OBJECT_TASK, seed=11, difficulty=0.5)
    assert first.task_id == second.task_id
    assert first.response_kind == "token_selection"
    assert first.tokens == second.tokens
    payload = first.public_payload()
    assert "answer" not in payload
    assert "target_token_ids" not in payload
    assert all("is_target" not in token for token in payload["tokens"])
    assert len({token["token_id"] for token in payload["tokens"]}) == len(payload["tokens"])


def test_object_reconstruction_scores_f1_and_error_profile():
    scene = _scene()
    plan = build_reconstruction_plan(scene, OBJECT_TASK, seed=4, difficulty=0.5)
    assert plan is not None
    task = build_task(scene, OBJECT_TASK, seed=4, difficulty=0.5)
    target = set(plan.answer["target_token_ids"])
    decoys = [token["token_id"] for token in plan.tokens if token["token_id"] not in target]

    perfect = score_response(task, {"selected_token_ids": sorted(target)})
    assert perfect["score"] == 1.0
    assert perfect["correct"] is True
    assert perfect["error_profile"]["omissions"] == 0

    empty = score_response(task, {"selected_token_ids": []})
    assert empty["score"] == 0.0
    assert empty["error_profile"]["omissions"] == len(target)

    with_intrusion = score_response(task, {"selected_token_ids": sorted(target) + decoys[:1]})
    assert 0.0 < with_intrusion["score"] < 1.0
    assert with_intrusion["error_profile"]["intrusions"] == 1


def test_object_reconstruction_rejects_unknown_tokens():
    scene = _scene()
    task = build_task(scene, OBJECT_TASK, seed=4, difficulty=0.5)
    with pytest.raises(SceneValidationError):
        score_response(task, {"selected_token_ids": ["tok_not_offered"]})


def test_spatial_layout_scores_exact_and_offset_placements():
    scene = _scene(entities=5)
    plan = build_reconstruction_plan(scene, SPATIAL_TASK, seed=8, difficulty=0.4)
    assert plan is not None
    task = build_task(scene, SPATIAL_TASK, seed=8, difficulty=0.4)
    payload = task.public_payload()
    assert task.response_kind == "spatial_placement"
    assert "answer" not in payload
    assert "target_positions" not in payload
    assert "target_positions" not in (payload["layout"] or {})
    positions = plan.answer["target_positions"]
    exact = [{"token_id": token_id, "x": value[0], "z": value[1]}
             for token_id, value in positions.items()]

    perfect = score_response(task, {"placements": exact})
    assert perfect["score"] == 1.0
    assert perfect["error_profile"]["mean_spatial_error"] == 0.0

    shifted = [{"token_id": item["token_id"], "x": max(-1.0, item["x"] - 0.25), "z": item["z"]}
               for item in exact]
    worse = score_response(task, {"placements": shifted})
    assert worse["score"] < perfect["score"]

    missing = score_response(task, {"placements": exact[:-1]})
    assert missing["error_profile"]["omissions"] == 1
    assert missing["score"] < perfect["score"]


def test_spatial_layout_rejects_invalid_placement():
    scene = _scene()
    plan = build_reconstruction_plan(scene, SPATIAL_TASK, seed=8, difficulty=0.4)
    assert plan is not None
    task = build_task(scene, SPATIAL_TASK, seed=8, difficulty=0.4)
    with pytest.raises(SceneValidationError):
        score_spatial_placement(task.tokens, task.answer, task.layout,
                                {"placements": [{"token_id": task.tokens[0]["token_id"],
                                                 "x": 2.0, "z": 0.0}]})


def test_reconstruction_falls_back_when_scene_is_too_small_or_flat():
    small = build_task(_scene(entities=1), OBJECT_TASK, seed=3, difficulty=0.5)
    assert small.task_type == "attribute_recall"
    flat = build_task(_scene(entities=5, same_position=True), SPATIAL_TASK, seed=3, difficulty=0.5)
    assert flat.task_type == "spatial_view"
    assert len(flat.options) >= 2


def test_reconstruction_task_id_changes_with_scene_seed_and_difficulty():
    scene = _scene()
    base = build_task(scene, OBJECT_TASK, seed=9, difficulty=0.5).task_id
    assert build_task(scene, OBJECT_TASK, seed=9, difficulty=0.5).task_id == base
    assert build_task(scene, OBJECT_TASK, seed=10, difficulty=0.5).task_id != base
    assert build_task(scene, OBJECT_TASK, seed=9, difficulty=0.6).task_id != base
