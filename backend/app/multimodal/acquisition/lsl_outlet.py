"""LSL replay outlet: publishes a synthetic or recorded stream over Lab Streaming Layer in real time.

Used to exercise ``LSLInletProvider`` end-to-end without hardware. Supports injected pauses (dropouts: samples in
the pause are skipped, so the inlet sees a timestamp gap) and outlet restarts (disconnect/reconnect).
"""
from __future__ import annotations

import threading
import time

import numpy as np

from app.multimodal.schemas import StreamInfo


class LSLReplayOutlet:
    def __init__(self, info: StreamInfo, data: np.ndarray, stream_type: str, name: str, source_id: str,
                 chunk_s: float = 0.04, pauses: list[tuple[float, float]] | None = None,
                 restart_at_s: float | None = None, restart_gap_s: float = 1.0) -> None:
        self.info = info
        self.data = np.asarray(data, dtype=np.float32)
        self.stream_type, self.name, self.source_id = stream_type, name, source_id
        self.chunk_s = chunk_s
        self.pauses = pauses or []
        self.restart_at_s = restart_at_s
        self.restart_gap_s = restart_gap_s
        self.pushed = 0
        self.skipped = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.outlet = None

    def _make_outlet(self):
        import pylsl

        si = pylsl.StreamInfo(self.name, self.stream_type, self.data.shape[1], self.info.nominal_rate_hz,
                              pylsl.cf_float32, self.source_id)
        chans = si.desc().append_child("channels")
        for c in self.info.channels:
            ch = chans.append_child("channel")
            ch.append_child_value("label", c.name)
            ch.append_child_value("unit", c.unit)
        return pylsl.StreamOutlet(si, chunk_size=0, max_buffered=60)

    def start(self) -> LSLReplayOutlet:
        self.outlet = self._make_outlet()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        import pylsl

        fs = self.info.nominal_rate_hz
        t0 = pylsl.local_clock()
        i = 0
        restarted = False
        n = self.data.shape[0]
        step = max(1, int(self.chunk_s * fs))
        while not self._stop.is_set() and i < n:
            rel = i / fs
            if self.restart_at_s is not None and not restarted and rel >= self.restart_at_s:
                self.outlet = None
                time.sleep(self.restart_gap_s)
                skip = int(self.restart_gap_s * fs)
                self.skipped += skip
                i += skip
                self.outlet = self._make_outlet()
                restarted = True
                continue
            j = min(i + step, n)
            in_pause = [(a, b) for a, b in self.pauses if a <= rel < b]
            if in_pause:
                skip_to = min(int(in_pause[0][1] * fs), n)
                self.skipped += skip_to - i
                i = skip_to
            else:
                stamps = t0 + np.arange(i, j) / fs
                self.outlet.push_chunk(self.data[i:j].tolist(), stamps.tolist())
                self.pushed += j - i
                i = j
            delay = t0 + i / fs - pylsl.local_clock()
            if delay > 0:
                time.sleep(delay)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.outlet = None
