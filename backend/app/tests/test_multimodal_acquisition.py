import json

import numpy as np
import pytest

from app.multimodal.acquisition import fixtures
from app.multimodal.acquisition.base import FaultPlan, LifecycleState, StreamDisconnected
from app.multimodal.acquisition.devices import (
    ADS1299Config,
    ADS1299FrameDecoder,
    ADS1299StreamProvider,
    BrainFlowProvider,
    LSLInletProvider,
    encode_ads1299_frame,
)
from app.multimodal.acquisition.registry import create_synthetic, list_descriptors
from app.multimodal.acquisition.replay import FileReplayProvider, load_recording
from app.multimodal.acquisition.synthetic import SyntheticECG, SyntheticEEG, SyntheticFNIRS, SyntheticRespiration
from app.multimodal.schemas import ChannelSpec, Modality, Provenance, SourceKind, StreamInfo
from app.multimodal.storage import ConsentRecord, RetentionPolicy, SessionStore, pseudonymize
from app.multimodal.sync import SyncEngine


def _drain(p, t_end, step=0.25):
    chunks, t = [], 0.0
    while t < t_end:
        t += step
        c = p.read(t)
        if c is not None:
            chunks.append(c)
    return chunks


class TestRegistry:
    def test_all_seven_modalities_registered(self):
        mods = {d.modality for d in list_descriptors()}
        assert mods == set(Modality)

    def test_each_modality_has_synthetic_and_replay(self):
        for m in Modality:
            kinds = {d.source_kind for d in list_descriptors(m)}
            assert SourceKind.SYNTHETIC in kinds and SourceKind.REPLAY in kinds, m

    def test_offline_modalities_have_no_realtime_synthetic(self):
        with pytest.raises(ValueError):
            create_synthetic(Modality.FMRI)

    def test_real_sensor_entries_are_not_claimed_validated(self):
        for d in list_descriptors():
            if d.source_kind == SourceKind.REAL_SENSOR:
                assert d.support_level in {"INTERFACE_ONLY", "HARDWARE_REQUIRED", "NOT_IMPLEMENTED"}


class TestStreamInfoValidation:
    def _prov(self, kind=SourceKind.SYNTHETIC):
        return Provenance(source_kind=kind, provider_id="x", provider_version="1")

    def test_rejects_bad_unit(self):
        with pytest.raises(ValueError):
            StreamInfo(stream_id="s", modality=Modality.EDA, nominal_rate_hz=32,
                       channels=[ChannelSpec(name="a", unit="uV")], provenance=self._prov())

    def test_rejects_out_of_range_rate(self):
        with pytest.raises(ValueError):
            StreamInfo(stream_id="s", modality=Modality.EEG, nominal_rate_hz=10,
                       channels=[ChannelSpec(name="a", unit="uV")], provenance=self._prov())

    def test_rejects_duplicate_channels(self):
        with pytest.raises(ValueError):
            StreamInfo(stream_id="s", modality=Modality.EEG, nominal_rate_hz=256,
                       channels=[ChannelSpec(name="a", unit="uV")] * 2, provenance=self._prov())

    def test_offline_modality_cannot_be_realtime_unless_real(self):
        with pytest.raises(ValueError):
            StreamInfo(stream_id="s", modality=Modality.FMRI, nominal_rate_hz=0.5,
                       channels=[ChannelSpec(name="v", unit="a.u.")], provenance=self._prov())


