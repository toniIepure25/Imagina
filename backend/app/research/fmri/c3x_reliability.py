"""C3X dataset-agnostic imagery-reliability estimator.

Scientific definition (unchanged from C3G/C3R): repeatability of stimulus-specific
multivoxel patterns across INDEPENDENT trials/runs. Where the dataset has multiple
acquisition runs we prefer RUN-DISJOINT split halves (half A = a set of whole
runs, half B = the complementary runs), balanced for content identity, so no
physical trial and — preferably — no whole run can enter both halves. This better
measures reproducibility across acquisitions than an arbitrary within-run split.

On a fixture with no run structure the run-disjoint estimator reduces to the C3G
split-half quantity (same statistic: Pearson r of the concatenated content-mean
patterns across halves, Spearman-Brown corrected). This module imports NO geometry
function and exposes none: C3X qualifies datasets WITHOUT observing any geometry
endpoint.
"""
from __future__ import annotations

import numpy as np

FORBIDDEN_GEOMETRY = ("participation_ratio", "subspace_overlap", "principal_angles",
                      "linear_cka", "procrustes_disparity", "crossnobis_rdm")

N_REP_POINT = 200
N_REP_RESAMPLE = 60


def _sb(r: float) -> float:
    return 2 * r / (1 + r) if r < 1 else 1.0


def _r_from_halves(A: np.ndarray, B: np.ndarray, eps: float = 1e-24) -> float:
    a = (A - A.mean(0)).ravel()
    b = (B - B.mean(0)).ravel()
    return _sb(float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + eps)))


def _content_means(X, content, idxA, idxB, ids):
    A, B, keep = [], [], []
    for c in ids:
        ca = np.intersect1d(np.where(content == c)[0], idxA, assume_unique=False)
        cb = np.intersect1d(np.where(content == c)[0], idxB, assume_unique=False)
        if len(ca) == 0 or len(cb) == 0:
            continue
        A.append(X[ca].mean(0))
        B.append(X[cb].mean(0))
        keep.append(c)
    return (np.asarray(A), np.asarray(B), keep) if len(keep) >= 2 else (None, None, keep)


def run_disjoint_reliability(X, content, run, seed, n_rep=N_REP_POINT) -> float:
    """Mean run-disjoint split-half reliability over n_rep random run-splits.
    Falls back to a per-content rep split when there is no usable run structure."""
    content = np.asarray(content)
    ids = sorted(set(int(c) for c in content))
    rng = np.random.default_rng(seed)
    runs = np.asarray(run)
    uruns = sorted(set(int(r) for r in runs.tolist()))
    vals = []
    use_runs = len(uruns) >= 2
    for _ in range(n_rep):
        if use_runs:
            perm = rng.permutation(uruns)
            h = len(uruns) // 2
            idxA = np.where(np.isin(runs, perm[:h]))[0]
            idxB = np.where(np.isin(runs, perm[h:2 * h]))[0]
        else:
            idxA, idxB = _percontent_split(content, ids, rng)
        A, B, keep = _content_means(X, content, idxA, idxB, ids)
        if A is not None:
            vals.append(_r_from_halves(A, B))
    return float(np.mean(vals)) if vals else 0.0


def _percontent_split(content, ids, rng):
    idxA, idxB = [], []
    for c in ids:
        idx = np.where(content == c)[0]
        idx = idx[rng.permutation(len(idx))]
        h = len(idx) // 2
        idxA.extend(idx[:h].tolist())
        idxB.extend(idx[h:2 * h].tolist())
    return np.array(idxA), np.array(idxB)


def _bootstrap_value(X, content, run, rng, ids) -> float:
    """Non-straddling bootstrap draw: fixed run-disjoint (or per-content) halves,
    then resample trials WITHIN each half with replacement."""
    content = np.asarray(content)
    runs = np.asarray(run)
    uruns = sorted(set(int(r) for r in runs.tolist()))
    if len(uruns) >= 2:
        perm = rng.permutation(uruns)
        h = len(uruns) // 2
        idxA = np.where(np.isin(runs, perm[:h]))[0]
        idxB = np.where(np.isin(runs, perm[h:2 * h]))[0]
    else:
        idxA, idxB = _percontent_split(content, ids, rng)
    A, B = [], []
    for c in ids:
        ca = np.intersect1d(np.where(content == c)[0], idxA)
        cb = np.intersect1d(np.where(content == c)[0], idxB)
        if len(ca) == 0 or len(cb) == 0:
            continue
        A.append(X[rng.choice(ca, len(ca), replace=True)].mean(0))
        B.append(X[rng.choice(cb, len(cb), replace=True)].mean(0))
    return _r_from_halves(np.asarray(A), np.asarray(B)) if len(A) >= 2 else 0.0


