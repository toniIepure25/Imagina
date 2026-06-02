"""V3.1 scientific EEG analysis tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_cli_help():
    r = subprocess.run([CLI, "-m", "app.cli.scientific_eeg_analysis", "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "max-subjects" in r.stdout


def test_scientific_analysis_json_created():
    p = os.path.join(EXPORTS, "openmiir_scientific_analysis.json")
    assert os.path.exists(p)


def test_scientific_analysis_md_created():
    p = os.path.join(EXPORTS, "openmiir_scientific_analysis.md")
    assert os.path.exists(p)


def test_report_has_dataset():
    with open(os.path.join(EXPORTS, "openmiir_scientific_analysis.json")) as f:
        r = json.load(f)
    assert r["dataset"] == "openmiir"


def test_report_has_subjects():
    with open(os.path.join(EXPORTS, "openmiir_scientific_analysis.json")) as f:
        r = json.load(f)
    assert r["subjects_processed"] >= 1


def test_report_has_bandpower_keys():
    with open(os.path.join(EXPORTS, "openmiir_scientific_analysis.json")) as f:
        r = json.load(f)
    sub = r["subject_results"][0]
    for k in ("delta", "theta", "alpha", "beta", "signal_quality"):
        assert k in sub, f"Missing: {k}"


def test_report_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_scientific_analysis.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array", "raw_signal"):
        assert bad not in j


def test_csv_bandpower_created():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_scientific_subject_bandpower.csv"))


def test_csv_quality_created():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_scientific_subject_quality.csv"))


def test_manifest_missing_handled():
    r = subprocess.run(
        [CLI, "-m", "app.cli.scientific_eeg_analysis", "--dataset", "nonexistent"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
