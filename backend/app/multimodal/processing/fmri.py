"""Offline fMRI: BIDS discovery, TR-aware design matrices, motion/drift nuisance regression, ROI extraction,
GLM and trial-wise (LSA) betas for perception/imagery decoding.

This is offline research decoding. It is NOT scanner neurofeedback; no real-time fMRI path exists. NSD-specific
pipelines live in ``app.research.fmri`` and are not duplicated here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.multimodal.acquisition.synthetic_signals import canonical_hrf

REALTIME_NEUROFEEDBACK_SUPPORTED = False
MOTION_COLUMNS = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]


@dataclass
class BoldRun:
    subject: str
    bold_path: Path
    tr: float
    tr_source: str
    events: list[dict]
    confounds: np.ndarray | None
    confound_names: list[str]
    mask_path: Path | None


def discover_bids(root: Path) -> list[BoldRun]:
    import nibabel as nib

    runs = []
    for bold in sorted(Path(root).glob("sub-*/func/*_bold.nii*")):
        stem = bold.name.split("_bold")[0]
        func = bold.parent
        side = func / f"{stem}_bold.json"
        if side.exists() and "RepetitionTime" in json.loads(side.read_text()):
            tr, src = float(json.loads(side.read_text())["RepetitionTime"]), "sidecar"
        else:
            tr, src = float(nib.load(bold).header.get_zooms()[3]), "nifti_header"
        events = []
        ev = func / f"{stem}_events.tsv"
        if ev.exists():
            lines = ev.read_text().strip().splitlines()
            head = lines[0].split("\t")
            for line in lines[1:]:
                row = dict(zip(head, line.split("\t")))
                events.append({"onset": float(row["onset"]), "duration": float(row["duration"]),
                               "trial_type": row["trial_type"]})
        conf_path = func / f"{stem}_desc-confounds_timeseries.tsv"
        conf, names = None, []
        if conf_path.exists():
            lines = conf_path.read_text().strip().splitlines()
            head = lines[0].split("\t")
            names = [c for c in head if c in MOTION_COLUMNS]
            cols = [head.index(c) for c in names]
            conf = np.array([[float(line.split("\t")[c]) for c in cols] for line in lines[1:]])
        sub = stem.split("_")[0]
        masks = sorted(func.glob(f"{sub}_roi-*_mask.nii*"))
        runs.append(BoldRun(sub, bold, tr, src, events, conf, names, masks[0] if masks else None))
    return runs


def frame_times(n_vols: int, tr: float, slice_time_ref: float = 0.5) -> np.ndarray:
    return (np.arange(n_vols) + slice_time_ref) * tr


def _hrf_regressor(onsets, durations, ft: np.ndarray, tr: float, oversample: int = 16) -> np.ndarray:
    dt = tr / oversample
    hi_t = np.arange(0, ft[-1] + tr, dt)
    box = np.zeros_like(hi_t)
    for o, d in zip(onsets, durations):
        box[(hi_t >= o) & (hi_t < o + max(d, dt))] = 1.0
    conv = np.convolve(box, canonical_hrf(dt))[: hi_t.size]
    return np.interp(ft, hi_t, conv)


def cosine_drift(ft: np.ndarray, cutoff_s: float = 128.0) -> np.ndarray:
    n = ft.size
    order = int(np.floor(2 * (ft[-1] - ft[0]) / cutoff_s))
    k = np.arange(1, order + 1)
    return np.sqrt(2.0 / n) * np.cos(np.pi * (np.arange(n)[:, None] + 0.5) * k[None] / n) if order else np.empty((n, 0))


def design_matrix(run: BoldRun, n_vols: int, conditions: list[str] | None = None, trialwise: bool = False,
                  ) -> tuple[np.ndarray, list[str]]:
    ft = frame_times(n_vols, run.tr)
    conditions = conditions or sorted({e["trial_type"] for e in run.events})
    cols, names = [], []
    if trialwise:
        for k, e in enumerate(run.events):
            if e["trial_type"] in conditions:
                cols.append(_hrf_regressor([e["onset"]], [e["duration"]], ft, run.tr))
                names.append(f"trial{k:03d}_{e['trial_type']}")
    else:
        for c in conditions:
            ev = [e for e in run.events if e["trial_type"] == c]
            cols.append(_hrf_regressor([e["onset"] for e in ev], [e["duration"] for e in ev], ft, run.tr))
            names.append(c)
    if run.confounds is not None:
        conf = run.confounds[:n_vols] - run.confounds[:n_vols].mean(axis=0)
        cols.extend(conf.T)
        names.extend(run.confound_names)
    drift = cosine_drift(ft)
    cols.extend(drift.T)
    names.extend([f"drift{i}" for i in range(drift.shape[1])])
    cols.append(np.ones(n_vols))
    names.append("intercept")
    return np.column_stack(cols), names


def roi_timeseries(run: BoldRun, mask_path: Path | None = None) -> np.ndarray:
    import nibabel as nib

    img = nib.load(run.bold_path)
    mask_path = mask_path or run.mask_path
    if mask_path is None:
        raise ValueError(f"no ROI mask for {run.subject}")
    mask = np.asarray(nib.load(mask_path).get_fdata()) > 0
    data = np.asarray(img.get_fdata())
    if mask.shape != data.shape[:3]:
        raise ValueError("ROI mask grid does not match BOLD grid; resample in a validated pipeline first")
    ts = data[mask].T
    return (ts - ts.mean(axis=0)) / (ts.mean(axis=0) + 1e-9) * 100.0


def fit_glm(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    dof = x.shape[0] - np.linalg.matrix_rank(x)
    sigma2 = (resid ** 2).sum(axis=0) / max(dof, 1)
    xtx_inv = np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.outer(np.diag(xtx_inv), sigma2))
    return beta, beta / (se + 1e-12)


def trial_betas(run: BoldRun, conditions: list[str]) -> tuple[np.ndarray, list[str]]:
    y = roi_timeseries(run)
    x, names = design_matrix(run, y.shape[0], conditions, trialwise=True)
    beta, _ = fit_glm(y, x)
    idx = [i for i, n in enumerate(names) if n.startswith("trial")]
    labels = [names[i].split("_", 1)[1] for i in idx]
    return beta[idx], labels
