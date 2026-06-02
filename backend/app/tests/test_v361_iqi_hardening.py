"""V3.6.1 IQI v2 hardening tests."""

import json
import os
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_iqi_json_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_iqi_v2.json"))


def test_iqi_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_iqi_v2.md"))


def test_seven_components():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    sub = r["subject_results"][0]
    assert len(sub["components"]) == 7


def test_representation_consistency_exists():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    sub = r["subject_results"][0]
    names = [c["name"] for c in sub["components"]]
    assert "RepresentationConsistencyComponent" in names


def test_every_component_has_required_keys():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    for c in r["subject_results"][0]["components"]:
        for k in ("name", "score", "weight", "confidence", "explanation"):
            assert k in c, f"Missing {k} in {c['name']}"


def test_scores_in_range():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    for sub in r["subject_results"]:
        assert 0 <= sub["iqi"] <= 1


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_product_demo_has_iqi():
    with open(os.path.join(EXPORTS, "product_demo_report.json")) as f:
        r = json.load(f)
    assert "iqi_v2" in r.get("status", "").lower() or r.get("status") == "FIRST_REAL_EEG_EVALUATION_COMPLETE"


def test_figures_exist():
    base = os.path.join(EXPORTS, "figures")
    assert os.path.exists(os.path.join(base, "openmiir_iqi_v2_distribution.png"))
    assert os.path.exists(os.path.join(base, "openmiir_iqi_v2_components.png"))
