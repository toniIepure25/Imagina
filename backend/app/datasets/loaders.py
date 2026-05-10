"""EEG dataset loaders. Supports MNE-based loading with fixture fallback."""

import os

from app.datasets.catalog import DATASETS
from app.datasets.fixture import generate_synthetic_eeg
from app.schemas.signals import EEGSampleWindow

READERS: dict[str, str] = {
    ".fif": "read_raw_fif",
    ".edf": "read_raw_edf",
    ".bdf": "read_raw_bdf",
    ".vhdr": "read_raw_brainvision",
    ".set": "read_raw_eeglab",
}

SUPPORTED_EXTENSIONS = set(READERS.keys())


def detect_reader(file_path: str) -> str | None:
    ext = os.path.splitext(file_path)[1].lower()
    return READERS.get(ext)


def validate_eeg_file(file_path: str) -> dict | None:
    reader = detect_reader(file_path)
    if reader is None:
        return None
    import mne
    reader_func = getattr(mne.io, reader, None)
    if reader_func is None:
        return None
    raw = reader_func(file_path, preload=False, verbose=False)
    return summarize_raw(raw)


def summarize_raw(raw) -> dict:
    info = raw.info if isinstance(raw.info, dict) else {}
    sfreq = float(info.get("sfreq", raw.info["sfreq"] if "sfreq" in (raw.info or {}) else 1))
    nchan_val = info.get("nchan", getattr(raw, "nchan", None))
    if nchan_val is None:
        try:
            nchan_val = len(getattr(raw, "ch_names", []) or [])
        except Exception:
            nchan_val = 0
    ch_names = list(getattr(raw, "ch_names", []) if hasattr(raw, "ch_names") else [])
    n_times = getattr(raw, "n_times", 0) or 0
    duration = round(n_times / max(sfreq, 1), 2)
    return {
        "sampling_rate_hz": sfreq,
        "channel_count": nchan_val,
        "channel_names": ch_names,
        "n_times": n_times,
        "duration_seconds": duration,
        "reader_used": type(raw).__name__,
    }


def safe_read_raw(file_path: str):
    reader = detect_reader(file_path)
    if reader is None:
        raise ValueError(f"Unsupported EEG format: {file_path}")
    import mne
    reader_func = getattr(mne.io, reader)
    return reader_func(file_path, preload=False, verbose=False)


def load_windows(dataset_id: str, max_windows: int = 30) -> list[EEGSampleWindow]:
    ds = DATASETS.get(dataset_id)
    if ds is None:
        raise ValueError(f"Unknown dataset: {dataset_id}")

    if dataset_id == "fixture":
        return generate_synthetic_eeg(duration_seconds=60.0)[:max_windows]

    windows = _load_real_eeg(dataset_id, max_windows)
    if windows:
        return windows
    raise RuntimeError(
        f"No EEG files found for dataset '{dataset_id}'. "
        "Use --dataset fixture for synthetic data."
    )


def _load_real_eeg(dataset_id: str, max_windows: int) -> list[EEGSampleWindow]:
    windows: list[EEGSampleWindow] = []
    try:
        import mne
    except ImportError:
        raise RuntimeError("MNE is not installed. Cannot load real EEG files.")

    from app.datasets.manifest import read_manifest
    manifest = read_manifest(dataset_id)
    if manifest is None:
        return []

    files = manifest.get("files") or []
    for file_path in files:
        if not os.path.exists(file_path):
            continue
        ext = os.path.splitext(file_path)[1].lower()
        reader_name = READERS.get(ext)
        if reader_name is None:
            continue
        reader_func = getattr(mne.io, reader_name, None)
        if reader_func is None:
            continue
        raw = reader_func(file_path, preload=False, verbose=False)
        from app.datasets.windowing import windows_from_raw
        windows = windows_from_raw(raw, max_windows=max_windows)
        if windows:
            break

    return windows
