"""Tests for real_data_preflight CLI."""


from app.cli.real_data_preflight import main as preflight_main
from app.cli.real_data_preflight import run_preflight


def test_preflight_missing_path():
    rc = preflight_main(["--path", "/nonexistent.fif", "--dataset", "test"])
    assert rc == 1


def test_preflight_unsupported_extension(tmp_path):
    f = tmp_path / "test.mat"
    f.write_text("fake")
    rc = preflight_main(["--path", str(f), "--dataset", "test"])
    assert rc == 1


def test_preflight_oversized(monkeypatch, tmp_path):
    f = tmp_path / "big.fif"
    f.write_bytes(b"\x00" * 100)
    monkeypatch.setattr("os.path.getsize", lambda p: 5_000_000_000)
    rc = preflight_main(["--path", str(f), "--dataset", "test", "--max-gb", "1"])
    assert rc == 1


def test_preflight_valid_extension_exists(tmp_path):
    f = tmp_path / "test.fif"
    f.write_text("fake")
    r = run_preflight(str(f), "test", 3.0)
    assert r["exists"] is True
    assert r["extension_supported"] is True
    assert r["raw_persisted"] is False


def test_preflight_report_no_raw_keys(tmp_path):
    f = tmp_path / "test.fif"
    f.write_text("fake")
    r = run_preflight(str(f), "test", 3.0)
    import json
    j = json.dumps(r)
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j
