"""Vectorized fast-path for the C3XB run-pair-disjoint reliability inference.

This is NOT a new estimator: it reproduces the FROZEN c3xb_reliability.
reliability_with_inference_pairs BIT-IDENTICALLY by (a) consuming the numpy
Generator draws in the exact same order and (b) exploiting the GOD balance
(each run-pair has exactly one trial per category) so category-half means are
averages of precomputed per-(pair,category) patterns instead of repeated
np.where scans over the trial axis. Equivalence is asserted against the frozen
estimator on real data in run_c3xb_fast_screen (Subject1) and on synthetic
fixtures in test_c3xb_fast.py. The frozen estimator remains the definition; this
is only an accelerator so the 5-subject screen is tractable where a single
frozen subject takes ~90 min.
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.c3x_reliability import N_REP_POINT, N_REP_RESAMPLE, _r_from_halves


def _prep(X, content, pair):
    content = np.asarray(content)
    pair = np.asarray(pair)
    ids = sorted(set(int(c) for c in content))
    upairs = sorted(set(int(p) for p in pair.tolist()))
    cat_ix = {c: i for i, c in enumerate(ids)}
    V = X.shape[1]
    ncat = len(ids)
    # per-pair: trial data (in trial order), trial labels, and category-indexed means
    Xm, Lc, Mcat = [], [], []
    balanced = True
    for p in upairs:
        m = np.where(pair == p)[0]
        Xp = X[m]
        Lp = np.array([cat_ix[int(c)] for c in content[m]])
        Xm.append(Xp)
        Lc.append(Lp)
        Mc = np.full((ncat, V), np.nan)
        # category-indexed mean over the (>=1) trials of that category in this pair
        for c in range(ncat):
            sel = np.where(Lp == c)[0]
            if len(sel):
                Mc[c] = Xp[sel].mean(0)
            else:
                balanced = False
        Mcat.append(Mc)
    return ids, upairs, np.array(Mcat), Xm, Lc, balanced


def _split_seq(upairs, seed, n):
    """First n (pa_idx, pb_idx) splits from default_rng(seed) — indices into upairs order."""
    val2ix = {p: i for i, p in enumerate(upairs)}
    rng = np.random.default_rng(seed)
    h = len(upairs) // 2
    out = []
    for _ in range(n):
        perm = rng.permutation(upairs)  # frozen passes the list; values==pair ids
        pa = np.array([val2ix[int(v)] for v in perm[:h]])
        pb = np.array([val2ix[int(v)] for v in perm[h:2 * h]])
        out.append((pa, pb))
    return out


def _r_from_M(Mcat, pa, pb, balanced=True):
    # balanced (GOD): every category present in every pair -> plain mean, keep all 50.
    # Bit-identical to the frozen _content_means+_r_from_halves in that case, and far
    # faster than nanmean/isnan. The general (unbalanced) branch mirrors the frozen skip.
    if balanced:
        return _r_from_halves(Mcat[pa].mean(0), Mcat[pb].mean(0))
    A = np.nanmean(Mcat[pa], axis=0)
    B = np.nanmean(Mcat[pb], axis=0)
    keep = (~np.isnan(A).any(1)) & (~np.isnan(B).any(1))
    if keep.sum() < 2:
        return None
    return _r_from_halves(A[keep], B[keep])


def _point(Mcat, upairs, seed, n_rep, balanced=True):
    splits = _split_seq(upairs, seed, n_rep)
    vals = [r for pa, pb in splits if (r := _r_from_M(Mcat, pa, pb, balanced)) is not None]
    return float(np.mean(vals)) if vals else 0.0


def reliability_with_inference_pairs_fast(X, content, pair, seed, n_perm=1000, n_boot=1000) -> dict:
    ids, upairs, Mcat, Xm, Lc, balanced = _prep(X, content, pair)
    npairs = len(upairs)
    ncat = len(ids)
    R = _point(Mcat, upairs, seed, N_REP_POINT, balanced)

    # permutation null: outer rng(seed+1) consumed ONLY by within-pair label shuffles;
    # the inner 60 splits come from a fresh rng(seed) and are identical every perm.
    splits60 = _split_seq(upairs, seed, N_REP_RESAMPLE)
    rngN = np.random.default_rng(seed + 1)
    pair_arr = np.asarray(pair)
    set_order = list(set(int(x) for x in pair_arr.tolist()))  # match frozen iteration order
    val2ix = {p: i for i, p in enumerate(upairs)}
    V = Mcat.shape[2]
    null = np.empty(n_perm)
    Mp = np.empty((npairs, ncat, V))
    for k in range(n_perm):
        for p in set_order:
            pi = val2ix[int(p)]
            perm = rngN.permutation(len(Lc[pi]))
            if not balanced:
                Mp[pi].fill(np.nan)
            Mp[pi][Lc[pi][perm]] = Xm[pi]
        vals = [r for pa, pb in splits60 if (r := _r_from_M(Mp, pa, pb, balanced)) is not None]
        null[k] = float(np.mean(vals)) if vals else 0.0
    p = float((np.sum(null >= R) + 1) / (n_perm + 1))

    # non-straddling hierarchical bootstrap: rng(seed+2)
    rng2 = np.random.default_rng(seed + 2)
    h = npairs // 2
    boot = np.empty(n_boot)
    for k in range(n_boot):
        perm = rng2.permutation(upairs)
        pa0, pb0 = perm[:h], perm[h:2 * h]
        pa = rng2.choice(pa0, len(pa0), replace=True)
        pb = rng2.choice(pb0, len(pb0), replace=True)
        pa_ix = np.array([val2ix[int(v)] for v in pa])
        pb_ix = np.array([val2ix[int(v)] for v in pb])
        r = _r_from_M(Mcat, pa_ix, pb_ix, balanced)
        boot[k] = r if r is not None else 0.0
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    seeds = [seed, seed + 100, seed + 200]
    robust = [_point(Mcat, upairs, s, N_REP_POINT, balanced) for s in seeds]
    return {"reliability": float(R), "bootstrap_ci95": ci, "bootstrap_mean": float(boot.mean()),
            "null_mean": float(null.mean()), "null_std": float(null.std()), "perm_p_one_sided": p,
            "split_seed_values": [float(x) for x in robust],
            "split_seed_min": float(np.min(robust)), "split_seed_max": float(np.max(robust)),
            "n_perm": int(n_perm), "n_boot": int(n_boot), "n_pairs": int(npairs),
            "unit": "run_pair_disjoint", "fast_path": True}
