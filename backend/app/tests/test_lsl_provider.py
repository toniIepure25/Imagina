import sys
import types

import pytest

from app.signals import get_provider, list_providers
from app.signals.lsl_real_provider import RealLSLProvider


def test_real_lsl_provider_imports_no_pylsl(monkeypatch):
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    p = RealLSLProvider()
    assert p.provider_id == "lsl.real"
    assert p.provider_type == "lsl"


def test_real_lsl_provider_health_unavailable_no_pylsl(monkeypatch):
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    p = RealLSLProvider()
    health = p.health()
    assert health["status"] == "unavailable"
    assert health["available"] is False
    assert health["pylsl_installed"] is False
    assert health["stream_found"] is False
    assert health["session_start_allowed"] is False
    assert "error_message" in health or "disabled_reason" in health


def test_real_lsl_provider_metadata_required_fields(monkeypatch):
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    p = RealLSLProvider()
    meta = p.metadata()
    assert meta["clinical_use"] is False
    assert meta["raw_persistence_default"] is False
    assert meta["window_collection_implemented"] is True
    assert meta["real_signal_supported"] is True
    assert meta["requires_optional_dependency"] == "pylsl"
    assert meta["provider_id"] == "lsl.real"


def test_real_lsl_provider_discover_no_pylsl_returns_empty(monkeypatch):
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: None,
    )
    p = RealLSLProvider()
    assert p.discover_streams() == []


@pytest.mark.asyncio
async def test_real_lsl_provider_next_window_raises_without_start():
    p = RealLSLProvider()
    try:
        await p.next_window("s1", 0)
        assert False
    except (RuntimeError, NotImplementedError):
        pass


def test_registry_includes_lsl_real():
    p = get_provider("lsl.real")
    assert p is not None
    assert p.provider_id == "lsl.real"


def test_registry_list_includes_both_lsl_providers():
    ids = {p.provider_id for p in list_providers()}
    assert "lsl.stub" in ids
    assert "lsl.real" in ids


def test_real_lsl_provider_health_with_mocked_pylsl(monkeypatch):
    fake_pylsl = types.ModuleType("pylsl")
    fake_pylsl.resolve_streams = lambda timeout=1.0: []
    monkeypatch.setitem(sys.modules, "pylsl", fake_pylsl)
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: fake_pylsl if name == "pylsl" else None,
    )
    p = RealLSLProvider()
    health = p.health()
    assert health["pylsl_installed"] is True
    assert health["available"] is True
    assert health["status"] == "no_stream_found"
    assert health["stream_found"] is False


def test_real_lsl_provider_discover_with_mocked_pylsl(monkeypatch):
    fake_stream = types.SimpleNamespace()
    fake_stream.name = lambda: "Muse-ABCD"
    fake_stream.type = lambda: "EEG"
    fake_stream.source_id = lambda: "muse123"
    fake_stream.channel_count = lambda: 4
    fake_stream.nominal_srate = lambda: 256.0

    fake_pylsl = types.ModuleType("pylsl")
    fake_pylsl.resolve_streams = lambda timeout=1.0: [fake_stream]
    monkeypatch.setitem(sys.modules, "pylsl", fake_pylsl)
    monkeypatch.setattr(
        "importlib.util.find_spec",
        lambda name, path=None: fake_pylsl if name == "pylsl" else None,
    )
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {"enable_experimental_lsl": True})(),
    )
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is True
    assert health["stream_name"] == "Muse-ABCD"
    assert health["channel_count"] == 4
    streams = p.discover_streams()
    assert len(streams) == 1
    assert streams[0]["name"] == "Muse-ABCD"
    assert streams[0]["type"] == "EEG"
    assert streams[0]["channel_count"] == 4
    assert streams[0]["nominal_srate"] == 256.0


def test_lsl_real_metadata_session_start_not_allowed(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name, path=None: None)
    p = RealLSLProvider()
    meta = p.metadata()
    assert meta["window_collection_implemented"] is True
    assert meta["clinical_use"] is False
    health = p.health()
    assert health["session_start_allowed"] is False
    assert health["disabled_reason"] is not None


def test_lsl_real_health_session_start_not_allowed(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name, path=None: None)
    p = RealLSLProvider()
    health = p.health()
    assert health["session_start_allowed"] is False
    assert health["disabled_reason"] is not None


def test_simulated_provider_session_start_allowed():
    from app.signals.simulated_provider import SimulatedSignalProvider
    p = SimulatedSignalProvider()
    assert p.metadata()["session_start_allowed"] is True
    assert p.health()["session_start_allowed"] is True

    from app.signals.manual_provider import ManualSignalProvider
    mp = ManualSignalProvider()
    assert mp.metadata()["session_start_allowed"] is True

    from app.signals.replay_provider import ReplaySignalProvider
    rp = ReplaySignalProvider()
    assert rp.metadata()["session_start_allowed"] is True