class TestSyntheticProviders:
    @pytest.mark.parametrize("modality", [Modality.EEG, Modality.ECG, Modality.EDA, Modality.RESPIRATION,
                                          Modality.FNIRS])
    def test_stream_and_label(self, modality):
        p = create_synthetic(modality, duration_s=20.0, seed=1)
        info = p.connect()
        assert info.source_kind == SourceKind.SYNTHETIC
        assert "SYNTHETIC" in info.provenance.notes
        chunks = _drain(p, 10.0)
        n = sum(c.n_samples for c in chunks)
        assert abs(n - 10.0 * info.nominal_rate_hz) <= 2

    def test_deterministic(self):
        a = SyntheticEEG(duration_s=5, seed=3)
        b = SyntheticEEG(duration_s=5, seed=3)
        a.connect()
        b.connect()
        assert np.array_equal(a.read(4.0).data, b.read(4.0).data)

    def test_eeg_channel_count_bounds(self):
        p = SyntheticEEG(n_channels=16, duration_s=2)
        assert len(p.connect().channels) == 16
        with pytest.raises(ValueError):
            SyntheticEEG(n_channels=17, duration_s=2).connect()

    def test_dropout_is_counted_and_indexed(self):
        p = SyntheticECG(duration_s=10, faults=FaultPlan(dropouts=[(2.0, 3.0)]))
        p.connect()
        chunks = _drain(p, 10.0)
        idx = np.concatenate([c.sample_indices for c in chunks])
        assert p.stats.samples_dropped == 500
        assert np.max(np.diff(idx)) == 501

    def test_disconnect_and_reconnect(self):
        p = SyntheticRespiration(duration_s=20, faults=FaultPlan(disconnect_at_s=5.0, reconnect_after_s=3.0))
        p.connect()
        _drain(p, 5.0)
        assert p.state == LifecycleState.LOST
        with pytest.raises(StreamDisconnected):
            p.read(5.5)
        assert not p.try_reconnect(6.0)
        assert p.try_reconnect(8.5)
        c = p.read(10.0)
        assert c.sample_indices[0] >= int(8.5 * 50)
        assert p.stats.disconnects == 1 and p.stats.reconnects == 1


class TestSync:
    def test_drift_and_offset_estimation(self):
        p = SyntheticECG(duration_s=60, seed=2,
                         faults=FaultPlan(clock_offset_s=123.4, clock_drift_ppm=200.0, jitter_s=0.002))
        eng = SyncEngine()
        eng.add_stream(p.connect())
        for c in _drain(p, 60.0):
            eng.ingest(c)
        h = eng.health(now=60.0)["streams"][p.info.stream_id]
        assert abs(h["clock_drift_ppm"] - 200.0) < 10.0
        w = eng.window(40.0, 2.0)
        sw = next(iter(w.streams.values()))
        true_t = sw.times[0]
        idx = int(round(true_t * (1 + 200e-6) * 500))
        assert abs(true_t - idx / 500 / (1 + 200e-6)) < 0.003

    def test_two_streams_aligned_on_common_timeline(self):
        a = SyntheticECG(duration_s=30, seed=1, faults=FaultPlan(clock_offset_s=10.0, clock_drift_ppm=-150))
        b = SyntheticRespiration(duration_s=30, seed=1, faults=FaultPlan(clock_offset_s=-50.0, clock_drift_ppm=300))
        eng = SyncEngine()
        eng.add_stream(a.connect())
        eng.add_stream(b.connect())
        for t in np.arange(0.25, 30.0, 0.25):
            for p in (a, b):
                c = p.read(float(t))
                if c is not None:
                    eng.ingest(c)
        w = eng.window(20.0, 4.0)
        for sw in w.streams.values():
            assert sw.times[0] >= 16.0 and sw.times[-1] < 20.0
            assert sw.coverage > 0.98
        assert w.max_alignment_uncertainty_s is not None and w.max_alignment_uncertainty_s < 0.005

    def test_host_receive_time_uncertainty_is_unknown(self):
        p = SyntheticECG(duration_s=5)
        info = p.connect()
        info.metadata["sync_method"] = "host_receive_time"
        eng = SyncEngine()
        eng.add_stream(info)
        for c in _drain(p, 5.0):
            eng.ingest(c)
        h = eng.health(5.0)
        assert h["max_alignment_uncertainty_ms"] is None
        assert "constant_transport_latency_unobservable" in h["streams"][info.stream_id]["warnings"]

    def test_stale_and_disconnected_streams_unusable(self):
        p = SyntheticECG(duration_s=30, faults=FaultPlan(disconnect_at_s=10.0, reconnect_after_s=30))
        eng = SyncEngine()
        eng.add_stream(p.connect())
        t = 0.0
        while t < 15.0:
            t += 0.25
            if p.state == LifecycleState.LOST:
                eng.set_connected(p.info.stream_id, False)
                continue
            c = p.read(t)
            if c is not None:
                eng.ingest(c)
        sw = next(iter(eng.window(15.0, 2.0).streams.values()))
        assert sw.stale and not sw.connected and not sw.usable

    def test_late_samples_detected(self):
        p = SyntheticECG(duration_s=10, faults=FaultPlan(transport_latency_s=0.0))
        eng = SyncEngine()
        eng.add_stream(p.connect())
        eng.ingest(p.read(2.0))
        eng.window(4.0, 2.0)
        eng.ingest(p.read(4.0))
        assert eng.health(4.0)["streams"][p.info.stream_id]["late_samples"] > 0

    def test_deterministic_windows(self):
        def run():
            p = SyntheticEEG(duration_s=10, seed=9, faults=FaultPlan(jitter_s=0.003, clock_drift_ppm=50))
            eng = SyncEngine()
            eng.add_stream(p.connect())
            for c in _drain(p, 10.0):
                eng.ingest(c)
            return eng.window(8.0, 2.0)
        w1, w2 = run(), run()
        k = next(iter(w1.streams))
        assert np.array_equal(w1.streams[k].data, w2.streams[k].data)
        assert np.array_equal(w1.streams[k].times, w2.streams[k].times)


