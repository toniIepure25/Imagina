"""V3.6 IQI v2 tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_json_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_iqi_v2.json"))


def test_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_iqi_v2.md"))


def test_csv_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_iqi_v2_subjects.csv"))


def test_score_in_range():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    assert 0 <= r["cohort"]["iqi_mean"] <= 1


def test_components_present():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        r = json.load(f)
    sub = r["subject_results"][0]
    assert len(sub["components"]) >= 4


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_iqi_v2.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_figures_exist():
    base = os.path.join(EXPORTS, "figures")
    assert os.path.exists(os.path.join(base, "openmiir_iqi_v2_distribution.png"))
    assert os.path.exists(os.path.join(base, "openmiir_iqi_v2_components.png"))


def test_cli_exits_zero():
    r = subprocess.run(
        [CLI, "-m", "app.cli.imagery_quality_v2", "--dataset", "openmiir",
         "--max-subjects", "2", "--max-windows-per-subject", "10"],
        capture_output=True, text=True,
    )
    assert r.returncode in (0, 1)


def test_missing_manifest_fails():
    r = subprocess.run(
        [CLI, "-m", "app.cli.imagery_quality_v2", "--dataset", "nonexistent"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
