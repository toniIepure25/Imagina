"""C3X Phase 3 — acquire and certify the minimal D1 (ds001506) reliability subset.

Downloads the KamitaniLab figshare preprocessed VC bdpy files (imagery +
perceptionNaturalImageTest for sub-01/02/03), MD5-verifies, parses the bdpy
structure (VoxelData / ROI_* flags, Label = content, Run = acquisition run),
extracts the VC voxel matrices with content and run labels for both conditions,
and certifies the trial contract. Emits the trial manifest and
perception/imagery correspondence. No geometry is computed.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np

FILES = {  # figshare file id, expected md5
    "sub-01_imagery": (22713854, "d1a9634e220ff5e836348374d812c636"),
    "sub-02_imagery": (22713863, "b558e779770e036e52948191f4886116"),
    "sub-03_imagery": (22713953, "5b05fb8e3a388dd821915d02a15ea7d9"),
    "sub-01_perceptionTest": (14830631, "ee503598904a4d50a7df7be0880aaadf"),
    "sub-02_perceptionTest": (14830697, "3767c08b4b138d3114ec69cfaa8274ab"),
    "sub-03_perceptionTest": (14830856, "ffcd06aa419b1f9fbce65709a742a368"),
}
ROIS = ["ROI_VC", "ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4"]


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


def parse_bdpy(path: Path):
    """Return (dataset, keys, value) and the column index maps."""
    import h5py
    with h5py.File(str(path), "r") as f:
        ds = f["dataset"][:]
        keys = [k.decode() if isinstance(k, bytes) else k for k in f["metadata/key"][:]]
        val = f["metadata/value"][:]
    kv = {k: val[i] for i, k in enumerate(keys)}
    voxel_cols = np.where(kv["VoxelData"] == 1)[0]
    run_col = int(np.where(kv["Run"] == 1)[0][0])
    label_col = int(np.where(kv["Label"] == 1)[0][0])
    roi_cols = {r: np.where(kv[r] == 1)[0] for r in ROIS if r in kv}
    content = ds[:, label_col].astype(np.int64)
    run = ds[:, run_col].astype(np.int64)
    return ds, voxel_cols, roi_cols, content, run


def certify_subject(subj: str, data_dir: Path, out_dir: Path) -> dict:
    cond = {}
    for role in ("imagery", "perceptionTest"):
        key = f"{subj}_{role}"
        fid, md5 = FILES[key]
        dst = data_dir / f"{key}.h5"
        status = _download(fid, md5, dst)
        ds, voxel_cols, roi_cols, content, run = parse_bdpy(dst)
        vc = roi_cols["ROI_VC"]
        Xvc = ds[:, vc].astype(np.float32)
        (out_dir / subj).mkdir(parents=True, exist_ok=True)
        np.save(out_dir / subj / f"{role}_VC.npy", Xvc)
        np.save(out_dir / subj / f"{role}_content.npy", content)
        np.save(out_dir / subj / f"{role}_run.npy", run)
        # secondary ROI membership (index into VC-column order) for V1-V4
        vc_set = {int(c): i for i, c in enumerate(vc)}
        roi_in_vc = {}
        for r in ("ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4"):
            if r in roi_cols:
                idx = [vc_set[int(c)] for c in roi_cols[r] if int(c) in vc_set]
                roi_in_vc[r] = idx
                np.save(out_dir / subj / f"{role}_{r}_idx.npy", np.array(idx, dtype=np.int64))
        uc, counts = np.unique(content, return_counts=True)
        cond[role] = {
            "file_md5": md5, "file_sha256": _sha256(dst), "download": status,
            "n_samples": int(ds.shape[0]), "n_VC_voxels": int(len(vc)),
            "n_content": int(len(uc)), "reps_per_content_min": int(counts.min()),
            "reps_per_content_max": int(counts.max()), "reps_per_content_median": int(np.median(counts)),
            "n_runs": int(len(set(run.tolist()))),
            "roi_voxel_counts": {r: int(len(v)) for r, v in roi_cols.items()},
            "all_finite": bool(np.isfinite(Xvc).all()),
            "content_ids_sample": uc[:8].tolist(),
        }
    # correspondence (category/image identity shared across conditions)
    ci = set(np.load(out_dir / subj / "imagery_content.npy").tolist())
    cp = set(np.load(out_dir / subj / "perceptionTest_content.npy").tolist())
    cond["correspondence"] = {
        "imagery_contents": len(ci), "perception_contents": len(cp),
        "shared_contents": len(ci & cp), "imagery_only": len(ci - cp), "perception_only": len(cp - ci),
        "level": "category/image identity (bdpy Label); exact-image vs category to be treated per "
                 "dataset docs; C3X reliability is WITHIN-condition and does not require the mapping",
    }
    cond["subject"] = subj
    cond["contract_ok"] = bool(
        cond["imagery"]["n_content"] >= 5 and cond["imagery"]["n_runs"] >= 2
        and cond["imagery"]["all_finite"] and cond["perceptionTest"]["all_finite"])
    cond["status"] = "CERTIFIED" if cond["contract_ok"] else "BLOCKED_PARTICIPANT_DATA_CONTRACT"
    cond["self_hash"] = hashlib.sha256(json.dumps(cond, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(cond, open(out_dir / f"d1_certify_{subj}.json", "w"), indent=2)
    return cond


def main() -> None:
    data_dir = Path(os.environ["C3X_DATA_DIR"])
    out_dir = Path(os.environ["C3X_OUT_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    subs = os.environ.get("C3X_SUBJECTS", "sub-01,sub-02,sub-03").split(",")
    summary = {}
    manifest = {"artifact": "C3X_D1_TRIAL_MANIFEST", "dataset": "ds001506",
                "figshare_doi": "10.6084/m9.figshare.7033577.v16",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "subjects": {}}
    corr = {"artifact": "C3X_D1_PERCEPTION_IMAGERY_CORRESPONDENCE", "subjects": {}}
    for s in subs:
        c = certify_subject(s, data_dir, out_dir)
        summary[s] = {"status": c["status"],
                      "imagery": {k: c["imagery"][k] for k in ("n_samples", "n_content",
                                  "reps_per_content_median", "n_runs", "n_VC_voxels")},
                      "perceptionTest": {k: c["perceptionTest"][k] for k in ("n_samples", "n_content",
                                         "reps_per_content_median", "n_runs", "n_VC_voxels")}}
        manifest["subjects"][s] = {"imagery": c["imagery"], "perceptionTest": c["perceptionTest"]}
        corr["subjects"][s] = c["correspondence"]
        print(f"[{s}] {c['status']} | imagery: {c['imagery']['n_content']} contents x "
              f"~{c['imagery']['reps_per_content_median']} reps, {c['imagery']['n_runs']} runs, "
              f"VC={c['imagery']['n_VC_voxels']} | percTest: {c['perceptionTest']['n_content']} contents "
              f"x ~{c['perceptionTest']['reps_per_content_median']} reps, {c['perceptionTest']['n_runs']} runs")
    json.dump(manifest, open(out_dir / "d1_trial_manifest.json", "w"), indent=2)
    json.dump(corr, open(out_dir / "d1_perception_imagery_correspondence.json", "w"), indent=2)
    json.dump(summary, open(out_dir / "d1_certify_summary.json", "w"), indent=2)
    print(f"Wrote {out_dir}/d1_trial_manifest.json")


if __name__ == "__main__":
    main()
