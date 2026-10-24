"""C3XC buffered accelerator for the run-pair(session)-disjoint reliability inference.

Same statistic and SAME numpy Generator draw order as c3xb_fast /
c3xb_reliability, but the per-split correlation uses PREALLOCATED buffers and
avoids the per-split ~O(ncat*V) array allocations that make the pure c3xb_fast
null pathologically slow when V ~ 17k voxels (D2 whole-brain VC) over 60k splits.

It is therefore BIT-IDENTICAL to the frozen estimator (asserted in
test_c3xc_fast_equivalence.py against c3xb_reliability, and on real Subject1
data before large-scale use). Balanced case only (one trial per (unit, content)),
which is exactly the D2 session structure; falls back is unnecessary here.
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.c3x_reliability import N_REP_POINT, N_REP_RESAMPLE
from app.research.fmri.c3xb_fast import _prep, _split_seq


def _sb(r):
    return 2 * r / (1 + r) if r < 1 else 1.0


def _corr_buf(Mcat, pa, pb, Abuf, Bbuf):
    """A = mean over units pa; B = mean over units pb; SB-corrected Pearson r of the
    across-content-demeaned, flattened halves. Uses preallocated Abuf/Bbuf (no per-call
    allocation of the ncat x V arrays). Numerically identical to
    _r_from_halves(Mcat[pa].mean(0), Mcat[pb].mean(0))."""
    Abuf[:] = 0.0
    for s in pa:
        Abuf += Mcat[s]
    Abuf /= len(pa)
    Bbuf[:] = 0.0
    for s in pb:
        Bbuf += Mcat[s]
    Bbuf /= len(pb)
    Abuf -= Abuf.mean(0)
    Bbuf -= Bbuf.mean(0)
    a = Abuf.ravel()
    b = Bbuf.ravel()
    denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-24
    return _sb(float(np.dot(a, b) / denom))


def _point(Mcat, upairs, seed, n_rep, Abuf, Bbuf):
    splits = _split_seq(upairs, seed, n_rep)
    if not splits:
        return 0.0
    return float(np.mean([_corr_buf(Mcat, pa, pb, Abuf, Bbuf) for pa, pb in splits]))


def reliability_with_inference_pairs_fast(X, content, pair, seed, n_perm=1000, n_boot=1000) -> dict:
    ids, upairs, Mcat, Xm, Lc, balanced = _prep(X, content, pair)
    if not balanced:
        raise ValueError("c3xc_fast requires the balanced case (one trial per (unit, content))")
    npairs = len(upairs)
    ncat = len(ids)
    V = Mcat.shape[2]
    Abuf = np.empty((ncat, V))
    Bbuf = np.empty((ncat, V))

    R = _point(Mcat, upairs, seed, N_REP_POINT, Abuf, Bbuf)

    splits60 = _split_seq(upairs, seed, N_REP_RESAMPLE)
    rngN = np.random.default_rng(seed + 1)
    set_order = list(set(int(x) for x in np.asarray(pair).tolist()))
    val2ix = {p: i for i, p in enumerate(upairs)}
    Mp = np.empty((npairs, ncat, V))
    null = np.empty(n_perm)
    for k in range(n_perm):
        for p in set_order:
            pi = val2ix[int(p)]
            perm = rngN.permutation(len(Lc[pi]))
            Mp[pi][Lc[pi][perm]] = Xm[pi]
        null[k] = float(np.mean([_corr_buf(Mp, pa, pb, Abuf, Bbuf) for pa, pb in splits60]))
    p = float((np.sum(null >= R) + 1) / (n_perm + 1))

    rng2 = np.random.default_rng(seed + 2)
    h = npairs // 2
    boot = np.empty(n_boot)
    for k in range(n_boot):
        perm = rng2.permutation(upairs)
        pa0, pb0 = perm[:h], perm[h:2 * h]
        pa = rng2.choice(pa0, len(pa0), replace=True)
        pb = rng2.choice(pb0, len(pb0), replace=True)
        pa_ix = [val2ix[int(v)] for v in pa]
        pb_ix = [val2ix[int(v)] for v in pb]
        boot[k] = _corr_buf(Mcat, pa_ix, pb_ix, Abuf, Bbuf)
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    seeds = [seed, seed + 100, seed + 200]
    robust = [_point(Mcat, upairs, s, N_REP_POINT, Abuf, Bbuf) for s in seeds]
    return {"reliability": float(R), "bootstrap_ci95": ci, "bootstrap_mean": float(boot.mean()),
            "null_mean": float(null.mean()), "null_std": float(null.std()), "perm_p_one_sided": p,
            "split_seed_values": [float(x) for x in robust],
            "split_seed_min": float(np.min(robust)), "split_seed_max": float(np.max(robust)),
            "n_perm": int(n_perm), "n_boot": int(n_boot), "n_pairs": int(npairs),
            "unit": "run_pair_disjoint", "fast_path": "c3xc_buffered"}
