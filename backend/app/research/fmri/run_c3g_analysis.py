"""C3G confirmatory analysis (Phases 2, 3, 6, 7) — subj01.

For a given voxel space (nsdgeneral, or an ROI subset) compares the perception
state P (Set-B VISION, 48 trials) and imagery state I (Set-B IMAGERY, 96 trials),
which share session and the same 6 content items, so the contrast isolates state.

For each geometry metric we report:
  - the observed P and I values (subsample-matched, bootstrap CI),
  - a STATE-LABEL PERMUTATION p (pool the 144 trials, relabel, subsample-match),
  - the SNR-MATCHED PERCEPTION control (degrade P to I's split-half reliability
    with isotropic noise; recompute the I-vs-degradedP difference).

Also runs Phase-7 negative controls. Emits one JSON per space; the driver
aggregates spaces and applies FDR. NO decision threshold is embedded here beyond
what the sealed protocol fixes; this runner only produces metrics + inference.
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
N_PERM = 1000
N_BOOT = 1000
K_SUBSPACE = 10
N_TOP_SPEC = 20


def _p_from_null(observed: float, null: np.ndarray, two_sided: bool = True) -> float:
    null = np.asarray(null)
    if two_sided:
        c = np.mean(np.abs(null - null.mean()) >= abs(observed - null.mean()))
    else:
        c = np.mean(null >= observed)
    return float((c * len(null) + 1) / (len(null) + 1))


def _folds_by_rep(content: np.ndarray, n_folds: int, seed: int) -> np.ndarray:
    """Assign each trial a CV fold, balanced within content."""
    rng = np.random.default_rng(seed)
    folds = np.zeros(len(content), dtype=int)
    for c in sorted(set(content.tolist())):
        idx = np.where(content == c)[0]
        rng.shuffle(idx)
        folds[idx] = np.arange(len(idx)) % n_folds
    return folds


def state_metric_with_perm(fn, P, Im, n_match, seed, **kw):
    """Observed diff (subsample-matched) + state-label permutation p."""
    obs = G.subsample_matched(fn, P, Im, n_match, N_BOOT, seed, **kw)
    pooled = np.vstack([P, Im])
    nP = P.shape[0]
    rng = np.random.default_rng(seed + 1)
    null = np.empty(N_PERM)
    for t in range(N_PERM):
        perm = rng.permutation(pooled.shape[0])
        pp, pi = pooled[perm[:nP]], pooled[perm[nP:]]
        ip = rng.choice(pp.shape[0], n_match, replace=False)
        ii = rng.choice(pi.shape[0], n_match, replace=False)
        null[t] = fn(pi[ii], **kw) - fn(pp[ip], **kw)
    return {**obs, "perm_p": _p_from_null(obs["diff_mean"], null)}


def content_metric_with_perm(metric_fn, Mp, Mi, seed):
    """Content-level similarity (CKA/Procrustes) + content-label permutation p."""
    obs = metric_fn(Mp, Mi)
    rng = np.random.default_rng(seed + 2)
    K = Mp.shape[0]
    null = np.array([metric_fn(Mp, Mi[rng.permutation(K)]) for _ in range(N_PERM)])
    return {"observed": float(obs), "null_mean": float(null.mean()),
            "perm_p": _p_from_null(obs, null)}


def analyze_space(name, cols, P_all, I_all, cP, cI, seed):
    P = P_all[:, cols] if cols is not None else P_all
    Im = I_all[:, cols] if cols is not None else I_all
    n_match = min(P.shape[0], Im.shape[0])
    out = {"space": name, "n_voxels": int(P.shape[1]),
           "n_P": int(P.shape[0]), "n_I": int(Im.shape[0]), "n_match": int(n_match)}

    # ---- G9 reliability / SNR ----
    relP = G.split_half_reliability(P, cP, seed, n_rep=200)
    relI = G.split_half_reliability(Im, cI, seed, n_rep=200)
    out["reliability"] = {"P": relP, "I": relI}

    # ---- G1 centroid, G2 amplitude ----
    out["G1_centroid_displacement"] = G.centroid_displacement(P, Im)
    out["G2_amplitude_gain"] = G.amplitude_gain(P, Im)

    # ---- G3 participation ratio, eigenspectrum ----
    out["G3_participation_ratio"] = state_metric_with_perm(
        G.participation_ratio, P, Im, n_match, seed)
    out["G3_eigenspectrum_logdiv"] = {
        "observed": G.eigenspectrum_logdivergence(P, Im, N_TOP_SPEC)}

    # ---- G4 subspace overlap ----
    out["G4_subspace_overlap"] = state_metric_with_perm(
        G.subspace_overlap, P, Im, n_match, seed, k=K_SUBSPACE)

    # ---- content-level G6 CKA, G7 Procrustes, G8 crossnobis RDM ----
    Mp, ids_p = G.content_average(P, cP)
    Mi, ids_i = G.content_average(Im, cI)
    common = sorted(set(ids_p) & set(ids_i))
    Mp = np.stack([Mp[ids_p.index(c)] for c in common])
    Mi = np.stack([Mi[ids_i.index(c)] for c in common])
    out["G6_cka"] = content_metric_with_perm(G.linear_cka, Mp, Mi, seed)
    out["G7_procrustes_disparity"] = {"observed": G.procrustes_disparity(Mp, Mi)}
    fP = _folds_by_rep(cP, 4, seed)
    fI = _folds_by_rep(cI, 4, seed)
    Dp = G.crossnobis_rdm(P, cP, fP)
    Di = G.crossnobis_rdm(Im, cI, fI)
    # restrict RDMs to common content
    ip = [sorted(set(cP.tolist())).index(c) for c in common]
    ii = [sorted(set(cI.tolist())).index(c) for c in common]
    Dp, Di = Dp[np.ix_(ip, ip)], Di[np.ix_(ii, ii)]
    rng = np.random.default_rng(seed + 3)
    obs_rdm = G.rdm_correlation(Dp, Di)
    null_rdm = np.array([G.rdm_correlation(Dp, Di[np.ix_(pp, pp)])
                         for pp in (rng.permutation(len(common)) for _ in range(N_PERM))])
    out["G8_rdm_correlation"] = {"observed": float(obs_rdm),
                                 "perm_p": _p_from_null(obs_rdm, null_rdm, two_sided=False),
                                 "n_content": len(common)}

    # ---- CRITICAL SNR control: degrade P to I reliability, recompute vs I ----
    Pdeg = G.add_isotropic_noise_to_reliability(P, cP, target_reliability=relI, rng_seed=seed + 5)
    relPdeg = G.split_half_reliability(Pdeg, cP, seed, n_rep=100)
    snr = {"target_reliability": relI, "achieved_reliability": relPdeg}
    snr["G3_participation_ratio"] = state_metric_with_perm(
        G.participation_ratio, Pdeg, Im, n_match, seed + 6)
    snr["G4_subspace_overlap"] = state_metric_with_perm(
        G.subspace_overlap, Pdeg, Im, n_match, seed + 6, k=K_SUBSPACE)
    Mpdeg, ids_pd = G.content_average(Pdeg, cP)
    Mpdeg = np.stack([Mpdeg[ids_pd.index(c)] for c in common])
    snr["G6_cka_degP_vs_I"] = float(G.linear_cka(Mpdeg, Mi))
    snr["G6_cka_P_vs_degP"] = float(G.linear_cka(Mp, Mpdeg))
    # does degraded perception reproduce imagery's participation ratio (within CI)?
    prI = out["G3_participation_ratio"]["I_mean"]
    prPdeg = snr["G3_participation_ratio"]["P_mean"]
    snr["degP_reproduces_I_participation_ratio"] = bool(
        snr["G3_participation_ratio"]["diff_ci95"][0] <= 0 <= snr["G3_participation_ratio"]["diff_ci95"][1])
    snr["participation_ratio_I"] = prI
    snr["participation_ratio_degP"] = prPdeg
    out["SNR_matched_perception_control"] = snr

    # ---- Phase 7 negative controls ----
    # The shuffled-state-pairing / label-permutation controls are the perm nulls above.
    # gain-only model: does matching P's global amplitude to I reproduce I's dimensionality?
    alpha = out["G2_amplitude_gain"]["global_amplitude_ratio"]
    Pgain = (P - P.mean(0)) * alpha + Im.mean(0)
    controls = {
        "gain_only_participation_ratio_diff_vs_I": G.subsample_matched(
            G.participation_ratio, Pgain, Im, n_match, N_BOOT, seed + 10)["diff_mean"],
        "identity_participation_ratio_diff_vs_I": out["G3_participation_ratio"]["diff_mean"],
        "alpha_gain": float(alpha),
    }
    out["negative_controls"] = controls
    return out


def main() -> None:
    data_dir = Path(os.environ["C3G_DATA_DIR"])
    out_dir = Path(os.environ.get("C3G_OUT_DIR", data_dir / "results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    spaces_arg = os.environ.get("C3G_SPACES", "nsdgeneral")

    S = data_dir / "states"
    P_all = np.load(S / "setB_vision.npy").astype(np.float64)
    I_all = np.load(S / "setB_imagery.npy").astype(np.float64)
    cP = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_vision_meta.json"))])
    cI = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_imagery_meta.json"))])

    prf = np.load(data_dir / "roi" / "prf_visualrois_labels.npy")
    streams = np.load(data_dir / "roi" / "streams_labels.npy")
    fam = {
        "nsdgeneral": None,
        "V1": np.where(np.isin(prf, [1, 2]))[0], "V2": np.where(np.isin(prf, [3, 4]))[0],
        "V3": np.where(np.isin(prf, [5, 6]))[0], "hV4": np.where(prf == 7)[0],
        "ventral": np.where(np.isin(streams, [2, 5]))[0],
        "lateral": np.where(np.isin(streams, [3, 6]))[0],
        "parietal": np.where(np.isin(streams, [4, 7]))[0],
    }
    spaces = list(fam.keys()) if spaces_arg == "all" else spaces_arg.split(",")

    results = {}
    for sp in spaces:
        results[sp] = analyze_space(sp, fam[sp], P_all, I_all, cP, cI, SEED)
        print(f"[{sp}] reliab P={results[sp]['reliability']['P']:.3f} I={results[sp]['reliability']['I']:.3f} "
              f"PR diff={results[sp]['G3_participation_ratio']['diff_mean']:.2f} "
              f"(p={results[sp]['G3_participation_ratio']['perm_p']:.4f}) "
              f"subspace diff={results[sp]['G4_subspace_overlap']['diff_mean']:.3f} "
              f"RDM r={results[sp]['G8_rdm_correlation']['observed']:.3f} "
              f"SNRctrl reproduces PR="
              f"{results[sp]['SNR_matched_perception_control']['degP_reproduces_I_participation_ratio']}")

    obj = {"artifact": "C3G_ANALYSIS", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "seed": SEED, "n_perm": N_PERM, "n_boot": N_BOOT, "k_subspace": K_SUBSPACE,
           "spaces": results,
           "data_manifest_self_hash": json.load(open(data_dir / "c3g_data_manifest.json"))["self_hash"]}
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    tag = spaces_arg if spaces_arg != "all" else "all"
    json.dump(obj, open(out_dir / f"c3g_analysis_{tag}.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3g_analysis_{tag}.json")


if __name__ == "__main__":
    main()
