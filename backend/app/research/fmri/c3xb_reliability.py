"""C3XB run-pair-disjoint imagery-reliability estimator (GOD category imagery).

Scientific definition is IDENTICAL to C3G/C3R/C3X: repeatability of content-specific
multivoxel patterns across INDEPENDENT acquisitions, measured as the Pearson r of the
concatenated content-mean patterns of two disjoint halves, Spearman-Brown corrected.
The ONLY thing that changes here is the INDEPENDENT UNIT used to form the halves.

In GOD imagery the acquisition is balanced at the level of a 2-RUN PAIR: every two
consecutive runs cover all 50 categories exactly once (verified empirically in Phase 1;
BLOCKED_GOD_RUN_CATEGORY_CONTRACT otherwise). There are 10 such pairs -> 10 reps/category.
Splitting on whole run-PAIRS (5 vs 5) gives each half exactly 5 reps of every category,
keeps the acquisition balance intact, and guarantees no physical trial straddles halves.

Core statistic primitives (`_content_means`, `_r_from_halves`) are IMPORTED UNCHANGED from
c3x_reliability, so the estimated quantity is provably the same statistic as C3X/C3R/C3G;
only the unit of the split differs. On a fixture where the pair labelling equals the run
labelling, this estimator reduces EXACTLY to c3x_reliability.run_disjoint_reliability
(proved in test_c3xb_reliability.py::test_reduces_to_c3x_run_disjoint).

Imports NO geometry function and exposes none: C3XB qualifies a dataset WITHOUT observing
any geometry endpoint.
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.c3x_reliability import (  # reuse the EXACT C3X statistic
    FORBIDDEN_GEOMETRY,
    N_REP_POINT,
    N_REP_RESAMPLE,
    _content_means,
    _r_from_halves,
    dataset_gate,
    subject_quality_class,
    subject_reliability_gate,
)

__all__ = [
    "run_pair_disjoint_reliability",
    "reliability_with_inference_pairs",
    "subject_reliability_gate",
    "subject_quality_class",
    "dataset_gate",
    "FORBIDDEN_GEOMETRY",
]


def _split_pairs(upairs, rng):
    """Assign the independent units (run-pairs) to two disjoint halves (5 vs 5)."""
    perm = rng.permutation(upairs)
    h = len(upairs) // 2
    return perm[:h], perm[h:2 * h]


def run_pair_disjoint_reliability(X, content, pair, seed, n_rep=N_REP_POINT) -> float:
    """Mean run-pair-disjoint split-half reliability over n_rep random pair-splits.

    pair: integer id of the 2-run pair each trial belongs to (the independent unit).
    Falls back to c3x behaviour only in the degenerate case of <2 distinct pairs.
    """
    content = np.asarray(content)
    pair = np.asarray(pair)
    ids = sorted(set(int(c) for c in content))
    upairs = sorted(set(int(p) for p in pair.tolist()))
    if len(upairs) < 2:
        return 0.0
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_rep):
        pa, pb = _split_pairs(upairs, rng)
        idxA = np.where(np.isin(pair, pa))[0]
        idxB = np.where(np.isin(pair, pb))[0]
        A, B, keep = _content_means(X, content, idxA, idxB, ids)
        if A is not None:
            vals.append(_r_from_halves(A, B))
    return float(np.mean(vals)) if vals else 0.0


def _permute_within_pairs(content, pair, rng):
    """Permutation null: shuffle category identities WITHIN each run-pair.

    Preserves the run-pair acquisition structure and each pair's category composition,
    but destroys the cross-pair category correspondence, so the null tests reproducible
    category-specific pattern structure and nothing else.
    """
    out = np.array(content, copy=True)
    for p in set(int(x) for x in pair.tolist()):
        m = np.where(pair == p)[0]
        out[m] = content[m][rng.permutation(len(m))]
    return out


def _bootstrap_value_pairs(X, content, pair, rng, ids, upairs) -> float:
    """Non-straddling hierarchical bootstrap draw.

    Fix a disjoint 5-vs-5 run-pair split, then resample the INDEPENDENT UNITS
    (run-pairs) WITHIN each half with replacement. A physical trial can never enter
    both halves (non-straddling); resampling whole pairs propagates between-pair
    (between-acquisition) variance -- the hierarchical level that matters.
    """
    pa, pb = _split_pairs(upairs, rng)
    pa = rng.choice(pa, len(pa), replace=True)
    pb = rng.choice(pb, len(pb), replace=True)

    def _means(sel_pairs):
        rows = []
        for c in ids:
            vecs = []
            for p in sel_pairs:
                idx = np.where((pair == p) & (content == c))[0]
                if len(idx):
                    vecs.append(X[idx].mean(0))
            if vecs:
                rows.append((c, np.mean(vecs, 0)))
        return dict(rows)

    ma, mb = _means(pa), _means(pb)
    common = [c for c in ids if c in ma and c in mb]
    if len(common) < 2:
        return 0.0
    A = np.asarray([ma[c] for c in common])
    B = np.asarray([mb[c] for c in common])
    return _r_from_halves(A, B)


def reliability_with_inference_pairs(X, content, pair, seed, n_perm=1000, n_boot=1000) -> dict:
    """Point estimate + permutation null + non-straddling hierarchical bootstrap +
    seed robustness. Returns the SAME dict schema as c3x_reliability so the frozen
    subject_reliability_gate / dataset_gate apply unchanged."""
    content = np.asarray(content)
    pair = np.asarray(pair)
    ids = sorted(set(int(c) for c in content))
    upairs = sorted(set(int(p) for p in pair.tolist()))
    R = run_pair_disjoint_reliability(X, content, pair, seed, n_rep=N_REP_POINT)

    rng = np.random.default_rng(seed + 1)
    null = np.array([run_pair_disjoint_reliability(X, _permute_within_pairs(content, pair, rng),
                                                   pair, seed, n_rep=N_REP_RESAMPLE)
                     for _ in range(n_perm)])
    p = float((np.sum(null >= R) + 1) / (n_perm + 1))

    rng2 = np.random.default_rng(seed + 2)
    boot = np.array([_bootstrap_value_pairs(X, content, pair, rng2, ids, upairs) for _ in range(n_boot)])
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    seeds = [seed, seed + 100, seed + 200]
    robust = [run_pair_disjoint_reliability(X, content, pair, s, n_rep=N_REP_POINT) for s in seeds]
    return {"reliability": float(R), "bootstrap_ci95": ci, "bootstrap_mean": float(boot.mean()),
            "null_mean": float(null.mean()), "null_std": float(null.std()), "perm_p_one_sided": p,
            "split_seed_values": [float(x) for x in robust],
            "split_seed_min": float(np.min(robust)), "split_seed_max": float(np.max(robust)),
            "n_perm": int(n_perm), "n_boot": int(n_boot), "n_pairs": int(len(upairs)),
            "unit": "run_pair_disjoint"}