def reliability_with_inference(X, content, run, seed, n_perm=1000, n_boot=1000) -> dict:
    content = np.asarray(content)
    ids = sorted(set(int(c) for c in content))
    R = run_disjoint_reliability(X, content, run, seed, n_rep=N_REP_POINT)

    rng = np.random.default_rng(seed + 1)
    null = np.array([run_disjoint_reliability(X, rng.permutation(content), run, seed,
                                              n_rep=N_REP_RESAMPLE) for _ in range(n_perm)])
    p = float((np.sum(null >= R) + 1) / (n_perm + 1))

    rng2 = np.random.default_rng(seed + 2)
    boot = np.array([_bootstrap_value(X, content, run, rng2, ids) for _ in range(n_boot)])
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    seeds = [seed, seed + 100, seed + 200]
    robust = [run_disjoint_reliability(X, content, run, s, n_rep=N_REP_POINT) for s in seeds]
    return {"reliability": float(R), "bootstrap_ci95": ci, "bootstrap_mean": float(boot.mean()),
            "null_mean": float(null.mean()), "null_std": float(null.std()), "perm_p_one_sided": p,
            "split_seed_values": [float(x) for x in robust],
            "split_seed_min": float(np.min(robust)), "split_seed_max": float(np.max(robust)),
            "n_perm": int(n_perm), "n_boot": int(n_boot), "run_disjoint": bool(len(set(np.asarray(run).tolist())) >= 2)}


# --------------------------------------------------------------------------- #
# gates (subject-level like C3R; dataset-level requires >=2 passing subjects)
# --------------------------------------------------------------------------- #
def subject_reliability_gate(res: dict) -> str:
    R = res["reliability"]
    ci_lo = res["bootstrap_ci95"][0]
    p = res["perm_p_one_sided"]
    stable = min(res["split_seed_values"]) > 0
    if R > 0 and p < 0.05 and ci_lo > 0 and stable:
        return "SUBJECT_RELIABILITY_PASS"
    if R <= 0:
        return "SUBJECT_RELIABILITY_NOISE_FLOOR"
    return "SUBJECT_RELIABILITY_MARGINAL"


def subject_quality_class(R_vision: dict, R_imagery: dict) -> str:
    gv = subject_reliability_gate(R_vision)
    gi = subject_reliability_gate(R_imagery)
    if gv == "SUBJECT_RELIABILITY_PASS" and gi == "SUBJECT_RELIABILITY_PASS":
        return "VISION_RELIABLE_IMAGERY_RELIABLE"
    if gv == "SUBJECT_RELIABILITY_PASS":
        return "VISION_RELIABLE_IMAGERY_NOISE_FLOOR"
    return "VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER"


def dataset_gate(subject_results: dict) -> str:
    """subject_results: {subj: {'imagery': res, 'vision': res}}. Dataset PASS needs
    >=2 subjects with imagery PASS AND matched perception reliable."""
    n_pass = 0
    n_quality_block = 0
    n_promising = 0
    for _, r in subject_results.items():
        gi = subject_reliability_gate(r["imagery"])
        gv = subject_reliability_gate(r["vision"])
        if gv != "SUBJECT_RELIABILITY_PASS":
            n_quality_block += 1
            continue
        if gi == "SUBJECT_RELIABILITY_PASS":
            n_pass += 1
        elif gi == "SUBJECT_RELIABILITY_MARGINAL" and r["imagery"]["reliability"] > 0:
            n_promising += 1
    if n_pass >= 2:
        return "DATASET_RELIABILITY_PASS"
    if n_pass == 1 or n_promising >= 1:
        return "DATASET_RELIABILITY_PROMISING"
    if n_quality_block == len(subject_results) and len(subject_results) > 0:
        return "DATASET_QUALITY_BLOCKED"
    return "DATASET_RELIABILITY_FAIL"
