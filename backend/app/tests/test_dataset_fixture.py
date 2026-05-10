import json

import pytest

from app.datasets.catalog import get_dataset, list_datasets
from app.datasets.fixture import generate_synthetic_eeg
from app.datasets.loaders import load_windows
from app.services.feature_engine import FeatureEngine
from app.services.signal_quality import evaluate_signal_quality
from app.signals.dataset_replay_provider import DatasetReplayProvider


def test_catalog_lists_fixture():
    ds_list = list_datasets()
    ids = {d["dataset_id"] for d in ds_list}
    assert "fixture" in ids
    assert "yoto" in ids
    assert "openmiir" in ids


def test_catalog_get_fixture():
    ds = get_dataset("fixture")
    assert ds is not None
    assert ds["status"] == "available"


def test_catalog_yoto_not_hardcoded_unreachable():
    ds = get_dataset("yoto")
    assert ds is not None
    assert ds["status"] == "unknown"
    assert ds["url"] == "https://openneuro.org/datasets/ds005815"


def test_fixture_generates_windows():
    windows = generate_synthetic_eeg(duration_seconds=60.0)
    assert len(windows) == 30
    w = windows[0]
    assert w.provider_id == "dataset.fixture"
    assert w.raw_persisted is False
    assert w.samples is not None
    assert len(w.samples) == 512
    assert len(w.samples[0]) == 4


def test_feature_engine_processes_fixture_window():
    windows = generate_synthetic_eeg(duration_seconds=4.0)
    engine = FeatureEngine()
    fv = engine.process_eeg_window(windows[0])
    assert fv.real_signal is False
    assert fv.provider_id == "dataset.fixture"
    assert 0 <= fv.alpha_power <= 1
    assert 0 <= fv.signal_quality <= 1


def test_signal_quality_on_fixture():
    windows = generate_synthetic_eeg(duration_seconds=10.0)
    engine = FeatureEngine()
    fvs = [engine.process_eeg_window(w) for w in windows]
    result = evaluate_signal_quality(fvs)
    assert result["quality_score"] > 0.5
    assert result["warnings"] == []


def test_signal_quality_empty_produces_warning():
    result = evaluate_signal_quality([])
    assert result["warnings"] == ["insufficient_windows"]


@pytest.mark.asyncio
async def test_dataset_replay_provider():
    provider = DatasetReplayProvider()
    await provider.start("test", dataset_id="fixture", max_windows=5)
    fv = await provider.next_window("test", 0, total_windows=5)
    assert fv.provider_id is not None
    health = provider.health()
    assert health["dataset_available"] is True
    assert health["session_start_allowed"] is True
    await provider.stop("test")


@pytest.mark.asyncio
async def test_dataset_replay_provider_exhausts_windows():
    provider = DatasetReplayProvider()
    await provider.start("test", dataset_id="fixture", max_windows=2)
    await provider.next_window("test", 0, total_windows=2)
    await provider.next_window("test", 1, total_windows=2)
    try:
        await provider.next_window("test", 2, total_windows=2)
        assert False
    except RuntimeError:
        pass
    await provider.stop("test")


def test_dataset_eval_output_has_no_raw_samples(tmp_path):
    from argparse import Namespace

    from app.cli.dataset_eval import evaluate

    args = Namespace(dataset="fixture", max_windows=3, compute_pid_iqi=False, output=None, fallback=None)
    report = evaluate(args)
    report_str = json.dumps(report)
    assert "samples" not in report_str
    assert report["windows_valid"] == 3


def test_catalog_openmiir_correct_url():
    ds = get_dataset("openmiir")
    assert ds is not None
    assert "sstober/openmiir" in ds["url"]
    assert "sllvir" not in ds["url"]


def test_catalog_yoto_url_correct():
    ds = get_dataset("yoto")
    assert ds is not None
    assert "openneuro.org/datasets/ds005815" in ds["url"]


def test_catalog_openmiir_not_hardcoded_unreachable():
    ds = get_dataset("openmiir")
    assert ds is not None
    assert ds["status"] != "unreachable"


def test_dataset_eval_fallback_works(tmp_path):
    from argparse import Namespace

    from app.cli.dataset_eval import evaluate

    args = Namespace(dataset="yoto", max_windows=3, compute_pid_iqi=False, output=None, fallback="fixture")
    report = evaluate(args)
    assert report["requested_dataset"] == "yoto"
    assert report["actual_dataset"] == "fixture"
    assert report["fallback_used"] is True
    assert report["fallback_reason"] is not None
    assert report["dataset_status"] == "fixture_fallback"


def test_dataset_eval_report_has_no_raw_samples_with_fallback(tmp_path):
    from argparse import Namespace

    from app.cli.dataset_eval import evaluate

    args = Namespace(dataset="yoto", max_windows=3, compute_pid_iqi=False, output=None, fallback="fixture")
    report = evaluate(args)
    report_str = json.dumps(report)
    assert "samples" not in report_str


def test_loader_dispatches_fif_to_mne_mock(monkeypatch):
    import sys as _sys
    saved_mne = _sys.modules.get("mne")

    class FakeRaw:
        def __init__(self):
            self.info = {"sfreq": 256, "ch_names": ["ch0", "ch1"], "nchan": 2}
            self.ch_names = self.info["ch_names"]
            self.n_times = 512

        def get_data(self, picks=None):
            import numpy as np
            n_ch = min(self.info["nchan"], len(picks) if picks else 2)
            data = np.tile(np.sin(np.linspace(0, 4 * np.pi, self.n_times)), (n_ch, 1))
            if picks:
                data = data[:len(picks)]
            return data

    fake_mne = type("fake_mne", (), {})()
    fake_mne.io = type("io", (), {
        "read_raw_fif": staticmethod(lambda path, preload=False, verbose=False: FakeRaw()),
    })()
    _sys.modules["mne"] = fake_mne
    monkeypatch.setattr("app.datasets.manifest.read_manifest", lambda ds: {"files": ["test.fif"]})
    monkeypatch.setattr("os.path.exists", lambda p: True)

    windows = load_windows("yoto", max_windows=3)
    assert len(windows) > 0
    if saved_mne:
        _sys.modules["mne"] = saved_mne


def test_dataset_eval_fallback_fixture_no_op(tmp_path):
    from argparse import Namespace

    from app.cli.dataset_eval import evaluate

    args = Namespace(dataset="fixture", max_windows=3, compute_pid_iqi=False, output=None, fallback=None)
    report = evaluate(args)
    assert report["requested_dataset"] == "fixture"
    assert report["actual_dataset"] == "fixture"
    assert report["fallback_used"] is False


def test_catalog_has_download_fields():
    for ds_id in ("yoto", "openmiir", "fixture"):
        ds = get_dataset(ds_id)
        assert ds is not None
        assert "download_supported" in ds
        assert "requires_manual_download" in ds
        assert "estimated_size_gb" in ds
