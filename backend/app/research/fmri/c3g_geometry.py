"""C3G geometry library — deterministic representational-geometry metrics for
comparing two neural state distributions (perception P vs imagery I) in a shared
voxel space. Pure functions; all randomness is explicit (np.random.Generator).

Design notes
------------
- Voxel dimension V (e.g. 15587) >> trial count n, so covariances are rank-
  deficient; eigenspectra are computed from the n x n Gram (trial covariance),
  giving the min(n-1, V) nonzero eigenvalues.
- Many geometry statistics (participation ratio, subspace angles) depend on n.
  To compare P and I fairly we ALWAYS subsample both states to a common trial
  count n_match, averaging the statistic over `n_boot` random equal-n draws.
- Content-level metrics (CKA, Procrustes, RDM/crossnobis) operate on the K
  content-averaged patterns (K=6 Set-B items) present in both states.
"""
from __future__ import annotations

import numpy as np

Array = np.ndarray


# --------------------------------------------------------------------------- #
# basic distributional statistics
# --------------------------------------------------------------------------- #
def centroid_displacement(P: Array, Im: Array) -> float:
    """‖mean_I − mean_P‖ normalized by the pooled within-state RMS voxel scatter."""
    mp, mi = P.mean(0), Im.mean(0)
    pooled = np.sqrt(0.5 * (P.var(0).mean() + Im.var(0).mean())) + 1e-12
    return float(np.linalg.norm(mi - mp) / (np.sqrt(P.shape[1]) * pooled))


def amplitude_gain(P: Array, Im: Array) -> dict:
    """Global amplitude ratio and per-voxel std-ratio summary (Im relative to P)."""
    tp = float(P.var(0, ddof=1).sum())
    ti = float(Im.var(0, ddof=1).sum())
    sp = np.clip(P.std(0, ddof=1), 1e-12, None)
    si = Im.std(0, ddof=1)
    ratio = si / sp
    return {"global_amplitude_ratio": float(np.sqrt(ti / (tp + 1e-12))),
            "voxel_std_ratio_median": float(np.median(ratio)),
            "voxel_std_ratio_iqr": [float(np.percentile(ratio, 25)), float(np.percentile(ratio, 75))]}


def _gram_eigs(Xc: Array) -> Array:
    """Nonneg eigenvalues of the trial covariance via the n x n Gram (descending)."""
    n = Xc.shape[0]
    G = (Xc @ Xc.T) / max(n - 1, 1)
    ev = np.linalg.eigvalsh(G)
    return np.clip(ev[::-1], 0, None)


def participation_ratio(X: Array) -> float:
    """Effective dimensionality PR = (Σλ)^2 / Σλ^2 of the trial covariance."""
    ev = _gram_eigs(X - X.mean(0, keepdims=True))
    s1, s2 = ev.sum(), (ev ** 2).sum()
    return float(s1 * s1 / (s2 + 1e-24)) if s2 > 0 else 0.0


def covariance_subspace(X: Array, k: int) -> Array:
    """Top-k voxel-space principal directions (V x k) of the trial covariance,
    via the Gram eigenvectors lifted to voxel space."""
    Xc = X - X.mean(0, keepdims=True)
    n = Xc.shape[0]
    G = (Xc @ Xc.T) / max(n - 1, 1)
    w, U = np.linalg.eigh(G)                    # ascending
    idx = np.argsort(w)[::-1][:k]
    w = np.clip(w[idx], 1e-12, None)
    # voxel-space loadings: B = Xc^T U / sqrt((n-1) w), columns orthonormal
    B = (Xc.T @ U[:, idx]) / np.sqrt((n - 1) * w)
    # re-orthonormalize for numerical safety
    Q, _ = np.linalg.qr(B)
    return Q[:, :k]


def principal_angles(P: Array, Im: Array, k: int) -> Array:
    """Principal angles (radians, ascending) between the top-k P and Im subspaces."""
    Bp, Bi = covariance_subspace(P, k), covariance_subspace(Im, k)
    s = np.linalg.svd(Bp.T @ Bi, compute_uv=False)
    return np.arccos(np.clip(s, -1.0, 1.0))


def subspace_overlap(P: Array, Im: Array, k: int) -> float:
    """Mean cos^2 of the top-k principal angles (1 = identical subspace, 0 = orthogonal)."""
    ang = principal_angles(P, Im, k)
    return float(np.mean(np.cos(ang) ** 2))


def eigenspectrum_logdivergence(P: Array, Im: Array, n_top: int) -> float:
    """L2 distance between the log-normalized top eigenvalue profiles of P and Im."""
    ep = _gram_eigs(P - P.mean(0, keepdims=True))[:n_top]
    ei = _gram_eigs(Im - Im.mean(0, keepdims=True))[:n_top]
    m = min(len(ep), len(ei))
    ep, ei = ep[:m] / (ep[:m].sum() + 1e-24), ei[:m] / (ei[:m].sum() + 1e-24)
    lp, li = np.log(ep + 1e-12), np.log(ei + 1e-12)
    return float(np.linalg.norm(lp - li) / np.sqrt(m))


def subsample_matched(fn, P: Array, Im: Array, n_match: int, n_boot: int, seed: int, **kw) -> dict:
    """Average a distributional statistic over equal-n random subsamples of P and Im.
    Returns the two states' bootstrap means, their difference, and a CI on the diff."""
    rng = np.random.default_rng(seed)
    vp, vi = [], []
    for _ in range(n_boot):
        ip = rng.choice(P.shape[0], n_match, replace=False)
        ii = rng.choice(Im.shape[0], n_match, replace=False)
        vp.append(fn(P[ip], **kw))
        vi.append(fn(Im[ii], **kw))
    vp, vi = np.asarray(vp), np.asarray(vi)
    diff = vi - vp
    return {"P_mean": float(vp.mean()), "I_mean": float(vi.mean()),
            "diff_mean": float(diff.mean()),
            "diff_ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
            "n_match": int(n_match), "n_boot": int(n_boot)}


