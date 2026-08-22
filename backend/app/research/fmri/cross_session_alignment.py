"""Cross-session neural alignment transforms for Scientific Gate C3M.

A session-alignment transform maps a raw ROI beta vector from the NSD-Imagery
session into the core-NSD perception session's distribution, applied BEFORE the
frozen C3 decoder's own z-scoring:

    y_hat_aligned(x) = frozen_decoder.predict( T(x) )

All transforms are represented compactly (offset vectors, diagonal scales, or a
shared low-rank subspace basis) so that no V x V matrix is ever materialized
(V ~= 15587 voxels -> a dense V x V matrix is ~1.9 GB).

Supervision hierarchy (frozen in C3M_PROTOCOL.md / c3m_protocol_decision.json):

  Family A - TARGET-BLIND (no imagery/vision target identity used to FIT):
    M0 identity, M1 mean correction, M2 affine, M3 CORAL/shrinkage covariance,
    M4 low-rank distribution alignment.

  Family B - VISION-CALIBRATED (fit on a TRAIN subset of NSD-Imagery VISION
  trials paired with the subject's own perception betas of the same seen image;
  evaluated ONLY on HELD-OUT VISION TARGET IDENTITIES):
    M5 ridge voxel-space session map, M6 reduced-rank session map,
    M7 orthogonal/Procrustes alignment.

Imagery target labels are NEVER used to fit or select any transform here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


# --------------------------------------------------------------------------- #
# Result container
# --------------------------------------------------------------------------- #
@dataclass
class AlignmentTransform:
    """A fitted session-alignment transform.

    `apply` maps [n, V] session betas into perception space. `method` and
    `params` record provenance (rank, shrinkage, alpha) for the manifest.
    """
    method: str
    apply: Callable[[Array], Array]
    params: dict

    def __call__(self, X: Array) -> Array:
        return self.apply(np.asarray(X, dtype=np.float64))


def _as2d(X: Array) -> Array:
    X = np.asarray(X, dtype=np.float64)
    return X[None, :] if X.ndim == 1 else X


# --------------------------------------------------------------------------- #
# Family A - target-blind
# --------------------------------------------------------------------------- #
def fit_identity() -> AlignmentTransform:
    """M0: no-op (== strict C3)."""
    return AlignmentTransform("M0_identity", lambda X: _as2d(X).copy(), {})


def fit_mean_correction(
    session_betas: Array, perception_mean: Array, per_voxel: bool = True
) -> AlignmentTransform:
    """M1: T(x) = x - m_s + mu_p.

    session_betas: [n_s, V] unlabeled NSD-Imagery vision betas (target-blind).
    perception_mean mu_p: frozen perception-train per-voxel mean (from decoder).
    per_voxel=False collapses m_s and mu_p to their scalar grand means.
    """
    S = _as2d(session_betas)
    m_s = S.mean(axis=0)
    mu_p = np.asarray(perception_mean, dtype=np.float64)
    if not per_voxel:
        m_s = np.full_like(m_s, m_s.mean())
        mu_p = np.full_like(mu_p, mu_p.mean())
    shift = mu_p - m_s

    def apply(X: Array) -> Array:
        return _as2d(X) + shift

    return AlignmentTransform("M1_mean_correction", apply,
                              {"per_voxel": per_voxel, "n_session": int(S.shape[0])})


def fit_affine(
    session_betas: Array, perception_mean: Array, perception_std: Array,
    eps: float = 1e-8,
) -> AlignmentTransform:
    """M2: per-voxel affine T(x)_v = (x_v - m_s,v) * (sigma_p,v / sigma_s,v) + mu_p,v."""
    S = _as2d(session_betas)
    m_s = S.mean(axis=0)
    s_s = np.clip(S.std(axis=0), eps, None)
    mu_p = np.asarray(perception_mean, dtype=np.float64)
    sig_p = np.clip(np.asarray(perception_std, dtype=np.float64), eps, None)
    scale = sig_p / s_s

    def apply(X: Array) -> Array:
        return (_as2d(X) - m_s) * scale + mu_p

    return AlignmentTransform("M2_affine", apply, {"n_session": int(S.shape[0])})


def _shrunk_cov(Xc: Array, shrinkage: float) -> tuple[Array, Array]:
    """Ledoit-Wolf-style shrunk covariance in the row-span subspace.

    Xc: [n, V] centered. Returns (U [V x r], evals [r]) such that the shrunk
    covariance's action is U diag(evals_shrunk) U^T on the subspace plus a
    diagonal target*I off-subspace. We keep the subspace factors so V x V is
    never formed. shrinkage in [0, 1]: 0 = empirical (subspace only),
    1 = pure diagonal (identity * mean-variance).
    """
    n = Xc.shape[0]
    # right singular vectors of Xc span the sample covariance range
    # Xc = W S Vt ;  sample cov = Vt^T (S^2/n) Vt  (V x V), rank <= n
    _, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    U = Vt.T                      # [V, r]
    emp_evals = (s ** 2) / max(n - 1, 1)   # [r]
    mu = float(np.mean(emp_evals)) if emp_evals.size else 0.0
    shr_evals = (1.0 - shrinkage) * emp_evals + shrinkage * mu
    return U, shr_evals


def fit_coral(
    session_betas: Array, perception_betas: Array,
    perception_mean: Array, shrinkage: float = 0.1, eps: float = 1e-8,
) -> AlignmentTransform:
    """M3: CORAL / shrinkage covariance alignment (target-blind).

    Whiten with the shrunk session covariance, recolor with the shrunk
    perception covariance, then shift to the perception mean:
        T(x) = (x - m_s) Sigma_s^{-1/2} Sigma_p^{1/2} + mu_p
    computed entirely in the shared low-rank (row-span) subspaces. Both
    covariances are estimated from UNLABELED betas -> target-blind.

    perception_betas: [n_p, V] core-NSD perception betas (unlabeled reference).
    """
    S = _as2d(session_betas)
    P = _as2d(perception_betas)
    m_s = S.mean(axis=0)
    mu_p = np.asarray(perception_mean, dtype=np.float64)
    Us, es = _shrunk_cov(S - m_s, shrinkage)          # session subspace
    Up, ep = _shrunk_cov(P - P.mean(axis=0), shrinkage)  # perception subspace
    inv_sqrt_s = 1.0 / np.sqrt(np.clip(es, eps, None))
    sqrt_p = np.sqrt(np.clip(ep, eps, None))

    def apply(X: Array) -> Array:
        Xc = _as2d(X) - m_s
        # whiten in session subspace: keep in-subspace component only
        coeff_s = Xc @ Us                     # [n, rs]
        whitened_sub = coeff_s * inv_sqrt_s   # scale each session PC
        # off-subspace residual passes through unwhitened (session cov ~ diag there)
        recon_s = whitened_sub @ Us.T
        resid = Xc - coeff_s @ Us.T
        z = recon_s + resid
        # recolor in perception subspace
        coeff_p = z @ Up
        colored_sub = coeff_p * sqrt_p
        out = colored_sub @ Up.T + (z - coeff_p @ Up.T)
        return out + mu_p

    return AlignmentTransform(
        "M3_coral", apply,
        {"shrinkage": shrinkage, "rank_session": int(Us.shape[1]),
         "rank_perception": int(Up.shape[1])})


def fit_lowrank_moment(
    session_betas: Array, perception_betas: Array,
    perception_mean: Array, rank: int = 10, eps: float = 1e-8,
) -> AlignmentTransform:
    """M4: low-rank distribution alignment (target-blind).

    Project onto the top-`rank` session PCs, match the first two moments to the
    perception distribution within that subspace, map back, restore mu_p.
    """
    S = _as2d(session_betas)
    P = _as2d(perception_betas)
    m_s = S.mean(axis=0)
    mu_p = np.asarray(perception_mean, dtype=np.float64)
    _, _, Vt = np.linalg.svd(S - m_s, full_matrices=False)
    r = int(min(rank, Vt.shape[0]))
    B = Vt[:r].T                                  # [V, r] session PCs
    # moments of each distribution projected into B
    s_coeff = (S - m_s) @ B                        # [n_s, r]
    p_coeff = (P - P.mean(axis=0)) @ B             # [n_p, r]
    s_std = np.clip(s_coeff.std(axis=0), eps, None)
    p_std = np.clip(p_coeff.std(axis=0), eps, None)
    gain = p_std / s_std

    def apply(X: Array) -> Array:
        Xc = _as2d(X) - m_s
        c = Xc @ B
        matched = (c * gain) @ B.T
        resid = Xc - c @ B.T
        return matched + resid + mu_p

    return AlignmentTransform("M4_lowrank_moment", apply,
                              {"rank": r})


# --------------------------------------------------------------------------- #
# Family B - vision-calibrated (fit on paired seen targets, eval held-out)
# --------------------------------------------------------------------------- #
def _subspace_basis(X: Array, rank: int) -> Array:
    """Top-`rank` right singular vectors (columns) of X: [V, r]."""
    _, _, Vt = np.linalg.svd(X - X.mean(axis=0), full_matrices=False)
    r = int(min(rank, Vt.shape[0]))
    return Vt[:r].T


def fit_ridge_map(
    X_v_train: Array, X_p_train: Array, alpha: float = 1e4, rank: int = 40,
) -> AlignmentTransform:
    """M5: ridge voxel-space session map, fit in a shared low-rank subspace.

    X_v_train: [n, V] NSD-Imagery VISION betas (train targets).
    X_p_train: [n, V] the subject's perception betas of the SAME seen images
               (row-aligned to X_v_train).
    Solve, in the joint subspace B ([V, r]) of the stacked training betas,
        argmin_M || Xv_B M - Xp_B ||^2 + alpha ||M||^2
    and lift back: T(x) = ((x-mv) B) M B^T + mp.  Never forms V x V.
    """
    Xv = _as2d(X_v_train); Xp = _as2d(X_p_train)
    mv = Xv.mean(axis=0); mp = Xp.mean(axis=0)
    B = _subspace_basis(np.vstack([Xv - mv, Xp - mp]), rank)   # [V, r]
    A = (Xv - mv) @ B                                          # [n, r]
    T = (Xp - mp) @ B                                          # [n, r]
    r = B.shape[1]
    M = np.linalg.solve(A.T @ A + alpha * np.eye(r), A.T @ T)  # [r, r]

    def apply(X: Array) -> Array:
        c = (_as2d(X) - mv) @ B
        return (c @ M) @ B.T + mp

    return AlignmentTransform("M5_ridge_map", apply,
                              {"alpha": alpha, "rank": int(r), "n_train": int(Xv.shape[0])})


def fit_reduced_rank(
    X_v_train: Array, X_p_train: Array, alpha: float = 1e4, rank: int = 40,
    out_rank: int = 6,
) -> AlignmentTransform:
    """M6: reduced-rank session map (M5 with the map M truncated to out_rank)."""
    Xv = _as2d(X_v_train); Xp = _as2d(X_p_train)
    mv = Xv.mean(axis=0); mp = Xp.mean(axis=0)
    B = _subspace_basis(np.vstack([Xv - mv, Xp - mp]), rank)
    A = (Xv - mv) @ B
    T = (Xp - mp) @ B
    r = B.shape[1]
    M = np.linalg.solve(A.T @ A + alpha * np.eye(r), A.T @ T)
    # truncate M to out_rank via SVD
    Um, sm, Vmt = np.linalg.svd(M, full_matrices=False)
    k = int(min(out_rank, sm.shape[0]))
    M_lr = (Um[:, :k] * sm[:k]) @ Vmt[:k]

    def apply(X: Array) -> Array:
        c = (_as2d(X) - mv) @ B
        return (c @ M_lr) @ B.T + mp

    return AlignmentTransform("M6_reduced_rank", apply,
                              {"alpha": alpha, "rank": int(r), "out_rank": k,
                               "n_train": int(Xv.shape[0])})


def fit_procrustes(
    X_v_train: Array, X_p_train: Array, rank: int = 40,
) -> AlignmentTransform:
    """M7: orthogonal/Procrustes alignment in a shared low-rank subspace.

    Find orthogonal Omega minimizing ||Xv_B Omega - Xp_B|| in the subspace B,
    lift back: T(x) = ((x-mv) B) Omega B^T + mp.
    """
    Xv = _as2d(X_v_train); Xp = _as2d(X_p_train)
    mv = Xv.mean(axis=0); mp = Xp.mean(axis=0)
    B = _subspace_basis(np.vstack([Xv - mv, Xp - mp]), rank)
    A = (Xv - mv) @ B
    T = (Xp - mp) @ B
    # orthogonal Procrustes: Omega = U V^T from SVD of A^T T
    U, _, Vt = np.linalg.svd(A.T @ T, full_matrices=False)
    Omega = U @ Vt

    def apply(X: Array) -> Array:
        c = (_as2d(X) - mv) @ B
        return (c @ Omega) @ B.T + mp

    return AlignmentTransform("M7_procrustes", apply,
                              {"rank": int(B.shape[1]), "n_train": int(Xv.shape[0])})


# --------------------------------------------------------------------------- #
# Matched-random capacity control
# --------------------------------------------------------------------------- #
def fit_matched_random(
    reference: AlignmentTransform, session_betas: Array, perception_mean: Array,
    seed: int, rank: int | None = None,
) -> AlignmentTransform:
    """A random transform of capacity matched to `reference`.

    For subspace/linear reference methods, use a random orthogonal map in a
    subspace of the same rank; for mean/affine references, use a random offset
    of matched norm. This isolates 'this specific fitted transform helps' from
    'any transform of this capacity helps'.
    """
    rng = np.random.default_rng(seed)
    S = _as2d(session_betas)
    m_s = S.mean(axis=0)
    mu_p = np.asarray(perception_mean, dtype=np.float64)
    meth = reference.method

    if meth in ("M0_identity", "M1_mean_correction"):
        # random offset with the same norm as the true mean shift
        true_shift = mu_p - m_s
        g = rng.standard_normal(true_shift.shape)
        g *= np.linalg.norm(true_shift) / max(np.linalg.norm(g), 1e-12)

        def apply(X: Array) -> Array:
            return _as2d(X) + g

        return AlignmentTransform("Mrand_offset", apply,
                                  {"matched_to": meth, "seed": seed})

    r = int(rank if rank is not None else reference.params.get("rank", 10))
    B = _subspace_basis(S - m_s, r)                # [V, r]
    G = rng.standard_normal((B.shape[1], B.shape[1]))
    Q, _ = np.linalg.qr(G)                          # random orthogonal r x r

    def apply(X: Array) -> Array:
        Xc = _as2d(X) - m_s
        c = Xc @ B
        return (c @ Q) @ B.T + (Xc - c @ B.T) + mu_p

    return AlignmentTransform("Mrand_orthogonal", apply,
                              {"matched_to": meth, "rank": int(B.shape[1]), "seed": seed})


# --------------------------------------------------------------------------- #
# Diagnostic metrics (candidate entropy, prediction-covariance effective rank)
# --------------------------------------------------------------------------- #
def candidate_score_entropy(
    predictions: Array, candidate_pool: Array, set_cols: list[int], eps: float = 1e-12,
) -> float:
    """Mean normalized Shannon entropy of the softmax over within-set candidate
    cosine scores. 1.0 = uniform (diverse), ~0 = peaky/collapsed.
    """
    pred = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), eps, None)
    pool = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), eps, None)
    sims = pred @ pool[set_cols].T                 # [n, k]
    z = sims - sims.max(axis=1, keepdims=True)
    p = np.exp(z); p /= p.sum(axis=1, keepdims=True)
    H = -np.sum(p * np.log(np.clip(p, eps, None)), axis=1)
    return float(np.mean(H) / np.log(len(set_cols)))


def prediction_covariance_effective_rank(predictions: Array, eps: float = 1e-12) -> float:
    """Effective rank exp(H(normalized eigenvalues)) of the across-trial
    covariance of the predicted embeddings. A collapsed decoder -> ~1.
    """
    Xc = predictions - predictions.mean(axis=0, keepdims=True)
    # eigenvalues of the trial-covariance via Gram (n small)
    n = Xc.shape[0]
    G = Xc @ Xc.T / max(n - 1, 1)
    ev = np.linalg.eigvalsh(G)
    ev = np.clip(ev, 0, None)
    tot = ev.sum()
    if tot <= eps:
        return 1.0
    p = ev / tot
    p = p[p > eps]
    H = -np.sum(p * np.log(p))
    return float(np.exp(H))
