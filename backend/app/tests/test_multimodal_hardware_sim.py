"""Hardware-path integration tests without hardware: LSL replay outlet -> inlet, BrainFlow synthetic board, ADS1299
bench fixtures. Skipped when pylsl / brainflow are not installed."""
import importlib.util
import time
import uuid

import numpy as np
import pytest

from app.multimodal.acquisition.base import LifecycleState
from app.multimodal.acquisition.devices import (
    ADS1299Config,
    ADS1299StreamProvider,
    BrainFlowProvider,
    LSLInletProvider,
    encode_ads1299_frame,
)
from app.multimodal.acquisition.replay import FileReplayProvider
from app.multimodal.acquisition.synthetic import SyntheticECG
from app.multimodal.schemas import Modality
from app.multimodal.storage import StreamRecorder
from app.multimodal.sync import SyncEngine

needs_lsl = pytest.mark.skipif(importlib.util.find_spec("pylsl") is None, reason="pylsl not installed")
needs_bf = pytest.mark.skipif(importlib.util.find_spec("brainflow") is None, reason="brainflow not installed")


def _source(duration=8.0, seed=3):
    p = SyntheticECG(duration_s=duration, seed=seed)
    return p, p.connect()


def _collect(inlet, seconds, sync=None, recorder=None):
    import pylsl

    chunks, lat = [], []
    end = time.time() + seconds
    while time.time() < end:
        c = inlet.read(0)
        if c is not None:
            lat.append(pylsl.local_clock() - c.local_timestamps[-1])
            chunks.append(c)
            if sync is not None:
                sync.ingest(c)
            if recorder is not None:
                recorder.append(c)
        time.sleep(0.05)
    return chunks, lat


def _start(info, data, **kw):
    from app.multimodal.acquisition.lsl_outlet import LSLReplayOutlet

    name = f"imagina-test-{uuid.uuid4().hex[:8]}"
    out = LSLReplayOutlet(info, data, "ECG", name, source_id=name, **kw).start()
    inlet = LSLInletProvider(Modality.ECG, "ECG", "mV", name=name, timeout_s=5.0)
    return out, inlet


@needs_lsl
class TestLSL:
    def test_fidelity_timing_and_sync(self):
        p, info = _source()
        out, inlet = _start(info, p._data)
        try:
            linfo = inlet.connect()
            assert linfo.metadata["sync_method"] == "lsl_time_correction" and len(linfo.channels) == 1
            sync = SyncEngine()
            sync.add_stream(linfo)
            chunks, lat = _collect(inlet, 4.0, sync)
        finally:
            out.stop()
            inlet.disconnect()
        data = np.concatenate([c.data for c in chunks])
        k = data.shape[0]
        assert k > 0.8 * 4.0 * 500
        start = int(np.argmin(np.abs(p._data[:2000, 0] - data[0, 0])))
        np.testing.assert_allclose(data[:200, 0], p._data[start:start + 200, 0], atol=1e-5)
        assert abs(inlet.last_time_correction) < 0.01
        h = sync.health(chunks[-1].local_timestamps[-1])["streams"][linfo.stream_id]
        assert h["alignment_uncertainty_ms"] is not None and h["gap_samples"] == 0
        assert np.median(lat) < 0.5

    def test_dropout_detected_from_timestamps(self):
        p, info = _source()
        out, inlet = _start(info, p._data, pauses=[(1.5, 2.5)])
        try:
            linfo = inlet.connect()
            sync = SyncEngine()
            sync.add_stream(linfo)
            _collect(inlet, 4.0, sync)
        finally:
            out.stop()
            inlet.disconnect()
        assert abs(inlet.stats.samples_dropped - 500) <= 25
        assert sync.health(0)["streams"][linfo.stream_id]["gap_samples"] == inlet.stats.samples_dropped

    def test_outlet_restart_recovers(self):
        p, info = _source(duration=10.0)
        out, inlet = _start(info, p._data, restart_at_s=2.0, restart_gap_s=1.0)
        try:
            inlet.connect()
            chunks, _ = _collect(inlet, 6.0)
        finally:
            out.stop()
            inlet.disconnect()
        stamps = np.concatenate([c.device_timestamps for c in chunks])
        assert stamps.max() - stamps.min() > 4.0
        assert inlet.stats.samples_dropped >= 400

    def test_record_and_deterministic_replay(self, tmp_path):
        p, info = _source()
        out, inlet = _start(info, p._data)
        try:
            linfo = inlet.connect()
            rec = StreamRecorder(tmp_path / "lsl.h5", linfo)
            chunks, _ = _collect(inlet, 3.0, recorder=rec)
            rec.close()
        finally:
            out.stop()
            inlet.disconnect()
        received = np.concatenate([c.data for c in chunks])
        reps = []
        for _ in range(2):
            r = FileReplayProvider(tmp_path / "lsl.h5")
            r.connect()
            reps.append(r._data.copy())
        np.testing.assert_array_equal(reps[0], reps[1])
        np.testing.assert_allclose(reps[0], received)


