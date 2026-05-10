import json
import os
from unittest.mock import MagicMock

from app.cli.dataset_manager import main as acquire_main


def test_acquire_real_dry_run_no_download(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("network blocked")))
    rc = acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1", "--subjects", "1", "--dry-run"])
    assert rc == 1


def test_acquire_real_writes_acquisition_report(monkeypatch, tmp_path):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("network blocked")))
    rc = acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1", "--subjects", "1"])
    assert rc in (0, 1, 3)
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir",
        "acquisition_report.json",
    )
    if os.path.exists(report_path):
        with open(report_path) as f:
            r = json.load(f)
        assert r["real_signal"] is False
        assert r["raw_persisted"] is False
        assert r["acquisition_method"] == "fixture_fallback"


def test_acquire_real_records_attempted_mirrors(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("network blocked")))
    acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1", "--subjects", "1"])
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir",
        "acquisition_report.json",
    )
    if os.path.exists(report_path):
        with open(report_path) as f:
            r = json.load(f)
        assert len(r["attempted_mirrors"]) >= 2
        assert len(r["errors"]) > 0


def test_acquire_real_unknown_dataset(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("blocked")))
    rc = acquire_main(["acquire-real", "--dataset", "nonexistent", "--max-gb", "1", "--dry-run"])
    assert rc == 1


def test_acquire_real_fallback_has_correct_metadata(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("blocked")))
    acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1"])
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir",
        "acquisition_report.json",
    )
    if os.path.exists(report_path):
        with open(report_path) as f:
            r = json.load(f)
        assert r["acquisition_method"] == "fixture_fallback"
        assert r["raw_persisted"] is False
        assert r["real_signal"] is False


def test_acquire_real_mocked_200_but_no_files(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"<html>No files here</html>"
    mock_urlopen = MagicMock(return_value=mock_resp)
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    rc = acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1", "--dry-run"])
    assert rc == 1


def test_acquire_real_report_has_no_raw_sample_keys(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", MagicMock(side_effect=Exception("blocked")))
    acquire_main(["acquire-real", "--dataset", "openmiir", "--max-gb", "1"])
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir",
        "acquisition_report.json",
    )
    if os.path.exists(report_path):
        with open(report_path) as f:
            content = f.read()
        for key in ("samples", "raw_samples", "eeg_samples", "raw_signal", "timeseries"):
            assert key not in content
