from typing import Any

DATASETS: dict[str, dict[str, Any]] = {
    "yoto": {
        "name": "YOTO ds005815",
        "source": "OpenNeuro",
        "url": "https://openneuro.org/datasets/ds005815",
        "version": "2.0.1",
        "description": "EEG dataset for multisensory perception and mental imagery (YOTO).",
        "format": "BIDS",
        "status": "unknown",
        "download_supported": False,
        "requires_manual_download": True,
        "estimated_size_gb": None,
        "last_probe_status": None,
        "notes": (
            "OpenNeuro dataset ds005815. May require openneuro-py, datalad, "
            "or direct file URL for automated subset download."
        ),
    },
    "openmiir": {
        "name": "OpenMIIR",
        "source": "GitHub",
        "url": "https://github.com/sstober/openmiir",
        "version": None,
        "description": (
            "EEG recordings for music perception and imagination. "
            "Raw EEG is ~700 MB/subject, FIF format, MNE-compatible."
        ),
        "format": "FIF",
        "status": "unknown",
        "download_supported": False,
        "requires_manual_download": True,
        "estimated_size_gb": 0.7,
        "last_probe_status": None,
        "notes": (
            "Correct repository: sstober/openmiir (not sllvir/OpenMIIR). "
            "Raw EEG requires mirror/torrent/manual URL selection. "
            "FIF format compatible with mne.io.read_raw_fif."
        ),
    },
    "fixture": {
        "name": "IMAGINA Synthetic Fixture",
        "source": "local",
        "url": None,
        "version": None,
        "description": "Tiny synthetic 4-channel 256Hz EEG-like fixture for pipeline validation.",
        "format": "fixture",
        "status": "available",
        "download_supported": True,
        "requires_manual_download": False,
        "estimated_size_gb": 0.0,
        "last_probe_status": "available",
        "notes": None,
    },
}


def list_datasets() -> list[dict[str, Any]]:
    return [{"dataset_id": k, **v} for k, v in DATASETS.items()]


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    return DATASETS.get(dataset_id)
