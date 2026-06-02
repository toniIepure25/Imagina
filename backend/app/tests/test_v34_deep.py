"""V3.4 deep EEG benchmark tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_benchmark_json_exists():
    p = os.path.join(EXPORTS, "openmiir_deep_eeg_benchmark.json")
    assert os.path.exists(p)


def test_benchmark_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_deep_eeg_benchmark.md"))


def test_report_has_accuracy():
    with open(os.path.join(EXPORTS, "openmiir_deep_eeg_benchmark.json")) as f:
        r = json.load(f)
    assert 0 <= r["test_accuracy"] <= 1


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_deep_eeg_benchmark.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_cli_exits_zero():
    r = subprocess.run(
        [CLI, "-m", "app.cli.deep_eeg_benchmark", "--dataset", "openmiir",
         "--max-subjects", "2", "--max-windows-per-subject", "10", "--epochs", "2"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0


def test_fixture_fallback_works():
    r = subprocess.run(
        [CLI, "-m", "app.cli.deep_eeg_benchmark", "--dataset", "nonexistent"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
