"""C3XC acquisition/extraction for Mind Captioning (figshare 25808179 v2).

Streams each preprocessed testImagery_S*/testPerception_S*.mat (HDF5 v7.3),
MD5-verifies against the sealed inventory, records SHA-256, resolves the SEALED
localizer ROI voxel masks (VC primary; earlyVC/LVC/HVC secondary), extracts the
per-ROI (samples x voxels) matrices with content (video id), session, run labels,
then DELETES the .mat to reclaim disk. No geometry. No forbidden feature files.

Imagery content = imageryID; perception content = stimID. Independence unit =
Session (imagery: one trial per (session, video)).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

import h5py
import numpy as np

SUBS = [1, 2, 3, 4, 5, 6]


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


def _obj_strs(f, path):
    return ["".join(chr(c) for c in np.array(f[r]).flatten()) for r in f[path][:].flatten()]


def _roi_voxels(f, roiname, areas):
    """Voxel indices whose membership==1 in ANY localizer_r_{lh,rh}.<area> column."""
    want = set()
    for a in areas:
        want.add(f"localizer_r_lh.{a}")
        want.add(f"localizer_r_rh.{a}")
    cols = [i for i, nm in enumerate(roiname) if nm in want]
    if not cols:
        return np.array([], dtype=np.int64)
    ri = f["metainf/roiind_value"]
    mask = np.zeros(ri.shape[0], dtype=bool)
    for j in cols:
        mask |= (np.array(ri[:, j]) == 1)
    return np.where(mask)[0]


def extract_one(subj, cond, fid, md5, data_dir, out_dir, roi_sets, keep):
    dst = data_dir / f"{cond}_S{subj}.mat"
    status = _download(fid, md5, dst)
    sha = _sha256(dst)
    with h5py.File(str(dst), "r") as f:
        braindat = f["braindat"]  # (voxels, samples)
        nvox, nsamp = braindat.shape
        lt = _obj_strs(f, "metainf/label_type")
        Label = f["metainf/Label"][:]
        session = f["metainf/Session"][:].flatten().astype(np.int64)
        run = f["metainf/Run"][:].flatten().astype(np.int64)
        roiname = _obj_strs(f, "metainf/roiname")
        content_key = "imageryID" if cond == "testImagery" else "stimID"
        content = Label[lt.index(content_key)].astype(np.int64)
        sd = out_dir / f"S{subj}" / cond
        sd.mkdir(parents=True, exist_ok=True)
        roi_counts = {}
        X_full = None
        for rname, areas in roi_sets.items():
            vox = _roi_voxels(f, roiname, areas)
            roi_counts[rname] = int(len(vox))
            if len(vox):
                if X_full is None:
                    X_full = braindat[:, :]  # (voxels, samples) once
                np.save(sd / f"X_{rname}.npy", X_full[vox, :].T.astype(np.float32))  # (samples, voxels)
        np.save(sd / "content.npy", content)
        np.save(sd / "session.npy", session)
        np.save(sd / "run.npy", run)
        # behavioural (descriptive only)
        for beh in ("vividness", "accuracy"):
            if beh in lt:
                np.save(sd / f"{beh}.npy", Label[lt.index(beh)])
    if not keep:
        dst.unlink(missing_ok=True)
    return {"subject": f"S{subj}", "condition": cond, "file_id": fid, "supplied_md5": md5,
            "sha256": sha, "download": status, "n_samples": int(nsamp), "n_voxels_brain": int(nvox),
            "roi_voxel_counts": roi_counts, "content_key": content_key,
            "n_content": int(len(set(content.tolist()))), "n_sessions": int(len(set(session.tolist()))),
            "n_runs": int(len(set(run.tolist())))}


def main() -> None:
    seal = json.load(open(os.environ.get("C3XC_SEAL", "reports/c3xc/c3xc_protocol_seal.json")))
    inv = json.load(open(os.environ.get("C3XC_INVENTORY", "results/c3xc/c3xc_candidate_inventory.json")))
    data_dir = Path(os.environ["C3XC_DATA_DIR"])
    out_dir = Path(os.environ["C3XC_EXTRACT_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = os.environ.get("C3XC_KEEP_MAT", "0") == "1"
    subs = [int(s) for s in os.environ.get("C3XC_SUBJECTS", "1,2,3,4,5,6").split(",")]
    roi = seal["roi_contract"]
    roi_sets = {"VC": roi["VC_areas"], "earlyVC": roi["earlyVC_V1_areas"],
                "LVC": roi["LVC_areas"], "HVC": roi["HVC_areas"]}
    im = inv["files_used"]["imagery"]
    pe = inv["files_used"]["perception"]
    summary = {"artifact": "C3XC_EXTRACTION", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "subjects": {}}
    for s in subs:
        rec = {}
        rec["imagery"] = extract_one(s, "testImagery", im[f"testImagery_S{s}.mat"]["file_id"],
                                     im[f"testImagery_S{s}.mat"]["supplied_md5"], data_dir, out_dir, roi_sets, keep)
        pf = pe[f"testPerception_S{s}.mat"]
        rec["perception"] = extract_one(s, "testPerception", pf["file_id"], pf["supplied_md5"],
                                        data_dir, out_dir, roi_sets, keep)
        summary["subjects"][f"S{s}"] = rec
        print(f"[S{s}] imagery {rec['imagery']['n_samples']}x VC={rec['imagery']['roi_voxel_counts']['VC']} "
              f"cont={rec['imagery']['n_content']} sess={rec['imagery']['n_sessions']} | "
              f"perc {rec['perception']['n_samples']}x VC={rec['perception']['roi_voxel_counts']['VC']} "
              f"cont={rec['perception']['n_content']} runs={rec['perception']['n_runs']}", flush=True)
    json.dump(summary, open(out_dir / "c3xc_extraction_summary.json", "w"), indent=2)
    print(time.strftime("done %H:%M:%S"))


if __name__ == "__main__":
    main()
