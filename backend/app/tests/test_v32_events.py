"""V3.2 event analysis tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_event_inventory_json_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_events_inventory.json"))


def test_event_analysis_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_events_analysis.md"))


def test_report_has_dataset():
    with open(os.path.join(EXPORTS, "openmiir_events_inventory.json")) as f:
        r = json.load(f)
    assert r["dataset"] == "openmiir"


def test_report_has_subjects():
    with open(os.path.join(EXPORTS, "openmiir_events_inventory.json")) as f:
        r = json.load(f)
    assert r["subjects_scanned"] >= 1


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_events_inventory.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_csv_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_events_condition_bandpower.csv"))
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_events_subject_condition_summary.csv"))


def test_manifest_missing_handled():
    r = subprocess.run(
        [CLI, "-m", "app.cli.openmiir_events_analysis", "--dataset", "nonexistent"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
