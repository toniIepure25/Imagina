"""C3XAT-R1 secondary/enrichment analyses — DESCRIPTIVE ONLY; cannot alter the primary decision.

Computes imagery R_I (frozen session-disjoint estimator, unchanged) in secondary ROIs to test whether
imagery reliability is enriched in the atlas-defined visual network vs generic cortex. To avoid repeated
BOLD I/O, imagery betas are extracted ONCE per subject over the UNION of all requested ROI voxels, then
R_I is computed for each ROI by sub-indexing. Reuses the frozen imagery beta extraction; no scientific
parameter is changed.
"""
from __future__ import annotations

import json
import os

import numpy as np

from app.research.fmri import c3xat_pipeline as P
from app.research.fmri.run_c3xat_r1_confirmatory import _betas_for_task


def main():
    import nibabel as nib
    deriv = os.environ.get("C3XAT_DERIV", "/work/run2/deriv")
    out = os.environ.get("C3XAT_OUT", "/work/wang/results")
    os.makedirs(out, exist_ok=True)
    subs = os.environ.get("C3XAT_SUBS", "sub-01,sub-02,sub-03,sub-04,sub-05,sub-06").split(",")
    specs = os.environ["C3XAT_SEC_MASKS"].split(",")            # name=path,name=path
    names, paths = zip(*[s.split("=", 1) for s in specs])
    mask_flat = {n: (np.asanyarray(nib.load(p).dataobj) > 0).reshape(-1) for n, p in zip(names, paths)}
    union = np.zeros_like(next(iter(mask_flat.values())))
    for m in mask_flat.values():
        union = union | m
    union_idx = np.where(union)[0]
    # position of each ROI's voxels within the single union extraction
    pos = {n: np.where(mask_flat[n][union_idx])[0] for n in names}
    for sub in subs:
        # ONE extraction over the union ROI (imagery)
        obs, _pred, content, sess = _betas_for_task(deriv, sub, "testImagery", union_idx)
        for n in names:
            sub_obs = obs[:, pos[n]]
            ri = P.reliability_with_inference_pairs(sub_obs, content, sess, P.SEED_BASE,
                                                    n_perm=P.N_PERM, n_boot=P.N_BOOT)
            r = {"roi": n, "subject": sub, "n_voxels": int(pos[n].size),
                 "R_I": ri["reliability"], "perm_p": ri["perm_p_one_sided"],
                 "ci95": ri["bootstrap_ci95"], "split_seed_values": ri["split_seed_values"],
                 "split_seed_min": ri["split_seed_min"], "imagery_pass": P.subject_imagery_pass(ri)}
            json.dump(r, open(f"{out}/secondary_{n}_{sub}.json", "w"), indent=2)
            print(f"SEC {n} {sub} R_I={ri['reliability']:.4f} "
                  f"p={ri['perm_p_one_sided']:.4f} pass={r['imagery_pass']}")


if __name__ == "__main__":
    main()
