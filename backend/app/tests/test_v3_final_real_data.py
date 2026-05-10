"""V3.0-final-candidate comprehensive tests — real data state + mock isolation."""

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
EXTERNAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external")


def assert_no_raw(content):
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array", "raw_signal"):
        assert bad not in content, f"Forbidden: {bad}"


# ===== REAL DATA STATE TESTS =====

class TestRealDataManifest:
    def test_exists(self):
        assert os.path.exists(os.path.join(EXTERNAL, "openmiir", "manifest.json"))
    def test_real_signal_true(self):
        with open(os.path.join(EXTERNAL, "openmiir", "manifest.json")) as f:
            assert json.load(f)["real_signal"] is True
    def test_file_count(self):
        with open(os.path.join(EXTERNAL, "openmiir", "manifest.json")) as f:
            assert json.load(f).get("file_count", 0) >= 1
    def test_sampling_rate(self):
        with open(os.path.join(EXTERNAL, "openmiir", "manifest.json")) as f:
            assert json.load(f).get("sampling_rate_hz") == 512
    def test_channel_count(self):
        with open(os.path.join(EXTERNAL, "openmiir", "manifest.json")) as f:
            assert json.load(f).get("channel_count") == 69


class TestRealDataAPI:
    def test_catalog_200(self): assert client.get("/api/datasets/catalog").status_code == 200
    def test_manifest_200(self): assert client.get("/api/datasets/openmiir/manifest").status_code == 200
    def test_readiness_real_ready(self):
        assert client.get("/api/datasets/openmiir/readiness").json()["mode"] == "real_dataset_ready"
    def test_final_demo_200(self): assert client.get("/api/datasets/final-demo-status").status_code == 200
    def test_real_imported_true(self):
        assert client.get("/api/datasets/final-demo-status").json()["real_eeg_imported"] is True
    def test_status_is_complete(self):
        s = client.get("/api/datasets/final-demo-status").json()["demo_status"]
        assert "FIRST_REAL_EEG_EVALUATION_COMPLETE" in s
    def test_sci_val_false(self):
        assert client.get("/api/datasets/final-demo-status").json()["real_scientific_validation_complete"] is False
    def test_catalog_no_raw(self): assert_no_raw(client.get("/api/datasets/catalog").text)
    def test_manifest_no_raw(self): assert_no_raw(client.get("/api/datasets/openmiir/manifest").text)
    def test_final_demo_no_raw(self): assert_no_raw(client.get("/api/datasets/final-demo-status").text)
    def test_readiness_no_raw(self): assert_no_raw(client.get("/api/datasets/openmiir/readiness").text)


class TestProductDemoRealData:
    def test_mode_real(self): assert run_demo()["mode"] == "real_dataset"
    def test_imported_true(self): assert run_demo()["real_eeg_imported"] is True
    def test_status_complete(self): assert "FIRST_REAL_EEG" in run_demo().get("status", "")
    def test_has_files(self): assert run_demo().get("imported_real_files", 0) >= 1
    def test_has_sampling_rate(self): assert run_demo().get("real_sampling_rate_hz") is not None
    def test_sci_val_false(self): assert run_demo().get("real_scientific_validation_complete") is False
    def test_no_raw(self): assert_no_raw(json.dumps(run_demo()))


