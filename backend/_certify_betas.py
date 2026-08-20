"""Certify all 40 subj01 perception beta sessions.

LOCAL CONVENIENCE SCRIPT — hardcodes this developer's D:\\ComputaCenter paths.
NOT a reusable scientific runner and excluded from scientific replay; use
app/research/fmri/ingestion.py (NSD_DATA_ROOT/NSD_BETAS_ROOT env vars) instead.
"""
import json
import time
from pathlib import Path

import h5py
import numpy as np

betas_dir = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas\ppdata\subj01\func1pt8mm\betas_fithrf")
EXPECTED_SHAPE = (750, 83, 104, 81)
EXPECTED_DTYPE = np.int16

results = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "subject": "subj01",
    "sessions": {},
    "aggregate": {},
}

total_bytes = 0
all_pass = True
for sess in range(1, 41):
    fname = f"betas_session{sess:02d}.hdf5"
    fpath = betas_dir / fname
    entry = {"session": sess, "file": fname}

    if not fpath.exists():
        entry["status"] = "MISSING"
        all_pass = False
        results["sessions"][f"session{sess:02d}"] = entry
        continue

    entry["size"] = fpath.stat().st_size
    total_bytes += entry["size"]
    entry["size_ok"] = entry["size"] > 1_000_000_000

    try:
        with h5py.File(fpath, "r") as hf:
            entry["hdf5_opens"] = True
            entry["has_betas_key"] = "betas" in hf
            if "betas" in hf:
                ds = hf["betas"]
                entry["shape"] = list(ds.shape)
                entry["shape_ok"] = tuple(ds.shape) == EXPECTED_SHAPE
                entry["dtype"] = str(ds.dtype)
                entry["dtype_ok"] = ds.dtype == EXPECTED_DTYPE
                v_begin = ds[0, 0, 0, 0]
                v_mid = ds[375, 41, 52, 40]
                v_end = ds[749, 82, 103, 80]
                entry["readable"] = True
                entry["sample_values"] = [int(v_begin), int(v_mid), int(v_end)]
                entry["all_finite"] = bool(
                    np.isfinite(v_begin) and np.isfinite(v_mid) and np.isfinite(v_end)
                )
    except Exception as e:
        entry["hdf5_opens"] = False
        entry["error"] = str(e)
        all_pass = False

    session_pass = (
        entry.get("size_ok", False)
        and entry.get("hdf5_opens", False)
        and entry.get("shape_ok", False)
        and entry.get("dtype_ok", False)
        and entry.get("readable", False)
        and entry.get("all_finite", False)
    )
    entry["status"] = "CERTIFIED" if session_pass else "FAILED"
    if not session_pass:
        all_pass = False

    results["sessions"][f"session{sess:02d}"] = entry
    if sess % 10 == 0:
        print(f"  Checked sessions 1-{sess}: all pass so far = {all_pass}")

results["aggregate"] = {
    "total_sessions": 40,
    "certified_sessions": sum(
        1 for s in results["sessions"].values() if s.get("status") == "CERTIFIED"
    ),
    "total_bytes": total_bytes,
    "total_trials": 40 * 750,
    "all_certified": all_pass,
}

results["certification_status"] = (
    "SUBJ01_PERCEPTION_ACQUISITION_CERTIFIED" if all_pass else "INCOMPLETE"
)

out_path = Path(r"D:\ComputaCenter\Imagina\results\c3_subj01_perception_certification.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nCertification: {results['certification_status']}")
print(f"Sessions: {results['aggregate']['certified_sessions']}/40")
print(f"Total bytes: {total_bytes:,}")
print(f"Total trials: {results['aggregate']['total_trials']}")
print(f"Saved: {out_path}")
