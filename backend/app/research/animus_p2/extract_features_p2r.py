"""ANIMUS-P2-R Wang25 ROI feature extraction (frozen LSA/GLM).

Turns fMRIPrep MNI152NLin2009cAsym:res-2 BOLD (grid-identical to the sealed Wang25 mask) into the P2 feature
contract: per-imagenet-trial betas inside the frozen Wang25 ROI, matched to the sealed CLIP target embedding.
The GLM is the frozen C3XD/C3XAT primitive reused exactly (canonical spm_hrf + per-trial boxcar + frozen
nuisance = motion6 + csf/white_matter if present + cosine drift + run intercept) — an LSA design (one
regressor per image presentation). The design math is dependency-light and self-tested; nibabel is imported
lazily only to read real NIfTI on the cluster.

Runs after fMRIPrep + Wang25 ROI QC; produces /work/animus_p2r/features/sub-XX.npz + manifest. No decoding
metric is computed here (firewall).
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.c3xat_pipeline import (
    FROZEN_NUISANCE_MOTION,
    FROZEN_NUISANCE_TISSUE,
    _boxcar_tr,
    canonical_hrf,
)
from app.research.fmri.run_c3xd_design_sim import conv as c3xd_conv


def build_lsa_design(onsets, durations, tr: float, n_scans: int,
                     nuisance: np.ndarray | None = None) -> tuple[np.ndarray, list[int]]:
    """LSA design: one HRF-convolved boxcar regressor per trial, + nuisance + intercept.
    Returns (design [n_scans, n_cols], trial_column_indices)."""
    hrf = canonical_hrf(tr)
    cols, trial_idx = [], []
    for on, dur in zip(onsets, durations):
        trial_idx.append(len(cols))
        cols.append(c3xd_conv(_boxcar_tr(n_scans, float(on), float(dur), tr), hrf))
    if nuisance is not None and np.size(nuisance):
        for j in range(np.asarray(nuisance).shape[1]):
            cols.append(np.asarray(nuisance, float)[:, j])
    cols.append(np.ones(n_scans))  # run intercept
    return np.vstack(cols).T, trial_idx


def lsa_betas(bold_roi: np.ndarray, design: np.ndarray, trial_idx: list[int]) -> np.ndarray:
    """OLS betas for the trial regressors. bold_roi: (n_scans, n_vox). Returns (n_trials, n_vox)."""
    beta, *_ = np.linalg.lstsq(design, np.asarray(bold_roi, float), rcond=None)
    return beta[trial_idx, :]


def select_frozen_nuisance(confounds: dict) -> tuple[np.ndarray, list[str]]:
    """Frozen nuisance columns from an fMRIPrep confounds dict {col: array}: motion6 (required),
    csf/white_matter (if present), all cosine drift. Missing required motion -> fail-closed."""
    cols = list(confounds.keys())
    motion = [c for c in FROZEN_NUISANCE_MOTION if c in cols]
    missing = [c for c in FROZEN_NUISANCE_MOTION if c not in cols]
    if missing:
        raise ValueError(f"missing required motion confounds: {missing}")
    tissue = [c for c in FROZEN_NUISANCE_TISSUE if c in cols]
    cosine = sorted([c for c in cols if c.startswith("cosine")])
    selected = motion + tissue + cosine
    mat = np.column_stack([np.nan_to_num(np.asarray(confounds[c], float)) for c in selected]) \
        if selected else np.zeros((len(next(iter(confounds.values()))), 0))
    return mat, selected


# --- real-data driver (lazy nibabel; runs on cluster) --------------------------------------------------
def extract_subject(bold_paths, events, confounds_list, tr_list, wang_mask_path,
                    embeddings: dict) -> dict:  # pragma: no cover - requires real NIfTI on cluster
    """bold_paths: list of MNI BOLD nii per run; events: list of [(onset,dur,stim_file),...] per run;
    confounds_list: list of {col:array}; wang_mask_path: sealed Wang25 nii. Returns feature bundle dict."""
    import nibabel as nib
    mask_img = nib.load(wang_mask_path)
    mask = np.asarray(mask_img.get_fdata()) > 0
    X, sids = [], []
    for bp, ev, conf, tr in zip(bold_paths, events, confounds_list, tr_list):
        img = nib.load(bp)
        if img.shape[:3] != mask.shape:
            raise ValueError(f"grid mismatch {bp}: {img.shape[:3]} vs mask {mask.shape}")
        data = np.asarray(img.get_fdata())
        roi = data[mask].T                       # (n_scans, n_vox)
        onsets = [e[0] for e in ev]
        durs = [e[1] for e in ev]
        nuis, _ = select_frozen_nuisance(conf)
        design, tidx = build_lsa_design(onsets, durs, tr, roi.shape[0], nuis)
        betas = lsa_betas(roi, design, tidx)
        X.append(betas)
        sids.extend([e[2] for e in ev])
    X = np.vstack(X)
    Y = np.stack([embeddings[s] for s in sids])
    return {"X": X, "stimulus_ids": np.array(sids), "Y": Y, "n_vox": int(mask.sum())}
