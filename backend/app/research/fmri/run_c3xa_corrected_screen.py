"""C3XA corrected D1 reliability screen — fixation-excluded, family-stratified.

Reuses the FROZEN C3X run-disjoint estimator (c3x_reliability, unchanged); only
the valid-sample mask is corrected per the certified target contract:
  natural  = Label 1-10  (matched perception = perceptionNaturalImageTest)
  artificial = Label 11-25 (matched perception = perceptionArtificialImage)
  fixation = Label 26     (EXCLUDED from all primary reliability)

Acquires the missing perceptionArtificialImage bdpy, builds the 520-row imagery
manifest (500 target + 20 fixation), and computes R_I_natural, R_I_artificial,
R_I_combined_25 (confounded comparison), R_I_including_fixation (old C3X), plus
R_P_natural, R_P_artificial, attenuation ratios, and a fixation-sensitivity /
fixation-only repeatability diagnostic. No geometry.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.c3x_reliability import reliability_with_inference, subject_reliability_gate
from app.research.fmri.run_c3x_d1_acquire_certify import _download, _sha256, parse_bdpy

NATURAL = list(range(1, 11))
ARTIFICIAL = list(range(11, 26))
FIXATION = 26
ART_FILES = {"sub-01": (22713857, "22b24c253ce7468a3c4bd85d9b937620"),
             "sub-02": (22713866, "da311c57e99dad3c8b4d7a2af8ec283e"),
             "sub-03": (22713977, "2fc25e90151f0aa72140c405ac4bc03c")}
SEED = 20260826


def _subset(X, content, run, labels):
    m = np.isin(content, labels)
    return X[m], content[m], run[m]


def _fixation_repeatability(X, run, seed):
    """Run-disjoint split-half self-consistency of the single fixation pattern."""
    rng = np.random.default_rng(seed)
    uruns = sorted(set(int(r) for r in run.tolist()))
    vals = []
    for _ in range(200):
        perm = rng.permutation(uruns)
        h = len(uruns) // 2
        a = X[np.isin(run, perm[:h])].mean(0)
        b = X[np.isin(run, perm[h:2 * h])].mean(0)
        a = a - a.mean()
        b = b - b.mean()
        vals.append(float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-24)))
    return float(np.mean(vals))


def main() -> None:
    c3x_dir = Path(os.environ["C3X_DATA_DIR"])          # C3X extracted per-subject dir
    art_data = Path(os.environ["C3XA_ART_DIR"])          # download dir for perceptionArtificialImage
    out_dir = Path(os.environ["C3XA_OUT_DIR"])
    art_data.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_perm = int(os.environ.get("C3XA_NPERM", "1000"))
    n_boot = int(os.environ.get("C3XA_NBOOT", "1000"))
    subs = os.environ.get("C3XA_SUBJECTS", "sub-01,sub-02,sub-03").split(",")

    for s in subs:
        d = c3x_dir / s
        Xi = np.load(d / "imagery_VC.npy").astype(np.float64)
        ci = np.load(d / "imagery_content.npy")
        ri = np.load(d / "imagery_run.npy")
        # manifest invariants
        n_fix = int(np.sum(ci == FIXATION))
        n_tgt = int(np.sum(np.isin(ci, NATURAL + ARTIFICIAL)))
        assert n_tgt == 500 and n_fix == 20, (s, n_tgt, n_fix)

        # perceptionNaturalImageTest (from C3X)
        Xpn = np.load(d / "perceptionTest_VC.npy").astype(np.float64)
        cpn = np.load(d / "perceptionTest_content.npy")
        rpn = np.load(d / "perceptionTest_run.npy")

        # acquire + parse perceptionArtificialImage
        fid, md5 = ART_FILES[s]
        dst = art_data / f"{s}_perceptionArtificial.h5"
        dl = _download(fid, md5, dst)
        ds, voxel_cols, roi_cols, cpa, rpa = parse_bdpy(dst)
        Xpa = ds[:, roi_cols["ROI_VC"]].astype(np.float64)

        def infer(X, c, r):
            out = reliability_with_inference(X, c, r, SEED, n_perm=n_perm, n_boot=n_boot)
            out["gate"] = subject_reliability_gate(out)
            return out

        res = {"subject": s, "artificial_download": dl,
               "manifest": {"target_samples": n_tgt, "fixation_samples": n_fix,
                            "natural_contents": int(len(set(ci[np.isin(ci, NATURAL)].tolist()))),
                            "artificial_contents": int(len(set(ci[np.isin(ci, ARTIFICIAL)].tolist())))},
               "artificial_perception": {"md5": md5, "sha256": _sha256(dst),
                                         "n_samples": int(Xpa.shape[0]),
                                         "n_content": int(len(set(cpa.tolist()))),
                                         "n_VC": int(Xpa.shape[1])}}

        # PRIMARY family-stratified imagery reliability (fixation excluded)
        res["R_I_natural"] = infer(*_subset(Xi, ci, ri, NATURAL))
        res["R_I_artificial"] = infer(*_subset(Xi, ci, ri, ARTIFICIAL))
        # confounded comparison + old C3X (incl fixation)
        res["R_I_combined_25_confounded"] = infer(*_subset(Xi, ci, ri, NATURAL + ARTIFICIAL))
        res["R_I_including_fixation_oldC3X"] = infer(Xi, ci, ri)
        # matched perception per family
        res["R_P_natural"] = infer(Xpn, cpn, rpn)
        res["R_P_artificial"] = infer(Xpa, cpa, rpa)
        # attenuation ratios (within family)
        res["attenuation_natural"] = (res["R_I_natural"]["reliability"] / res["R_P_natural"]["reliability"]
                                      if res["R_P_natural"]["reliability"] > 0 else None)
        res["attenuation_artificial"] = (res["R_I_artificial"]["reliability"] / res["R_P_artificial"]["reliability"]
                                         if res["R_P_artificial"]["reliability"] > 0 else None)
        # fixation sensitivity
        Xf, _, rf = _subset(Xi, ci, ri, [FIXATION])
        res["fixation_diagnostic"] = {
            "R_I_including_fixation": res["R_I_including_fixation_oldC3X"]["reliability"],
            "R_I_excluding_fixation_combined25": res["R_I_combined_25_confounded"]["reliability"],
            "fixation_only_repeatability": _fixation_repeatability(Xf, rf, SEED)}
        res["self_hash"] = hashlib.sha256(json.dumps(res, sort_keys=True, default=str).encode()).hexdigest()
        json.dump(res, open(out_dir / f"c3xa_imagery_reliability_corrected_{s}.json", "w"), indent=2)
        rn, ra = res["R_I_natural"], res["R_I_artificial"]
        print(f"[{s}] R_I_nat={rn['reliability']:.4f} (p={rn['perm_p_one_sided']:.4f} "
              f"CI[{rn['bootstrap_ci95'][0]:.3f},{rn['bootstrap_ci95'][1]:.3f}] {rn['gate']}) "
              f"R_I_art={ra['reliability']:.4f} (p={ra['perm_p_one_sided']:.4f} {ra['gate']}) "
              f"R_P_nat={res['R_P_natural']['reliability']:.3f} R_P_art={res['R_P_artificial']['reliability']:.3f} "
              f"| R_I_incl_fix(old)={res['R_I_including_fixation_oldC3X']['reliability']:.3f} "
              f"fixrep={res['fixation_diagnostic']['fixation_only_repeatability']:.3f}", flush=True)
    print(time.strftime("done %H:%M:%S"))


if __name__ == "__main__":
    main()
