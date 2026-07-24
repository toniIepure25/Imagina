"""NSD / NSD-Imagery data ingestion for Scientific Gate C3.

Provides provenance-locked loading of:
- Beta HDF5 files (perception and imagery)
- ROI NIfTI masks
- Behavioral TSV files
- Stimulus target embeddings

All paths are resolved from environment variables; nothing is hardcoded.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np

from app.research.fmri.registry import ELIGIBLE_SUBJECTS, NSD_IMAGERY_DESCRIPTOR


def _env_path(var: str, fallback: str = "") -> Path:
    val = os.environ.get(var, fallback)
    if not val:
        raise EnvironmentError(f"Environment variable {var} is not set and no fallback provided.")
    return Path(val)


def get_nsd_data_root() -> Path:
    return _env_path("NSD_DATA_ROOT")


def get_nsd_betas_root() -> Path:
    return _env_path("NSD_BETAS_ROOT")


def get_nsd_stimuli_root() -> Path:
    return _env_path("NSD_STIMULI_ROOT")


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_roi_mask(participant_id: str, roi_name: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Load a NIfTI ROI mask for a given participant.

    Returns (mask_array, metadata_dict).
    Requires nibabel.
    """
    import nibabel as nib

    if participant_id not in ELIGIBLE_SUBJECTS:
        raise ValueError(f"Participant {participant_id} not in eligible set: {ELIGIBLE_SUBJECTS}")

    data_root = get_nsd_data_root()
    roi_dir = data_root / "ppdata" / participant_id / "func1pt8mm" / "roi"

    roi_file_map = {
        "nsdgeneral": "nsdgeneral.nii.gz",
        "prf-visualrois": "prf-visualrois.nii.gz",
        "streams": "streams.nii.gz",
    }
    if roi_name not in roi_file_map:
        raise ValueError(f"Unknown ROI: {roi_name}. Available: {list(roi_file_map.keys())}")

    roi_path = roi_dir / roi_file_map[roi_name]
    if not roi_path.exists():
        raise FileNotFoundError(f"ROI file not found: {roi_path}")

    img = nib.load(str(roi_path))
    mask_data = np.asarray(img.dataobj)
    file_hash = sha256_file(roi_path)

    metadata = {
        "participant_id": participant_id,
        "roi_id": roi_name,
        "file_path": str(roi_path),
        "file_hash": file_hash,
        "shape": mask_data.shape,
        "n_nonzero_voxels": int(np.count_nonzero(mask_data)),
        "unique_labels": sorted(int(v) for v in np.unique(mask_data) if v > 0),
    }
    return mask_data, metadata


