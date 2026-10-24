"""Multimodal synchronization.

Each stream's device clock is mapped onto the local monotonic timeline with a linear model
``t_local = a + b * t_device`` fit over recent (device, arrival) pairs. The slope captures drift; the intercept is
taken from the lower envelope of arrival delays because transport delay is non-negative.

What this can and cannot know:
- drift and jitter are observable from arrival timestamps;
- a *constant* transport/buffering latency is NOT observable from host receive times. It is only bounded when
  the stream uses LSL time correction, a shared hardware marker, or a shared synthetic clock. Health reports say so.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.multimodal.schemas import Marker, Modality, SampleChunk, StreamInfo

OBSERVABLE_LATENCY_METHODS = {"lsl_time_correction", "hardware_marker", "shared_clock_synthetic", "file_timebase"}

DEFAULT_STALE_S = {
    Modality.EEG: 0.5, Modality.ECG: 1.0, Modality.EDA: 2.0, Modality.RESPIRATION: 2.0, Modality.FNIRS: 2.0,
    Modality.MEG: 0.5, Modality.FMRI: 6.0,
}


@dataclass
class ClockModel:
    intercept: float = 0.0
    slope: float = 1.0
    jitter_sd_s: float = 0.0
    n_pairs: int = 0

    @property
    def drift_ppm(self) -> float:
        return (1.0 / self.slope - 1.0) * 1e6 if self.slope else 0.0

    def to_local(self, device_t: np.ndarray) -> np.ndarray:
        return self.intercept + self.slope * device_t


class _Store:
    """Amortized O(chunk) append with front trimming (capacity doubling, compaction on demand)."""

    def __init__(self, n_ch: int, cap: int = 4096) -> None:
        self._d = np.empty((cap, n_ch))
        self._a = np.empty(cap)
        self._i = np.empty(cap, dtype=np.int64)
        self.head = self.tail = 0

    def append(self, d: np.ndarray, a: np.ndarray, i: np.ndarray) -> None:
        k = d.shape[0]
        if self.tail + k > self._a.size:
            n = self.tail - self.head
            cap = self._a.size
            while n + k > cap // 2:
                cap *= 2
            nd, na, ni = np.empty((cap, self._d.shape[1])), np.empty(cap), np.empty(cap, dtype=np.int64)
            h, t = self.head, self.tail
            nd[:n], na[:n], ni[:n] = self._d[h:t], self._a[h:t], self._i[h:t]
            self._d, self._a, self._i, self.head, self.tail = nd, na, ni, 0, n
        self._d[self.tail:self.tail + k] = d
        self._a[self.tail:self.tail + k] = a
        self._i[self.tail:self.tail + k] = i
        self.tail += k

    def trim_before(self, t_min: float) -> None:
        self.head += int(np.searchsorted(self._a[self.head:self.tail], t_min))

    @property
    def data(self) -> np.ndarray:
        return self._d[self.head:self.tail]

    @property
    def aligned(self) -> np.ndarray:
        return self._a[self.head:self.tail]

    @property
    def indices(self) -> np.ndarray:
        return self._i[self.head:self.tail]


@dataclass
class _Buffer:
    info: StreamInfo
    method: str
    stale_s: float
    declared_latency_uncertainty_s: float
    store: _Store
    pairs_dev: list[np.ndarray] = field(default_factory=list)
    pairs_loc: list[np.ndarray] = field(default_factory=list)
    clock: ClockModel = field(default_factory=ClockModel)
    connected: bool = True
    last_arrival: float | None = None
    late_samples: int = 0
    gap_samples: int = 0
    total_samples: int = 0
    emitted_until: float = -np.inf
    disconnect_events: int = 0

    @property
    def data(self) -> np.ndarray:
        return self.store.data

    @property
    def aligned(self) -> np.ndarray:
        return self.store.aligned

    @property
    def indices(self) -> np.ndarray:
        return self.store.indices


@dataclass
class StreamWindow:
    stream_id: str
    modality: Modality
    data: np.ndarray
    times: np.ndarray
    coverage: float
    gap_samples: int
    data_age_s: float
    stale: bool
    connected: bool
    alignment_uncertainty_s: float | None
    rate_hz: float

    @property
    def usable(self) -> bool:
        return self.connected and not self.stale and self.coverage >= 0.8 and self.data.shape[0] > 1


@dataclass
class SyncedWindow:
    t_start: float
    t_end: float
    streams: dict[str, StreamWindow]
    markers: list[Marker]
    max_alignment_uncertainty_s: float | None

    def by_modality(self, modality: Modality) -> StreamWindow | None:
        for w in self.streams.values():
            if w.modality == modality:
                return w
        return None


class SyncEngine:
    def __init__(self, max_buffer_s: float = 120.0, fit_window_s: float = 60.0) -> None:
        self.max_buffer_s = max_buffer_s
        self.fit_window_s = fit_window_s
        self._streams: dict[str, _Buffer] = {}
        self._markers: list[Marker] = []

    def add_stream(self, info: StreamInfo, stale_s: float | None = None,
                   declared_latency_uncertainty_s: float = 0.0) -> None:
        n_ch = len(info.channels)
        self._streams[info.stream_id] = _Buffer(
            info=info, method=str(info.metadata.get("sync_method", "host_receive_time")),
            stale_s=stale_s if stale_s is not None else DEFAULT_STALE_S[info.modality],
            declared_latency_uncertainty_s=declared_latency_uncertainty_s,
            store=_Store(n_ch),
        )

    @property
    def stream_ids(self) -> list[str]:
        return list(self._streams)

    def add_marker(self, marker: Marker) -> None:
        self._markers.append(marker)

    def set_connected(self, stream_id: str, connected: bool) -> None:
        b = self._streams[stream_id]
        if b.connected and not connected:
            b.disconnect_events += 1
        b.connected = connected

    def ingest(self, chunk: SampleChunk) -> None:
        b = self._streams[chunk.stream_id]
        if chunk.n_samples == 0:
            return
        dev_c, loc_c = chunk.device_timestamps, chunk.local_timestamps
        sel = np.unique(np.concatenate([np.linspace(0, dev_c.size - 1, min(dev_c.size, 8)).astype(int),
                                        [int(np.argmin(loc_c - dev_c))]]))
        b.pairs_dev.append(dev_c[sel])
        b.pairs_loc.append(loc_c[sel])
        self._fit(b)
        aligned = b.clock.to_local(chunk.device_timestamps)
        if b.indices.size:
            gaps = np.diff(np.concatenate([[b.indices[-1]], chunk.sample_indices])) - 1
            b.gap_samples += int(np.clip(gaps, 0, None).sum())
        b.late_samples += int(np.sum(aligned < b.emitted_until))
        b.store.append(chunk.data, aligned, chunk.sample_indices)
        b.total_samples += chunk.n_samples
        b.last_arrival = float(chunk.local_timestamps[-1])
        b.store.trim_before(float(aligned[-1]) - self.max_buffer_s)

    def _fit(self, b: _Buffer) -> None:
        dev = np.concatenate(b.pairs_dev)
        loc = np.concatenate(b.pairs_loc)
        keep = dev >= dev[-1] - self.fit_window_s
        dev, loc = dev[keep], loc[keep]
        b.pairs_dev, b.pairs_loc = [dev], [loc]
        if dev.size < 2 or np.ptp(dev) < 1.0:
            delay = loc - dev
            b.clock = ClockModel(intercept=float(np.min(delay)), slope=1.0, jitter_sd_s=0.0, n_pairs=int(dev.size))
            return
        d0 = dev[0]
        slope, _ = np.polyfit(dev - d0, loc, 1)
        resid = loc - slope * (dev - d0)
        floor = float(np.quantile(resid, 0.02))
        intercept = floor - slope * d0
        jitter = float(np.std(resid - floor))
        b.clock = ClockModel(intercept=float(intercept), slope=float(slope), jitter_sd_s=jitter, n_pairs=int(dev.size))

    def alignment_uncertainty(self, stream_id: str) -> float | None:
        b = self._streams[stream_id]
        if b.method not in OBSERVABLE_LATENCY_METHODS and b.declared_latency_uncertainty_s <= 0:
            return None
        fit_se = b.clock.jitter_sd_s / np.sqrt(max(b.clock.n_pairs, 1)) * 10.0
        return float(np.sqrt(b.clock.jitter_sd_s ** 2 + fit_se ** 2 + b.declared_latency_uncertainty_s ** 2))

    def window(self, t_end: float, duration_s: float, now: float | None = None) -> SyncedWindow:
        now = t_end if now is None else now
        t_start = t_end - duration_s
        out: dict[str, StreamWindow] = {}
        uncertainties = []
        for sid, b in self._streams.items():
            m = (b.aligned >= t_start) & (b.aligned < t_end)
            idx = b.indices[m]
            expected = duration_s * b.info.nominal_rate_hz
            gaps = int(np.clip(np.diff(idx) - 1, 0, None).sum()) if idx.size > 1 else 0
            age = float(now - b.aligned[-1]) if b.aligned.size else float("inf")
            unc = self.alignment_uncertainty(sid)
            if unc is not None:
                uncertainties.append(unc)
            out[sid] = StreamWindow(
                stream_id=sid, modality=b.info.modality, data=b.data[m], times=b.aligned[m],
                coverage=float(min(1.0, m.sum() / expected)) if expected > 0 else 0.0, gap_samples=gaps,
                data_age_s=age, stale=age > b.stale_s, connected=b.connected, alignment_uncertainty_s=unc,
                rate_hz=b.info.nominal_rate_hz,
            )
            b.emitted_until = max(b.emitted_until, t_end)
        markers = [mk for mk in self._markers if t_start <= mk.local_time < t_end]
        has_unknown = any(self.alignment_uncertainty(s) is None for s in self._streams)
        return SyncedWindow(t_start, t_end, out, markers,
                            None if has_unknown or not uncertainties else max(uncertainties))

    def health(self, now: float) -> dict:
        streams = {}
        for sid, b in self._streams.items():
            age = float(now - b.aligned[-1]) if b.aligned.size else None
            unc = self.alignment_uncertainty(sid)
            warnings = []
            if b.method not in OBSERVABLE_LATENCY_METHODS:
                warnings.append("constant_transport_latency_unobservable")
            if not b.connected:
                warnings.append("disconnected")
            if age is None or age > b.stale_s:
                warnings.append("stale")
            if abs(b.clock.drift_ppm) > 500:
                warnings.append("excessive_clock_drift")
            if b.gap_samples:
                warnings.append("sample_gaps")
            if b.late_samples:
                warnings.append("late_samples")
            streams[sid] = {
                "modality": b.info.modality.value, "source_kind": b.info.source_kind.value,
                "sync_method": b.method, "connected": b.connected, "nominal_rate_hz": b.info.nominal_rate_hz,
                "clock_offset_s": round(b.clock.intercept, 6), "clock_drift_ppm": round(b.clock.drift_ppm, 2),
                "jitter_sd_ms": round(b.clock.jitter_sd_s * 1e3, 3),
                "alignment_uncertainty_ms": None if unc is None else round(unc * 1e3, 3),
                "data_age_s": None if age is None else round(age, 4), "stale_threshold_s": b.stale_s,
                "total_samples": b.total_samples, "gap_samples": b.gap_samples, "late_samples": b.late_samples,
                "disconnect_events": b.disconnect_events, "warnings": warnings,
            }
        known = [s["alignment_uncertainty_ms"] for s in streams.values() if s["alignment_uncertainty_ms"] is not None]
        return {
            "streams": streams,
            "n_streams": len(streams),
            "all_connected": all(s["connected"] for s in streams.values()),
            "max_alignment_uncertainty_ms": max(known) if known and len(known) == len(streams) else None,
            "alignment_note": ("Alignment uncertainty is reported only where constant latency is observable; "
                               "matching host timestamps alone does not guarantee synchronization."),
        }
