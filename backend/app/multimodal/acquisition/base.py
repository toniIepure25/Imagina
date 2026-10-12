from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field

from app.multimodal.schemas import Capabilities, Modality, SampleChunk, SourceKind, StreamInfo


class StreamDisconnected(RuntimeError):
    pass


class ProviderUnavailable(RuntimeError):
    pass


class LifecycleState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTED = "CONNECTED"
    LOST = "LOST"
    CLOSED = "CLOSED"


class FaultPlan(BaseModel):
    """Deterministic fault injection for synthetic and replay streams (device-clock seconds)."""

    clock_offset_s: float = 0.0
    clock_drift_ppm: float = 0.0
    jitter_s: float = Field(default=0.0, ge=0)
    transport_latency_s: float = Field(default=0.0, ge=0)
    dropouts: list[tuple[float, float]] = Field(default_factory=list)
    disconnect_at_s: float | None = None
    reconnect_after_s: float = Field(default=2.0, gt=0)
    flatline: list[tuple[float, float]] = Field(default_factory=list)
    artifact_bursts: list[tuple[float, float]] = Field(default_factory=list)


@dataclass
class LifecycleEvent:
    local_time: float
    event: str
    detail: str = ""


@dataclass
class StreamStats:
    samples_delivered: int = 0
    samples_dropped: int = 0
    disconnects: int = 0
    reconnects: int = 0
    events: list[LifecycleEvent] = field(default_factory=list)


class ModalityProvider(ABC):
    provider_id: str
    modality: Modality
    source_kind: SourceKind
    provider_version: str = "1.0"

    def __init__(self) -> None:
        self.state = LifecycleState.DISCONNECTED
        self.stats = StreamStats()
        self._info: StreamInfo | None = None

    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abstractmethod
    def connect(self, local_time: float = 0.0) -> StreamInfo: ...

    @abstractmethod
    def read(self, until_local_time: float) -> SampleChunk | None: ...

    def try_reconnect(self, local_time: float) -> bool:
        return False

    def disconnect(self, local_time: float = 0.0) -> None:
        self.state = LifecycleState.CLOSED
        self._log(local_time, "closed")

    @property
    def info(self) -> StreamInfo:
        if self._info is None:
            raise RuntimeError("provider not connected")
        return self._info

    def health(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "modality": self.modality.value,
            "source_kind": self.source_kind.value,
            "state": self.state.value,
            "samples_delivered": self.stats.samples_delivered,
            "samples_dropped": self.stats.samples_dropped,
            "disconnects": self.stats.disconnects,
            "reconnects": self.stats.reconnects,
        }

    def _log(self, local_time: float, event: str, detail: str = "") -> None:
        self.stats.events.append(LifecycleEvent(local_time, event, detail))


