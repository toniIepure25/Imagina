"""Tests for SDT scoring, provenance, and longitudinal reliability."""
from __future__ import annotations

import pytest

from app.core.animus.scene.model import SceneEntity, SceneGraph
from app.core.animus.studio.epistemic import (
    build_probe_pool,
    init_belief,
    update_belief,
)
from app.core.animus.studio.observatory import (
    build_evidence,
    build_observatory,
    build_reliability,
)
from app.core.animus.studio.sdt import (
    brier_score,
    calibration_summary,
    dprime_2afc,
    fit_threshold,
    overconfidence,
    pearson,
    side_bias,
    type2_auc,
)
from app.core.animus.studio.sdt import test_retest as retest_error

pytestmark = pytest.mark.core


def _scene() -> SceneGraph:
    items = [
        SceneEntity(
            id=f"ent_{index:08x}",
            kind=("castle", "tree", "moon", "water", "rock", "lantern")[index % 6],
            label=f"Item {index}",
            role="subject" if index == 0 else "prop",
            position=[float(index) - 2.5, 0.0, float((index * 3) % 7) - 3.0],
        )
        for index in range(6)
    ]
    return SceneGraph(scene_id="scene_12345678", seed=7, title="Observatory test", entities=items)


def test_dprime_uses_log_linear_correction_and_is_none_without_answers():
    assert dprime_2afc(0, 0) is None
    assert dprime_2afc(10, 10) is not None
    assert dprime_2afc(5, 10) == pytest.approx(0.0, abs=0.2)
    assert dprime_2afc(9, 10) > dprime_2afc(6, 10)


def test_side_bias_is_a_signed_proportion():
    assert side_bias([]) is None
    assert side_bias(["a", "a", "b", "b"]) == pytest.approx(0.0)
    assert side_bias(["a", "a", "a", "b"]) == pytest.approx(0.25)


def test_calibration_and_type2_are_withheld_when_sparse():
    assert brier_score([]) is None
    assert overconfidence([]) is None
    assert type2_auc([], []) is None
    assert calibration_summary([])["brier"] is None
    summary = calibration_summary([(0.9, True), (0.8, False), (0.7, True)])
    assert summary["n"] == 3
    assert summary["brier"] is not None
    assert summary["type2_auc"] is None


def test_threshold_fit_returns_an_estimate_for_mixed_data():
    trials = []
    for index in range(24):
        delta = 0.05 + index * 0.035
        trials.append({
            "delta": delta,
            "correct": index % 2 == 0,
            "abstained": False,
            "confidence": 0.8 if index % 2 == 0 else 0.6,
        })
    fitted = fit_threshold(trials, seed=3, bootstrap=0)
    assert fitted["scoring_version"] == "sdt-v1"
    assert fitted["n"] == 24
    assert fitted["threshold"] is not None
    assert 0.0 <= fitted["threshold"] <= 1.0
    assert fitted["status"] == "estimated"


def test_threshold_fit_withholds_with_too_few_trials():
    fitted = fit_threshold([{"delta": 0.3, "correct": True, "abstained": False}], bootstrap=0)
    assert fitted["threshold"] is None
    assert fitted["status"] == "insufficient_evidence"


def test_test_retest_is_insufficient_below_three_aligned_features():
    result = retest_error({"spatial_position": 0.3}, {"spatial_position": 0.35})
    assert result["status"] == "insufficient"
    assert result["sem"] is None
    assert pearson([1.0, 2.0], [1.0, 2.0]) is None


def test_test_retest_reports_error_and_change():
    first = {"spatial_position": 0.3, "object_color": 0.4, "object_presence": 0.2}
    second = {"spatial_position": 0.35, "object_color": 0.45, "object_presence": 0.25}
    result = retest_error(first, second)
    assert result["status"] == "estimated"
    assert result["n_features"] == 3
    assert result["r"] == pytest.approx(1.0)
    assert result["sem"] is not None
    assert result["mdc95"] is not None
    assert result["mean_change"] == pytest.approx(0.05)


def test_evidence_provenance_keeps_prior_abstention_and_direct_probe_distinct():
    scene = _scene()
    probes = build_probe_pool(scene, seed=5, form_id="A", difficulty=0.4)
    belief = init_belief(probes)
    probe = probes[0]
    initially = build_evidence(probes, belief, [])
    assert initially[0]["provenance"] == "prior"
    assert initially[0]["n_sources"] == 0
    assert initially[0]["sources"] == []

    updated = update_belief(belief, probe, choice=probe.answer["choice"], confidence=0.9)
    records = [{
        "probe_id": probe.probe_id,
        "probe_type": probe.probe_type,
        "choice": probe.answer["choice"],
        "confidence": 0.9,
        "abstained": False,
        "information_gain": 0.4,
        "created_at": "2026-01-01T00:00:00Z",
    }]
    evidence = build_evidence(probes, updated, records)
    direct = next(item for item in evidence if item["variable_id"] == probe.variable_id)
    assert direct["provenance"] == "direct_probe"
    assert direct["n_sources"] == 1
    assert "correct" not in direct["sources"][0]
    assert direct["leave_one_out_delta"] >= 0.0

    abstained = update_belief(
        belief, probe, choice="", confidence=0.5, abstained=True)
    abstained_records = [{**records[0], "choice": "", "abstained": True}]
    abstained_evidence = build_evidence(probes, abstained, abstained_records)
    item = next(item for item in abstained_evidence if item["variable_id"] == probe.variable_id)
    assert item["provenance"] == "abstained"
    assert item["n_sources"] == 1


def test_reliability_merges_two_completed_occasions_and_ignores_active():
    first = {
        "contrast_id": "ct_1", "status": "completed", "occasion": "baseline",
        "form_id": "A", "completed_at": "2026-01-01T00:00:00Z",
        "result": {"dprime": 1.2, "thresholds": {
            "spatial_position": {"threshold": 0.3},
            "object_color": {"threshold": 0.4},
            "object_presence": {"threshold": 0.2},
        }},
    }
    second = {
        "contrast_id": "ct_2", "status": "completed", "occasion": "follow_up",
        "form_id": "B", "completed_at": "2026-01-02T00:00:00Z",
        "result": {"dprime": 1.4, "thresholds": {
            "spatial_position": {"threshold": 0.35},
            "object_color": {"threshold": 0.45},
            "object_presence": {"threshold": 0.25},
        }},
    }
    active = {"contrast_id": "ct_3", "status": "active", "result": None}
    reliability = build_reliability([active, first, second])
    assert reliability["n_occasions"] == 2
    assert reliability["status"] == "estimated"
    assert reliability["dprime_change"] == pytest.approx(0.2)


def test_observatory_is_descriptive_and_has_no_composite_score():
    payload = build_observatory(
        session_id="s1", source_version_id="v1", scene_hash="hash",
        reconstruction={"objects": [], "relations": [], "uncertainty": {},
                        "scores": {}, "protocol_version": "eri-v1",
                        "scoring_version": "eri-v1"},
        evidence=[], discrimination={"status": "unavailable"},
        reliability={"status": "insufficient"},
    )
    assert payload["boundaries"]
    assert "composite" in " ".join(payload["boundaries"]).lower()
    assert payload["discrimination"]["status"] == "unavailable"
