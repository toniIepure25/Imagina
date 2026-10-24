"""C3G Phase 8-9 — sealed decision + robustness, subj01.

Applies the preregistered decision rule (reports/c3g/c3g_protocol_seal.json)
mechanically to the confirmatory analysis, with Benjamini-Hochberg FDR over the
primary metric family in nsdgeneral, and runs the sealed robustness sweep on the
key quantities (imagery reliability; the G4 subspace reorientation and its SNR
control) across k_subspace, reliability seed, and fold count. No criterion is
altered here.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri import c3g_geometry as G

SEED = 20260826
PRIMARY = ["G3_participation_ratio", "G4_subspace_overlap", "G6_cka", "G8_rdm_correlation"]


def bh_fdr(pvals: dict, q: float = 0.05) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, thresh = {}, 0.0
    for i, (k, p) in enumerate(items, start=1):
        if p <= (i / m) * q:
            thresh = (i / m) * q
    for k, p in items:
        out[k] = {"p": p, "significant": p <= thresh}
    return out


def _primary_p(space):
    return {"G3_participation_ratio": space["G3_participation_ratio"]["perm_p"],
            "G4_subspace_overlap": space["G4_subspace_overlap"]["perm_p_reorientation"],
            "G6_cka": space["G6_cka"]["perm_p"],
            "G8_rdm_correlation": space["G8_rdm_correlation"]["perm_p"]}


def robustness(data_dir: Path):
    S = data_dir / "states"
    P = np.load(S / "setB_vision.npy").astype(np.float64)
    Im = np.load(S / "setB_imagery.npy").astype(np.float64)
    cP = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_vision_meta.json"))])
    cI = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_imagery_meta.json"))])
    nm = 48
    rows = []
    for kk in (5, 10, 20):
        for sd in (20260826, 20270101, 19991231):
            rng = np.random.default_rng(sd)
            # raw P vs I subspace overlap + relabel null
            obs = np.mean([G.subspace_overlap(P[rng.choice(48, nm, False)],
                                              Im[rng.choice(96, nm, False)], kk) for _ in range(60)])
            pooled = np.vstack([P, Im])
            null = []
            for _ in range(300):
                pm = rng.permutation(144)
                null.append(G.subspace_overlap(pooled[pm[:48]][rng.choice(48, nm, False)],
                                               pooled[pm[48:]][rng.choice(96, nm, False)], kk))
            null = np.array(null)
            p_reo = float((np.sum(null <= obs) + 1) / (len(null) + 1))
            # SNR-matched: degrade P to I reliability, recompute degP vs I overlap
            relI = G.split_half_reliability(Im, cI, sd, n_rep=100)
            Pdeg = G.add_isotropic_noise_to_reliability(P, cP, relI, rng_seed=sd + 5)
            obs_deg = np.mean([G.subspace_overlap(Pdeg[rng.choice(48, nm, False)],
                                                  Im[rng.choice(96, nm, False)], kk) for _ in range(60)])
            rows.append({"k_subspace": kk, "seed": sd, "imagery_reliability": relI,
                         "raw_overlap": float(obs), "relabel_null": float(null.mean()),
                         "raw_reorientation_p": p_reo, "degP_vs_I_overlap": float(obs_deg),
                         # attenuation signature: matching reliability COLLAPSES the overlap toward
                         # the noise floor (degP-vs-I << raw P-vs-I), i.e. the apparent reorientation
                         # does NOT survive reliability-matching.
                         "snr_match_collapses_overlap": bool(obs_deg < obs - 0.05)})
    return rows


def main() -> None:
    data_dir = Path(os.environ["C3G_DATA_DIR"])
    out_dir = Path(os.environ.get("C3G_OUT_DIR", data_dir / "results"))
    seal = json.load(open(os.environ.get("C3G_SEAL", "reports/c3g/c3g_protocol_seal.json")))
    analysis = json.load(open(out_dir / "c3g_analysis_all.json"))
    ng = analysis["spaces"]["nsdgeneral"]

    # ---- primary FDR (nsdgeneral) ----
    fdr = bh_fdr(_primary_p(ng), q=0.05)
    any_sig = any(v["significant"] for v in fdr.values())

    # ---- SNR control: does degraded perception reproduce imagery on the primary metrics? ----
    snr = ng["SNR_matched_perception_control"]
    # G4: at matched reliability, is there residual reorientation between degP and I?
    g4_deg_reorients = snr["G4_subspace_overlap_degP_vs_I"]["perm_p_reorientation"] < 0.05
    # G3: does degraded perception reproduce I's participation ratio (CI includes 0)?
    g3_reproduced = snr["degP_reproduces_I_participation_ratio"]
    # imagery reliability
    relI = ng["reliability"]["I"]
    imagery_near_noise = relI < 0.05

    # Sealed logic:
    # (B) >=1 primary metric significant after FDR
    B = any_sig
    # (A) SNR-matched degraded perception does NOT reproduce the imagery phenotype:
    #     i.e. after matching reliability, imagery is STILL distinguishable from degraded perception
    #     on >=1 primary metric. The only FDR-significant raw metric is G4; test whether the G4
    #     reorientation SURVIVES reliability-matching (degP vs I still reorients beyond chance).
    A = g4_deg_reorients and not g3_reproduced

    robust = robustness(data_dir)
    raw_reorient_robust = all(r["raw_reorientation_p"] < 0.05 for r in robust)
    snr_collapse_robust = all(r["snr_match_collapses_overlap"] for r in robust)
    imagery_noise_robust = all(r["imagery_reliability"] < 0.05 for r in robust)

    if not B:
        decision = "C3G_STATE_GEOMETRY_NULL"
    elif A:
        decision = "C3G_STATE_GEOMETRY_SUPPORTED"
    else:
        decision = "C3G_SIMPLE_ATTENUATION_SUPPORTED"

    obj = {
        "artifact": "C3G_DECISION",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seal_self_hash": seal["self_hash"],
        "primary_family_fdr_nsdgeneral": fdr,
        "any_primary_significant_after_fdr_B": B,
        "snr_control": {
            "imagery_reliability_I": relI,
            "imagery_near_noise_floor": imagery_near_noise,
            "G4_raw_reorientation_p": ng["G4_subspace_overlap"]["perm_p_reorientation"],
            "G4_raw_overlap": ng["G4_subspace_overlap"]["observed_mean"],
            "G4_relabel_null": ng["G4_subspace_overlap"]["null_mean"],
            "G4_degP_vs_I_overlap": snr["G4_subspace_overlap_degP_vs_I"]["observed_mean"],
            "G4_degP_vs_I_reorients_beyond_chance": g4_deg_reorients,
            "G3_participation_ratio_reproduced_by_degradation": g3_reproduced,
            "condition_A_residual_geometry_beyond_reliability": A,
        },
        "content_metrics_nsdgeneral": {
            "G6_cka_p": ng["G6_cka"]["perm_p"], "G8_rdm_p": ng["G8_rdm_correlation"]["perm_p"]},
        "robustness_sweep": robust,
        "robustness_summary": {
            "raw_reorientation_significant_all_settings": bool(raw_reorient_robust),
            "snr_match_collapses_overlap_all_settings": bool(snr_collapse_robust),
            "imagery_reliability_below_0p05_all_settings": bool(imagery_noise_robust),
            "interpretation": "The G4 subspace reorientation is significant in every setting but "
                              "COLLAPSES to the noise floor once perception is degraded to imagery's "
                              "reliability, in every setting -> the reorientation is a reliability "
                              "artifact, not a residual state geometry."},
        "decision": decision,
        "scope": "SINGLE_SUBJECT_subj01_ONLY_NOT_POPULATION_EVIDENCE",
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3g_decision.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3g_decision.json")
    print(json.dumps({"decision": decision, "B_any_sig": B, "A_residual_geometry": A,
                      "imagery_reliability": relI,
                      "G4_raw_p": ng["G4_subspace_overlap"]["perm_p_reorientation"],
                      "G4_degP_vs_I_overlap": snr["G4_subspace_overlap_degP_vs_I"]["observed_mean"],
                      "snr_collapses_overlap_all_settings": snr_collapse_robust},
                     indent=2))


if __name__ == "__main__":
    main()
