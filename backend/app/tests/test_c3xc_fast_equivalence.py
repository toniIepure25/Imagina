"""C3XC uses the FROZEN C3XB run-pair-disjoint estimator with unit:=session (D2 sessions
are one-trial-per-(session,video)). This test proves the c3xb_fast accelerator is
BIT-IDENTICAL to the frozen c3xb_reliability estimator in the D2 configuration
(5 balanced units, 72 contents) — synthetic, no downloads.
"""
import numpy as np

from app.research.fmri.c3xb_fast import reliability_with_inference_pairs_fast as fast
from app.research.fmri.c3xb_reliability import reliability_with_inference_pairs as frozen
from app.research.fmri.c3xc_fast import reliability_with_inference_pairs_fast as buffast


def _d2_like(n_content, n_sessions, V, seed, noise):
    """One trial per (session, content), content order varied per session (like D2 imagery)."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((n_content, V)) * 3
    X, c, sess = [], [], []
    for s in range(n_sessions):
        for k in rng.permutation(n_content):
            X.append(centers[k] + rng.standard_normal(V) * noise)
            c.append(int(k))
            sess.append(s)
    return np.array(X), np.array(c), np.array(sess)


def _assert_identical(a, b):
    for k in ["reliability", "perm_p_one_sided", "bootstrap_ci95", "bootstrap_mean",
              "null_mean", "null_std", "split_seed_values"]:
        assert np.allclose(a[k], b[k], atol=1e-12), (k, a[k], b[k])


def test_fast_equals_frozen_d2_reliable():
    X, c, s = _d2_like(72, 5, 40, seed=1, noise=0.6)
    _assert_identical(frozen(X, c, s, 20260907, n_perm=60, n_boot=60),
                      fast(X, c, s, 20260907, n_perm=60, n_boot=60))


def test_fast_equals_frozen_d2_noise():
    rng = np.random.default_rng(9)
    n_content, n_sessions, V = 72, 5, 40
    X = rng.standard_normal((n_content * n_sessions, V))
    c = np.tile(np.arange(n_content), n_sessions)
    s = np.repeat(np.arange(n_sessions), n_content)
    _assert_identical(frozen(X, c, s, 20260907, n_perm=60, n_boot=60),
                      fast(X, c, s, 20260907, n_perm=60, n_boot=60))


def test_fast_deterministic():
    X, c, s = _d2_like(30, 5, 30, seed=4, noise=0.7)
    a = fast(X, c, s, 20260907, n_perm=50, n_boot=50)
    b = fast(X, c, s, 20260907, n_perm=50, n_boot=50)
    _assert_identical(a, b)


# --- c3xc_fast (buffered accelerator actually used for the D2 screen) ---
def test_buffast_equals_frozen_d2_reliable():
    X, c, s = _d2_like(72, 5, 40, seed=1, noise=0.6)
    _assert_identical(frozen(X, c, s, 20260907, n_perm=60, n_boot=60),
                      buffast(X, c, s, 20260907, n_perm=60, n_boot=60))


def test_buffast_equals_frozen_d2_noise():
    rng = np.random.default_rng(9)
    nc, ns, V = 72, 5, 40
    X = rng.standard_normal((nc * ns, V))
    c = np.tile(np.arange(nc), ns)
    s = np.repeat(np.arange(ns), nc)
    _assert_identical(frozen(X, c, s, 20260907, n_perm=60, n_boot=60),
                      buffast(X, c, s, 20260907, n_perm=60, n_boot=60))


def test_buffast_equals_c3xb_fast():
    X, c, s = _d2_like(40, 5, 35, seed=5, noise=0.7)
    _assert_identical(fast(X, c, s, 12345, n_perm=50, n_boot=50),
                      buffast(X, c, s, 12345, n_perm=50, n_boot=50))
