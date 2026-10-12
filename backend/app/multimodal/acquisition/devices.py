"""Real-device adapter interfaces.

- ``LSLInletProvider``: works when ``pylsl`` is installed and a matching stream exists. Uses LSL's own
  ``time_correction`` for clock alignment.
- ``BrainFlowProvider``: works when ``brainflow`` is installed; board IDs are passed through, nothing is assumed
  about specific hardware.
- ``ADS1299FrameDecoder``: transport-independent frame protocol for future DIY ADS1299 boards. Bench-test code
  only; no hardware has been validated and human connection requires independent electrical-safety review.
"""
from __future__ import annotations

import importlib.util
import struct
import time
from dataclasses import dataclass

import numpy as np

from app.multimodal.acquisition.base import LifecycleState, ModalityProvider, ProviderUnavailable
from app.multimodal.schemas import Capabilities, ChannelSpec, Modality, Provenance, SampleChunk, SourceKind, StreamInfo


def _has(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None


class LSLInletProvider(ModalityProvider):
    source_kind = SourceKind.REAL_SENSOR

    def __init__(self, modality: Modality, stream_type: str, unit: str, name: str | None = None,
                 timeout_s: float = 2.0) -> None:
        super().__init__()
        self.modality = modality
        self.stream_type = stream_type
        self.unit = unit
        self.name = name
        self.timeout_s = timeout_s
        self.provider_id = f"lsl.{modality.value}"
        self._inlet = None
        self._index = 0
        self._last_stamp: float | None = None
        self.last_time_correction: float | None = None

    def capabilities(self) -> Capabilities:
        ok = _has("pylsl")
        return Capabilities(
            provider_id=self.provider_id, modality=self.modality, source_kind=self.source_kind, available=ok,
            reason="" if ok else "pylsl not installed (pip install pylsl)", realtime=True,
            requires_package="pylsl", support_level="INTERFACE_ONLY" if not ok else "IMPLEMENTED_UNVALIDATED",
        )

    def connect(self, local_time: float = 0.0) -> StreamInfo:
        if not _has("pylsl"):
            raise ProviderUnavailable("pylsl not installed")
        import pylsl

        pred = f"type='{self.stream_type}'" + (f" and name='{self.name}'" if self.name else "")
        found = pylsl.resolve_bypred(pred, 1, self.timeout_s)
        if not found:
            raise ProviderUnavailable(f"no LSL stream matching {pred}")
        self._inlet = pylsl.StreamInlet(found[0], max_buflen=60, recover=True)
        info = self._inlet.info()
        names = []
        ch = info.desc().child("channels").child("channel")
        for _ in range(info.channel_count()):
            names.append(ch.child_value("label") or f"ch{len(names)}")
            ch = ch.next_sibling()
        self._info = StreamInfo(
            stream_id=f"lsl:{info.source_id() or info.name()}", modality=self.modality,
            nominal_rate_hz=info.nominal_srate(), channels=[ChannelSpec(name=n, unit=self.unit) for n in names],
            provenance=Provenance(source_kind=self.source_kind, provider_id=self.provider_id,
                                  provider_version=pylsl.library_version().__str__(), device_model=info.name()),
            metadata={"sync_method": "lsl_time_correction"},
        )
        self.state = LifecycleState.CONNECTED
        self._log(local_time, "connected")
        return self._info

    def read(self, until_local_time: float) -> SampleChunk | None:
        """Pull available samples. LSL has no sample counter, so gaps are inferred from timestamp jumps
        larger than 1.5 nominal sample periods and reflected in ``sample_indices``."""
        if self._inlet is None:
            raise RuntimeError("not connected")
        samples, stamps = self._inlet.pull_chunk(timeout=0.0)
        if not stamps:
            return None
        self.last_time_correction = self._inlet.time_correction()
        device = np.asarray(stamps, dtype=float)
        local = device + self.last_time_correction
        fs = self.info.nominal_rate_hz
        prev = self._last_stamp if self._last_stamp is not None else device[0] - 1.0 / fs
        steps = np.maximum(1, np.round(np.diff(np.concatenate([[prev], device])) * fs).astype(np.int64))
        idx = self._index - 1 + np.cumsum(steps)
        self.stats.samples_dropped += int((steps - 1).sum())
        self._index = int(idx[-1]) + 1
        self._last_stamp = float(device[-1])
        self.stats.samples_delivered += len(stamps)
        return SampleChunk(stream_id=self.info.stream_id, data=np.asarray(samples, dtype=float),
                           device_timestamps=device, local_timestamps=np.maximum.accumulate(local),
                           sample_indices=idx, dropped_before=max(int(steps[0]) - 1, 0))

    def disconnect(self, local_time: float = 0.0) -> None:
        if self._inlet is not None:
            self._inlet.close_stream()
            self._inlet = None
        super().disconnect(local_time)


class BrainFlowProvider(ModalityProvider):
    source_kind = SourceKind.REAL_SENSOR

    def __init__(self, board_id: int, serial_port: str = "", modality: Modality = Modality.EEG,
                 clock=time.monotonic) -> None:
        super().__init__()
        self.clock = clock
        self._last_pkg: int | None = None
        self.board_id = board_id
        self.serial_port = serial_port
        self.modality = modality
        self.provider_id = f"brainflow.{board_id}"
        self._board = None
        self._index = 0

    def capabilities(self) -> Capabilities:
        ok = _has("brainflow")
        return Capabilities(
            provider_id=self.provider_id, modality=self.modality, source_kind=self.source_kind, available=ok,
            reason="" if ok else "brainflow not installed (pip install brainflow)", realtime=True,
            requires_package="brainflow", support_level="INTERFACE_ONLY" if not ok else "IMPLEMENTED_UNVALIDATED",
        )

    def connect(self, local_time: float = 0.0) -> StreamInfo:
        if not _has("brainflow"):
            raise ProviderUnavailable("brainflow not installed")
        from brainflow.board_shim import BoardShim, BrainFlowInputParams

        params = BrainFlowInputParams()
        params.serial_port = self.serial_port
        self._board = BoardShim(self.board_id, params)
        self._board.prepare_session()
        self._board.start_stream()
        self._rows = BoardShim.get_eeg_channels(self.board_id)
        self._ts_row = BoardShim.get_timestamp_channel(self.board_id)
        self._pkg_row = BoardShim.get_package_num_channel(self.board_id)
        if self._info is None:
            self._info = StreamInfo(
                stream_id=self.provider_id, modality=self.modality,
                nominal_rate_hz=BoardShim.get_sampling_rate(self.board_id),
                channels=[ChannelSpec(name=f"ch{r}", unit="uV") for r in self._rows],
                provenance=Provenance(source_kind=self.source_kind, provider_id=self.provider_id,
                                      provider_version="brainflow", device_model=str(self.board_id)),
                metadata={"sync_method": "host_receive_time", "package_counter_modulo": 256},
            )
        self.state = LifecycleState.CONNECTED
        self._log(local_time, "connected")
        return self._info

    def read(self, until_local_time: float) -> SampleChunk | None:
        """Board timestamps are Unix wall-clock seconds; they are kept as device timestamps and mapped onto the
        local monotonic clock using the receive time of the newest sample. The 0-255 package counter gives
        true sample gaps."""
        assert self._board is not None
        buf = self._board.get_board_data()
        if buf.shape[1] == 0:
            return None
        now = self.clock()
        stamps = buf[self._ts_row]
        pkg = buf[self._pkg_row].astype(np.int64)
        prev = self._last_pkg if self._last_pkg is not None else pkg[0] - 1
        steps = np.mod(np.diff(np.concatenate([[prev], pkg])), 256)
        steps[steps == 0] = 256
        idx = self._index - 1 + np.cumsum(steps)
        self.stats.samples_dropped += int(steps.sum() - len(steps))
        self._index = int(idx[-1]) + 1
        self._last_pkg = int(pkg[-1])
        self.stats.samples_delivered += buf.shape[1]
        local = now - (stamps[-1] - stamps)
        return SampleChunk(stream_id=self.info.stream_id, data=buf[self._rows].T, device_timestamps=stamps,
                           local_timestamps=np.maximum.accumulate(local), sample_indices=idx,
                           dropped_before=int(steps[0] - 1))

    def try_reconnect(self, local_time: float) -> bool:
        try:
            if self._board is not None:
                self._board.release_session()
            self.connect(local_time)
            self.stats.reconnects += 1
            return True
        except Exception:  # noqa: BLE001
            return False

    def disconnect(self, local_time: float = 0.0) -> None:
        if self._board is not None:
            self._board.stop_stream()
            self._board.release_session()
            self._board = None
        super().disconnect(local_time)


FRAME_START = 0xA0
FRAME_END = 0xC0


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class ADS1299Config:
    n_channels: int = 8
    vref_v: float = 4.5
    gain: int = 24
    rate_hz: float = 250.0

    @property
    def lsb_uv(self) -> float:
        return (2.0 * self.vref_v / self.gain) / (2 ** 24) * 1e6

    def frame_size(self) -> int:
        return 1 + 2 + 3 + 3 * self.n_channels + 2 + 1


def encode_ads1299_frame(seq: int, counts: list[int], cfg: ADS1299Config, status: int = 0xC00000) -> bytes:
    body = struct.pack(">H", seq & 0xFFFF) + status.to_bytes(3, "big")
    for c in counts:
        body += (c & 0xFFFFFF).to_bytes(3, "big")
    return bytes([FRAME_START]) + body + struct.pack(">H", crc16_ccitt(body)) + bytes([FRAME_END])


class ADS1299FrameDecoder:
    """Incremental decoder. Feed arbitrary byte chunks from any transport (serial, BLE, TCP)."""

    def __init__(self, cfg: ADS1299Config) -> None:
        self.cfg = cfg
        self._buf = bytearray()
        self.last_seq: int | None = None
        self.frames_ok = 0
        self.crc_errors = 0
        self.resyncs = 0
        self.lost_frames = 0

    def feed(self, chunk: bytes) -> list[tuple[int, np.ndarray]]:
        self._buf.extend(chunk)
        out = []
        size = self.cfg.frame_size()
        while len(self._buf) >= size:
            if self._buf[0] != FRAME_START:
                self._buf.pop(0)
                self.resyncs += 1
                continue
            frame = bytes(self._buf[:size])
            if frame[-1] != FRAME_END:
                self._buf.pop(0)
                self.resyncs += 1
                continue
            body = frame[1:-3]
            if struct.unpack(">H", frame[-3:-1])[0] != crc16_ccitt(body):
                self.crc_errors += 1
                self._buf.pop(0)
                continue
            del self._buf[:size]
            seq = struct.unpack(">H", body[:2])[0]
            if self.last_seq is not None:
                self.lost_frames += (seq - self.last_seq - 1) & 0xFFFF
            self.last_seq = seq
            raw = body[5:]
            counts = np.array([int.from_bytes(raw[3 * i:3 * i + 3], "big", signed=True)
                               for i in range(self.cfg.n_channels)], dtype=float)
            self.frames_ok += 1
            out.append((seq, counts * self.cfg.lsb_uv))
        return out


class ADS1299StreamProvider(ModalityProvider):
    """Wraps any byte transport callable ``read_bytes() -> bytes``. Timestamps are host receive time."""

    source_kind = SourceKind.REAL_SENSOR
    modality = Modality.EEG

    def __init__(self, read_bytes, cfg: ADS1299Config | None = None, clock=time.monotonic) -> None:
        super().__init__()
        self.cfg = cfg or ADS1299Config()
        self.decoder = ADS1299FrameDecoder(self.cfg)
        self.read_bytes = read_bytes
        self.clock = clock
        self.provider_id = "ads1299.diy"
        self._seq_total = 0
        self._wraps = 0

    def capabilities(self) -> Capabilities:
        return Capabilities(
            provider_id=self.provider_id, modality=self.modality, source_kind=self.source_kind, available=True,
            realtime=True, max_channels=16, supported_rates_hz=[250.0, 500.0, 1000.0],
            support_level="HARDWARE_REQUIRED",
            reason="Bench-test protocol only; DIY hardware is not validated for human connection.",
        )

    def connect(self, local_time: float = 0.0) -> StreamInfo:
        if not 1 <= self.cfg.n_channels <= 16:
            raise ValueError("ADS1299 boards support 1-16 channels (daisy-chained)")
        self._info = StreamInfo(
            stream_id=self.provider_id, modality=self.modality, nominal_rate_hz=self.cfg.rate_hz,
            channels=[ChannelSpec(name=f"ch{i + 1}", unit="uV") for i in range(self.cfg.n_channels)],
            provenance=Provenance(source_kind=self.source_kind, provider_id=self.provider_id,
                                  provider_version="ads1299-frame-v1", device_model="DIY ADS1299 (unvalidated)"),
            metadata={"sync_method": "host_receive_time", "lsb_uv": self.cfg.lsb_uv, "gain": self.cfg.gain},
        )
        self.state = LifecycleState.CONNECTED
        return self._info

    def read(self, until_local_time: float) -> SampleChunk | None:
        frames = self.decoder.feed(self.read_bytes())
        if not frames:
            return None
        now = self.clock()
        idx = []
        for seq, _ in frames:
            if self._seq_total and seq < (self._seq_total & 0xFFFF):
                self._wraps += 1
            self._seq_total = self._wraps * 65536 + seq
            idx.append(self._seq_total)
        n = len(frames)
        local = now - (n - 1 - np.arange(n)) / self.cfg.rate_hz
        self.stats.samples_delivered += n
        self.stats.samples_dropped = self.decoder.lost_frames
        return SampleChunk(stream_id=self.info.stream_id, data=np.array([f[1] for f in frames]),
                           device_timestamps=np.array(idx, dtype=float) / self.cfg.rate_hz,
                           local_timestamps=local, sample_indices=np.array(idx))
