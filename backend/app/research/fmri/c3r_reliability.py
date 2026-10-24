"""C3R imagery-reliability screen — inference wrappers around the INHERITED C3G
split-half reliability estimator (app.research.fmri.c3g_geometry.split_half_
reliability). This module adds ONLY the sealed permutation null, bootstrap CI,
split-seed robustness, and the reliability-gate decision rules. It deliberately
imports NO geometry function and exposes none: C3R must decide participant
eligibility WITHOUT observing any state-geometry endpoint.

Primary quantity: R_I = Set-B imagery stimulus-pattern split-half reliability in
nsdgeneral. Same estimator/preprocessing as C3G. Null destroys stable stimulus
identity (permute the content-label vector, which preserves 16 reps/content, the
trial/run structure and the ROI dimension) and recomputes reliability with the
same estimator. Bootstrap resamples reps within content.
"""
from __future__ import annotations

import numpy as np

from app.research.fmri.c3g_geometry import split_half_reliability

# Guard: C3R must not call geometry endpoints. Referenced by tests.
FORBIDDEN_GEOMETRY = ("participation_ratio", "subspace_overlap", "principal_angles",
                      "linear_cka", "procrustes_disparity", "crossnobis_rdm")

N_REP_POINT = 200
N_REP_RESAMPLE = 60


def _splithalf_bootstrap_value(X: np.ndarray, content: np.ndarray, rng: np.random.Generator,
                               eps: float = 1e-24) -> float:
    """One split-half reliability draw with a VALID (non-straddling) bootstrap:
    each content's reps are split into two DISJOINT halves first, then reps are
    resampled with replacement WITHIN each half. This preserves the split-half
    logic (no physical trial can appear in both halves, which would spuriously
    inflate the correlation), then Pearson-r of the concatenated 6-content mean
    patterns across halves, Spearman-Brown corrected -- matching the inherited
    estimator's statistic."""
    ids = sorted(set(int(c) for c in content))
    A, B = [], []
    for c in ids:
        idx = np.where(content == c)[0]
        idx = idx[rng.permutation(len(idx))]
        h = len(idx) // 2
        h1, h2 = idx[:h], idx[h:2 * h]
        a = rng.choice(h1, len(h1), replace=True)
        b = rng.choice(h2, len(h2), replace=True)
        A.append(X[a].mean(0))
        B.append(X[b].mean(0))
    A, B = np.asarray(A), np.asarray(B)
    av = (A - A.mean(0)).ravel()
    bv = (B - B.mean(0)).ravel()
    r = float(np.dot(av, bv) / (np.linalg.norm(av) * np.linalg.norm(bv) + eps))
    return 2 * r / (1 + r) if r < 1 else 1.0


def reliability_with_inference(X: np.ndarray, content: np.ndarray, seed: int,
                               n_perm: int = 1000, n_boot: int = 1000) -> dict:
    """Observed reliability + permutation p + bootstrap CI + split-seed robustness."""
    R = split_half_reliability(X, content, seed, n_rep=N_REP_POINT)

    rng = np.random.default_rng(seed + 1)
    null = np.array([split_half_reliability(X, rng.permutation(content), seed, n_rep=N_REP_RESAMPLE)
                     for _ in range(n_perm)])
    p_one_sided = float((np.sum(null >= R) + 1) / (n_perm + 1))

    rng2 = np.random.default_rng(seed + 2)
    boot = np.array([_splithalf_bootstrap_value(X, content, rng2) for _ in range(n_boot)])
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    seeds = [seed, seed + 100, seed + 200]
    robust = [split_half_reliability(X, content, s, n_rep=N_REP_POINT) for s in seeds]

    return {"reliability": float(R),
            "bootstrap_ci95": ci, "bootstrap_mean": float(boot.mean()),
            "null_mean": float(null.mean()), "null_std": float(null.std()),
            "perm_p_one_sided": p_one_sided,
            "split_seed_values": [float(x) for x in robust],
            "split_seed_min": float(np.min(robust)), "split_seed_max": float(np.max(robust)),
            "n_perm": int(n_perm), "n_boot": int(n_boot), "n_rep_point": N_REP_POINT}


def reliability_gate(res: dict) -> str:
    """Sealed reliability-gate rule from the observed-reliability inference dict."""
    R = res["reliability"]
    ci_lo = res["bootstrap_ci95"][0]
    p = res["perm_p_one_sided"]
    seed_stable = min(res["split_seed_values"]) > 0
    if R > 0 and p < 0.05 and ci_lo > 0 and seed_stable:
        return "RELIABILITY_PASS"
    if R <= 0:
        return "RELIABILITY_NOISE_FLOOR"
    # positive point estimate but CI includes 0 or p>=0.05
    if ci_lo <= 0 or p >= 0.05:
        return "RELIABILITY_MARGINAL"
    return "RELIABILITY_MARGINAL"


def vision_imagery_quality(R_vision: dict, R_imagery: dict) -> str:
    """Classify session/participant quality from vision and imagery gates."""
    gv = reliability_gate(R_vision)
    gi = reliability_gate(R_imagery)
    if gv == "RELIABILITY_PASS" and gi == "RELIABILITY_PASS":
        return "VISION_RELIABLE_IMAGERY_RELIABLE"
    if gv == "RELIABILITY_PASS" and gi in ("RELIABILITY_NOISE_FLOOR", "RELIABILITY_MARGINAL"):
        return "VISION_RELIABLE_IMAGERY_NOISE_FLOOR"
    if gv != "RELIABILITY_PASS":
        return "VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER"
    return "VISION_RELIABLE_IMAGERY_NOISE_FLOOR"


def practical_effect_flags(R: float) -> dict:
    """Descriptive practical-effect bins (NOT significance thresholds)."""
    return {"R_gt_0p05": bool(R > 0.05), "R_gt_0p10": bool(R > 0.10), "R_gt_0p20": bool(R > 0.20)}
