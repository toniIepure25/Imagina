import csv
import json
import os

from app.cli.dataset_eval import main as eval_main

FORBIDDEN = (
    "samples", "raw_samples", "eeg_samples", "raw_signal",
    "timeseries", "time_series", "eeg_window", "sample_array",
)
EVAL_HEADERS = {
    "window_index", "theta_power", "alpha_power", "beta_power", "theta_beta_ratio",
    "alpha_stability", "signal_quality", "blink_score", "muscle_score", "drift_score",
    "clipping_score", "missing_data_ratio", "real_signal",
}


def test_eval_main_writes_distribution_report(tmp_path):
    out = str(tmp_path / "eval.json")
    rc = eval_main([
        "--dataset", "fixture", "--max-windows", "5",
        "--distribution-report", "--output", out,
    ])
    assert rc == 0
    assert os.path.exists(out)
    with open(out) as f:
        r = json.load(f)
    for k in ("tool", "signal_quality", "bandpower", "artifacts", "missing_data_ratio", "disclaimer"):
        assert k in r, f"Missing key: {k}"
    j = json.dumps(r)
    for bad in FORBIDDEN:
        assert bad not in j, f"Forbidden key found: {bad}"
    dist_path = str(tmp_path / "dataset_distribution_fixture.json")
    if not os.path.exists(dist_path):
        dist_path = os.path.join(os.path.dirname(out), "dataset_distribution_fixture.json")
    assert os.path.exists(dist_path), f"Distribution not at {dist_path}"
    with open(dist_path) as f:
        dist = json.load(f)
    assert dist["dataset"] == "fixture"


def test_eval_main_writes_features_csv(tmp_path):
    out = str(tmp_path / "eval.csv_test.json")
    rc = eval_main([
        "--dataset", "fixture", "--max-windows", "5",
        "--export-features-csv", "--output", out,
    ])
    assert rc == 0
    csv_path = os.path.join(os.path.dirname(out), "dataset_features_fixture.csv")
    assert os.path.exists(csv_path), f"CSV not at {csv_path}"
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0
    header_set = set(rows[0].keys())
    missing = EVAL_HEADERS - header_set
    assert not missing, f"Missing CSV columns: {missing}"
    with open(csv_path) as f:
        content = f.read()
    for bad in FORBIDDEN:
        assert bad not in content, f"Forbidden key in CSV: {bad}"


def test_eval_main_fallback_csv_uses_actual_dataset(tmp_path):
    out = str(tmp_path / "fallback.json")
    rc = eval_main([
        "--dataset", "yoto", "--fallback", "fixture",
        "--max-windows", "5", "--export-features-csv", "--output", out,
    ])
    assert rc == 0
    with open(out) as f:
        r = json.load(f)
    assert r["requested_dataset"] == "yoto"
    assert r["actual_dataset"] == "fixture"
    assert r["fallback_used"] is True
    csv_path = os.path.join(os.path.dirname(out), "dataset_features_fixture.csv")
    assert os.path.exists(csv_path)
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0
    with open(csv_path) as f:
        content = f.read()
    for bad in FORBIDDEN:
        assert bad not in content


def test_eval_main_compare_writes_comparison_report(tmp_path):
    out = str(tmp_path / "compare.json")
    rc = eval_main([
        "--dataset", "fixture", "--compare", "fixture",
        "--max-windows", "5", "--output", out,
    ])
    assert rc == 0
    comp_path = os.path.join(os.path.dirname(out), "dataset_eval_compare_fixture_vs_fixture.json")
    assert os.path.exists(comp_path), f"Compare report not at {comp_path}"
    with open(comp_path) as f:
        c = json.load(f)
    comp_keys = (
        "primary_dataset", "comparison_dataset",
        "signal_quality_diff", "alpha_mean_diff", "beta_mean_diff", "theta_mean_diff",
    )
    for k in comp_keys:
        assert k in c, f"Missing compare key: {k}"


def test_eval_main_report_no_raw_sample_keys(tmp_path):
    out = str(tmp_path / "privacy.json")
    eval_main(["--dataset", "fixture", "--max-windows", "3", "--output", out])
    with open(out) as f:
        content = f.read()
    for bad in FORBIDDEN:
        assert bad not in content, f"Forbidden: {bad}"


def test_eval_main_fallback_reports_fallback_reason(tmp_path):
    out = str(tmp_path / "reason.json")
    eval_main([
        "--dataset", "yoto", "--fallback", "fixture",
        "--max-windows", "3", "--output", out,
    ])
    with open(out) as f:
        r = json.load(f)
    assert r["fallback_used"] is True
    assert r["fallback_reason"] is not None
    assert "yoto" in r["fallback_reason"].lower()
    assert r["actual_dataset"] == "fixture"


def test_eval_main_fallback_distribution_uses_actual_dataset(tmp_path):
    out = str(tmp_path / "fallback_dist.json")
    eval_main([
        "--dataset", "yoto", "--fallback", "fixture",
        "--max-windows", "5", "--distribution-report", "--output", out,
    ])
    with open(out) as f:
        r = json.load(f)
    assert r["actual_dataset"] == "fixture"
    dist_yoto = os.path.join(os.path.dirname(out), "dataset_distribution_yoto.json")
    dist_fix = os.path.join(os.path.dirname(out), "dataset_distribution_fixture.json")
    assert os.path.exists(dist_yoto) or os.path.exists(dist_fix)


def test_eval_main_all_outputs_no_raw_samples(tmp_path):
    out = str(tmp_path / "all.json")
    eval_main([
        "--dataset", "fixture", "--max-windows", "5",
        "--distribution-report", "--export-features-csv", "--output", out,
    ])
    for filename in os.listdir(os.path.dirname(out)):
        fpath = os.path.join(os.path.dirname(out), filename)
        with open(fpath) as f:
            content = f.read()
        for bad in FORBIDDEN:
            assert bad not in content, f"{bad} in {filename}"


def test_eval_main_pid_iqi_computation(tmp_path):
    out = str(tmp_path / "pid_iqi.json")
    eval_main([
        "--dataset", "fixture", "--max-windows", "5",
        "--compute-pid-iqi", "--output", out,
    ])
    with open(out) as f:
        r = json.load(f)
    assert "pid_iqi" in r
    assert 0 <= r["pid_iqi"]["pid_mean"] <= 1
    assert 0 <= r["pid_iqi"]["iqi_mean"] <= 1