class TestDevices:
    def test_optional_device_adapters_report_unavailability(self):
        for p in (LSLInletProvider(Modality.EEG, "EEG", "uV"), BrainFlowProvider(board_id=-1)):
            cap = p.capabilities()
            if not cap.available:
                assert cap.reason and cap.support_level == "INTERFACE_ONLY"

    def test_ads1299_frame_roundtrip_and_loss(self):
        cfg = ADS1299Config(n_channels=8)
        counts = [100, -100, 2 ** 23 - 1, -(2 ** 23), 0, 1, -1, 42]
        stream = b"".join(encode_ads1299_frame(s, counts, cfg) for s in (0, 1, 3))
        stream = b"\x00\x13" + stream
        dec = ADS1299FrameDecoder(cfg)
        out = dec.feed(stream[:10]) + dec.feed(stream[10:])
        assert [s for s, _ in out] == [0, 1, 3]
        assert dec.lost_frames == 1 and dec.resyncs == 2
        np.testing.assert_allclose(out[0][1][:2], np.array([100, -100]) * cfg.lsb_uv)
        assert abs(cfg.lsb_uv - 0.02235) < 1e-4

    def test_ads1299_crc_rejects_corruption(self):
        cfg = ADS1299Config(n_channels=4)
        f = bytearray(encode_ads1299_frame(5, [1, 2, 3, 4], cfg))
        f[8] ^= 0xFF
        dec = ADS1299FrameDecoder(cfg)
        assert dec.feed(bytes(f)) == [] and dec.crc_errors == 1

    def test_ads1299_provider_streams(self):
        cfg = ADS1299Config(n_channels=8)
        frames = iter([b"".join(encode_ads1299_frame(s, [s] * 8, cfg) for s in range(10)), b""])
        p = ADS1299StreamProvider(lambda: next(frames), cfg, clock=lambda: 100.0)
        info = p.connect()
        assert info.source_kind == SourceKind.REAL_SENSOR
        c = p.read(0)
        assert c.n_samples == 10 and c.sample_indices.tolist() == list(range(10))
        assert p.capabilities().support_level == "HARDWARE_REQUIRED"