@needs_bf
class TestBrainFlowSynthetic:
    def test_stream_rate_channels_and_monotonic_time(self):
        from brainflow.board_shim import BoardIds

        bf = BrainFlowProvider(BoardIds.SYNTHETIC_BOARD.value)
        info = bf.connect()
        try:
            chunks = []
            for _ in range(30):
                time.sleep(0.1)
                c = bf.read(0)
                if c is not None:
                    chunks.append(c)
        finally:
            bf.disconnect()
        n = sum(c.n_samples for c in chunks)
        span = chunks[-1].device_timestamps[-1] - chunks[0].device_timestamps[0]
        assert len(info.channels) == 16 and info.metadata["sync_method"] == "host_receive_time"
        assert abs(n / span - 250) < 25
        idx = np.concatenate([c.sample_indices for c in chunks])
        assert np.all(np.diff(idx) >= 1)
        assert int((np.diff(idx) - 1).sum()) == bf.stats.samples_dropped
        assert bf.stats.samples_dropped <= 0.02 * n
        loc = np.concatenate([c.local_timestamps for c in chunks])
        assert np.all(np.diff(loc) >= 0)
        sync = SyncEngine()
        sync.add_stream(info)
        for c in chunks:
            sync.ingest(c)
        assert sync.health(loc[-1])["max_alignment_uncertainty_ms"] is None

    def test_reconnect(self):
        from brainflow.board_shim import BoardIds

        bf = BrainFlowProvider(BoardIds.SYNTHETIC_BOARD.value)
        bf.connect()
        try:
            time.sleep(0.5)
            first = bf.read(0)
            assert bf.try_reconnect(1.0) and bf.stats.reconnects == 1
            time.sleep(0.5)
            second = bf.read(0)
        finally:
            bf.disconnect()
        assert first is not None and second is not None
        assert second.sample_indices[0] > first.sample_indices[-1]
        assert bf.state == LifecycleState.CLOSED


class TestADS1299BenchFixtures:
    def _frames(self, n, cfg, start_seq=65000, drop_every=97, corrupt_every=211, seed=0):
        rng = np.random.default_rng(seed)
        t = np.arange(n) / cfg.rate_hz
        true_uv = 50.0 * np.sin(2 * np.pi * 10.0 * t)
        counts = np.round(true_uv / cfg.lsb_uv).astype(int)
        blob, kept, dropped, corrupted = bytearray(), [], 0, 0
        for i in range(n):
            if i % drop_every == drop_every - 1:
                dropped += 1
                continue
            f = bytearray(encode_ads1299_frame((start_seq + i) & 0xFFFF, [int(counts[i])] * cfg.n_channels, cfg))
            if i % corrupt_every == corrupt_every - 1:
                f[5] ^= 0x5A
                corrupted += 1
            else:
                kept.append(i)
            blob += f
        pieces, pos = [], 0
        while pos < len(blob):
            k = int(rng.integers(1, 64))
            pieces.append(bytes(blob[pos:pos + k]))
            pos += k
        return pieces, true_uv, kept, dropped, corrupted

    def test_sine_fidelity_loss_and_wraparound(self, tmp_path):
        cfg = ADS1299Config(n_channels=8, rate_hz=250.0)
        pieces, true_uv, kept, dropped, corrupted = self._frames(2500, cfg)
        it = iter(pieces + [b""] * 5)
        prov = ADS1299StreamProvider(lambda: next(it, b""), cfg, clock=time.monotonic)
        info = prov.connect()
        rec = StreamRecorder(tmp_path / "ads.h5", info)
        chunks = []
        for _ in range(len(pieces) + 5):
            c = prov.read(0)
            if c is not None:
                chunks.append(c)
                rec.append(c)
        rec.close()
        data = np.concatenate([c.data for c in chunks])
        idx = np.concatenate([c.sample_indices for c in chunks])
        assert data.shape[0] == len(kept)
        np.testing.assert_allclose(data[:, 0], true_uv[kept], atol=cfg.lsb_uv)
        assert np.all(np.diff(idx) > 0) and idx[-1] > 65535
        assert prov.decoder.crc_errors == corrupted
        assert prov.decoder.lost_frames == dropped + corrupted
        spec = np.abs(np.fft.rfft(data[:1024, 0]))
        assert abs(np.fft.rfftfreq(1024, 1 / cfg.rate_hz)[np.argmax(spec)] - 10.0) < 0.5
        r = FileReplayProvider(tmp_path / "ads.h5")
        r.connect()
        np.testing.assert_array_equal(r._data, data)
