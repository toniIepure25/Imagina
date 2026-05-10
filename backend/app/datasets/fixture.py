"""Synthetic EEG fixture generator for pipeline validation.

Produces a tiny 4-channel 256Hz signal with known alpha (10Hz) activity
and controlled noise levels.  Not real EEG — clearly labeled as fixture data.
"""

import math
import random
from datetime import datetime, timezone

from app.schemas.signals import EEGSampleWindow


def generate_synthetic_eeg(
    duration_seconds: float = 60.0,
    sampling_rate_hz: int = 256,
    channel_count: int = 4,
    alpha_freq_hz: float = 10.0,
    noise_scale: float = 0.10,
    seed: int = 42,
) -> list[EEGSampleWindow]:
    rng = random.Random(seed)
    total_samples = int(duration_seconds * sampling_rate_hz)
    window_samples = sampling_rate_hz * 2
    windows = total_samples // window_samples
    result: list[EEGSampleWindow] = []

    channel_names = [f"ch{i}" for i in range(channel_count)]
    full_signal: list[float] = []
    for i in range(total_samples):
        t = i / sampling_rate_hz
        alpha = math.sin(2 * math.pi * alpha_freq_hz * t)
        noise = rng.gauss(0, noise_scale)
        full_signal.append(alpha + noise)

    for w in range(windows):
        start = w * window_samples
        end = start + window_samples
        segment = full_signal[start:end]
        samples = [
            [
                segment[i] * (0.8 + 0.2 * (ch / max(1, channel_count - 1)))
                for ch in range(channel_count)
            ]
            for i in range(window_samples)
        ]

        timestamp = datetime.now(timezone.utc)
        eeg = EEGSampleWindow(
            session_id=f"fixture_{w}",
            timestamp=timestamp,
            window_index=w,
            sampling_rate_hz=sampling_rate_hz,
            duration_seconds=2.0,
            channels=channel_names,
            samples=samples,
            simulated=False,
            generator_version="fixture_v1",
            provider_id="dataset.fixture",
            provider_type="dataset",
            channel_names=channel_names,
            channel_count=channel_count,
            nominal_sampling_rate_hz=float(sampling_rate_hz),
            raw_persisted=False,
            preprocessing_version="fixture_v1",
        )
        result.append(eeg)

    return result
