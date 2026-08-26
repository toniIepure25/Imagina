"""C3G Phases 4-5 (SECONDARY / corroborative) — perception->imagery transform
hierarchy and content-invariance, subj01.

With only K=6 Set-B content items, supervised transforms are severely sample-
limited; this stage is explicitly UNDERPOWERED and cannot drive the primary C3G
decision (which rests on the unsupervised geometry of run_c3g_analysis). We fit a
nested hierarchy mapping perception content-patterns -> imagery content-patterns
with LEAVE-ONE-CONTENT-OUT CV, all fitting in a shared low-dim subspace (K-2
train items), and score held-out cosine against identity and capacity-matched
random maps.

Hierarchy: T0 identity, T1 scalar gain, T3 orthogonal Procrustes, T4 low-rank
linear. (T2 diagonal and T5/T6 are omitted as non-identifiable at K=6 and are
recorded as such.)

Content-invariance (H-common vs H-content) is assessed via the leave-one-content-
out generalization of a single shared transform: if one common low-capacity T
predicts held-out imagery content above identity and random, that supports a
content-invariant state transform; failure at K=6 is reported as underpowered,
NOT as evidence for content-dependence.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np

SEED = 20260826
N_RAND = 200


def _subspace(M, rank):
    Mc = M - M.mean(0, keepdims=True)
    _, _, Vt = np.linalg.svd(Mc, full_matrices=False)
    return Vt[:rank].T


def _cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-24))


def fit_apply(kind, Ptr, Itr, Pte, rank, seed=0):
    """Fit transform on train content patterns, predict held-out imagery pattern."""
    mp, mi = Ptr.mean(0), Itr.mean(0)
    B = _subspace(np.vstack([Ptr - mp, Itr - mi]), rank)          # [V, r]
    A = (Ptr - mp) @ B
    T = (Itr - mi) @ B
    x = (Pte - mp) @ B
    if kind == "T0_identity":
        yhat = (Pte - mp)
        return yhat + mi
    if kind == "T1_gain":
        alpha = float((A * T).sum() / ((A * A).sum() + 1e-24))
        return (x * alpha) @ B.T + mi
    if kind == "T3_procrustes":
        U, _, Vt = np.linalg.svd(A.T @ T, full_matrices=False)
        Om = U @ Vt
        return (x @ Om) @ B.T + mi
    if kind == "T4_lowrank":
        lam = 1.0
        Wm = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ T)
        return (x @ Wm) @ B.T + mi
    if kind == "random":
        rng = np.random.default_rng(seed)
        Q, _ = np.linalg.qr(rng.standard_normal((B.shape[1], B.shape[1])))
        return (x @ Q) @ B.T + mi
    raise ValueError(kind)


def loco(kind, Mp, Mi, rank, seed=0):
    """Leave-one-content-out held-out cosine between predicted and true imagery."""
    K = Mp.shape[0]
    cos = []
    for h in range(K):
        tr = [j for j in range(K) if j != h]
        yhat = fit_apply(kind, Mp[tr], Mi[tr], Mp[h], rank, seed=seed + h)
        cos.append(_cos(yhat, Mi[h] - Mi[tr].mean(0)))
    return float(np.mean(cos)), [float(c) for c in cos]


def main() -> None:
    data_dir = Path(os.environ["C3G_DATA_DIR"])
    out_dir = Path(os.environ.get("C3G_OUT_DIR", data_dir / "results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    S = data_dir / "states"
    P = np.load(S / "setB_vision.npy").astype(np.float64)
    Im = np.load(S / "setB_imagery.npy").astype(np.float64)
    cP = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_vision_meta.json"))])
    cI = np.array([r["content_pool_index"] for r in json.load(open(S / "setB_imagery_meta.json"))])
    ids = sorted(set(cP.tolist()) & set(cI.tolist()))
    Mp = np.stack([P[cP == c].mean(0) for c in ids])
    Mi = np.stack([Im[cI == c].mean(0) for c in ids])
    K = len(ids)
    rank = K - 2   # shared subspace dim: train items minus 1

    hierarchy = {}
    for kind in ["T0_identity", "T1_gain", "T3_procrustes", "T4_lowrank"]:
        m, per = loco(kind, Mp, Mi, rank)
        hierarchy[kind] = {"heldout_cosine_mean": m, "per_content": per}

    # capacity-matched random maps (same shared-subspace rank)
    rand = [loco("random", Mp, Mi, rank, seed=SEED + 1000 + i)[0] for i in range(N_RAND)]
    rand = np.asarray(rand)
    idc = hierarchy["T0_identity"]["heldout_cosine_mean"]
    best = max(("T1_gain", "T3_procrustes", "T4_lowrank"),
               key=lambda k: hierarchy[k]["heldout_cosine_mean"])
    best_val = hierarchy[best]["heldout_cosine_mean"]

    obj = {
        "artifact": "C3G_TRANSFORMS_SECONDARY",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "UNDERPOWERED_K6_SECONDARY_DOES_NOT_DRIVE_PRIMARY_DECISION",
        "n_content": K, "shared_subspace_rank": rank, "seed": SEED,
        "hierarchy_heldout_cosine": {k: v["heldout_cosine_mean"] for k, v in hierarchy.items()},
        "hierarchy_detail": hierarchy,
        "identity_heldout_cosine": idc,
        "best_learned_transform": best, "best_learned_heldout_cosine": best_val,
        "capacity_matched_random": {
            "n": N_RAND, "mean": float(rand.mean()), "pct95": float(np.percentile(rand, 95)),
            "max": float(rand.max())},
        "best_beats_identity": bool(best_val > idc),
        "best_beats_random_95pct": bool(best_val > np.percentile(rand, 95)),
        "content_invariance_note": (
            "H-common vs H-content is not separable at K=6 with a leakage-free split; a common "
            "low-capacity transform generalizing to held-out content above identity+random would "
            "support content-invariance, but absence of such generalization here is UNDERPOWERED, "
            "not evidence for content-dependence."),
        "omitted_transforms": {"T2_diagonal": "non-identifiable at K=6",
                               "T5_covariance": "coincides with frozen C3M correction",
                               "T6_nonlinear": "not justified; linear stage underpowered"},
    }
    obj["self_hash"] = hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
    json.dump(obj, open(out_dir / "c3g_transforms.json", "w"), indent=2)
    print(f"Wrote {out_dir}/c3g_transforms.json")
    print(json.dumps({"identity": idc, "hierarchy": obj["hierarchy_heldout_cosine"],
                      "best": best, "beats_identity": obj["best_beats_identity"],
                      "beats_random95": obj["best_beats_random_95pct"],
                      "rand95": obj["capacity_matched_random"]["pct95"]}, indent=2))


if __name__ == "__main__":
    main()
