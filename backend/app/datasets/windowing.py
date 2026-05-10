"""Convert raw EEG data into EEGSampleWindow objects."""

from datetime import datetime, timezone
from typing import Optional

from app.schemas.signals import EEGSampleWindow


def windows_from_raw(
    raw,  # mne.io.Raw
    window_duration_seconds: float = 2.0,
    max_windows: int = 30,
    channel_names: Optional[list[str]] = None,
    provider_id: str = "dataset.replay",
    provider_type: str = "dataset",
    dataset_id: str = "unknown",
) -> list[EEGSampleWindow]:

    sfreq = raw.info["sfreq"]
    ch_names = channel_names or raw.ch_names
    ch_count = len(ch_names)
    samples_per_window = int(sfreq * window_duration_seconds)
    total_samples = raw.n_times
    windows: list[EEGSampleWindow] = []

    data = raw.get_data(picks=list(range(ch_count))) if ch_count <= raw.info["nchan"] else raw.get_data()[:ch_count]
    n_windows = min(max_windows, total_samples // samples_per_window)

    for w in range(n_windows):
        start = w * samples_per_window
        end = start + samples_per_window
        if end > data.shape[1]:
            break
        segment = data[:, start:end]
        samples = segment.T.tolist()

        window = EEGSampleWindow(
            session_id=f"{dataset_id}_win{w}",
            timestamp=datetime.now(timezone.utc),
            window_index=w,
            sampling_rate_hz=int(sfreq),
            duration_seconds=window_duration_seconds,
            channels=ch_names[:ch_count],
            samples=samples,
            simulated=False if dataset_id != "fixture" else False,
            generator_version=f"dataset_{dataset_id}",
            provider_id=provider_id,
            provider_type=provider_type,
            channel_names=ch_names[:ch_count],
            channel_count=ch_count,
            nominal_sampling_rate_hz=float(sfreq),
            raw_persisted=False,
            preprocessing_version="dataset_v1",
        )
        windows.append(window)

    return windows
