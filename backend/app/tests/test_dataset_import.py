import json
import os
import sys
import tempfile
from argparse import Namespace

from app.cli.dataset_eval import evaluate
from app.cli.dataset_manager import cmd_import_local as import_local
from app.datasets.loaders import (
    SUPPORTED_EXTENSIONS,
    detect_reader,
    load_windows,
    safe_read_raw,
    summarize_raw,
    validate_eeg_file,
)


class FakeRaw:
    def __init__(self, sfreq=256, nchan=4, ntimes=512):
        self.info = {"sfreq": sfreq, "nchan": nchan}
        self.ch_names = [f"ch{i}" for i in range(nchan)]
        self.n_times = ntimes

    def get_data(self, picks=None):
        import numpy as np
        n = self.info["nchan"]
        data = np.sin(np.linspace(0, 4 * np.pi, self.n_times)).reshape(1, -1)
        return np.tile(data, (n, 1))


def _mock_mne_fif(monkeypatch):
    fake_mne = type("fake_mne", (), {})()
    fake_mne.io = type("io", (), {
        "read_raw_fif": staticmethod(
            lambda path, preload=False, verbose=False: FakeRaw(sfreq=250, nchan=8, ntimes=1000)
        ),
    })()
    monkeypatch.setitem(sys.modules, "mne", fake_mne)
    return fake_mne


def _ns(**kw):
    defaults = dict(dataset="t", path="/t", format="auto", max_gb=3.0, copy=False, overwrite=False, notes=None)
    defaults.update(kw)
    return Namespace(**defaults)


# --- Loader tests ---

def test_supported_extensions():
    assert ".fif" in SUPPORTED_EXTENSIONS
    assert ".edf" in SUPPORTED_EXTENSIONS
    assert ".bdf" in SUPPORTED_EXTENSIONS


def test_detect_reader_fif():
    assert detect_reader("sub.fif") == "read_raw_fif"
    assert detect_reader("sub.FIF") == "read_raw_fif"


def test_detect_reader_edf():
    assert detect_reader("sub.edf") == "read_raw_edf"


def test_detect_reader_bdf():
    assert detect_reader("sub.bdf") == "read_raw_bdf"


def test_detect_reader_vhdr():
    assert detect_reader("sub.vhdr") == "read_raw_brainvision"


def test_detect_reader_set():
    assert detect_reader("sub.set") == "read_raw_eeglab"


def test_detect_reader_unsupported():
    assert detect_reader("sub.mat") is None


def test_summarize_raw_extracts_metadata():
    raw = FakeRaw(sfreq=256, nchan=4, ntimes=1024)
    s = summarize_raw(raw)
    assert s["sampling_rate_hz"] == 256.0
    assert s["channel_count"] == 4
    assert s["duration_seconds"] == 4.0


def test_summarize_raw_missing_channels():
    class Bare:
        info = {"sfreq": 128}
        n_times = 256

    s = summarize_raw(Bare())
    assert s["sampling_rate_hz"] == 128.0
    assert s["channel_count"] == 0


def test_validate_eeg_file_fif(monkeypatch):
    _mock_mne_fif(monkeypatch)
    r = validate_eeg_file("test.fif")
    assert r is not None
    assert r["channel_count"] == 8
    assert r["sampling_rate_hz"] == 250.0


def test_validate_eeg_file_unsupported():
    assert validate_eeg_file("test.mat") is None


def test_safe_read_raw_fif(monkeypatch):
    _mock_mne_fif(monkeypatch)
    raw = safe_read_raw("test.fif")
    assert raw.ch_names == ["ch0", "ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7"]


# --- Import-local tests ---

def test_import_local_refuses_missing_path():
    ns = Namespace(
        dataset="test", path="/nonexistent", format="auto",
        max_gb=3.0, copy=False, overwrite=False, notes=None,
    )
    rc = import_local(ns)
    assert rc == 1