class ArrayStreamProvider(ModalityProvider):
    """Streams a pre-materialized recording through a simulated device clock and transport.

    Sample i has device time ``i / fs``. Its true (reference) time is ``(t_dev - offset) / (1 + drift)``;
    the local arrival timestamp adds transport latency and jitter. Faults are applied deterministically.
    """

    def __init__(self, faults: FaultPlan | None = None, seed: int = 0) -> None:
        super().__init__()
        self.faults = faults or FaultPlan()
        self.seed = seed
        self._data: np.ndarray | None = None
        self._cursor = 0
        self._arrival: np.ndarray | None = None
        self._device_ts: np.ndarray | None = None
        self._keep: np.ndarray | None = None
        self._lost_until: float | None = None

    @abstractmethod
    def _materialize(self) -> tuple[StreamInfo, np.ndarray]: ...

    def connect(self, local_time: float = 0.0) -> StreamInfo:
        if self._info is None:
            info, data = self._materialize()
            self._info, self._data = info, np.asarray(data, dtype=float)
            self._prepare_timing()
        self.state = LifecycleState.CONNECTED
        self._log(local_time, "connected")
        return self.info

    def _prepare_timing(self) -> None:
        assert self._data is not None
        fp = self.faults
        n = self._data.shape[0]
        fs = self.info.nominal_rate_hz
        device_rel = np.arange(n) / fs
        true_t = device_rel / (1.0 + fp.clock_drift_ppm * 1e-6)
        rng = np.random.default_rng(self.seed + 7919)
        arrival = true_t + fp.transport_latency_s
        if fp.jitter_s > 0:
            arrival = arrival + rng.uniform(0, fp.jitter_s, n)
        self._arrival = np.maximum.accumulate(arrival)
        self._device_ts = device_rel + fp.clock_offset_s
        keep = np.ones(n, dtype=bool)
        for a, b in fp.dropouts:
            keep[(device_rel >= a) & (device_rel < b)] = False
        self._keep = keep
        data = self._data.copy()
        for a, b in fp.flatline:
            m = (device_rel >= a) & (device_rel < b)
            if m.any():
                data[m] = data[np.argmax(m)]
        for a, b in fp.artifact_bursts:
            m = (device_rel >= a) & (device_rel < b)
            data[m] += rng.normal(0, 50.0 * (np.std(data) + 1e-9), (int(m.sum()), data.shape[1]))
        self._data = data

    def try_reconnect(self, local_time: float) -> bool:
        if self.state != LifecycleState.LOST:
            return self.state == LifecycleState.CONNECTED
        if self._lost_until is not None and local_time >= self._lost_until:
            assert self._arrival is not None
            skip = int(np.searchsorted(self._arrival, local_time, side="right"))
            if skip > self._cursor:
                assert self._keep is not None
                self.stats.samples_dropped += int(self._keep[self._cursor:skip].sum())
                self._cursor = skip
            self.state = LifecycleState.CONNECTED
            self.stats.reconnects += 1
            self._log(local_time, "reconnected")
            return True
        return False

    def read(self, until_local_time: float) -> SampleChunk | None:
        if self.state == LifecycleState.LOST:
            raise StreamDisconnected(self.provider_id)
        if self.state != LifecycleState.CONNECTED:
            raise RuntimeError(f"{self.provider_id} not connected ({self.state.value})")
        assert self._arrival is not None and self._data is not None
        assert self._device_ts is not None and self._keep is not None
        fp = self.faults
        if fp.disconnect_at_s is not None and until_local_time >= fp.disconnect_at_s and self.stats.disconnects == 0:
            stop = int(np.searchsorted(self._arrival, fp.disconnect_at_s, side="left"))
            chunk = self._slice(self._cursor, max(stop, self._cursor)) if stop > self._cursor else None
            self.state = LifecycleState.LOST
            self.stats.disconnects += 1
            self._lost_until = fp.disconnect_at_s + fp.reconnect_after_s
            self._log(fp.disconnect_at_s, "lost", "injected disconnect")
            return chunk
        stop = int(np.searchsorted(self._arrival, until_local_time, side="right"))
        if stop <= self._cursor:
            return None
        return self._slice(self._cursor, stop)

    def _slice(self, start: int, stop: int) -> SampleChunk | None:
        assert self._keep is not None and self._data is not None
        assert self._arrival is not None and self._device_ts is not None
        self._cursor = stop
        idx = np.arange(start, stop)[self._keep[start:stop]]
        if idx.size == 0:
            self.stats.samples_dropped += stop - start
            return None
        dropped = int(idx[0] - start)
        self.stats.samples_dropped += (stop - start) - idx.size
        self.stats.samples_delivered += idx.size
        return SampleChunk(
            stream_id=self.info.stream_id,
            data=self._data[idx],
            device_timestamps=self._device_ts[idx],
            local_timestamps=self._arrival[idx],
            sample_indices=idx,
            dropped_before=dropped,
        )

    @property
    def total_samples(self) -> int:
        return 0 if self._data is None else int(self._data.shape[0])
