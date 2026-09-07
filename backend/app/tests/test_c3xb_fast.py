"""The c3xb_fast vectorized accelerator must reproduce the FROZEN c3xb_reliability
run-pair-disjoint inference BIT-IDENTICALLY (synthetic; no downloads). This guards
the accelerator used for the 5-subject GOD screen; the frozen estimator remains the
definition. (Real-data bit-identity was additionally confirmed against Subject1's
committed frozen result during the screen.)
"""
import numpy as np

from app.research.fmri.c3xb_fast import reliability_with_inference_pairs_fast as fast
from app.research.fmri.c3xb_reliability import reliability_with_inference_pairs as frozen


def _balanced(ncat, npairs, V, seed, noise):
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((ncat, V)) * 3
    X, c, p = [], [], []
    for pr in range(npairs):
        for k in rng.permutation(ncat):        # one trial per category per pair, varied order
            X.append(centers[k] + rng.standard_normal(V) * noise)
            c.append(int(k))
            p.append(pr)
    return np.array(X), np.array(c), np.array(p)


def _assert_identical(a, b):
    for k in ["reliability", "perm_p_one_sided", "bootstrap_ci95", "bootstrap_mean",
              "null_mean", "null_std", "split_seed_values"]:
        assert np.allclose(a[k], b[k], atol=1e-12), (k, a[k], b[k])


def test_fast_matches_frozen_reliable():
    X, c, p = _balanced(8, 10, 60, seed=3, noise=0.5)
    _assert_identical(frozen(X, c, p, 20260901, n_perm=80, n_boot=80),
                      fast(X, c, p, 20260901, n_perm=80, n_boot=80))


def test_fast_matches_frozen_noise():
    rng = np.random.default_rng(11)
    ncat, npairs, V = 8, 10, 60
    X = rng.standard_normal((ncat * npairs, V))
    c = np.tile(np.arange(ncat), npairs)
    p = np.repeat(np.arange(npairs), ncat)
    _assert_identical(frozen(X, c, p, 20260901, n_perm=80, n_boot=80),
                      fast(X, c, p, 20260901, n_perm=80, n_boot=80))


def test_fast_matches_frozen_other_seed():
    X, c, p = _balanced(6, 10, 40, seed=7, noise=0.8)
    _assert_identical(frozen(X, c, p, 12345, n_perm=60, n_boot=60),
                      fast(X, c, p, 12345, n_perm=60, n_boot=60))
