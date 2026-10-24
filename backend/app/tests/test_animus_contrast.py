"""Core tests for contrast pair generation, scoring, and the adaptive staircase."""
from __future__ import annotations

import pytest

from app.core.animus.scene.model import AttributeValue, SceneEntity, SceneGraph
from app.core.animus.studio.contrast import (
    CONTRAST_PROTOCOL_VERSION,
    FORM_IDS,
    build_pair,
    next_trial,
    score_trial,
    summarize_contrast,
    validate_reflection,
)

pytestmark = pytest.mark.core


def _scene(entities: int = 6) -> SceneGraph:
    items = [
        SceneEntity(
            id=f"ent_{index:08x}",
            kind=("castle", "tree", "moon", "water", "rock", "lantern")[index % 6],
            label=f"Item {index}",
            role="subject" if index == 0 else "prop",
            position=[float(index) - 2.5, 0.0, float((index * 3) % 7) - 3.0],
            attributes={
                "color": AttributeValue(
                    value=["#8899aa", "#aa8866", "#66aa88", "#8866aa", "#aaaa66", "#6688aa"][
                        index % 6
                    ],
                    confidence=0.7,
                )
            },
        )
        for index in range(entities)
    ]
    return SceneGraph(scene_id="scene_12345678", seed=7, title="Contrast test", entities=items)


def _session(**overrides) -> dict:
    payload = {
        "contrast_id": "ct_test",
        "session_id": "session_test",
        "source_version_id": "ver_test",
        "scene_hash": "hash",
        "protocol_version": CONTRAST_PROTOCOL_VERSION,
        "form_id": "A",
        "seed": 11,
        "max_trials": 16,
        "difficulty": 0.45,
        "occasion": "baseline",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_next_trial_is_deterministic_and_hides_target_and_delta():
    scene = _scene()
    first = next_trial(scene, _session(), [])
    second = next_trial(scene, _session(), [])
    assert first is not None and second is not None
    assert first.trial_id == second.trial_id
    assert first.task_id == second.task_id
    assert first.trial_index == 0
    assert first.feature_type == "object_presence"
    payload = first.public_payload()
    assert "target_side" not in payload
    assert "correct_option_id" not in payload
    assert "feature_type" not in payload
    assert "delta" not in payload
    assert [option["id"] for option in payload["options"]] == ["a", "b"]
    assert all("scene" in option for option in payload["options"])


def test_pair_contains_original_and_minimally_changed_variant():
    scene = _scene()
    pair = next_trial(scene, _session(), [])
    assert pair is not None
    hashes = [option["scene"]["metadata"]["content_hash"] for option in pair.options]
    assert scene.content_hash() in hashes
    assert len(set(hashes)) == 2
    target = next(option for option in pair.options if option["id"] == pair.target_side)
    assert target["scene"]["metadata"]["content_hash"] == scene.content_hash()
    assert pair.correct_option_id == pair.target_side


def test_target_side_is_seeded_and_block_balanced():
    scene = _scene()
    for form_id in FORM_IDS:
        session = _session(form_id=form_id, max_trials=12)
        sides: list[str] = []
        trials: list[dict] = []
        while True:
            pair = next_trial(scene, session, trials)
            if pair is None:
                break
            sides.append(pair.target_side)
            trials.append({
                "feature_type": pair.feature_type,
                "feature_key": pair.feature_key,
                "delta": pair.delta,
                "choice": pair.target_side,
                "correct": True,
                "confidence": 0.9,
                "abstained": False,
            })
        assert len(sides) == 12
        assert set(sides) == {"a", "b"}
        for index in range(0, len(sides), 2):
            assert set(sides[index:index + 2]) == {"a", "b"}


def test_scoring_is_binary_and_abstention_is_not_correctness():
    scene = _scene()
    pair = build_pair(
        scene,
        feature_type="spatial_position",
        feature_key="pos:ent_00000001:x",
        delta=0.3,
        seed=3,
        form_id="A",
        trial_index=2,
    )
    correct = score_trial(pair, choice=pair.target_side, confidence=0.9)
    incorrect = score_trial(
        pair, choice="b" if pair.target_side == "a" else "a", confidence=0.9)
    abstained = score_trial(pair, choice="", confidence=0.5, abstained=True)
    assert correct["correct"] is True
    assert incorrect["correct"] is False
    assert abstained["answered"] is False
    assert abstained["correct"] is None
    assert abstained["brier"] is None
    with pytest.raises(ValueError):
        score_trial(pair, choice="c", confidence=0.8)


def test_staircase_lowers_delta_after_repeated_success():
    scene = _scene()
    session = _session(max_trials=24)
    trials: list[dict] = []
    pair = next_trial(scene, session, trials)
    assert pair is not None
    trials.append({
        "feature_type": pair.feature_type, "delta": pair.delta,
        "correct": True, "abstained": False,
    })
    earlier = None
    for _ in range(8):
        pair = next_trial(scene, session, trials)
        assert pair is not None
        if pair.feature_type == "spatial_position":
            if earlier is not None:
                assert pair.delta is not None
                assert pair.delta <= earlier + 1e-9
            earlier = pair.delta
        trials.append({
            "feature_type": pair.feature_type, "delta": pair.delta,
            "correct": True, "abstained": False,
        })
    assert earlier is not None


def test_summary_keeps_sensitivity_threshold_and_calibration_separate():
    scene = _scene()
    session = _session(max_trials=16)
    trials: list[dict] = []
    while True:
        pair = next_trial(scene, session, trials)
        if pair is None:
            break
        trials.append({
            "feature_type": pair.feature_type,
            "feature_key": pair.feature_key,
            "delta": pair.delta,
            "choice": pair.target_side,
            "correct": True,
            "confidence": 0.9,
            "abstained": False,
        })
    summary = summarize_contrast(session, trials, bootstrap=0)
    assert summary["n_trials"] == len(trials)
    assert summary["n_answered"] == len(trials)
    assert summary["coverage"] == 1.0
    assert summary["dprime"] is not None and summary["dprime"] > 1.0
    assert summary["calibration"]["brier"] is not None
    assert "spatial_position" in summary["thresholds"]
    assert "object_color" in summary["thresholds"]
    assert summary["thresholds"]["spatial_position"]["scoring_version"] == "sdt-v1"


def test_summary_withholds_thresholds_when_evidence_is_sparse():
    summary = summarize_contrast(_session(), [], bootstrap=0)
    assert summary["n_trials"] == 0
    assert summary["coverage"] is None
    assert summary["dprime"] is None
    assert summary["thresholds"] == {}
    assert summary["calibration"]["brier"] is None


def test_reflection_validation_accepts_only_known_strategies():
    assert validate_reflection(["visual", "Visual", " spatial "]) == ["visual", "spatial"]
    with pytest.raises(ValueError):
        validate_reflection(["telepathy"])
