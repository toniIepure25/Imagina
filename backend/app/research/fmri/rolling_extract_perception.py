"""Rolling extraction of core-NSD perception betas (betas_fithrf) into the
frozen decoder's exact 15587-voxel order, to build the perception reference X_p
in the SAME beta pipeline as the imagery betas (fithrf) and the C3 decoder.

For each requested session: download betas_sessionSS.hdf5 from the NSD public
S3, SHA-256 it, extract [n_trials, 15587] float32 at the decoder's beta_coords
(chunk-aware read), persist the ROI matrix + provenance, then delete the raw
volume (re-downloadable). nsdId/session labels come from the acquisition-ordered
trial_meta design (version-independent).

This is the mission-prescribed acquisition path after the FMRI2images
pre-extracted features were REJECTED by certification (a ~2% systematic
per-voxel beta-version difference; see results/c3m_xp_certification.json).
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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def extract_session(ds, coords: np.ndarray, block: int = 100) -> np.ndarray:
    """Read [n_trials, V] at coords (i,j,k) in beta_coords order, chunk-aware."""
    n = ds.shape[0]
    ii, jj, kk = coords[:, 0], coords[:, 1], coords[:, 2]
    chunks = ds.chunks
    out = np.empty((n, coords.shape[0]), dtype=np.float32)
    if chunks is not None and chunks[0] == 1:
        # per-trial chunked: block reads are chunk-aligned
        for a in range(0, n, block):
            b = min(a + block, n)
            vol = ds[a:b]  # [blk,83,104,81]
            out[a:b] = vol[:, ii, jj, kk].astype(np.float32)
    else:
        # per-voxel chunked (or unknown): read per-voxel across all trials
        for v in range(coords.shape[0]):
            out[:, v] = ds[:, ii[v], jj[v], kk[v]].astype(np.float32)
    return out


def main() -> None:
    import h5py
    import pandas as pd

    subject = os.environ.get("SUBJECT", "subj01")
    sessions = [int(s) for s in os.environ["SESSIONS"].split(",")]
    decoder_path = Path(os.environ["C3M_DECODER"])
    meta_path = Path(os.environ["FMRI2I_META"])
    raw_dir = Path(os.environ["RAW_TMP_DIR"])
    out_dir = Path(os.environ["XP_OUT_DIR"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    keep_raw = os.environ.get("KEEP_RAW", "0") == "1"

    import pickle
    frozen = pickle.load(open(decoder_path, "rb"))
    coords = np.asarray(frozen["beta_coords"])
    tm = pd.read_parquet(meta_path)
    nsd_all = tm["nsdId"].to_numpy()

    prov = {"artifact": "C3M_PERCEPTION_ROLLING_EXTRACTION", "subject": subject,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "beta_version": "betas_fithrf", "n_voxels": int(coords.shape[0]),
            "sessions": {}}
    for s in sessions:
        url = (f"{S3}/nsddata_betas/ppdata/{subject}/func1pt8mm/betas_fithrf/"
               f"betas_session{s:02d}.hdf5")
        raw = raw_dir / f"betas_session{s:02d}.hdf5"
        out = out_dir / f"xp_{subject}_session{s:02d}.npy"
        if out.exists():
            print(f"session {s:02d}: already extracted, skipping")
            continue
        t0 = time.time()
        print(f"session {s:02d}: downloading ...", flush=True)
        urllib.request.urlretrieve(url, raw)
        sha = _sha256_file(raw)
        with h5py.File(str(raw), "r") as hf:
            ds = hf["betas"]
            shape = tuple(int(x) for x in ds.shape)
            X = extract_session(ds, coords)
        np.save(out, X)
        # attach nsdId labels for this session's 750 trials (acquisition order)
        nsd_sess = nsd_all[(s - 1) * X.shape[0]:s * X.shape[0]]
        np.save(out_dir / f"xp_{subject}_session{s:02d}_nsdid.npy", nsd_sess.astype(np.int64))
        if not keep_raw:
            raw.unlink()
        prov["sessions"][str(s)] = {
            "url": url, "raw_sha256": sha, "raw_shape": shape,
            "extracted_shape": [int(X.shape[0]), int(X.shape[1])],
            "roi_matrix": str(out), "seconds": round(time.time() - t0, 1),
            "raw_deleted": (not keep_raw),
        }
        print(f"session {s:02d}: extracted {X.shape} sha={sha[:16]} "
              f"in {prov['sessions'][str(s)]['seconds']}s", flush=True)

    prov["self_hash"] = hashlib.sha256(
        json.dumps(prov, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(prov, open(out_dir / f"c3m_xp_extraction_{subject}.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3m_xp_extraction_{subject}.json")


if __name__ == "__main__":
    main()
