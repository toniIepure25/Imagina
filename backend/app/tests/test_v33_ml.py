"""V3.3 ML benchmark tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_benchmark_json_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_ml_baseline_benchmark.json"))


def test_benchmark_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_ml_baseline_benchmark.md"))


def test_csv_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_ml_baseline_features.csv"))


def test_dummy_baseline_included():
    with open(os.path.join(EXPORTS, "openmiir_ml_baseline_benchmark.json")) as f:
        r = json.load(f)
    for bm in r["benchmarks"].values():
        assert "DummyClassifier" in bm["models"], "Missing DummyClassifier baseline"


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_ml_baseline_benchmark.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_manifest_missing_handled():
    r = subprocess.run(
        [CLI, "-m", "app.cli.ml_baseline_benchmark", "--dataset", "nonexistent"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
