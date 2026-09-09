"""C3XC Phase 4/5/6 reliability screen (per subject).

R_I (imagery)  : SESSION-disjoint reliability via the FROZEN C3XB run-pair estimator with
                 unit:=session (D2 sessions are one-trial-per-(session,video), the estimator's
                 precondition). Computed with the VALIDATED c3xb_fast accelerator (bit-identical
                 to the frozen estimator; validated on synthetic + Subject1 real data).
R_P (perception): matched video-identity perception reliability via the FROZEN C3X run-disjoint
                 estimator on perception runs. Attenuation A = R_I / R_P.
Cue ROI-profile control: point R_I in earlyVC(V1) vs HVC; HVC>V1 argues against an early-visual
                 cue/leakage artifact (imagery shows no video, so target leakage is structurally
                 absent). Primary gating ROI = VC only.

No geometry. Writes results/c3xc/c3xc_reliability_<subj>.json (R_I checkpointed first).
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
from app.research.fmri.c3xb_reliability import run_pair_disjoint_reliability, subject_reliability_gate
from app.research.fmri.c3xc_fast import reliability_with_inference_pairs_fast

SEED = 20260907


def main() -> None:
    ext = Path(os.environ["C3XC_EXTRACT_DIR"])
    out_dir = Path(os.environ.get("C3XC_OUT_DIR", "results/c3xc"))
    out_dir.mkdir(parents=True, exist_ok=True)
    n_perm = int(os.environ.get("C3XC_NPERM", "1000"))
    n_boot = int(os.environ.get("C3XC_NBOOT", "1000"))
    rp_nperm = int(os.environ.get("C3XC_RP_NPERM", "1000"))
    rp_nboot = int(os.environ.get("C3XC_RP_NBOOT", "1000"))
    subj = os.environ["C3XC_SUBJECT"]
    sd = ext / subj

    ic = np.load(sd / "testImagery" / "content.npy")
    isess = np.load(sd / "testImagery" / "session.npy")
    pc = np.load(sd / "testPerception" / "content.npy")
    prun = np.load(sd / "testPerception" / "run.npy")

    def load(cond, roi):
        return np.load(sd / cond / f"X_{roi}.npy").astype(np.float64)

    t0 = time.time()
    res = {"artifact": "C3XC_RELIABILITY", "subject": subj, "seed": SEED,
           "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "R_I_n_perm": n_perm, "R_I_n_boot": n_boot, "R_P_n_perm": rp_nperm, "R_P_n_boot": rp_nboot,
           "R_I_estimator": "c3xb run-pair-disjoint, unit=SESSION; c3xc_fast buffered accelerator "
                            "(validated BIT-IDENTICAL to frozen c3xb_reliability, synthetic + real S1)",
           "R_P_estimator": "c3x run-disjoint on perception runs"}

    # PRIMARY: imagery VC, session-disjoint, full inference + gate
    Xi = load("testImagery", "VC")
    R_I = reliability_with_inference_pairs_fast(Xi, ic, isess, SEED, n_perm=n_perm, n_boot=n_boot)
    R_I["gate"] = subject_reliability_gate(R_I)
    res["R_I_VC"] = R_I
    res["self_hash"] = ""
    json.dump(res, open(out_dir / f"c3xc_reliability_{subj}.json", "w"), indent=2)  # checkpoint
    print(f"[{subj}] R_I done R={R_I['reliability']:.4f} p={R_I['perm_p_one_sided']:.4f} "
          f"{R_I['gate']} ({time.time() - t0:.0f}s) [ckpt]", flush=True)

    # perception positive control (VC). Full inference on the anchor subject (C3XC_RP_FULL=1),
    # else POINT-only (documented sealed fallback: perception is a strong control; VC has ~17k
    # voxels making the frozen global-shuffle null ~expensive; the anchor subject's full-inference
    # PASS establishes perception reliability). run-disjoint on perception runs.
    Xp = load("testPerception", "VC")
    if os.environ.get("C3XC_RP_FULL", "0") == "1":
        R_P = rp_inference(Xp, pc, prun, SEED, n_perm=rp_nperm, n_boot=rp_nboot)
        R_P["gate"] = subject_reliability_gate(R_P)
    else:
        R_P = {"reliability": run_disjoint_reliability(Xp, pc, prun, SEED), "point_only": True,
               "full_inference_reference": "anchor subject C3XC_RP_FULL run"}
    res["R_P_VC"] = R_P
    res["attenuation_VC"] = (R_I["reliability"] / R_P["reliability"] if R_P["reliability"] > 0 else None)
    print(f"[{subj}] R_P R={R_P['reliability']:.4f} ({time.time() - t0:.0f}s)", flush=True)

    # cue ROI-profile control: point R_I in earlyVC(V1), LVC, HVC (imagery) + point R_P
    roi_profile = {"VC": {"R_I": R_I["reliability"], "R_P": R_P["reliability"]}}
    for r in ("earlyVC", "LVC", "HVC"):
        fi = sd / "testImagery" / f"X_{r}.npy"
        if fi.exists():
            roi_profile[r] = {"R_I": run_pair_disjoint_reliability(load("testImagery", r), ic, isess, SEED),
                              "R_P": run_disjoint_reliability(load("testPerception", r), pc, prun, SEED),
                              "n_voxels": int(np.load(fi, mmap_mode="r").shape[1])}
    res["roi_profile"] = roi_profile
    v1 = roi_profile.get("earlyVC", {}).get("R_I", 0.0)
    hvc = roi_profile.get("HVC", {}).get("R_I", 0.0)
    res["cue_roi_profile_control"] = {"earlyVC_V1_R_I": v1, "HVC_R_I": hvc, "hvc_gt_v1": bool(hvc > v1),
        "interpretation": "HVC>earlyVC is consistent with internally-generated (recall) content and "
                          "against an early-visual cue/leakage artifact; imagery shows no video."}
    res["early_vs_late_temporal_control"] = {"computable_from_release": False,
        "reason": "preprocessed single block-averaged amplitude per recall trial; no within-trial time "
                  "axis. Requires raw BIDS ds005191 + GLM; deferred."}

    res.pop("self_hash", None)
    res["self_hash"] = hashlib.sha256(json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(res, open(out_dir / f"c3xc_reliability_{subj}.json", "w"), indent=2)
    print(f"[{subj}] DONE R_I={R_I['reliability']:.4f} {R_I['gate']} | R_P={R_P['reliability']:.4f} "
          f"{R_P.get('gate', 'point-only')} | HVC={hvc:.3f} V1={v1:.3f} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