def load_imagery_betas(participant_id: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Load NSD-Imagery betas (HDF5) for a given participant.

    Returns (betas_array [n_trials, n_voxels_full], metadata_dict).
    Requires h5py.
    """
    import h5py

    if participant_id not in ELIGIBLE_SUBJECTS:
        raise ValueError(f"Participant {participant_id} not in eligible set: {ELIGIBLE_SUBJECTS}")

    betas_root = get_nsd_betas_root()
    beta_path = (
        betas_root / "ppdata" / participant_id / "func1pt8mm"
        / "nsdimagerybetas_fithrf" / "betas_nsdimagery.hdf5"
    )
    if not beta_path.exists():
        raise FileNotFoundError(f"Imagery betas not found: {beta_path}")

    file_hash = sha256_file(beta_path)

    with h5py.File(str(beta_path), "r") as f:
        keys = list(f.keys())
        if "betas" in keys:
            betas = f["betas"][:]
        else:
            first_key = keys[0]
            betas = f[first_key][:]

    metadata = {
        "dataset_id": NSD_IMAGERY_DESCRIPTOR.dataset_id,
        "dataset_version": NSD_IMAGERY_DESCRIPTOR.dataset_version,
        "participant_id": participant_id,
        "beta_variant": NSD_IMAGERY_DESCRIPTOR.beta_variant,
        "beta_space": "func1pt8mm",
        "file_path": str(beta_path),
        "file_hash": file_hash,
        "file_size_bytes": beta_path.stat().st_size,
        "shape": betas.shape,
        "n_trials": betas.shape[0],
        "n_voxels": betas.shape[1] if betas.ndim == 2 else int(np.prod(betas.shape[1:])),
    }
    return betas, metadata


def load_ncsnr(participant_id: str) -> tuple[np.ndarray, dict[str, Any]]:
    """Load noise-ceiling SNR map for a participant.

    Returns (ncsnr_array, metadata_dict).
    """
    import nibabel as nib

    if participant_id not in ELIGIBLE_SUBJECTS:
        raise ValueError(f"Participant {participant_id} not in eligible set: {ELIGIBLE_SUBJECTS}")

    betas_root = get_nsd_betas_root()
    ncsnr_path = betas_root / "ppdata" / participant_id / "func1pt8mm" / "betas_fithrf" / "ncsnr.nii.gz"
    if not ncsnr_path.exists():
        raise FileNotFoundError(f"ncsnr file not found: {ncsnr_path}")

    img = nib.load(str(ncsnr_path))
    ncsnr_data = np.asarray(img.dataobj, dtype=np.float32)
    file_hash = sha256_file(ncsnr_path)

    metadata = {
        "participant_id": participant_id,
        "file_path": str(ncsnr_path),
        "file_hash": file_hash,
        "shape": ncsnr_data.shape,
        "n_positive": int(np.sum(ncsnr_data > 0)),
        "mean_ncsnr": float(np.mean(ncsnr_data[ncsnr_data > 0])) if np.any(ncsnr_data > 0) else 0.0,
    }
    return ncsnr_data, metadata


def load_behavioral_tsv(participant_id: str, run_type: str) -> list[dict[str, Any]]:
    """Load a behavioral TSV file for imagery experiment.

    run_type examples: 'visA', 'imgA_1', 'imgB_2', 'attC'
    Returns list of trial dicts.
    """
    if participant_id not in ELIGIBLE_SUBJECTS:
        raise ValueError(f"Participant {participant_id} not in eligible set: {ELIGIBLE_SUBJECTS}")

    data_root = get_nsd_data_root()
    tsv_path = data_root / "bdata" / "nsdimagery" / f"nsdimagery_{participant_id}_{run_type}.tsv"
    if not tsv_path.exists():
        raise FileNotFoundError(f"Behavioral TSV not found: {tsv_path}")

    trials = []
    with open(tsv_path, "r") as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            trial = dict(zip(header, values))
            trials.append(trial)
    return trials


def get_imagery_run_types() -> list[str]:
    """Return the run type identifiers for imagery runs."""
    return ["imgA_1", "imgA_2", "imgB_1", "imgB_2", "imgC_1", "imgC_2"]


def get_vision_run_types() -> list[str]:
    """Return the run type identifiers for vision runs."""
    return ["visA", "visB", "visC"]


def get_stimulus_set_for_run(run_type: str) -> str:
    """Map run type to stimulus set."""
    if "A" in run_type:
        return "simple"
    elif "B" in run_type:
        return "complex"
    elif "C" in run_type:
        return "conceptual"
    raise ValueError(f"Cannot determine stimulus set for run: {run_type}")


def validate_participant_data(participant_id: str) -> dict[str, Any]:
    """Check which data files are available for a participant.

    Does NOT load data, only checks file existence.
    """
    report: dict[str, Any] = {"participant_id": participant_id, "eligible": participant_id in ELIGIBLE_SUBJECTS}

    try:
        data_root = get_nsd_data_root()
        betas_root = get_nsd_betas_root()
    except EnvironmentError as e:
        report["error"] = str(e)
        return report

    imagery_beta_path = (
        betas_root / "ppdata" / participant_id / "func1pt8mm"
        / "nsdimagerybetas_fithrf" / "betas_nsdimagery.hdf5"
    )
    ncsnr_path = betas_root / "ppdata" / participant_id / "func1pt8mm" / "betas_fithrf" / "ncsnr.nii.gz"
    roi_dir = data_root / "ppdata" / participant_id / "func1pt8mm" / "roi"

    report["imagery_betas_available"] = imagery_beta_path.exists()
    report["ncsnr_available"] = ncsnr_path.exists()
    report["roi_nsdgeneral_available"] = (roi_dir / "nsdgeneral.nii.gz").exists()
    report["roi_visualrois_available"] = (roi_dir / "prf-visualrois.nii.gz").exists()
    report["roi_streams_available"] = (roi_dir / "streams.nii.gz").exists()

    bdata_dir = data_root / "bdata" / "nsdimagery"
    report["behavioral_files"] = {}
    for rt in get_imagery_run_types() + get_vision_run_types():
        tsv = bdata_dir / f"nsdimagery_{participant_id}_{rt}.tsv"
        report["behavioral_files"][rt] = tsv.exists()

    return report
