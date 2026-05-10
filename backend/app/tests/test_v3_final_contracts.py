"""V3.0-final API + eval + privacy contract tests."""

import json
import os
import subprocess
import sys
import tempfile

from fastapi.testclient import TestClient

from app.cli.product_demo import run_demo
from app.main import app

client = TestClient(app)
EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")


def assert_no_raw(obj):
    forbidden = {"raw_samples", "eeg_samples", "sample_array",
                 "timeseries", "time_series", "raw_signal", "eeg_window"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert k not in forbidden, f"Forbidden key: {k}"
            assert_no_raw(v)
    elif isinstance(obj, list):
        for item in obj:
            assert_no_raw(item)


class TestAPIContract:
    def test_catalog_200(self): client.get("/api/datasets/catalog").status_code == 200
    def test_fixture_manifest(self): assert client.get("/api/datasets/fixture/manifest").status_code == 200
    def test_openmiir_manifest(self): assert client.get("/api/datasets/openmiir/manifest").status_code == 200
    def test_fixture_readiness(self):
        r = client.get("/api/datasets/fixture/readiness").json()
        assert r["mode"] == "fixture_demo"
    def test_openmiir_readiness(self):
        r = client.get("/api/datasets/openmiir/readiness").json()
        assert r["mode"] == "real_dataset_ready"
    def test_final_demo_200(self): assert client.get("/api/datasets/final-demo-status").status_code == 200
    def test_real_eeg_imported(self):
        r = client.get("/api/datasets/final-demo-status").json()
        assert r["real_eeg_imported"] is True
    def test_demo_status(self):
        r = client.get("/api/datasets/final-demo-status").json()
        assert r["demo_status"] == "FIRST_REAL_EEG_EVALUATION_COMPLETE"
    def test_sci_val_false(self):
        r = client.get("/api/datasets/final-demo-status").json()
        assert r["real_scientific_validation_complete"] is False
    def test_no_raw_catalog(self): assert_no_raw(client.get("/api/datasets/catalog").json())
    def test_no_raw_manifest(self): assert_no_raw(client.get("/api/datasets/openmiir/manifest").json())
    def test_no_raw_final_demo(self): assert_no_raw(client.get("/api/datasets/final-demo-status").json())


class TestRealEvalContract:
    CLI = sys.executable

    def test_eval_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            r = subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            assert r.returncode == 0

    def test_eval_actual_dataset_openmiir(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                r = json.load(f)
            assert r["actual_dataset"] == "openmiir"

    def test_eval_fallback_used_false(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                r = json.load(f)
            assert r["fallback_used"] is False

    def test_eval_real_signal_true(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                r = json.load(f)
            assert r["real_signal"] is True

    def test_eval_windows_valid(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                r = json.load(f)
            assert r["windows_valid"] > 0

    def test_eval_has_signal_quality(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                r = json.load(f)
            assert "signal_quality" in r

    def test_eval_no_raw(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            with open(out) as f:
                assert_no_raw(json.load(f))


class TestPrivacyContract:
    def test_product_demo_no_raw(self):
        assert_no_raw(run_demo())

    def test_api_no_raw(self):
        for path in ("/api/datasets/catalog", "/api/datasets/openmiir/manifest",
                     "/api/datasets/final-demo-status", "/api/datasets/openmiir/readiness"):
            assert_no_raw(client.get(path).json())

    def test_reports_no_raw(self):
        for fn in ("product_demo_report.json", "release_artifacts.json",
                   "mock_real_eeg_e2e_report.json",
                   "dataset_eval_openmiir.json", "dataset_quality_openmiir.json"):
            rp = os.path.join(EXPORTS, fn)
            if os.path.exists(rp):
                with open(rp) as f:
                    assert_no_raw(json.load(f))


class TestProductDemoContract:
    def test_mode(self): assert run_demo()["mode"] == "real_dataset"
    def test_real_imported(self): assert run_demo()["real_eeg_imported"] is True
    def test_rc(self): assert run_demo()["release_candidate"] == "V3.0-final-candidate"
    def test_status(self): assert "FIRST_REAL_EEG" in run_demo()["status"]
    def test_sci_val(self): assert run_demo()["real_scientific_validation_complete"] is False
    def test_file_count(self): assert run_demo()["imported_real_files"] >= 1
    def test_sampling_rate(self): assert run_demo()["real_sampling_rate_hz"] == 512
    def test_channel_count(self): assert run_demo()["real_channel_count"] == 69
    def test_no_raw(self): assert_no_raw(run_demo())


class TestNoDataIsolation:
    def test_readiness_manual(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        monkeypatch.setattr("app.api.routes_datasets.read_manifest", lambda ds: None)
        assert client.get("/api/datasets/openmiir/readiness").json()["mode"] == "manual_import_required"

    def test_real_eeg_false(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        monkeypatch.setattr("app.api.routes_datasets.read_manifest", lambda ds: None)
        assert client.get("/api/datasets/final-demo-status").json()["real_eeg_imported"] is False

    def test_real_mode_blocked(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        from argparse import Namespace

        from app.cli.dataset_eval import evaluate
        args = Namespace(
            dataset="openmiir", max_windows=2, real_mode=True, fallback=None,
            compare=None, compute_pid_iqi=False, distribution_report=False,
            export_features_csv=False, output=None,
        )
        try:
            evaluate(args)
            assert False
        except RuntimeError:
            pass