# --------------------------------------------------------------------------- #
# content-level metrics (K content-averaged patterns present in both states)
# --------------------------------------------------------------------------- #
def content_average(X: Array, content: Array) -> tuple[Array, list]:
    """Mean pattern per content id. Returns (K x V, ordered content ids)."""
    ids = sorted(set(int(c) for c in content))
    M = np.stack([X[content == c].mean(0) for c in ids])
    return M, ids


def linear_cka(A: Array, B: Array) -> float:
    """Linear CKA between two K x V pattern matrices (same K content items)."""
    A = A - A.mean(0, keepdims=True)
    B = B - B.mean(0, keepdims=True)
    ga, gb = A @ A.T, B @ B.T
    hsic = float((ga * gb).sum())
    na, nb = float((ga * ga).sum()), float((gb * gb).sum())
    return hsic / (np.sqrt(na * nb) + 1e-24)


def procrustes_disparity(A: Array, B: Array) -> float:
    """Orthogonal Procrustes disparity between K x V pattern matrices, scale-free
    (both centered and Frobenius-normalized). 0 = identical up to rotation."""
    A = A - A.mean(0, keepdims=True)
    B = B - B.mean(0, keepdims=True)
    A = A / (np.linalg.norm(A) + 1e-24)
    B = B / (np.linalg.norm(B) + 1e-24)
    # optimal orthogonal alignment: disparity = ‖A‖² + ‖B‖² − 2 Σσ = 2(1 − Σσ) after norm
    s = np.linalg.svd(A @ B.T, compute_uv=False)
    return float(2.0 * (1.0 - s.sum()))


def crossnobis_rdm(X: Array, content: Array, folds: Array, rng_seed: int = 0) -> Array:
    """Cross-validated (crossnobis) RDM over content ids using leave-one-fold-out
    cross-validation of the pattern difference (diagonal noise normalization).
    Returns a K x K symmetric matrix. `folds` assigns each trial to a CV fold."""
    ids = sorted(set(int(c) for c in content))
    K = len(ids)
    ufolds = sorted(set(int(f) for f in folds))
    # per-voxel noise variance (pooled within content), for diagonal normalization
    resid = np.vstack([X[content == c] - X[content == c].mean(0) for c in ids])
    var = np.clip(resid.var(0, ddof=1), 1e-6, None)
    D = np.zeros((K, K))
    counts = np.zeros((K, K))
    for fa in ufolds:
        tr = folds != fa
        te = folds == fa
        mean_tr = {c: X[(content == c) & tr].mean(0) for c in ids}
        mean_te = {c: X[(content == c) & te].mean(0) for c in ids}
        for a in range(K):
            for b in range(a + 1, K):
                da = (mean_tr[ids[a]] - mean_tr[ids[b]]) / var
                db = (mean_te[ids[a]] - mean_te[ids[b]])
                d = float(np.dot(da, db))
                D[a, b] += d
                D[b, a] += d
                counts[a, b] += 1
                counts[b, a] += 1
    with np.errstate(invalid="ignore"):
        D = np.where(counts > 0, D / np.clip(counts, 1, None), 0.0)
    return D


def rdm_correlation(Da: Array, Db: Array) -> float:
    """Spearman-like rank correlation of the off-diagonal RDM entries."""
    iu = np.triu_indices_from(Da, k=1)
    a, b = Da[iu], Db[iu]
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra * ra).sum() * (rb * rb).sum()) + 1e-24
    return float((ra * rb).sum() / denom)


# --------------------------------------------------------------------------- #
# reliability / SNR
# --------------------------------------------------------------------------- #
def split_half_reliability(X: Array, content: Array, rng_seed: int, n_rep: int = 200) -> float:
    """Mean split-half reliability of content-mean patterns (Pearson r, averaged
    over random rep splits and content, Spearman-Brown corrected)."""
    rng = np.random.default_rng(rng_seed)
    ids = sorted(set(int(c) for c in content))
    rs = []
    for _ in range(n_rep):
        A, B = [], []
        for c in ids:
            idx = np.where(content == c)[0]
            rng.shuffle(idx)
            h = len(idx) // 2
            A.append(X[idx[:h]].mean(0))
            B.append(X[idx[h:2 * h]].mean(0))
        A, B = np.array(A), np.array(B)
        a = (A - A.mean(0)).ravel()
        b = (B - B.mean(0)).ravel()
        r = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-24))
        rs.append(2 * r / (1 + r) if r < 1 else 1.0)  # Spearman-Brown
    return float(np.mean(rs))


def add_isotropic_noise_to_reliability(X: Array, content: Array, target_reliability: float,
                                       rng_seed: int, tol: float = 0.01, max_iter: int = 40) -> Array:
    """Return X + isotropic Gaussian noise whose split-half reliability ~= target.
    Noise scale found by bisection on sigma. Does NOT use imagery labels — only
    the (perception) X and its own content structure."""
    rng = np.random.default_rng(rng_seed)
    base_sigma = float(np.sqrt(np.median(X.var(0))))
    lo, hi = 0.0, 20.0 * base_sigma + 1e-9
    Xn = X
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        Xn = X + rng.standard_normal(X.shape) * mid
        rel = split_half_reliability(Xn, content, rng_seed + 1, n_rep=60)
        if abs(rel - target_reliability) < tol:
            break
        if rel > target_reliability:
            lo = mid
        else:
            hi = mid
    return Xn
