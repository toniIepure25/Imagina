"""C3XB Phase 1 acquisition/extraction for GOD (figshare 7387130 v8).

Streams each per-subject bdpy .h5 (Imagery + ImageNetTest), MD5-verifies against the
sealed candidate inventory, records SHA-256, extracts the officially-released functional
ROI voxel matrices (VC primary; V1 V2 V3 V4 LOC FFA PPA secondary) with category / run /
run-pair / vividness labels, then DELETES the .h5 to reclaim disk. No geometry. No raw
neural data is written into the git tree (extraction target is an out-of-repo dir).

category  = integer (WNID) part of stimulus_number (vmap: 'n%08d_%d')
run-pair  = (run-1)//2  (imagery only; the balanced independent unit)
vividness = 'evaluation' column (imagery only; DESCRIPTIVE, never used to select trials)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np

ROIS = ["ROI_VC", "ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4", "ROI_LOC", "ROI_FFA", "ROI_PPA"]
SUBS = ["Subject1", "Subject2", "Subject3", "Subject4", "Subject5"]


def _md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _download(fid: int, md5: str, dst: Path) -> str:
    if dst.exists() and _md5(dst) == md5:
        return "reused"
    part = dst.with_suffix(".part")
    urllib.request.urlretrieve(f"https://ndownloader.figshare.com/files/{fid}", part)
    got = _md5(part)
    if got != md5:
        raise RuntimeError(f"MD5 mismatch {dst.name}: {got} != {md5}")
    part.replace(dst)
    return "downloaded"


def _parse(path: str):
    import h5py
    with h5py.File(path, "r") as f:
        D = f["dataset"][:]
        keys = [k.decode() if isinstance(k, bytes) else k for k in f["metadata/key"][:]]
        val = f["metadata/value"][:]
    kv = {k: np.asarray(val[i], dtype=float) for i, k in enumerate(keys)}

    def col(name):
        c = np.where(kv[name] == 1)[0]
        return int(c[0])

    roi_cols = {r: np.where(kv[r] == 1)[0] for r in ROIS if r in kv}
    stim = D[:, col("stimulus_number")]
    category = np.floor(stim).astype(np.int64)
    run = D[:, col("Run")].astype(np.int64)
    evaluation = D[:, col("evaluation")] if "evaluation" in kv else None
    trial_type = D[:, col("trial_type")].astype(np.int64) if "trial_type" in kv else None
    return D, roi_cols, category, run, evaluation, trial_type, stim


def extract_one(subj: str, cond: str, fid: int, md5: str, data_dir: Path, out_dir: Path,
                keep_h5: bool) -> dict:
    dst = data_dir / f"{subj}_{cond}.h5"
    status = _download(fid, md5, dst)
    sha = _sha256(dst)
    D, roi_cols, category, run, evaluation, trial_type, stim = _parse(str(dst))
    sd = out_dir / subj / cond
    sd.mkdir(parents=True, exist_ok=True)
    roi_counts = {}
    for r in ROIS:
        if r in roi_cols:
            np.save(sd / f"{r}.npy", D[:, roi_cols[r]].astype(np.float32))
            roi_counts[r] = int(len(roi_cols[r]))
    np.save(sd / "category.npy", category)
    np.save(sd / "run.npy", run)
    if cond == "Imagery":
        np.save(sd / "pair.npy", ((run - 1) // 2).astype(np.int64))
        if evaluation is not None:
            np.save(sd / "vividness.npy", evaluation)
    uc, cnt = np.unique(category, return_counts=True)
    finite = bool(np.isfinite(D[:, roi_cols["ROI_VC"]]).all())
    meta = {"subject": subj, "condition": cond, "figshare_file_id": fid, "supplied_md5": md5,
            "sha256": sha, "download": status, "n_samples": int(D.shape[0]),
            "n_categories": int(len(uc)), "reps_min": int(cnt.min()), "reps_max": int(cnt.max()),
            "n_runs": int(len(set(run.tolist()))), "roi_voxel_counts": roi_counts,
            "vc_all_finite": finite,
            "trial_type_values": (sorted(set(trial_type.tolist())) if trial_type is not None else None)}
    if keep_h5 is False:
        dst.unlink(missing_ok=True)
    return meta


def main() -> None:
    inv = json.load(open(os.environ.get("C3XB_INVENTORY",
                    "results/c3xb/c3xb_candidate_inventory.json")))
    data_dir = Path(os.environ["C3XB_DATA_DIR"])
    out_dir = Path(os.environ["C3XB_EXTRACT_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = os.environ.get("C3XB_KEEP_H5", "0") == "1"
    subs = os.environ.get("C3XB_SUBJECTS", ",".join(SUBS)).split(",")

    imag = inv["files_to_use"]["imagery"]
    perc = inv["files_to_use"]["category_matched_perception"]
    summary = {"artifact": "C3XB_GOD_EXTRACTION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "figshare_version": inv["primary_candidate"]["figshare"]["selected_version"],
               "subjects": {}}
    for subj in subs:
        rec = {}
        rec["Imagery"] = extract_one(subj, "Imagery", imag[f"{subj}_Imagery.h5"]["file_id"],
                                     imag[f"{subj}_Imagery.h5"]["supplied_md5"], data_dir, out_dir, keep)
        rec["ImageNetTest"] = extract_one(subj, "ImageNetTest",
                                          perc[f"{subj}_ImageNetTest.h5"]["file_id"],
                                          perc[f"{subj}_ImageNetTest.h5"]["supplied_md5"],
                                          data_dir, out_dir, keep)
        summary["subjects"][subj] = rec
        print(f"[{subj}] imagery {rec['Imagery']['n_samples']}x"
              f"{rec['Imagery']['roi_voxel_counts'].get('ROI_VC')}VC "
              f"cats={rec['Imagery']['n_categories']} runs={rec['Imagery']['n_runs']} | "
              f"test {rec['ImageNetTest']['n_samples']}x"
              f"{rec['ImageNetTest']['roi_voxel_counts'].get('ROI_VC')}VC "
              f"cats={rec['ImageNetTest']['n_categories']} runs={rec['ImageNetTest']['n_runs']}",
              flush=True)
    json.dump(summary, open(out_dir / "god_extraction_summary.json", "w"), indent=2)
    print(time.strftime("done %H:%M:%S"))


if __name__ == "__main__":
    main()
