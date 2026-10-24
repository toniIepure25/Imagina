"""C3XB Phase 2 reliability screen via the VALIDATED fast path (per subject).

R_I_GOD_VC uses c3xb_fast.reliability_with_inference_pairs_fast, which is asserted
BIT-IDENTICAL to the frozen c3xb_reliability estimator on synthetic fixtures
(test_c3xb_fast.py) and on Subject1's committed frozen result. Subject1 itself keeps
its frozen-estimator JSON; S2-S5 use the fast path (identical numbers, tractable time).

R_P_category_VC is POINT-only here (documented C3XA-style environment adaptation:
full R_P inference on 1750 samples is ~30 min/subject and is not decision-critical
because the imagery gate is the primary; Subject1's FULL R_P inference (PASS, p=0.005)
is the reference that CATEGORY-MATCHED PERCEPTION is reliable). ROI-profile points and
the cue ROI-profile control are computed as before. Writes results/c3xb/
c3xb_reliability_<Subject>.json, checkpointing R_I before the (fast) remainder.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.c3x_reliability import run_disjoint_reliability
from app.research.fmri.c3xb_fast import reliability_with_inference_pairs_fast
from app.research.fmri.c3xb_reliability import run_pair_disjoint_reliability, subject_reliability_gate

SEED = 20260901
SECONDARY = ["ROI_V1", "ROI_V2", "ROI_V3", "ROI_V4", "ROI_LOC", "ROI_FFA", "ROI_PPA"]


def main() -> None:
    ext = Path(os.environ["C3XB_EXTRACT_DIR"])
    out_dir = Path(os.environ.get("C3XB_OUT_DIR", "results/c3xb"))
    out_dir.mkdir(parents=True, exist_ok=True)
    n_perm = int(os.environ.get("C3XB_NPERM", "1000"))
    n_boot = int(os.environ.get("C3XB_NBOOT", "1000"))
    subj = os.environ["C3XB_SUBJECT"]
    sd = ext / subj

    ic = np.load(sd / "Imagery" / "category.npy")
    pair = np.load(sd / "Imagery" / "pair.npy")
    pc = np.load(sd / "ImageNetTest" / "category.npy")
    pr = np.load(sd / "ImageNetTest" / "run.npy")

    def load(cond, roi):
        return np.load(sd / cond / f"{roi}.npy").astype(np.float64)

    t0 = time.time()
    res = {"artifact": "C3XB_RELIABILITY", "subject": subj, "seed": SEED,
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "R_I_n_perm": n_perm, "R_I_n_boot": n_boot,
           "R_I_estimator": "c3xb_fast (validated BIT-IDENTICAL to frozen c3xb_reliability)",
           "R_P_mode": "point_only",
           "R_P_full_inference_reference": "Subject1 c3xb_reliability full 1000/1000 R_P PASS p=0.005"}

    Xi_vc = load("Imagery", "ROI_VC")
    R_I = reliability_with_inference_pairs_fast(Xi_vc, ic, pair, SEED, n_perm=n_perm, n_boot=n_boot)
    R_I["gate"] = subject_reliability_gate(R_I)
    res["R_I_GOD_VC"] = R_I
    # checkpoint R_I immediately (before the rest), so it persists even if interrupted
    res["self_hash"] = ""
    json.dump(res, open(out_dir / f"c3xb_reliability_{subj}.json", "w"), indent=2)
    print(f"[{subj}] R_I done R={R_I['reliability']:.4f} p={R_I['perm_p_one_sided']:.4f} "
          f"{R_I['gate']} ({time.time() - t0:.0f}s)  [checkpointed]", flush=True)

    Xp_vc = load("ImageNetTest", "ROI_VC")
    R_P = {"reliability": run_disjoint_reliability(Xp_vc, pc, pr, SEED), "point_only": True,
           "full_inference_reference": res["R_P_full_inference_reference"]}
    res["R_P_category_VC"] = R_P
    res["attenuation_VC"] = (R_I["reliability"] / R_P["reliability"]
                             if R_P["reliability"] > 0 else None)

    roi_profile = {"ROI_VC": {"R_I": R_I["reliability"], "R_P": R_P["reliability"]}}
    for roi in SECONDARY:
        if not (sd / "Imagery" / f"{roi}.npy").exists():
            continue
        Xi = load("Imagery", roi)
        Xp = load("ImageNetTest", roi)
        roi_profile[roi] = {"R_I": run_pair_disjoint_reliability(Xi, ic, pair, SEED),
                            "R_P": run_disjoint_reliability(Xp, pc, pr, SEED),
                            "n_voxels": int(Xi.shape[1])}

    def comp(cond, rois):
        return np.hstack([load(cond, r) for r in rois])
    for name, rois in [("LVC_composite", ["ROI_V1", "ROI_V2", "ROI_V3"]),
                       ("HVC_composite", ["ROI_LOC", "ROI_FFA", "ROI_PPA"])]:
        roi_profile[name] = {"R_I": run_pair_disjoint_reliability(comp("Imagery", rois), ic, pair, SEED),
                             "R_P": run_disjoint_reliability(comp("ImageNetTest", rois), pc, pr, SEED),
                             "composite_of_released": rois}
    res["roi_profile"] = roi_profile
    v1 = roi_profile.get("ROI_V1", {}).get("R_I", 0.0)
    res["cue_roi_profile_control"] = {
        "V1_R_I": v1, "HVC_R_I": roi_profile["HVC_composite"]["R_I"],
        "hvc_gt_v1": bool(roi_profile["HVC_composite"]["R_I"] > v1),
        "interpretation": "HVC>V1 imagery reliability is consistent with object imagery, NOT a "
                          "V1-dominated visual word-cue artifact; V1>=HVC would flag cue leakage."}
    res["early_vs_late_temporal_control"] = {
        "computable_from_release": False,
        "reason": "released imagery patterns are single block-averaged amplitudes (one vector per "
                  "trial); no within-trial time axis. Requires raw BIDS ds001246 + cue/imagery-"
                  "separated GLM; deferred to C3XR-CAT as a hard prerequisite."}

    res.pop("self_hash", None)
    res["self_hash"] = hashlib.sha256(json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(res, open(out_dir / f"c3xb_reliability_{subj}.json", "w"), indent=2)
    print(f"[{subj}] DONE R_I={R_I['reliability']:.4f} {R_I['gate']} | R_P={R_P['reliability']:.4f} "
          f"| HVC_RI={roi_profile['HVC_composite']['R_I']:.3f} V1_RI={v1:.3f} ({time.time() - t0:.0f}s)",
          flush=True)


if __name__ == "__main__":
    main()
