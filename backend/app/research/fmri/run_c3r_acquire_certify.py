"""C3R Phase 1-2 — acquire (imagery only) and certify subj02/05/07.

Downloads, per subject, only what the reliability screen needs (NO core-NSD
perception betas): betas_nsdimagery.hdf5, perception ncsnr.nii.gz, and the
nsdgeneral / prf-visualrois / streams ROI masks. Each object is fetched to a
.part file, atomically renamed, SHA-256 certified, and (for the HDF5) opened and
shape/dtype-checked. Then the per-subject nsdgeneral AND ncsnr>0 voxel selection
is built (identical policy to C3), and the Set-B VISION (48) and IMAGERY (96)
matrices are extracted at those voxels using the certified, subject-independent
row mapping. Emits results/c3r/c3r_certify_<subj>.json and the state matrices.

No raw neural data is committed to git. No geometry is computed here.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

import numpy as np

S3 = "https://natural-scenes-dataset.s3.amazonaws.com"
ROW = {"visB": (192, 240), "imgB_1": (336, 384), "imgB_2": (624, 672)}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dst: Path, expected_bytes: int | None = None) -> dict:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and (expected_bytes is None or dst.stat().st_size == expected_bytes):
        return {"reused": True, "bytes": dst.stat().st_size, "sha256": _sha256(dst)}
    part = dst.with_suffix(dst.suffix + ".part")
    urllib.request.urlretrieve(url, part)
    size = part.stat().st_size
    if expected_bytes is not None and size != expected_bytes:
        raise RuntimeError(f"size mismatch {url}: got {size} expected {expected_bytes}")
    part.replace(dst)
    return {"reused": False, "bytes": size, "sha256": _sha256(dst)}


def _roi_labels_at(coords, nii_path, nib):
    A = nib.load(str(nii_path)).get_fdata()
    return np.array([int(round(A[k, j, i])) for (i, j, k) in coords.tolist()], dtype=np.int64)


def certify_subject(subj: str, data_root: Path, content_visB, content_imgB, out_dir: Path) -> dict:
    import h5py
    import nibabel as nib

    inv = {
        "betas": (f"nsddata_betas/ppdata/{subj}/func1pt8mm/nsdimagerybetas_fithrf/betas_nsdimagery.hdf5",
                  data_root / subj / "betas_nsdimagery.hdf5"),
        "ncsnr": (f"nsddata_betas/ppdata/{subj}/func1pt8mm/betas_fithrf/ncsnr.nii.gz",
                  data_root / subj / "ncsnr.nii.gz"),
        "nsdgeneral": (f"nsddata/ppdata/{subj}/func1pt8mm/roi/nsdgeneral.nii.gz",
                       data_root / subj / "nsdgeneral.nii.gz"),
        "prf": (f"nsddata/ppdata/{subj}/func1pt8mm/roi/prf-visualrois.nii.gz",
                data_root / subj / "prf-visualrois.nii.gz"),
        "streams": (f"nsddata/ppdata/{subj}/func1pt8mm/roi/streams.nii.gz",
                    data_root / subj / "streams.nii.gz"),
    }
    dl = {}
    for key, (rel, dst) in inv.items():
        dl[key] = _download(f"{S3}/{rel}", dst)
        dl[key]["remote_rel"] = rel

    # ROI + ncsnr, build selection in hdf5 frame via transpose(2,1,0)
    M = nib.load(str(inv["nsdgeneral"][1])).get_fdata()
    N = nib.load(str(inv["ncsnr"][1])).get_fdata()
    assert M.shape == N.shape, (M.shape, N.shape)
    # NSD func1pt8mm volume dims are SUBJECT-SPECIFIC; the betas hdf5 is the nii
    # transposed (2,1,0). Derive dims per subject rather than hardcoding subj01.
    Mh = np.transpose(M, (2, 1, 0))
    Nh = np.transpose(N, (2, 1, 0))
    vol_shape = Mh.shape
    sel = (Mh > 0) & (Nh > 0)
    coords = np.argwhere(sel)
    V = int(coords.shape[0])
    nsdgeneral_count = int((Mh > 0).sum())

    # HDF5 open + shape/dtype certification (720 imagery betas x subject volume)
    with h5py.File(str(inv["betas"][1]), "r") as hf:
        ds = hf["betas"]
        shape = tuple(int(x) for x in ds.shape)
        dtype = str(ds.dtype)
        assert shape == (720,) + vol_shape, (shape, vol_shape)
        assert dtype == "int16", dtype
        ii, jj, kk = coords[:, 0], coords[:, 1], coords[:, 2]

        def extract(rng_pairs):
            rows = []
            for a, b in rng_pairs:
                rows.extend(range(a, b))
            rows = np.array(rows)
            out = np.empty((len(rows), V), dtype=np.float32)
            for vi in range(V):
                col = ds[:, ii[vi], jj[vi], kk[vi]]
                out[:, vi] = col[rows].astype(np.float32)
            return out, rows

        Xv, rows_v = extract([ROW["visB"]])
        Xi, rows_i = extract([ROW["imgB_1"], ROW["imgB_2"]])

    assert Xv.shape == (48, V) and Xi.shape == (96, V), (Xv.shape, Xi.shape)
    finite = bool(np.isfinite(Xv).all() and np.isfinite(Xi).all())
    assert len(content_visB) == 48 and len(content_imgB) == 96

    # ROI labels (secondary)
    prf = _roi_labels_at(coords, inv["prf"][1], nib)
    streams = _roi_labels_at(coords, inv["streams"][1], nib)

    (out_dir / subj).mkdir(parents=True, exist_ok=True)
    np.save(out_dir / subj / "setB_vision.npy", Xv)
    np.save(out_dir / subj / "setB_imagery.npy", Xi)
    np.save(out_dir / subj / "prf_labels.npy", prf)
    np.save(out_dir / subj / "streams_labels.npy", streams)
    np.save(out_dir / subj / "coords.npy", coords)

    roi_counts = {
        "prf": {"V1": int(np.isin(prf, [1, 2]).sum()), "V2": int(np.isin(prf, [3, 4]).sum()),
                "V3": int(np.isin(prf, [5, 6]).sum()), "hV4": int((prf == 7).sum())},
        "streams": {"ventral": int(np.isin(streams, [2, 5]).sum()),
                    "lateral": int(np.isin(streams, [3, 6]).sum()),
                    "parietal": int(np.isin(streams, [4, 7]).sum())},
    }
    cert = {
        "subject": subj, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "downloads": {k: {kk: vv for kk, vv in v.items()} for k, v in dl.items()},
        "beta_shape": list(shape), "beta_dtype": dtype, "orientation_transpose": "(2,1,0)",
        "nsdgeneral_count": nsdgeneral_count, "selected_voxel_count_nsdgeneral_and_ncsnr_gt0": V,
        "row_mapping": {k: list(v) for k, v in ROW.items()},
        "setB_vision_shape": list(Xv.shape), "setB_imagery_shape": list(Xi.shape),
        "vision_rows": rows_v.tolist()[:3] + ["..."], "imagery_rows": rows_i.tolist()[:3] + ["..."],
        "all_finite": finite, "roi_counts": roi_counts,
        "state_matrix_sha256": {"setB_vision": hashlib.sha256(Xv.tobytes()).hexdigest(),
                                "setB_imagery": hashlib.sha256(Xi.tobytes()).hexdigest()},
        "volume_shape": list(vol_shape),
        "contract_ok": bool(shape == (720,) + vol_shape and dtype == "int16"
                            and Xv.shape == (48, V) and Xi.shape == (96, V) and finite),
    }
    cert["status"] = "CERTIFIED" if cert["contract_ok"] else "BLOCKED_PARTICIPANT_DATA_CONTRACT"
    cert["self_hash"] = hashlib.sha256(json.dumps(cert, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(cert, open(out_dir / f"c3r_certify_{subj}.json", "w"), indent=2)
    return cert


def main() -> None:
    data_root = Path(os.environ["C3R_DATA_ROOT"])
    out_dir = Path(os.environ["C3R_OUT_DIR"])
    manifest = json.load(open(os.environ["C3M_EVENT_MANIFEST"]))["rows"]
    cvis = [r["candidate_pool_index"] for r in sorted(
        (r for r in manifest if r["event_type"] == "vision" and r["stimulus_set"] == "B"),
        key=lambda r: r["beta_row_index"])]
    cimg = [r["candidate_pool_index"] for r in sorted(
        (r for r in manifest if r["event_type"] == "imagery" and r["stimulus_set"] == "B"),
        key=lambda r: r["beta_row_index"])]
    np.save(out_dir / "content_visB.npy", np.array(cvis))
    np.save(out_dir / "content_imgB.npy", np.array(cimg))

    subjects = os.environ.get("C3R_SUBJECTS", "subj02,subj05,subj07").split(",")
    summary = {}
    for s in subjects:
        c = certify_subject(s, data_root, cvis, cimg, out_dir)
        summary[s] = {"status": c["status"], "V": c["selected_voxel_count_nsdgeneral_and_ncsnr_gt0"],
                      "beta_sha256": c["downloads"]["betas"]["sha256"][:16]}
        print(f"[{s}] {c['status']} V={c['selected_voxel_count_nsdgeneral_and_ncsnr_gt0']} "
              f"betas_sha={c['downloads']['betas']['sha256'][:16]} finite={c['all_finite']}")
    json.dump(summary, open(out_dir / "c3r_certify_summary.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3r_certify_summary.json")


if __name__ == "__main__":
    main()
