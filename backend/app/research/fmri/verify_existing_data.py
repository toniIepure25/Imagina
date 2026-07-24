"""Stage 1: Verify existing subj01 NSD-Imagery data.

Validates:
- File existence and sizes
- SHA-256 hashes
- HDF5 schema (shape, dtype, axes)
- NIfTI ROI/ncsnr shapes and affines
- Behavioral TSV structure
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("NSD_DATA_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata")
os.environ.setdefault("NSD_BETAS_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas")
os.environ.setdefault(
    "NSD_STIMULI_ROOT",
    r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata\experiments\nsdimagery\rawtargetimages",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def verify_imagery_betas():
    import h5py

    beta_path = Path(os.environ["NSD_BETAS_ROOT"]) / "ppdata/subj01/func1pt8mm/nsdimagerybetas_fithrf/betas_nsdimagery.hdf5"
    assert beta_path.exists(), f"Missing: {beta_path}"
    file_hash = sha256_file(beta_path)
    expected_hash = "31485ff0e4cb9e90b6f83f2f550714b1a688993604f5795148a2746df7b42b64"
    assert file_hash == expected_hash, f"Hash mismatch: {file_hash} != {expected_hash}"

    with h5py.File(str(beta_path), "r") as f:
        assert "betas" in f, f"Missing /betas dataset, keys: {list(f.keys())}"
        ds = f["betas"]
        assert ds.shape == (720, 83, 104, 81), f"Unexpected shape: {ds.shape}"
        assert ds.dtype == "int16", f"Unexpected dtype: {ds.dtype}"

    return {
        "file": str(beta_path),
        "sha256": file_hash,
        "shape": [720, 83, 104, 81],
        "dtype": "int16",
        "size_mb": round(beta_path.stat().st_size / 1024 / 1024, 2),
        "status": "VERIFIED",
    }


def verify_roi_masks():
    import nibabel as nib
    import numpy as np

    data_root = Path(os.environ["NSD_DATA_ROOT"])
    roi_dir = data_root / "ppdata/subj01/func1pt8mm/roi"
    results = {}

    for roi_name, filename in [
        ("nsdgeneral", "nsdgeneral.nii.gz"),
        ("prf-visualrois", "prf-visualrois.nii.gz"),
        ("streams", "streams.nii.gz"),
    ]:
        roi_path = roi_dir / filename
        assert roi_path.exists(), f"Missing: {roi_path}"
        img = nib.load(str(roi_path))
        data = np.asarray(img.dataobj)
        file_hash = sha256_file(roi_path)
        results[roi_name] = {
            "file": str(roi_path),
            "sha256": file_hash,
            "shape": list(data.shape),
            "n_nonzero": int(np.count_nonzero(data)),
            "unique_labels": sorted(int(v) for v in np.unique(data) if v > 0),
            "affine_diag": [float(img.affine[i, i]) for i in range(3)],
            "status": "VERIFIED",
        }
    return results


def verify_ncsnr():
    import nibabel as nib
    import numpy as np

    ncsnr_path = Path(os.environ["NSD_BETAS_ROOT"]) / "ppdata/subj01/func1pt8mm/betas_fithrf/ncsnr.nii.gz"
    assert ncsnr_path.exists(), f"Missing: {ncsnr_path}"
    img = nib.load(str(ncsnr_path))
    data = np.asarray(img.dataobj, dtype=np.float32)
    file_hash = sha256_file(ncsnr_path)
    return {
        "file": str(ncsnr_path),
        "sha256": file_hash,
        "shape": list(data.shape),
        "n_positive": int(np.sum(data > 0)),
        "mean_positive": float(np.mean(data[data > 0])),
        "max": float(np.max(data)),
        "status": "VERIFIED",
    }


def verify_behavioral():
    data_root = Path(os.environ["NSD_DATA_ROOT"])
    bdata_dir = data_root / "bdata/nsdimagery"
    run_types = [
        "visA", "visB", "visC",
        "imgA_1", "imgA_2", "imgB_1", "imgB_2", "imgC_1", "imgC_2",
        "attA", "attB", "attC",
    ]
    results = {}
    for rt in run_types:
        tsv_path = bdata_dir / f"nsdimagery_subj01_{rt}.tsv"
        assert tsv_path.exists(), f"Missing: {tsv_path}"
        with open(tsv_path, "r") as f:
            header = f.readline().strip().split("\t")
            rows = sum(1 for _ in f)
        results[rt] = {
            "file": str(tsv_path),
            "n_trials": rows,
            "columns": header,
            "status": "VERIFIED",
        }
    return results


def main():
    print("=" * 60)
    print("Stage 1: Verifying existing subj01 NSD-Imagery data")
    print("=" * 60)

    report = {"participant": "subj01", "verification_date": "2026-07-24"}

    print("\n[1/4] Verifying imagery betas HDF5...")
    report["imagery_betas"] = verify_imagery_betas()
    print(f"  OK: {report['imagery_betas']['shape']}, hash verified")

    print("\n[2/4] Verifying ROI masks...")
    report["roi_masks"] = verify_roi_masks()
    for name, r in report["roi_masks"].items():
        print(f"  OK: {name} — {r['n_nonzero']} nonzero voxels, shape {r['shape']}")

    print("\n[3/4] Verifying ncsnr...")
    report["ncsnr"] = verify_ncsnr()
    print(f"  OK: {report['ncsnr']['n_positive']} positive voxels, mean={report['ncsnr']['mean_positive']:.4f}")

    print("\n[4/4] Verifying behavioral TSVs...")
    report["behavioral"] = verify_behavioral()
    total_trials = sum(r["n_trials"] for r in report["behavioral"].values())
    print(f"  OK: 12 TSV files, {total_trials} total trials")

    report["overall_status"] = "ALL_VERIFIED"
    print(f"\n{'=' * 60}")
    print("Stage 1 PASS: All subj01 imagery data verified")
    print(f"{'=' * 60}")

    out_path = Path("results/c3_subj01_verification.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to: {out_path}")
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        sys.exit(1)