class TestFileFormats:
    def test_edf_roundtrip(self, tmp_path):
        p = SyntheticECG(duration_s=10, seed=4)
        p.connect()
        data = p._data
        fixtures.write_edf(tmp_path / "ecg.edf", data, 500, ["ECG_II"], ["mV"])
        rec = load_recording(tmp_path / "ecg.edf", Modality.ECG)
        assert rec.rate_hz == 500 and rec.channels[0].unit == "mV"
        assert np.max(np.abs(rec.data[:, 0] - data[:5000, 0])) < 1e-3
        assert rec.metadata["origin_note"] == "synthetic fixture"

    def test_edf_replay_provider_is_labeled_replay(self, tmp_path):
        p = SyntheticRespiration(duration_s=10)
        p.connect()
        fixtures.write_edf(tmp_path / "resp.edf", p._data, 50, ["RESP"], ["mV"])
        r = FileReplayProvider(tmp_path / "resp.edf", Modality.RESPIRATION)
        info = r.connect()
        assert info.source_kind == SourceKind.REPLAY and len(info.provenance.file_sha256) == 64
        assert sum(c.n_samples for c in _drain(r, 10.0)) == 500

    def test_snirf_roundtrip_preserves_geometry(self, tmp_path):
        s = SyntheticFNIRS(duration_s=30)
        info = s.connect()
        layout = [{"name": c.name, "pair": c.name.split(" ")[0], "wavelength_nm": c.wavelength_nm,
                   "source_position_m": c.source_position_m, "detector_position_m": c.detector_position_m}
                  for c in info.channels]
        fixtures.write_snirf(tmp_path / "x.snirf", s._data, 10.0, layout)
        rec = load_recording(tmp_path / "x.snirf")
        assert rec.modality == Modality.FNIRS
        assert {c.wavelength_nm for c in rec.channels} == {760.0, 850.0}
        d = [np.linalg.norm(np.subtract(c.detector_position_m, c.source_position_m)) for c in rec.channels]
        assert min(d) == pytest.approx(0.008, abs=1e-6) and max(d) == pytest.approx(0.03, abs=1e-6)

    def test_meg_fif_reader(self, tmp_path):
        path, meta = fixtures.write_meg_fif(tmp_path / "meg_raw.fif", n_trials_per_class=5)
        rec = load_recording(path)
        assert rec.modality == Modality.MEG and rec.channels[0].unit == "T"
        assert len(rec.events) == meta["n_trials"]
        assert rec.stream_info("replay.meg", realtime_capable=False).realtime_capable is False

    def test_tabular_requires_sidecar_fields(self, tmp_path):
        f = tmp_path / "eda.csv"
        f.write_text("EDA\n1.0\n1.1\n")
        (tmp_path / "eda.csv.json").write_text(json.dumps({"modality": "eda", "rate_hz": 4}))
        with pytest.raises(ValueError):
            load_recording(f)
        (tmp_path / "eda.csv.json").write_text(json.dumps(
            {"modality": "eda", "rate_hz": 4, "channels": [{"name": "EDA", "unit": "uS"}]}))
        assert load_recording(f).data.shape == (2, 1)


class TestStorage:
    def test_record_and_replay_hdf5(self, tmp_path):
        store = SessionStore(tmp_path)
        pid = pseudonymize("participant-007", b"0123456789abcdef")
        assert pid.startswith("P-") and "007" not in pid
        store.create_session("sess1", pid, ConsentRecord(protocol_id="A", consent_version="1"))
        p = SyntheticECG(duration_s=6, seed=5)
        info = p.connect()
        rec = store.recorder("sess1", info)
        for c in _drain(p, 6.0):
            rec.append(c)
        rec.close()
        path = next((tmp_path / "sess1" / "streams").iterdir())
        r = FileReplayProvider(path)
        rinfo = r.connect()
        assert rinfo.source_kind == SourceKind.REPLAY and rinfo.modality == Modality.ECG
        assert np.array_equal(r._data, p._data[: r._data.shape[0]])

    def test_review_bundle_excludes_raw_by_default(self, tmp_path):
        store = SessionStore(tmp_path / "store")
        store.create_session("s2", "P-x", ConsentRecord(protocol_id="A", consent_version="1"))
        info = SyntheticEEG(duration_s=2).connect()
        store.recorder("s2", info).close()
        out = store.export_review_bundle("s2", tmp_path / "bundle")
        assert out["raw_included"] is False and not (tmp_path / "bundle" / "s2" / "streams").exists()
        with pytest.raises(PermissionError):
            store.export_review_bundle("s2", tmp_path / "bundle", include_raw=True)

    def test_retention(self, tmp_path):
        from datetime import datetime, timedelta, timezone

        store = SessionStore(tmp_path)
        store.create_session("old", "P-1", None, RetentionPolicy(retain_days=1))
        store.create_session("raw", "P-2", None, RetentionPolicy(retain_days=30, delete_raw_after_days=1))
        store.recorder("raw", SyntheticEEG(duration_s=2).connect()).close()
        res = store.apply_retention(datetime.now(timezone.utc) + timedelta(days=2))
        assert res == {"deleted_sessions": ["old"], "raw_purged": ["raw"]}
        assert not any((tmp_path / "raw" / "streams").iterdir())

    def test_rejects_path_traversal(self, tmp_path):
        with pytest.raises(ValueError):
            SessionStore(tmp_path).session_dir("../etc")