def test_import_local_refuses_unsupported_single_file():
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as tf:
        tf.write(b"fake")
        tf.flush()
        ns = _ns(dataset="test", path=tf.name)
        rc = import_local(ns)
    os.unlink(tf.name)
    assert rc == 1


def test_import_local_refuses_size_over_budget(monkeypatch):
    mega = 500_000_000
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as tf:
        tf.seek(mega)
        tf.write(b"\x00")
        tf.flush()
        _mock_mne_fif(monkeypatch)
        ns = Namespace(dataset="test", path=tf.name, format="auto", max_gb=0.1, copy=False, overwrite=False, notes=None)
        rc = import_local(ns)
    os.unlink(tf.name)
    assert rc == 1


def test_import_local_accepts_fif_with_mock(monkeypatch):
    _mock_mne_fif(monkeypatch)
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as tf:
        tf.write(b"fake eeg")
        tf.flush()
        ns = _ns(dataset="test_fif", path=tf.name, overwrite=True, notes="test")
        rc = import_local(ns)
        assert rc == 0
    os.unlink(tf.name)


def test_import_local_writes_manifest(monkeypatch):
    _mock_mne_fif(monkeypatch)
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as tf:
        tf.write(b"fake eeg")
        tf.flush()
        ns = _ns(dataset="test_manifest", path=tf.name, overwrite=True)
        import_local(ns)
    os.unlink(tf.name)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "external", "test_manifest"))
    manifest_path = os.path.join(base, "manifest.json")
    assert os.path.exists(manifest_path)
    with open(manifest_path) as f:
        m = json.load(f)
    assert m["file_count"] == 1
    assert m["real_signal"] is True
    assert m["raw_persisted"] is False


def test_import_local_writes_import_report(monkeypatch):
    _mock_mne_fif(monkeypatch)
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as tf:
        tf.write(b"fake eeg")
        tf.flush()
        ns = _ns(dataset="test_report", path=tf.name, overwrite=True)
        import_local(ns)
    os.unlink(tf.name)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "external", "test_report"))
    assert os.path.exists(os.path.join(base, "import_report.json"))


def test_import_local_refuses_overwrite_without_flag(monkeypatch):
    _mock_mne_fif(monkeypatch)
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as tf:
        tf.write(b"fake eeg")
        tf.flush()
        ns = _ns(dataset="test_no_overwrite", path=tf.name, overwrite=False)
        import_local(ns)  # first succeeds
        rc = import_local(ns)  # second should fail
    os.unlink(tf.name)
    assert rc == 1


# --- Dataset eval + compare tests ---

def test_dataset_eval_fixture_fallback_false():
    ns = Namespace(dataset="fixture", max_windows=3, compute_pid_iqi=False, output=None, fallback=None, compare=None)
    r = evaluate(ns)
    assert r["fallback_used"] is False
    assert r["requested_dataset"] == "fixture"


def test_dataset_eval_fallback_to_fixture():
    ns = Namespace(dataset="yoto", max_windows=3, compute_pid_iqi=False, output=None, fallback="fixture", compare=None)
    r = evaluate(ns)
    assert r["requested_dataset"] == "yoto"
    assert r["actual_dataset"] == "fixture"
    assert r["fallback_used"] is True


def test_dataset_eval_report_no_samples():
    ns = Namespace(dataset="fixture", max_windows=3, compute_pid_iqi=False, output=None, fallback=None, compare=None)
    r = evaluate(ns)
    j = json.dumps(r)
    assert "samples" not in j
    assert "raw" not in j


def test_load_windows_fixture_works():
    wins = load_windows("fixture", max_windows=3)
    assert len(wins) == 3
    assert wins[0].provider_id == "dataset.fixture"


def test_load_windows_unknown_raises():
    try:
        load_windows("nonexistent_dataset", max_windows=3)
        assert False
    except ValueError:
        pass
