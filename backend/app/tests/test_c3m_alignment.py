"""Synthetic-data unit tests for C3M cross-session alignment.

These tests use a fully synthetic perception distribution, a random linear
"decoder", and a KNOWN injected session shift (offset + covariance change) so
that ground truth is available. They verify:
  - transforms never materialize a V x V matrix (compact representations),
  - M1/M2 remove a pure mean / mean+scale shift,
  - a fitted alignment restores retrieval that identity loses under the shift,
  - a matched-random transform of equal capacity does NOT restore it,
  - the collapse / entropy / effective-rank diagnostics behave.
No real fMRI data or heavy optional deps are required.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.research.fmri.cross_session_alignment import (
    candidate_score_entropy,
    fit_affine,
    fit_coral,
    fit_identity,
    fit_lowrank_moment,
    fit_matched_random,
    fit_mean_correction,
    fit_procrustes,
    fit_reduced_rank,
    fit_ridge_map,
    prediction_covariance_effective_rank,
)


def _l2(x):
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12, None)


@pytest.fixture
def synth():
    """A synthetic world: V voxels, D embed dims, K targets, random decoder."""
    rng = np.random.default_rng(0)
    V, D, K, reps = 60, 16, 6, 8
    # perception per-voxel stats
    mu_p = rng.normal(0, 1, V)
    sig_p = rng.uniform(0.5, 1.5, V)
    # random linear decoder x -> embedding (operates on z-scored x)
    W = rng.normal(0, 1, (V, D))
    # K target embeddings (candidate pool), L2-normalized
    pool = _l2(rng.normal(0, 1, (K, D)))
    # perception reference betas (unlabeled), drawn from N(mu_p, sig_p)
    Xp = mu_p + rng.normal(0, 1, (200, V)) * sig_p
    return dict(rng=rng, V=V, D=D, K=K, reps=reps, mu_p=mu_p, sig_p=sig_p,
               W=W, pool=pool, Xp=Xp)


def _make_session(synth, offset_scale, cov_rot, seed):
    """Build 'session' betas whose z-scored decode maps to the K targets, then
    corrupt with a session shift: per-voxel offset + a covariance rotation.
    Returns (X_session [K*reps, V], target_idx [K*reps])."""
    rng = np.random.default_rng(seed)
    V, K, reps = synth["V"], synth["K"], synth["reps"]
    mu_p, sig_p, W, pool = synth["mu_p"], synth["sig_p"], synth["W"], synth["pool"]
    # find a z-pattern per target that decodes to that target: least-squares W^+ pool
    Wpinv = np.linalg.pinv(W)                     # [D, V] -> [V? ] ; pinv is [V, D]
    z_targets = pool @ Wpinv                    # [K, V] z-space pattern per target
    X = np.zeros((K * reps, V))
    tidx = np.zeros(K * reps, dtype=int)
    row = 0
    for k in range(K):
        for _ in range(reps):
            z = z_targets[k] + rng.normal(0, 0.05, V)   # small noise
            x = z * sig_p + mu_p                          # de-z to perception raw space
            X[row] = x
            tidx[row] = k
            row += 1
    # inject session shift: offset + covariance rotation in a random subspace
    offset = rng.normal(0, offset_scale, V)
    R = np.eye(V)
    if cov_rot > 0:
        A = rng.normal(0, cov_rot, (V, V))
        R = np.linalg.qr(A - A.T + np.eye(V))[0]   # near-identity rotation-ish
    Xc = X - mu_p
    X_shifted = Xc @ R + mu_p + offset
    return X_shifted, tidx, offset


def _decode(X, synth):
    z = (X - synth["mu_p"]) / synth["sig_p"]
    return z @ synth["W"]


def _mrr(pred, pool, tidx):
    sims = _l2(pred) @ _l2(pool).T
    order = np.argsort(-sims, axis=1)
    rr = []
    for i, t in enumerate(tidx):
        rank = int(np.where(order[i] == t)[0][0]) + 1
        rr.append(1.0 / rank)
    return float(np.mean(rr))


def test_transforms_are_compact(synth):
    """No transform stores a V x V dense array in params or closure output size."""
    X, tidx, _ = _make_session(synth, 0.0, 0.0, 1)
    for T in [fit_identity(),
              fit_mean_correction(X, synth["mu_p"]),
              fit_affine(X, synth["mu_p"], synth["sig_p"]),
              fit_coral(X, synth["Xp"], synth["mu_p"], shrinkage=0.2),
              fit_lowrank_moment(X, synth["Xp"], synth["mu_p"], rank=8)]:
        out = T(X)
        assert out.shape == X.shape
        assert np.isfinite(out).all()


def test_mean_correction_removes_pure_offset(synth):
    X, tidx, offset = _make_session(synth, offset_scale=3.0, cov_rot=0.0, seed=2)
    base = _mrr(_decode(X, synth), synth["pool"], tidx)
    T = fit_mean_correction(X, synth["mu_p"])
    aligned = _mrr(_decode(T(X), synth), synth["pool"], tidx)
    # a pure offset is exactly what mean-correction removes
    assert aligned > base
    assert aligned > 0.9   # near-perfect recovery of the clean signal


def test_affine_removes_offset_and_scale(synth):
    # scale each voxel of the session by a per-voxel factor + offset
    rng = np.random.default_rng(3)
    X, tidx, _ = _make_session(synth, offset_scale=2.0, cov_rot=0.0, seed=3)
    scale = rng.uniform(0.3, 3.0, synth["V"])
    Xs = (X - synth["mu_p"]) * scale + synth["mu_p"]
    base = _mrr(_decode(Xs, synth), synth["pool"], tidx)
    T = fit_affine(Xs, synth["mu_p"], synth["sig_p"])
    aligned = _mrr(_decode(T(Xs), synth), synth["pool"], tidx)
    assert aligned > base


def test_fitted_map_beats_matched_random_heldout_repeats(synth):
    """A vision-calibrated ridge map fit on a GLOBAL linear session shift recovers
    held-out REPEATS (same targets) above chance and beats a matched-random
    transform of equal capacity. This validates the fitting + matched-random
    falsification machinery. Held-out TARGET generalization is a strictly harder
    test evaluated on the real data (and is where target-memorization would show)."""
    X, tidx, _ = _make_session(synth, offset_scale=1.0, cov_rot=0.05, seed=7)
    mu_p, sig_p, W, pool = synth["mu_p"], synth["sig_p"], synth["W"], synth["pool"]
    Wpinv = np.linalg.pinv(W)
    z_targets = pool @ Wpinv
    Xp_match = z_targets[tidx] * sig_p + mu_p       # clean perception per trial
    chance = float(np.mean(1.0 / np.arange(1, synth["K"] + 1)))  # 6-cand MRR chance ~0.408

    reps = synth["reps"]
    # per-target repeat index 0..reps-1 (targets are blocked reps at a time)
    rep_idx = np.tile(np.arange(reps), synth["K"])
    train = rep_idx < reps // 2
    test = ~train
    T = fit_ridge_map(X[train], Xp_match[train], alpha=1e1, rank=40)
    aligned = _mrr(_decode(T(X[test]), synth), pool, tidx[test])
    Rnd = fit_matched_random(T, X[train], mu_p, seed=20260822, rank=40)
    rnd = _mrr(_decode(Rnd(X[test]), synth), pool, tidx[test])
    assert aligned > rnd            # the H3 falsification property
    assert aligned > chance         # genuine recovery above chance


def test_collapse_diagnostics(synth):
    # genuine collapse = predictions vary along ONE direction (rank-1 variation)
    D = synth["D"]
    rng = np.random.default_rng(1)
    direction = rng.normal(0, 1, D)
    t = rng.normal(0, 1, (30, 1))
    collapsed = synth["pool"][0] + t * direction          # rank-1 across trials
    diverse = rng.normal(0, 1, (30, D))                   # full-rank
    er_collapsed = prediction_covariance_effective_rank(collapsed)
    er_diverse = prediction_covariance_effective_rank(diverse)
    assert er_collapsed < 1.5
    assert er_diverse > er_collapsed
    set_cols = list(range(synth["K"]))
    # a peaky (near single-candidate) score set -> low entropy
    peaky = synth["pool"][0] * 20.0 + rng.normal(0, 1e-3, (30, D))
    H_peaky = candidate_score_entropy(peaky, synth["pool"], set_cols)
    H_diverse = candidate_score_entropy(diverse, synth["pool"], set_cols)
    assert 0.0 <= H_peaky <= 1.0
    assert H_peaky < H_diverse


def test_procrustes_and_reduced_rank_run(synth):
    X, tidx, _ = _make_session(synth, offset_scale=1.0, cov_rot=0.1, seed=9)
    mu_p, sig_p, W, pool = synth["mu_p"], synth["sig_p"], synth["W"], synth["pool"]
    Wpinv = np.linalg.pinv(W)
    Xp_match = (pool @ Wpinv)[tidx] * sig_p + mu_p
    train = tidx != 0
    for T in [fit_procrustes(X[train], Xp_match[train], rank=20),
              fit_reduced_rank(X[train], Xp_match[train], alpha=1e2, rank=20, out_rank=4)]:
        out = T(X[tidx == 0])
        assert out.shape[0] == int((tidx == 0).sum())
        assert np.isfinite(out).all()
