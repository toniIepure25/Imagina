"""Core tests for the epistemic reconstruction interview (ERI)."""
from __future__ import annotations

import pytest

from app.core.animus.scene.model import SceneEntity, SceneGraph, SceneValidationError
from app.core.animus.studio.epistemic import (
    ERI_RESPONSE_KIND,
    EpistemicProbe,
    build_probe_pool,
    build_reconstruction,
    expected_information_gain,
    information_gain,
    init_belief,
    score_probe,
    select_probe,
    summarize_interview,
    update_belief,
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
        )
        for index in range(entities)
    ]
    return SceneGraph(scene_id="scene_12345678", seed=7, title="ERI test", entities=items)


def test_probe_pool_is_deterministic_and_never_exposes_target_answers():
    scene = _scene()
    first = build_probe_pool(scene, seed=11, form_id="A", difficulty=0.45)
    second = build_probe_pool(scene, seed=11, form_id="A", difficulty=0.45)
    assert [probe.probe_id for probe in first] == [probe.probe_id for probe in second]
    assert [probe.task_id for probe in first] == [probe.task_id for probe in second]
    assert {probe.probe_type for probe in first} == {"object_presence", "spatial_relation"}
    payloads = [probe.public_payload() for probe in first]
    assert all("answer" not in payload for payload in payloads)
    assert all("metadata" not in payload for payload in payloads)
    assert len({payload["probe_id"] for payload in payloads}) == len(payloads)


def test_probe_pool_rejects_unknown_form():
    with pytest.raises(SceneValidationError):
        build_probe_pool(_scene(), seed=1, form_id="D")


def test_confidence_updates_the_beta_posterior_without_a_composite_score():
    scene = _scene()
    probes = build_probe_pool(scene, seed=3, form_id="B", difficulty=0.5)
    probe = next(item for item in probes if item.probe_type == "object_presence")
    belief = init_belief(probes)
    truth = probe.answer["choice"]
    updated = update_belief(belief, probe, choice=truth, confidence=0.9)
    assert updated.probability(probe.variable_id) > 0.5
    assert updated.probability(probe.variable_id) < 1.0
    assert probe.probe_id in updated.asked
    abstained = update_belief(belief, probe, choice="", confidence=0.5, abstained=True)
    assert abstained.probability(probe.variable_id) == pytest.approx(0.5)
    assert probe.probe_id in abstained.asked


def test_correct_negative_answers_move_the_posterior_toward_the_negative_state():
    absent = EpistemicProbe(
        probe_id="pr_absent", task_id="eri_absent", probe_type="object_presence",
        prompt="Was there a lantern?", options=({"id": "present", "label": "Present"},
                                                {"id": "absent", "label": "Absent"}),
        dimension="stability", difficulty=0.4, preview_seconds=4,
        variable_id="decoy:lantern:0", answer={"choice": "absent"},
    )
    belief = init_belief((absent,))
    updated = update_belief(belief, absent, choice="absent", confidence=0.9)
    assert updated.probability(absent.variable_id) < 0.5

    right = EpistemicProbe(
        probe_id="pr_right", task_id="eri_right", probe_type="spatial_relation",
        prompt="Left or right?", options=({"id": "left", "label": "Left"},
                                          {"id": "right", "label": "Right"}),
        dimension="spatial", difficulty=0.4, preview_seconds=4,
        variable_id="rel:a:b:x", answer={"choice": "right"},
    )
    relation_belief = init_belief((right,))
    relation_updated = update_belief(relation_belief, right, choice="right", confidence=0.9)
    assert relation_updated.probability(right.variable_id) < 0.5


def test_coverage_floor_then_information_gain_selection():
    scene = _scene()
    probes = build_probe_pool(scene, seed=5, form_id="C", difficulty=0.4)
    belief = init_belief(probes)
    first = select_probe(probes, belief)
    assert first is not None
    assert first.probe_type == "object_presence"
    belief = update_belief(belief, first, choice=first.answer["choice"], confidence=0.8)
    second = select_probe(probes, belief)
    assert second is not None
    assert second.probe_type == "spatial_relation"
    gain = expected_information_gain(1.0, 1.0)
    assert gain >= 0.0
    assert information_gain(0.5, 0.8) > 0.0


def test_probe_scoring_and_summary_keep_calibration_separate_from_accuracy():
    scene = _scene()
    probes = build_probe_pool(scene, seed=13, form_id="A", difficulty=0.45)
    answered = [
        (probe, probe.answer["choice"], 0.9)
        for probe in probes
        if probe.probe_type == "object_presence"
    ]
    records = []
    for probe, choice, confidence in answered:
        score = score_probe(probe, choice=choice, confidence=confidence)
        records.append({
            "probe_type": probe.probe_type,
            "correct": score["correct"],
            "brier": score["brier"],
            "confidence": confidence,
            "abstained": False,
            "information_gain": 0.01,
        })
    records.append({
        "probe_type": "spatial_relation",
        "correct": None,
        "brier": None,
        "confidence": 0.5,
        "abstained": True,
        "information_gain": 0.0,
    })
    summary = summarize_interview(records)
    assert summary["object_accuracy"] == 1.0
    assert summary["coverage"] == pytest.approx(len(answered) / (len(answered) + 1))
    assert summary["abstention_rate"] == pytest.approx(round(1 / (len(answered) + 1), 6))
    assert summary["mean_brier"] == pytest.approx(0.01)
    assert "composite" not in summary
    assert records[0]["correct"] is True
    assert score_probe(probes[0], choice="", confidence=0.5, abstained=True)["brier"] is None


def test_reconstruction_reports_uncertainty_and_eri_versions():
    scene = _scene()
    probes = build_probe_pool(scene, seed=17, form_id="A", difficulty=0.45)
    belief = init_belief(probes)
    probe = probes[0]
    updated = update_belief(belief, probe, choice=probe.answer["choice"], confidence=0.8)
    records = [{
        "probe_type": probe.probe_type,
        "correct": True,
        "brier": 0.04,
        "confidence": 0.8,
        "abstained": False,
        "information_gain": 0.02,
    }]
    reconstruction = build_reconstruction(updated, probes, records)
    assert reconstruction["objects"]
    assert reconstruction["scoring_version"] == "eri-v1"
    assert reconstruction["scores"]["n_probes"] == 1
    assert 0.0 <= reconstruction["uncertainty"]["object_entropy"] <= 1.0
    assert all(0.0 <= item["probability"] <= 1.0 for item in reconstruction["objects"])
    assert all(item["status"] in {"likely_present", "likely_absent", "uncertain"}
               for item in reconstruction["objects"])
    assert ERI_RESPONSE_KIND == "probability_choice"