def test_provider_api_returns_disabled_reason_for_lsl_real():
    from app.signals import list_providers
    lsl_real = next((p for p in list_providers() if p.provider_id == "lsl.real"), None)
    assert lsl_real is not None
    meta = lsl_real.metadata()
    assert meta["window_collection_implemented"] is True
    health = lsl_real.health()
    assert health["session_start_allowed"] is False
    assert health["disabled_reason"] is not None


def _mock_lsl_module(monkeypatch, stream_count=1):
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
            import math as _math
            self._t += 1.0 / 256.0
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
        lambda name, path=None: fake_pylsl if name == "pylsl" else None,
    )
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {"enable_experimental_lsl": True})(),
    )
    return fake_pylsl


def test_real_lsl_discover_with_mock(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    streams = p.discover_streams()
    assert len(streams) == 1
    assert streams[0]["name"] == "Muse-ABCD"


def test_real_lsl_health_stream_found_with_mock(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is True
    assert health["session_start_allowed"] is True
    assert health["stream_name"] == "Muse-ABCD"


def test_real_lsl_no_stream_health_not_start_allowed(monkeypatch):
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
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is False
    assert health["session_start_allowed"] is False


@pytest.mark.asyncio
async def test_real_lsl_start_with_mock(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_s1")
    health = p.health()
    assert health["stream_found"] is True
    await p.stop("test_s1")


@pytest.mark.asyncio
async def test_real_lsl_next_window_returns_fv(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_fv")
    fv = await p.next_window("test_fv", 0)
    assert fv.session_id == "test_fv"
    assert fv.real_signal is True
    await p.stop("test_fv")


@pytest.mark.asyncio
async def test_real_lsl_fv_has_metadata(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_meta")
    fv = await p.next_window("test_meta", 0, total_windows=60)
    assert fv.provider_id == "lsl.real"
    assert fv.provider_type == "lsl"
    assert fv.channel_count == 4
    assert fv.sampling_rate_hz == 256
    assert fv.preprocessing_version is not None
    assert fv.feature_version is not None
    await p.stop("test_meta")


@pytest.mark.asyncio
async def test_real_lsl_next_window_values_in_range(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_range")
    fv = await p.next_window("test_range", 0, total_windows=60)
    assert 0 <= fv.theta_power <= 1
    assert 0 <= fv.alpha_power <= 1
    assert 0 <= fv.beta_power <= 1
    assert 0 <= fv.signal_quality <= 1
    assert 0 <= fv.alpha_stability <= 1
    assert 0 <= fv.behavioral_stability <= 1
    assert fv.clipping_score is not None and 0 <= fv.clipping_score <= 1
    assert fv.missing_data_ratio is not None and 0 <= fv.missing_data_ratio <= 1
    await p.stop("test_range")


@pytest.mark.asyncio
async def test_real_lsl_stop_cleans_state(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_stop")
    await p.stop("test_stop")
    try:
        await p.next_window("test_stop", 0)
        assert False
    except RuntimeError:
        pass


def test_real_lsl_does_not_persist_raw_samples_by_default(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    assert p.metadata()["raw_persistence_default"] is False


def test_normal_session_start_does_not_enable_lsl_real_by_default(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name, path=None: None)
    p = RealLSLProvider()
    assert p.metadata()["window_collection_implemented"] is True
    assert p.health()["session_start_allowed"] is False


def test_lsl_health_flag_false_stream_found_not_allowed(monkeypatch):
    _mock_lsl_module(monkeypatch)
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {"enable_experimental_lsl": False})(),
    )
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is True
    assert health["session_start_allowed"] is False


def test_lsl_health_flag_true_stream_found_allowed(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is True
    assert health["session_start_allowed"] is True


def test_lsl_health_flag_true_no_stream_not_allowed(monkeypatch):
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
    p = RealLSLProvider()
    health = p.health()
    assert health["stream_found"] is False
    assert health["session_start_allowed"] is False


@pytest.mark.asyncio
async def test_lsl_pipeline_produces_events(monkeypatch):
    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_pipeline")
    fv = await p.next_window("test_pipeline", 0, total_windows=10)
    assert fv.real_signal is True

    from app.services.curriculum_manager import CurriculumManager
    from app.services.feedback_policy_engine import FeedbackPolicyEngine
    from app.services.pid_iqi_engine import PIDIQIEngine
    from app.services.state_estimator import StateEstimator

    baseline = {"focus": 6, "relaxation": 5, "vividness": 5, "fatigue": 3}
    estimator = StateEstimator()
    metrics = PIDIQIEngine()
    curriculum = CurriculumManager(starting_level=1)
    feedback = FeedbackPolicyEngine()

    state = estimator.estimate("test_pipeline", fv, None, baseline, 0)
    assert 0 <= state.attention_stability <= 1
    pid_est, iqi_est = metrics.compute("test_pipeline", state, fv, 0)
    assert 0 <= pid_est.pid <= 1
    assert 0 <= iqi_est.iqi <= 1
    curr = curriculum.update("test_pipeline", state, pid_est, iqi_est)
    assert curr.current_level >= 1
    fb = feedback.compute("test_pipeline", state, pid_est, iqi_est, curr, 0)
    assert fb.scene_clarity >= 0

    await p.stop("test_pipeline")


@pytest.mark.asyncio
async def test_lsl_persisted_feature_vector_no_raw_samples(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.database.DB_PATH", str(tmp_path / "test.db"))
    from app.storage.database import init_db as _init_db
    await _init_db()

    _mock_lsl_module(monkeypatch)
    p = RealLSLProvider()
    await p.start("test_nr")
    fv = await p.next_window("test_nr", 0, total_windows=10)
    await p.stop("test_nr")

    payload = fv.model_dump(mode="json")
    assert "samples" not in payload
    raw_keys = [k for k in payload if "sample" in k]
    assert not raw_keys


@pytest.mark.asyncio
async def test_lsl_report_and_export_no_raw_samples(monkeypatch, tmp_path):
    monkeypatch.setattr("app.storage.database.DB_PATH", str(tmp_path / "test.db"))
    from app.storage.database import init_db as _init_db
    await _init_db()

    from app.schemas.calibration import CalibrationCompleteInput
    from app.schemas.session import SessionCreate

    _mock_lsl_module(monkeypatch)
    monkeypatch.setattr(
        "app.signals.lsl_real_provider.settings",
        type("Settings", (), {
            "enable_experimental_lsl": True,
            "max_session_duration_seconds": 1200,
            "window_interval_seconds": 2.0,
        })(),
    )

    from app.services import calibration_service, export_service, report_service, session_service
    session = await session_service.create_session(
        SessionCreate(task_id="corridor_simple", signal_provider_id="lsl.real")
    )
    await calibration_service.complete_calibration(
        session.session_id, session.user_id,
        CalibrationCompleteInput(duration_seconds=30, mode="simulated", focus=5, relaxation=5, vividness=5, fatigue=3),
    )

    p = RealLSLProvider()
    await p.start("test_export")
    for i in range(3):
        fv = await p.next_window("test_export", i, total_windows=3)
        payload = fv.model_dump(mode="json")
        assert "samples" not in payload
    await p.stop("test_export")

    summary = await report_service.generate_summary(session.session_id)
    assert summary.session_id == session.session_id
    jl = await export_service.events_jsonl(session.session_id)
    assert "samples" not in jl or "window_index" in jl


def test_feature_engine_eeg_window_produces_valid_fv():
    from datetime import datetime, timezone

    from app.schemas.signals import EEGSampleWindow
    from app.services.feature_engine import FeatureEngine
    engine = FeatureEngine()
    t = datetime.now(timezone.utc)
    import math as _math
    import random as _random
    rng = _random.Random(42)
    samples = []
    for i in range(512):
        val = _math.sin(2 * _math.pi * 10 * i / 256) + rng.gauss(0, 0.05)
        samples.append([val, val * 0.8, val * 0.9, val * 1.1])
    window = EEGSampleWindow(
        session_id="t", timestamp=t, window_index=0,
        sampling_rate_hz=256, channels=["ch0", "ch1", "ch2", "ch3"],
        samples=samples, simulated=False,
        generator_version="test",
        provider_id="test", provider_type="lsl",
        channel_count=4,
    )
    fv = engine.process_eeg_window(window)
    assert fv.real_signal is True
    assert 0 <= fv.alpha_power <= 1
    assert 0 <= fv.beta_power <= 1
    assert 0 <= fv.signal_quality <= 1
    assert fv.missing_data_ratio is not None and fv.missing_data_ratio < 0.2


def test_feature_engine_empty_samples_returns_default_fv():
    from datetime import datetime, timezone

    from app.schemas.signals import EEGSampleWindow
    from app.services.feature_engine import FeatureEngine
    engine = FeatureEngine()
    t = datetime.now(timezone.utc)
    window = EEGSampleWindow(
        session_id="t", timestamp=t, window_index=0,
        samples=None, simulated=False,
        generator_version="test",
        provider_id="test", provider_type="lsl",
    )
    fv = engine.process_eeg_window(window)
    assert fv.signal_quality == 0.0
