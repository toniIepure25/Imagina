"""Writers for SYNTHETIC test fixtures in standard research formats (EDF, SNIRF, FIF, BIDS/NIfTI).

Files written here are labeled synthetic in their headers/sidecars and must never be mixed with real data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.multimodal.acquisition import synthetic_signals as ss

SYNTHETIC_LABEL = "IMAGINA-SYNTHETIC"


def write_edf(path: Path, data: np.ndarray, fs: int, labels: list[str], units: list[str],
              record_s: int = 1) -> Path:
    """Minimal EDF (16-bit) writer. ``data`` is (n_samples, n_channels)."""
    n, ns = data.shape
    spr = fs * record_s
    n_rec = n // spr
    data = data[: n_rec * spr]
    pmin = data.min(axis=0) - 1e-6
    pmax = data.max(axis=0) + 1e-6
    dmin, dmax = -32768, 32767
    digital = np.round((data - pmin) / (pmax - pmin) * (dmax - dmin) + dmin).astype("<i2")

    def f(v, w):
        s = str(v)[:w]
        return s.ljust(w).encode("ascii")

    hdr = b"".join([
        f("0", 8), f(f"X X X {SYNTHETIC_LABEL}", 80), f(f"Startdate X X X {SYNTHETIC_LABEL}", 80),
        f("01.01.26", 8), f("00.00.00", 8), f(256 + 256 * ns, 8), f("", 44), f(n_rec, 8), f(record_s, 8), f(ns, 4),
    ])
    for field, width in [
        (labels, 16), (["synthetic"] * ns, 80), (units, 8), ([f"{v:.4f}" for v in pmin], 8),
        ([f"{v:.4f}" for v in pmax], 8), ([dmin] * ns, 8), ([dmax] * ns, 8), ([""] * ns, 80), ([spr] * ns, 8),
        ([""] * ns, 32),
    ]:
        hdr += b"".join(f(v, width) for v in field)
    body = b"".join(digital[r * spr:(r + 1) * spr].T.tobytes() for r in range(n_rec))
    path.write_bytes(hdr + body)
    return path


def write_snirf(path: Path, intensities: np.ndarray, fs: float, layout: list[dict]) -> Path:
    import h5py

    wavelengths = sorted({c["wavelength_nm"] for c in layout})
    src_pos, det_pos = {}, {}
    for c in layout:
        s_idx = int(c["pair"].split("_")[0][1:])
        d_idx = int(c["pair"].split("_")[1][1:])
        src_pos[s_idx] = c["source_position_m"]
        det_pos[d_idx] = c["detector_position_m"]
    vs = h5py.string_dtype()
    with h5py.File(path, "w") as h:
        h.create_dataset("formatVersion", data="1.0", dtype=vs)
        nirs = h.create_group("nirs")
        meta = nirs.create_group("metaDataTags")
        for k, v in {"SubjectID": SYNTHETIC_LABEL, "MeasurementDate": "2026-01-01", "MeasurementTime": "00:00:00Z",
                     "LengthUnit": "m", "TimeUnit": "s", "FrequencyUnit": "Hz"}.items():
            meta.create_dataset(k, data=v, dtype=vs)
        d1 = nirs.create_group("data1")
        d1.create_dataset("dataTimeSeries", data=intensities)
        d1.create_dataset("time", data=np.arange(intensities.shape[0]) / fs)
        for k, c in enumerate(layout, start=1):
            ml = d1.create_group(f"measurementList{k}")
            ml.create_dataset("sourceIndex", data=int(c["pair"].split("_")[0][1:]))
            ml.create_dataset("detectorIndex", data=int(c["pair"].split("_")[1][1:]))
            ml.create_dataset("wavelengthIndex", data=wavelengths.index(c["wavelength_nm"]) + 1)
            ml.create_dataset("dataType", data=1)
            ml.create_dataset("dataTypeIndex", data=1)
        probe = nirs.create_group("probe")
        probe.create_dataset("wavelengths", data=np.array(wavelengths, dtype=float))
        probe.create_dataset("sourcePos3D", data=np.array([src_pos[i] for i in sorted(src_pos)]))
        probe.create_dataset("detectorPos3D", data=np.array([det_pos[i] for i in sorted(det_pos)]))
        probe.create_dataset("sourceLabels", data=[f"S{i}" for i in sorted(src_pos)], dtype=vs)
        probe.create_dataset("detectorLabels", data=[f"D{i}" for i in sorted(det_pos)], dtype=vs)
    return path


def write_meg_fif(path: Path, seed: int = 0, n_channels: int = 24, fs: float = 200.0,
                  n_trials_per_class: int = 30) -> tuple[Path, dict]:
    """SYNTHETIC magnetometer recording with perception/imagery events whose topographies differ."""
    import mne

    rng = np.random.default_rng(seed)
    iti = 2.0
    n_trials = 2 * n_trials_per_class
    n = int((n_trials * iti + 2.0) * fs)
    t = np.arange(n) / fs
    data = rng.normal(0, 200e-15, (n_channels, n))
    topo = {1: rng.normal(0, 1, n_channels), 2: rng.normal(0, 1, n_channels)}
    labels = np.array([1, 2] * n_trials_per_class)
    rng.shuffle(labels)
    events = []
    for k, lab in enumerate(labels):
        onset = int((1.0 + k * iti) * fs)
        events.append([onset, 0, int(lab)])
        lat = t[: int(0.8 * fs)]
        wave = np.exp(-0.5 * ((lat - 0.3) / 0.06) ** 2) * 150e-15
        data[:, onset:onset + lat.size] += np.outer(topo[int(lab)], wave)
    stim = np.zeros((1, n))
    for onset, _, lab in events:
        stim[0, onset] = lab
    info = mne.create_info([f"MAG{i:03d}" for i in range(n_channels)] + ["STI014"], fs,
                           ["mag"] * n_channels + ["stim"])
    info["description"] = SYNTHETIC_LABEL
    raw = mne.io.RawArray(np.vstack([data, stim]), info, verbose="error")
    raw.save(path, overwrite=True, verbose="error")
    return path, {"event_id": {"perception": 1, "imagery": 2}, "n_trials": n_trials}


def write_bids_fmri(root: Path, seed: int = 0, n_subjects: int = 2, n_vols: int = 120, tr: float = 2.0,
                    shape: tuple[int, int, int] = (8, 8, 6)) -> dict:
    """SYNTHETIC BIDS-like dataset: bold NIfTI, events, motion confounds and an ROI mask per subject."""
    import nibabel as nib

    root.mkdir(parents=True, exist_ok=True)
    (root / "dataset_description.json").write_text(json.dumps({
        "Name": SYNTHETIC_LABEL, "BIDSVersion": "1.8.0", "DatasetType": "raw",
        "GeneratedBy": [{"Name": "imagina.multimodal.fixtures", "Description": "synthetic test fixture"}]}))
    rng = np.random.default_rng(seed)
    hrf = ss.canonical_hrf(tr)
    roi = np.zeros(shape, dtype=np.uint8)
    roi[2:6, 2:6, 1:4] = 1
    n_roi = int(roi.sum())
    pattern = {"perception": rng.normal(0, 1, n_roi), "imagery": rng.normal(0, 1, n_roi)}
    out = {"subjects": []}
    for s in range(1, n_subjects + 1):
        sub = f"sub-{s:02d}"
        func = root / sub / "func"
        func.mkdir(parents=True, exist_ok=True)
        events, t = [], 10.0
        conds = ["perception", "imagery", "rest"]
        while t < n_vols * tr - 20:
            cond = conds[len(events) % 3]
            events.append((t, 8.0, cond))
            t += 14.0 + float(rng.uniform(0, 4))
        frame_t = np.arange(n_vols) * tr
        bold = 1000.0 + rng.normal(0, 5.0, shape + (n_vols,))
        motion = np.cumsum(rng.normal(0, 0.02, (n_vols, 6)), axis=0)
        for onset, dur, cond in events:
            if cond == "rest":
                continue
            box = ((frame_t >= onset) & (frame_t < onset + dur)).astype(float)
            reg = np.convolve(box, hrf)[:n_vols]
            subj_pattern = pattern[cond] + rng.normal(0, 0.3, n_roi)
            bold[roi.astype(bool)] += 8.0 * np.outer(subj_pattern, reg)
        bold += 20.0 * motion[:, 0][None, None, None, :]
        stem = f"{sub}_task-imagery_run-1"
        affine = np.diag([3.0, 3.0, 3.0, 1.0])
        img = nib.Nifti1Image(bold.astype(np.float32), affine)
        img.header.set_xyzt_units("mm", "sec")
        img.header["pixdim"][4] = tr
        nib.save(img, func / f"{stem}_bold.nii.gz")
        (func / f"{stem}_bold.json").write_text(json.dumps({"RepetitionTime": tr, "TaskName": "imagery",
                                                            "Note": SYNTHETIC_LABEL}))
        with open(func / f"{stem}_events.tsv", "w") as fh:
            fh.write("onset\tduration\ttrial_type\n")
            for onset, dur, cond in events:
                fh.write(f"{onset:.3f}\t{dur:.3f}\t{cond}\n")
        with open(func / f"{stem}_desc-confounds_timeseries.tsv", "w") as fh:
            names = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
            fh.write("\t".join(names) + "\n")
            for row in motion:
                fh.write("\t".join(f"{v:.6f}" for v in row) + "\n")
        nib.save(nib.Nifti1Image(roi, affine), func / f"{sub}_roi-visual_mask.nii.gz")
        out["subjects"].append(sub)
    out["created"] = datetime.now(timezone.utc).isoformat()
    return out
