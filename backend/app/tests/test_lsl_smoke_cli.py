import json
import sys
import types

from app.cli.lsl_smoke_test import main


def _mock_for_cli(monkeypatch, stream_count=1, enable_experimental=True):
    fake_stream = types.SimpleNamespace()
    fake_stream.name = lambda: "Muse-ABCD"
    fake_stream.type = lambda: "EEG"
    fake_stream.source_id = lambda: "muse123"
    fake_stream.channel_count = lambda: 4
    fake_stream.nominal_srate = lambda: 256.0

    class FakeInlet:
        def __init__(self, stream_info):
            self._info = stream_info
            self._t = 0.0
            import random as _random
            self._rng = _random.Random(42)

        def info(self):
            return self._info

        def pull_sample(self, timeout=0):
            self._t += 1.0 / 256.0
            import math as _math
            alpha = _math.sin(2 * _math.pi * 10 * self._t)
            noise = self._rng.gauss(0, 0.05)
            val = alpha + noise
            return [val, val * 0.8, val * 0.9, val * 1.1], self._t

        def close_stream(self):
            pass

    fake_pylsl = types.ModuleType("pylsl")
    fake_pylsl.resolve_streams = lambda timeout=1.0: [fake_stream] * stream_count
    fake_pylsl.StreamInlet = FakeInlet
    monkeypatch.setitem(sys.modules, "pylsl", fake_pylsl)
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: fake_pylsl if name in ("pylsl",) else None,
    )
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {"enable_experimental_lsl": enable_experimental})(),
    )
    monkeypatch.setattr(
        "app.core.config.settings",
        type("Settings", (), {"enable_experimental_lsl": enable_experimental})(),
    )


def test_lsl_smoke_cli_requires_experimental_enablement(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings",
        type("Settings", (), {"enable_experimental_lsl": False})(),
    )
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    rc = main(["--windows", "1"])
    assert rc == 2


def test_lsl_smoke_cli_allow_experimental_flag(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings",
        type("Settings", (), {"enable_experimental_lsl": False})(),
    )
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    rc = main(["--windows", "1", "--allow-experimental"])
    assert rc == 3


def test_lsl_smoke_cli_mock_stream_success(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    _mock_for_cli(monkeypatch, enable_experimental=True)
    rc = main(["--windows", "2", "--allow-experimental", "--output", output_file])
    assert rc == 0
    with open(output_file) as f:
        report = json.load(f)
    assert report["windows_collected"] == 2
    assert len(report["feature_summaries"]) == 2
    assert report["feature_summaries"][0]["real_signal"] is True
    assert report["feature_summaries"][0]["provider_id"] == "lsl.real"


def test_lsl_smoke_cli_report_has_no_raw_samples(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    _mock_for_cli(monkeypatch, enable_experimental=True)
    main(["--windows", "1", "--allow-experimental", "--output", output_file])
    with open(output_file) as f:
        content = f.read()
    assert "samples" not in content
    assert '"sample"' not in content
    assert "raw_samples" not in content
    assert "eeg_samples" not in content


def test_lsl_smoke_cli_report_has_feature_summaries(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    _mock_for_cli(monkeypatch, enable_experimental=True)
    main(["--windows", "3", "--allow-experimental", "--output", output_file])
    with open(output_file) as f:
        report = json.load(f)
    assert report["windows_collected"] == 3
    for fs in report["feature_summaries"]:
        assert 0 <= fs["alpha_power"] <= 1
        assert 0 <= fs["theta_power"] <= 1
        assert isinstance(fs["raw_persisted"], bool)
        assert fs["raw_persisted"] is False


def test_lsl_smoke_cli_handles_no_stream(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    fake_pylsl = types.ModuleType("pylsl")
    fake_pylsl.resolve_streams = lambda timeout=1.0: []
    monkeypatch.setitem(sys.modules, "pylsl", fake_pylsl)
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: fake_pylsl if name == "pylsl" else None,
    )
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {"enable_experimental_lsl": True})(),
    )
    monkeypatch.setattr(
        "app.core.config.settings",
        type("Settings", (), {"enable_experimental_lsl": True})(),
    )
    rc = main(["--windows", "1", "--allow-experimental", "--output", output_file])
    assert rc == 3


def test_lsl_smoke_cli_handles_window_error(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    _mock_for_cli(monkeypatch, enable_experimental=True)
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.RealLSLProvider.next_window",
        lambda self, *a, **kw: (_ for _ in ()).throw(RuntimeError("mock error")),
    )
    rc = main(["--windows", "2", "--allow-experimental", "--output", output_file])
    assert rc == 1
    with open(output_file) as f:
        report = json.load(f)
    assert len(report["errors"]) > 0


def test_lsl_smoke_cli_refuses_overwrite_without_flag(monkeypatch, tmp_path):
    output_file = str(tmp_path / "smoke.json")
    _mock_for_cli(monkeypatch, enable_experimental=True)
    main(["--windows", "1", "--allow-experimental", "--output", output_file])
    rc = main(["--windows", "1", "--allow-experimental", "--output", output_file])
    assert rc == 1
