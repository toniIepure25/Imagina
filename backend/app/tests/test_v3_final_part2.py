"""V3.0-final comprehensive tests — part 2 (clean long lines)."""

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


def assert_no_raw(content):
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array", "raw_signal"):
        assert bad not in content, f"Forbidden: {bad}"


class TestAPIEndpoints:
    def test_catalog_200(self):
        assert client.get("/api/datasets/catalog").status_code == 200

    def test_fixture_manifest_200(self):
        assert client.get("/api/datasets/fixture/manifest").status_code == 200

    def test_fixture_readiness_mode(self):
        r = client.get("/api/datasets/fixture/readiness")
        assert r.json()["mode"] == "fixture_demo"

    def test_openmiir_readiness_mode(self):
        r = client.get("/api/datasets/openmiir/readiness")
        assert r.json()["mode"] == "real_dataset_ready"

    def test_final_demo_200(self):
        assert client.get("/api/datasets/final-demo-status").status_code == 200

    def test_real_imported_true(self):
        r = client.get("/api/datasets/final-demo-status")
        assert r.json()["real_eeg_imported"] is True

    def test_sci_val_false(self):
        r = client.get("/api/datasets/final-demo-status")
        assert r.json()["real_scientific_validation_complete"] is False

    def test_no_raw_catalog(self):
        assert_no_raw(client.get("/api/datasets/catalog").text)

    def test_no_raw_manifest(self):
        assert_no_raw(client.get("/api/datasets/openmiir/manifest").text)

    def test_no_raw_final_demo(self):
        assert_no_raw(client.get("/api/datasets/final-demo-status").text)


class TestReportFiles:
    def test_eval_exists(self):
        p = os.path.join(EXPORTS, "dataset_eval_openmiir.json")
        assert os.path.exists(p)

    def test_quality_exists(self):
        p = os.path.join(EXPORTS, "dataset_quality_openmiir.json")
        assert os.path.exists(p)

    def test_product_demo_json_exists(self):
        assert os.path.exists(os.path.join(EXPORTS, "product_demo_report.json"))

    def test_product_demo_md_exists(self):
        assert os.path.exists(os.path.join(EXPORTS, "product_demo_summary.md"))

    def test_release_artifacts_json_exists(self):
        assert os.path.exists(os.path.join(EXPORTS, "release_artifacts.json"))

    def test_release_artifacts_md_exists(self):
        assert os.path.exists(os.path.join(EXPORTS, "release_artifacts.md"))

    def test_eval_no_raw(self):
        with open(os.path.join(EXPORTS, "dataset_eval_openmiir.json")) as f:
            assert_no_raw(f.read())

    def test_quality_no_raw(self):
        with open(os.path.join(EXPORTS, "dataset_quality_openmiir.json")) as f:
            assert_no_raw(f.read())


class TestProductDemoFields:
    def test_mode(self):
        assert run_demo()["mode"] == "real_dataset"

    def test_imported(self):
        assert run_demo()["real_eeg_imported"] is True

    def test_rc(self):
        assert "V3.0-final" in run_demo()["release_candidate"]

    def test_status(self):
        assert "FIRST_REAL_EEG" in run_demo()["status"]

    def test_sci_val(self):
        assert run_demo()["real_scientific_validation_complete"] is False

    def test_has_files(self):
        assert run_demo()["imported_real_files"] >= 1

    def test_has_sr(self):
        assert run_demo()["real_sampling_rate_hz"] is not None

    def test_has_ch(self):
        assert run_demo()["real_channel_count"] is not None

    def test_no_raw(self):
        assert_no_raw(json.dumps(run_demo()))


class TestCLIs:
    CLI = sys.executable

    def test_product_demo(self):
        r = subprocess.run([self.CLI, "-m", "app.cli.product_demo"],
                           capture_output=True, text=True)
        assert r.returncode == 0

    def test_release_artifacts(self):
        r = subprocess.run([self.CLI, "-m", "app.cli.release_artifacts"],
                           capture_output=True, text=True)
        assert r.returncode == 0

    def test_real_eval_tmp(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "e.json")
            r = subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "openmiir", "--real-mode",
                 "--max-windows", "2", "--output", out],
                capture_output=True, text=True,
            )
            assert r.returncode == 0

    def test_quality_works(self):
        r = subprocess.run(
            [self.CLI, "-m", "app.cli.dataset_quality",
             "--dataset", "openmiir", "--max-windows", "2"],
            capture_output=True, text=True,
        )
        assert r.returncode in (0, 1)

    def test_fixture_eval_tmp(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "f.json")
            r = subprocess.run(
                [self.CLI, "-m", "app.cli.dataset_eval",
                 "--dataset", "fixture", "--max-windows", "2", "--output", out],
                capture_output=True, text=True,
            )
            assert r.returncode == 0

    def test_mock_e2e(self):
        r = subprocess.run([self.CLI, "-m", "app.cli.mock_real_eeg_e2e"],
                           capture_output=True, text=True)
        assert r.returncode == 0

    def test_wizard_explain(self):
        r = subprocess.run(
            [self.CLI, "-m", "app.cli.real_data_wizard", "--explain"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_acquire_dry_run(self):
        r = subprocess.run(
            [self.CLI, "-m", "app.cli.acquire_one_real_eeg",
             "--dry-run", "--manual-ok"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_dataset_manager_list(self):
        r = subprocess.run(
            [self.CLI, "-m", "app.cli.dataset_manager", "list"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

    def test_scenario_runner(self):
        r = subprocess.run(
            [self.CLI, "-m", "app.evaluation.scenario_runner",
             "--scenario", "improving_user", "--windows", "2"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0


class TestMockE2E:
    def test_report_exists(self):
        assert os.path.exists(os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json"))

    def test_mock_flag(self):
        with open(os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json")) as f:
            assert json.load(f)["mock_real_eeg"] is True

    def test_sci_val_false(self):
        with open(os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json")) as f:
            assert json.load(f)["real_scientific_validation"] is False

    def test_no_raw(self):
        with open(os.path.join(EXPORTS, "mock_real_eeg_e2e_report.json")) as f:
            assert_no_raw(f.read())


class TestPrivacy:
    def test_product_demo(self):
        assert_no_raw(json.dumps(run_demo()))

    def test_api(self):
        assert_no_raw(client.get("/api/datasets/final-demo-status").text)

    def test_quality(self):
        with open(os.path.join(EXPORTS, "dataset_quality_openmiir.json")) as f:
            assert_no_raw(f.read())

    def test_eval(self):
        with open(os.path.join(EXPORTS, "dataset_eval_openmiir.json")) as f:
            assert_no_raw(f.read())

    def test_release(self):
        with open(os.path.join(EXPORTS, "release_artifacts.json")) as f:
            assert_no_raw(f.read())


class TestNoDataBranch:
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
