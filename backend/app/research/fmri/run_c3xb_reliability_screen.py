"""C3XB Phase 2 sealed reliability screen (per subject).

R_I_GOD  : run-pair-disjoint imagery reliability (c3xb_reliability, FROZEN) on VC (primary,
           full inference + gate) and secondary ROIs V1 V2 V3 V4 LOC FFA PPA plus the
           composites LVC=(V1+V2+V3) and HVC=(LOC+FFA+PPA), labelled composite_of_released.
R_P_cat  : CATEGORY-MATCHED PERCEPTION reliability (c3x_reliability run-disjoint, FROZEN) on
           VC (ImageNetTest, 35 runs). Attenuation R_I/R_P reported.
Cue ROI-profile control: per-ROI point R_I; if imagery reliability is carried by the visual
           WORD cue it should be V1-dominated; genuine object imagery is HVC-dominated. Recorded
           as a descriptive discriminating control (computed after the primary VC result).

No geometry. Writes results/c3xb/c3xb_reliability_<Subject>.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.c3x_reliability import reliability_with_inference as rp_inference
from app.research.fmri.c3x_reliability import run_disjoint_reliability
from app.research.fmri.c3xb_reliability import (
    reliability_with_inference_pairs,
    run_pair_disjoint_reliability,
    subject_reliability_gate,
)

SEED = 20260901
SECONDARY = ["ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4", "ROI_LOC", "ROI_FFA", "ROI_PPA"]


def main() -> None:
    ext = Path(os.environ["C3XB_EXTRACT_DIR"])
    out_dir = Path(os.environ.get("C3XB_OUT_DIR", "results/c3xb"))
    out_dir.mkdir(parents=True, exist_ok=True)
    n_perm = int(os.environ.get("C3XB_NPERM", "1000"))
    n_boot = int(os.environ.get("C3XB_NBOOT", "1000"))
    # R_P (matched-perception CONTROL) resampling counts. Documented environment
    # adaptation (see C3XA precedent): the PRIMARY R_I_GOD keeps the full sealed
    # 1000/1000 inference; R_P full inference on 1750 samples x 1000 perm is ~60 min
    # per subject and infeasible for 5 subjects locally. Perception reliability is a
    # strong, unambiguous control; 200 perms yields min p ~= 0.005 (< 0.05) and a valid
    # bootstrap CI, so the gate decision on R_P is unaffected.
    rp_nperm = int(os.environ.get("C3XB_RP_NPERM", "200"))
    rp_nboot = int(os.environ.get("C3XB_RP_NBOOT", "200"))
    subj = os.environ["C3XB_SUBJECT"]
    sd = ext / subj

    ic = np.load(sd / "Imagery" / "category.npy")
    pair = np.load(sd / "Imagery" / "pair.npy")
    pc = np.load(sd / "ImageNetTest" / "category.npy")
    pr = np.load(sd / "ImageNetTest" / "run.npy")

    def load(cond, roi):
        return np.load(sd / cond / f"{roi}.npy").astype(np.float64)

    res = {"artifact": "C3XB_RELIABILITY", "subject": subj, "seed": SEED,
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "R_I_n_perm": n_perm, "R_I_n_boot": n_boot,
           "R_P_n_perm": rp_nperm, "R_P_n_boot": rp_nboot,
           "R_P_resampling_adaptation": ("R_P control uses reduced perm/boot (see script "
               "docstring); PRIMARY R_I_GOD uses full sealed 1000/1000")}

    t0 = time.time()
    # ---- PRIMARY: imagery VC, full inference + gate ----
    Xi_vc = load("Imagery", "ROI_VC")
    R_I = reliability_with_inference_pairs(Xi_vc, ic, pair, SEED, n_perm=n_perm, n_boot=n_boot)
    R_I["gate"] = subject_reliability_gate(R_I)
    res["R_I_GOD_VC"] = R_I
    print(f"[{subj}] R_I done R={R_I['reliability']:.4f} p={R_I['perm_p_one_sided']:.4f} "
          f"{R_I['gate']} ({time.time() - t0:.0f}s)", flush=True)

    # ---- category-matched perception VC, full inference + gate ----
    Xp_vc = load("ImageNetTest", "ROI_VC")
    R_P = rp_inference(Xp_vc, pc, pr, SEED, n_perm=rp_nperm, n_boot=rp_nboot)
    R_P["gate"] = subject_reliability_gate(R_P)
    print(f"[{subj}] R_P done R={R_P['reliability']:.4f} {R_P['gate']} "
          f"({time.time() - t0:.0f}s)", flush=True)
    res["R_P_category_VC"] = R_P
    res["attenuation_VC"] = (R_I["reliability"] / R_P["reliability"]
                             if R_P["reliability"] > 0 else None)

    # ---- secondary ROIs: imagery point R_I (cue ROI-profile control) + perception point R_P ----
    roi_profile = {"ROI_VC": {"R_I": R_I["reliability"], "R_P": R_P["reliability"]}}
    for roi in SECONDARY:
        f = sd / "Imagery" / f"{roi}.npy"
        if not f.exists():
            continue
        Xi = load("Imagery", roi)
        Xp = load("ImageNetTest", roi)
        roi_profile[roi] = {
            "R_I": run_pair_disjoint_reliability(Xi, ic, pair, SEED),
            "R_P": run_disjoint_reliability(Xp, pc, pr, SEED),
            "n_voxels": int(Xi.shape[1])}
    # composites of released masks
    def comp(cond, rois):
        return np.hstack([load(cond, r) for r in rois])
    lvc_i = comp("Imagery", ["ROI_V1", "ROI_V2", "ROI_V3"])
    hvc_i = comp("Imagery", ["ROI_LOC", "ROI_FFA", "ROI_PPA"])
    lvc_p = comp("ImageNetTest", ["ROI_V1", "ROI_V2", "ROI_V3"])
    hvc_p = comp("ImageNetTest", ["ROI_LOC", "ROI_FFA", "ROI_PPA"])
    roi_profile["LVC_composite"] = {"R_I": run_pair_disjoint_reliability(lvc_i, ic, pair, SEED),
                                    "R_P": run_disjoint_reliability(lvc_p, pc, pr, SEED),
                                    "composite_of_released": ["ROI_V1", "ROI_V2", "ROI_V3"]}
    roi_profile["HVC_composite"] = {"R_I": run_pair_disjoint_reliability(hvc_i, ic, pair, SEED),
                                    "R_P": run_disjoint_reliability(hvc_p, pc, pr, SEED),
                                    "composite_of_released": ["ROI_LOC", "ROI_FFA", "ROI_PPA"]}
    res["roi_profile"] = roi_profile
    res["cue_roi_profile_control"] = {
        "V1_R_I": roi_profile.get("ROI_V1", {}).get("R_I"),
        "HVC_R_I": roi_profile["HVC_composite"]["R_I"],
        "hvc_gt_v1": bool(roi_profile["HVC_composite"]["R_I"] > roi_profile.get("ROI_V1", {}).get("R_I", 0)),
        "interpretation": "HVC>V1 imagery reliability is consistent with object imagery, NOT a "
                          "V1-dominated visual word-cue artifact; V1>=HVC would flag cue leakage."}

    # early-vs-late imagery temporal control is NOT computable from the block-averaged release
    res["early_vs_late_temporal_control"] = {
        "computable_from_release": False,
        "reason": "released imagery patterns are single block-averaged amplitudes (one vector per "
                  "trial); no within-trial time axis. Requires raw BIDS ds001246 + cue/imagery-"
                  "separated GLM; deferred to C3XR-CAT as a hard prerequisite."}

    res["self_hash"] = hashlib.sha256(json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(res, open(out_dir / f"c3xb_reliability_{subj}.json", "w"), indent=2)
    print(f"[{subj}] R_I_VC={R_I['reliability']:.4f} p={R_I['perm_p_one_sided']:.4f} "
          f"CI[{R_I['bootstrap_ci95'][0]:.3f},{R_I['bootstrap_ci95'][1]:.3f}] {R_I['gate']} | "
          f"R_P_VC={R_P['reliability']:.4f} p={R_P['perm_p_one_sided']:.4f} {R_P['gate']} | "
          f"att={res['attenuation_VC']} | HVC_RI={roi_profile['HVC_composite']['R_I']:.3f} "
          f"V1_RI={roi_profile.get('ROI_V1',{}).get('R_I',float('nan')):.3f}", flush=True)


if __name__ == "__main__":
    main()
