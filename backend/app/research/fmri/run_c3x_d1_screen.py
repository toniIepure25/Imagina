"""C3X Phase 4-5 — sealed D1 (ds001506) imagery reliability screen.

Run-disjoint split-half reliability (c3x_reliability) with the sealed permutation
null, non-straddling bootstrap CI, and split-seed robustness, on each subject's
VC imagery (R_I) and matched perception-test (R_P), plus secondary V1-V4 point
estimates. Applies the sealed subject gate + quality class; the driver aggregates
to the dataset gate and attenuation ratio. No geometry.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.c3x_reliability import (
    reliability_with_inference,
    run_disjoint_reliability,
    subject_quality_class,
    subject_reliability_gate,
)

SEED = 20260826
SEC_ROIS = ["ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4"]


def screen_subject(subj: str, data_dir: Path, n_perm, n_boot) -> dict:
    d = data_dir / subj
    out = {"subject": subj}
    cond_res = {}
    for role in ("imagery", "perceptionTest"):
        X = np.load(d / f"{role}_VC.npy").astype(np.float64)
        content = np.load(d / f"{role}_content.npy")
        run = np.load(d / f"{role}_run.npy")
        res = reliability_with_inference(X, content, run, SEED, n_perm=n_perm, n_boot=n_boot)
        res["n_samples"] = int(X.shape[0])
        res["n_VC_voxels"] = int(X.shape[1])
        res["n_content"] = int(len(set(content.tolist())))
        # secondary ROI point reliability
        roi = {}
        for r in SEC_ROIS:
            f = d / f"{role}_{r}_idx.npy"
            if f.exists():
                idx = np.load(f)
                roi[r] = (run_disjoint_reliability(X[:, idx], content, run, SEED, n_rep=200)
                          if len(idx) >= 10 else None)
        res["roi_secondary"] = roi
        cond_res[role] = res

    R_I, R_P = cond_res["imagery"], cond_res["perceptionTest"]
    out["R_I_VC"] = R_I
    out["R_P_VC"] = R_P
    out["attenuation_ratio_RI_over_RP"] = (float(R_I["reliability"] / R_P["reliability"])
                                           if R_P["reliability"] > 0 else None)
    out["imagery_gate"] = subject_reliability_gate(R_I)
    out["vision_gate"] = subject_reliability_gate(R_P)
    out["quality_class"] = subject_quality_class(R_P, R_I)
    out["self_hash"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    return out


def main() -> None:
    data_dir = Path(os.environ["C3X_DATA_DIR"])
    out_dir = Path(os.environ["C3X_OUT_DIR"])
    n_perm = int(os.environ.get("C3X_NPERM", "1000"))
    n_boot = int(os.environ.get("C3X_NBOOT", "1000"))
    subs = os.environ.get("C3X_SUBJECTS", "sub-01,sub-02,sub-03").split(",")
    for s in subs:
        res = screen_subject(s, data_dir, n_perm, n_boot)
        json.dump(res, open(out_dir / f"d1_reliability_{s}.json", "w"), indent=2)
        ri, rp = res["R_I_VC"], res["R_P_VC"]
        print(f"[{s}] R_I={ri['reliability']:.4f} CI[{ri['bootstrap_ci95'][0]:.3f},"
              f"{ri['bootstrap_ci95'][1]:.3f}] p={ri['perm_p_one_sided']:.4f} gate={res['imagery_gate']} "
              f"| R_P={rp['reliability']:.4f} p={rp['perm_p_one_sided']:.4f} gate={res['vision_gate']} "
              f"| atten={res['attenuation_ratio_RI_over_RP']} | {res['quality_class']}",
              flush=True)
    print(time.strftime("done %H:%M:%S"))


if __name__ == "__main__":
    main()
