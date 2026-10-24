"""C3R Phase 3 — sealed imagery-reliability screen for subj02/05/07.

Runs the INHERITED C3G split-half reliability estimator with the sealed
permutation null, bootstrap CI, and split-seed robustness (c3r_reliability) on
each participant's certified Set-B IMAGERY (R_I) and VISION (R_P) matrices in
nsdgeneral (primary) and per ROI (secondary, point estimates). Applies the
sealed reliability gate and the vision/imagery quality classification. All three
participants are evaluated in ONE execution; no per-participant protocol change.
No geometry is computed.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.c3g_geometry import split_half_reliability
from app.research.fmri.c3r_reliability import (
    practical_effect_flags,
    reliability_gate,
    reliability_with_inference,
    vision_imagery_quality,
)

SEED = 20260826
ROI_DEF = {"prf": {"V1": [1, 2], "V2": [3, 4], "V3": [5, 6], "hV4": [7]},
           "streams": {"ventral": [2, 5], "lateral": [3, 6], "parietal": [4, 7]}}


def screen_subject(subj: str, data_dir: Path, cvis, cimg, n_perm, n_boot) -> dict:
    d = data_dir / subj
    Xv = np.load(d / "setB_vision.npy").astype(np.float64)
    Xi = np.load(d / "setB_imagery.npy").astype(np.float64)
    prf = np.load(d / "prf_labels.npy")
    streams = np.load(d / "streams_labels.npy")

    R_I = reliability_with_inference(Xi, cimg, SEED, n_perm=n_perm, n_boot=n_boot)
    R_P = reliability_with_inference(Xv, cvis, SEED, n_perm=n_perm, n_boot=n_boot)

    # secondary ROI-wise point reliability (imagery and vision)
    roi = {}
    for fam, groups in ROI_DEF.items():
        labels = prf if fam == "prf" else streams
        for name, vals in groups.items():
            cols = np.where(np.isin(labels, vals))[0]
            if len(cols) < 10:
                roi[name] = {"n_voxels": int(len(cols)), "R_I": None, "R_P": None}
                continue
            roi[name] = {"n_voxels": int(len(cols)),
                         "R_I": split_half_reliability(Xi[:, cols], cimg, SEED, n_rep=200),
                         "R_P": split_half_reliability(Xv[:, cols], cvis, SEED, n_rep=200)}

    gate_I = reliability_gate(R_I)
    gate_P = reliability_gate(R_P)
    quality = vision_imagery_quality(R_P, R_I)
    return {
        "subject": subj, "n_voxels_nsdgeneral": int(Xi.shape[1]),
        "R_I_nsdgeneral": R_I, "R_P_nsdgeneral": R_P,
        "R_I_over_R_P": float(R_I["reliability"] / R_P["reliability"])
        if R_P["reliability"] not in (0.0,) else None,
        "practical_effect_flags_imagery": practical_effect_flags(R_I["reliability"]),
        "imagery_gate": gate_I, "vision_gate": gate_P, "quality_class": quality,
        "roi_secondary": roi,
        "subj01_reference_descriptive": 0.011,
    }


def main() -> None:
    data_dir = Path(os.environ["C3R_DATA_DIR"])
    out_dir = Path(os.environ["C3R_OUT_DIR"])
    n_perm = int(os.environ.get("C3R_NPERM", "1000"))
    n_boot = int(os.environ.get("C3R_NBOOT", "1000"))
    cvis = np.load(out_dir / "content_visB.npy")
    cimg = np.load(out_dir / "content_imgB.npy")
    subjects = os.environ.get("C3R_SUBJECTS", "subj02,subj05,subj07").split(",")

    summary = {}
    for s in subjects:
        res = screen_subject(s, data_dir, cvis, cimg, n_perm, n_boot)
        res["self_hash"] = hashlib.sha256(
            json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
        json.dump(res, open(out_dir / f"c3r_reliability_{s}.json", "w"), indent=2)
        ri, rp = res["R_I_nsdgeneral"], res["R_P_nsdgeneral"]
        summary[s] = {"R_I": ri["reliability"], "R_I_ci95": ri["bootstrap_ci95"],
                      "R_I_perm_p": ri["perm_p_one_sided"], "R_P": rp["reliability"],
                      "imagery_gate": res["imagery_gate"], "vision_gate": res["vision_gate"],
                      "quality_class": res["quality_class"]}
        print(f"[{s}] R_I={ri['reliability']:.4f} CI[{ri['bootstrap_ci95'][0]:.4f},"
              f"{ri['bootstrap_ci95'][1]:.4f}] p={ri['perm_p_one_sided']:.4f} | "
              f"R_P={rp['reliability']:.4f} p={rp['perm_p_one_sided']:.4f} | "
              f"imagery={res['imagery_gate']} vision={res['vision_gate']} {res['quality_class']}")

    obj = {"artifact": "C3R_RELIABILITY_SUMMARY", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "seed": SEED, "n_perm": n_perm, "n_boot": n_boot,
           "subj01_reference_descriptive": 0.011, "subjects": summary}
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3r_reliability_summary.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3r_reliability_summary.json")


if __name__ == "__main__":
    main()