class TestCLIWorks:
    def test_product_demo_exit_0(self):
        r = subprocess.run([sys.executable, "-m", "app.cli.product_demo"], capture_output=True, text=True)
        assert r.returncode == 0
    def test_release_artifacts_exit_0(self):
        r = subprocess.run([sys.executable, "-m", "app.cli.release_artifacts"], capture_output=True, text=True)
        assert r.returncode == 0
    def test_dataset_eval_real_works_with_tmp_output(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            r = subprocess.run(
                [sys.executable, "-m", "app.cli.dataset_eval", "--dataset", "openmiir",
                 "--real-mode", "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            assert r.returncode == 0
    def test_dataset_quality_real_works(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.cli.dataset_quality", "--dataset", "openmiir", "--max-windows", "3"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
    def test_mock_e2e_exit_0(self):
        r = subprocess.run([sys.executable, "-m", "app.cli.mock_real_eeg_e2e"], capture_output=True, text=True)
        assert r.returncode == 0
    def test_scenario_runner_works(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.evaluation.scenario_runner", "--scenario", "improving_user", "--windows", "3"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0


class TestReportsExist:
    def test_eval_json(self): assert os.path.exists(os.path.join(EXPORTS, "dataset_eval_openmiir.json"))
    def test_quality_json(self): assert os.path.exists(os.path.join(EXPORTS, "dataset_quality_openmiir.json"))
    def test_product_demo_json(self): assert os.path.exists(os.path.join(EXPORTS, "product_demo_report.json"))
    def test_release_artifacts_json(self): assert os.path.exists(os.path.join(EXPORTS, "release_artifacts.json"))
    def test_mock_e2e_report(self): assert os.path.exists(os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json"))


# ===== MOCK NO-DATA BRANCH TESTS (isolated with monkeypatch) =====

class TestNoDataBranchIsolated:
    def test_readiness_manual_without_manifest(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        monkeypatch.setattr("app.api.routes_datasets.read_manifest", lambda ds: None)
        r = client.get("/api/datasets/openmiir/readiness")
        assert r.json()["mode"] == "manual_import_required"

    def test_real_eeg_false_without_manifest(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        monkeypatch.setattr("app.api.routes_datasets.read_manifest", lambda ds: None)
        r = client.get("/api/datasets/final-demo-status")
        assert r.json()["real_eeg_imported"] is False

    def test_status_ready_for_file_without_manifest(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        monkeypatch.setattr("app.api.routes_datasets.read_manifest", lambda ds: None)
        r = client.get("/api/datasets/final-demo-status")
        assert r.json()["real_eeg_imported"] is False

    def test_real_mode_fails_without_manifest(self, monkeypatch):
        monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: None)
        from argparse import Namespace

        from app.cli.dataset_eval import evaluate
        args = Namespace(dataset="openmiir", max_windows=3, real_mode=True, fallback=None, compare=None,
                         compute_pid_iqi=False, distribution_report=False, export_features_csv=False, output=None)
        try:
            evaluate(args)
            assert False
        except RuntimeError:
            pass


# ===== PRIVACY TESTS =====

class TestPrivacyAll:
    def test_product_demo_no_raw(self): assert_no_raw(json.dumps(run_demo()))
    def test_api_no_raw(self): assert_no_raw(client.get("/api/datasets/final-demo-status").text)
    def test_reports_dir_no_raw(self):
        for fn in ("product_demo_report.json", "release_artifacts.json", "mock_real_eeg_e2e_report.json"):
            rp = os.path.join(EXPORTS, fn)
            if os.path.exists(rp):
                with open(rp) as f:
                    assert_no_raw(f.read())
    def test_quality_json_no_raw(self):
        qp = os.path.join(EXPORTS, "dataset_quality_openmiir.json")
        if os.path.exists(qp):
            with open(qp) as f:
                assert_no_raw(f.read())
    def test_mock_e2e_no_false_real_claim(self):
        rp = os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json")
        if os.path.exists(rp):
            with open(rp) as f:
                r = json.load(f)
            assert r["mock_real_eeg"] is True
            assert r["real_scientific_validation"] is False


# ===== QUICK SMOKE TESTS =====

class TestSmoke:
    def test_fixture_eval_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "eval.json")
            r = subprocess.run(
                [sys.executable, "-m", "app.cli.dataset_eval", "--dataset", "fixture",
                 "--max-windows", "3", "--output", out],
                capture_output=True, text=True,
            )
            assert r.returncode == 0

    def test_fixture_quality_still_works(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.cli.dataset_quality", "--dataset", "fixture", "--max-windows", "3"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_wizard_explain_works(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.cli.real_data_wizard", "--explain"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_acquire_dry_run_works(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.cli.acquire_one_real_eeg", "--dry-run", "--manual-ok"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_preflight_fails_missing(self):
        r = subprocess.run(
            [sys.executable, "-m", "app.cli.real_data_preflight", "--path", "/nonexistent.fif", "--dataset", "test"],
            capture_output=True, text=True,
        )
        assert r.returncode == 1
