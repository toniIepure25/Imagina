from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class RingBufferStats:
    total_received: int = 0
    total_dropped: int = 0
    windows_extracted: int = 0

    @property
    def drop_rate(self) -> float:
        if self.total_received == 0:
            return 0.0
        return self.total_dropped / self.total_received


class EEGRingBuffer:
    """Thread-safe-ish ring buffer for continuous EEG sample collection.

    Stores up to `max_samples` of the most recent samples (FIFO eviction).
    Designed for the LSL provider to decouple sample ingestion from
    window-based feature extraction.
    """

    def __init__(self, max_samples: int = 2048, n_channels: int = 1):
        self._buffer: deque[list[float]] = deque(maxlen=max_samples)
        self._timestamps: deque[float] = deque(maxlen=max_samples)
        self.max_samples = max_samples
        self.n_channels = n_channels
        self.stats = RingBufferStats()

    def push(self, sample: list[float], timestamp: float = 0.0) -> None:
        was_full = len(self._buffer) == self.max_samples
        self._buffer.append(sample)
        self._timestamps.append(timestamp)
        self.stats.total_received += 1
        if was_full:
            self.stats.total_dropped += 1

    def push_chunk(self, samples: list[list[float]], timestamps: list[float] | None = None) -> None:
        if timestamps is None:
            timestamps = [0.0] * len(samples)
        for sample, ts in zip(samples, timestamps):
            self.push(sample, ts)

    def get_window(self, n_samples: int) -> tuple[list[list[float]], list[float]]:
        """Extract the most recent n_samples from the buffer (non-destructive)."""
        available = len(self._buffer)
        count = min(n_samples, available)
        samples = list(self._buffer)[-count:]
        timestamps = list(self._timestamps)[-count:]
        self.stats.windows_extracted += 1
        return samples, timestamps

    def get_and_clear(self, n_samples: int) -> tuple[list[list[float]], list[float]]:
        """Extract and remove samples (destructive read)."""
        available = len(self._buffer)
        count = min(n_samples, available)
        samples = []
        timestamps = []
        for _ in range(count):
            samples.append(self._buffer.popleft())
            timestamps.append(self._timestamps.popleft())
        self.stats.windows_extracted += 1
        return samples, timestamps

    @property
    def available(self) -> int:
        return len(self._buffer)

    @property
    def is_full(self) -> bool:
        return len(self._buffer) == self.max_samples

    def clear(self) -> None:
        self._buffer.clear()
        self._timestamps.clear()

    def signal_quality_estimate(self) -> dict:
        """Basic signal quality metrics from buffer state."""
        n = self.available
        if n == 0:
            return {"quality": 0.0, "available_samples": 0, "drop_rate": 0.0, "status": "empty"}

        timestamps = list(self._timestamps)
        if len(timestamps) >= 2 and timestamps[-1] > 0 and timestamps[0] > 0:
            duration = timestamps[-1] - timestamps[0]
            effective_rate = (len(timestamps) - 1) / duration if duration > 0 else 0.0
        else:
            effective_rate = 0.0

        flat_channels = 0
        if n >= 10:
            recent = list(self._buffer)[-10:]
            for ch_idx in range(min(self.n_channels, len(recent[0]) if recent else 0)):
                ch_vals = [s[ch_idx] for s in recent if ch_idx < len(s)]
                if ch_vals and max(ch_vals) - min(ch_vals) < 1e-6:
                    flat_channels += 1

        quality = 1.0
        quality -= self.stats.drop_rate * 0.5
        quality -= (flat_channels / max(1, self.n_channels)) * 0.3
        quality = max(0.0, min(1.0, quality))

        return {
            "quality": round(quality, 4),
            "available_samples": n,
            "drop_rate": round(self.stats.drop_rate, 4),
            "effective_sampling_rate_hz": round(effective_rate, 2),
            "flat_channels": flat_channels,
            "status": "good" if quality > 0.7 else "degraded" if quality > 0.3 else "poor",
        }
