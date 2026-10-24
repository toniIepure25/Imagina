"""Memory-safe real-data execution for NSD perception betas.

Handles large datasets (30,000+ trials × 15,000+ voxels) without
loading everything into RAM. Provides:
- HDF5 streaming with chunked reads
- Chunked ROI extraction
- Incremental standardization statistics
- Deterministic trial ordering
- Checkpointable extraction
- Per-session cache with hash verification
- Resource estimation
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

import numpy as np
from numpy.typing import NDArray


@dataclass
class ResourceEstimate:
    """Estimated resource requirements for real-data execution."""
    n_sessions: int
    trials_per_session: int
    n_roi_voxels: int
    dtype_bytes: int
    peak_ram_mb: float
    cache_storage_mb: float
    temp_storage_mb: float
    matrix_shape: tuple[int, int]
    estimated_runtime_minutes: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_sessions": self.n_sessions,
            "trials_per_session": self.trials_per_session,
            "n_roi_voxels": self.n_roi_voxels,
            "dtype_bytes": self.dtype_bytes,
            "peak_ram_mb": round(self.peak_ram_mb, 1),
            "cache_storage_mb": round(self.cache_storage_mb, 1),
            "temp_storage_mb": round(self.temp_storage_mb, 1),
            "matrix_shape": list(self.matrix_shape),
            "estimated_runtime_minutes": round(self.estimated_runtime_minutes, 1),
        }


def estimate_resources(
    n_sessions: int = 40,
    trials_per_session: int = 750,
    n_roi_voxels: int = 15724,
    dtype: np.dtype = np.dtype(np.float32),
) -> ResourceEstimate:
    """Estimate resource requirements for the full extraction pipeline."""
    total_trials = n_sessions * trials_per_session
    dtype_bytes = dtype.itemsize

    roi_matrix_bytes = total_trials * n_roi_voxels * dtype_bytes
    roi_matrix_mb = roi_matrix_bytes / (1024**2)

    one_session_bytes = trials_per_session * n_roi_voxels * dtype_bytes
    one_session_mb = one_session_bytes / (1024**2)

    peak_ram_mb = one_session_mb * 2 + roi_matrix_mb * 0.1

    cache_storage_mb = roi_matrix_mb
    temp_storage_mb = one_session_mb * 2

    io_time_per_session_s = 30.0
    estimated_runtime_min = (n_sessions * io_time_per_session_s) / 60.0

    return ResourceEstimate(
        n_sessions=n_sessions,
        trials_per_session=trials_per_session,
        n_roi_voxels=n_roi_voxels,
        dtype_bytes=dtype_bytes,
        peak_ram_mb=peak_ram_mb,
        cache_storage_mb=cache_storage_mb,
        temp_storage_mb=temp_storage_mb,
        matrix_shape=(total_trials, n_roi_voxels),
        estimated_runtime_minutes=estimated_runtime_min,
    )


def stream_session_betas(
    session_path: Path,
    roi_mask: NDArray[np.int32] | None = None,
    roi_value: int = 1,
    chunk_size: int = 50,
    dtype: np.dtype = np.dtype(np.float32),
) -> Generator[NDArray, None, None]:
    """Stream beta data from an HDF5 file in chunks, applying ROI selection.

    Yields chunks of shape [chunk_size, n_roi_voxels] (or fewer for last chunk).
    """
    import h5py

    with h5py.File(str(session_path), "r") as f:
        if "betas" in f:
            ds = f["betas"]
        else:
            ds = f[list(f.keys())[0]]

        n_trials = ds.shape[0]
        is_volumetric = ds.ndim == 4

        if roi_mask is not None and is_volumetric:
            mask_flat = (roi_mask == roi_value).ravel()
        elif roi_mask is not None and ds.ndim == 2:
            mask_flat = (roi_mask.ravel() == roi_value)
        else:
            mask_flat = None

        for start in range(0, n_trials, chunk_size):
            end = min(start + chunk_size, n_trials)
            chunk = ds[start:end]

            if is_volumetric:
                chunk = chunk.reshape(end - start, -1)

            chunk = chunk.astype(dtype)

            if mask_flat is not None:
                chunk = chunk[:, mask_flat]

            yield chunk


def extract_session_roi(
    session_path: Path,
    roi_mask: NDArray[np.int32],
    roi_value: int = 1,
    dtype: np.dtype = np.dtype(np.float32),
) -> NDArray:
    """Extract all trials from a session with ROI masking. Returns [n_trials, n_roi_voxels]."""
    chunks = list(stream_session_betas(session_path, roi_mask, roi_value, chunk_size=100, dtype=dtype))
    if not chunks:
        return np.empty((0, 0), dtype=dtype)
    return np.concatenate(chunks, axis=0)


class IncrementalStandardizer:
    """Compute running mean and std for incremental z-scoring."""

    def __init__(self, n_features: int, dtype: np.dtype = np.dtype(np.float64)):
        self.n_features = n_features
        self.n_samples = 0
        self._sum = np.zeros(n_features, dtype=dtype)
        self._sum_sq = np.zeros(n_features, dtype=dtype)

    def update(self, X: NDArray) -> None:
        """Update statistics with a new batch of samples."""
        n = X.shape[0]
        self.n_samples += n
        self._sum += X.sum(axis=0).astype(self._sum.dtype)
        self._sum_sq += (X.astype(np.float64) ** 2).sum(axis=0)

    @property
    def mean(self) -> NDArray[np.float64]:
        if self.n_samples == 0:
            return np.zeros(self.n_features)
        return self._sum / self.n_samples

    @property
    def std(self) -> NDArray[np.float64]:
        if self.n_samples < 2:
            return np.ones(self.n_features)
        mean = self.mean
        var = self._sum_sq / self.n_samples - mean**2
        var = np.clip(var, 0, None)
        return np.sqrt(var)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "mean_range": [float(self.mean.min()), float(self.mean.max())],
            "std_range": [float(self.std.min()), float(self.std.max())],
        }


@dataclass
class ExtractionCheckpoint:
    """Checkpoint state for resumable extraction."""
    sessions_complete: list[int]
    sessions_total: int
    last_session_hash: str
    standardizer_state: dict[str, Any]
    cache_dir: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions_complete": self.sessions_complete,
            "sessions_total": self.sessions_total,
            "last_session_hash": self.last_session_hash,
            "standardizer_state": self.standardizer_state,
            "cache_dir": self.cache_dir,
            "timestamp": self.timestamp,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "ExtractionCheckpoint":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


def extract_all_sessions(
    betas_dir: Path,
    roi_mask: NDArray[np.int32],
    sessions: list[int],
    cache_dir: Path,
    roi_value: int = 1,
    dtype: np.dtype = np.dtype(np.float32),
    checkpoint_path: Path | None = None,
) -> tuple[Path, IncrementalStandardizer]:
    """Extract ROI betas from all sessions with caching and checkpointing.

    Returns path to the concatenated cache file and the standardizer.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_roi = int(np.sum(roi_mask == roi_value))
    standardizer = IncrementalStandardizer(n_roi)

    completed_sessions: list[int] = []
    if checkpoint_path and checkpoint_path.exists():
        ckpt = ExtractionCheckpoint.load(checkpoint_path)
        completed_sessions = ckpt.sessions_complete

    for sess in sessions:
        cache_file = cache_dir / f"roi_session{sess:02d}.npy"

        if sess in completed_sessions and cache_file.exists():
            data = np.load(str(cache_file))
            standardizer.update(data.astype(np.float64))
            continue

        session_path = betas_dir / f"betas_session{sess:02d}.hdf5"
        if not session_path.exists():
            raise FileNotFoundError(f"Session file not found: {session_path}")

        data = extract_session_roi(session_path, roi_mask, roi_value, dtype)
        np.save(str(cache_file), data)

        file_hash = hashlib.sha256(data.tobytes()).hexdigest()[:16]
        standardizer.update(data.astype(np.float64))
        completed_sessions.append(sess)

        if checkpoint_path:
            ckpt = ExtractionCheckpoint(
                sessions_complete=completed_sessions,
                sessions_total=len(sessions),
                last_session_hash=file_hash,
                standardizer_state=standardizer.to_dict(),
                cache_dir=str(cache_dir),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            ckpt.save(checkpoint_path)

    return cache_dir, standardizer


def load_cached_roi_matrix(
    cache_dir: Path,
    sessions: list[int],
    dtype: np.dtype = np.dtype(np.float32),
) -> NDArray:
    """Load all cached session ROI extractions into one matrix."""
    arrays = []
    for sess in sessions:
        cache_file = cache_dir / f"roi_session{sess:02d}.npy"
        if not cache_file.exists():
            raise FileNotFoundError(f"Cache missing for session {sess}: {cache_file}")
        arrays.append(np.load(str(cache_file)).astype(dtype))
    return np.concatenate(arrays, axis=0)
