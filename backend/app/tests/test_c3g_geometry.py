"""C3G geometry-library invariants (synthetic; no real data required).

Validates the representational-geometry primitives that the C3G confirmatory
analysis depends on: determinism, correct behaviour on known constructions, and
the leakage-safe subsample-matched comparison.
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from app.research.fmri import c3g_geometry as g

_MANIFEST = Path(__file__).resolve().parents[3] / "results" / "c3g" / "c3g_data_manifest.json"


def _iso(n, V, seed, scale=1.0, shift=0.0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, V)) * scale + shift


def test_determinism():
    P = _iso(48, 200, 1)
    Im = _iso(96, 200, 2)
    a = g.subsample_matched(g.participation_ratio, P, Im, 40, 50, seed=7)
    b = g.subsample_matched(g.participation_ratio, P, Im, 40, 50, seed=7)
    assert a == b


def test_participation_ratio_bounds():
    # isotropic Gaussian: PR close to min(n-1, V); rank-1: PR ~ 1
    P = _iso(60, 300, 3)
    pr = g.participation_ratio(P)
    assert 30 < pr <= 60, pr
    direction = np.random.default_rng(0).standard_normal(300)
    t = np.linspace(-1, 1, 40)[:, None]
    rank1 = t * direction[None, :] + 5.0
    assert g.participation_ratio(rank1) < 1.5


def test_centroid_and_gain():
    P = _iso(80, 200, 4)
    assert g.centroid_displacement(P, P) < 1e-9
    shifted = P + 3.0
    assert g.centroid_displacement(P, shifted) > 0.1
    scaled = _iso(80, 200, 4, scale=2.0)
    ag = g.amplitude_gain(P, scaled)
    assert 1.7 < ag["global_amplitude_ratio"] < 2.3


def test_subspace_overlap():
    rng = np.random.default_rng(5)
    B = rng.standard_normal((300, 5))
    Q, _ = np.linalg.qr(B)
    coeffP = rng.standard_normal((60, 5)) * np.array([5, 4, 3, 2, 1])
    P = coeffP @ Q.T + 0.01 * rng.standard_normal((60, 300))
    coeffI = rng.standard_normal((60, 5)) * np.array([5, 4, 3, 2, 1])
    Isame = coeffI @ Q.T + 0.01 * rng.standard_normal((60, 300))
    # same subspace -> high overlap
    assert g.subspace_overlap(P, Isame, 5) > 0.8
    # orthogonal subspace -> low overlap
    B2 = rng.standard_normal((300, 5))
    Q2, _ = np.linalg.qr(np.hstack([Q, B2]))
    Q2 = Q2[:, 5:10]
    Iorth = (rng.standard_normal((60, 5)) * np.array([5, 4, 3, 2, 1])) @ Q2.T
    assert g.subspace_overlap(P, Iorth, 5) < 0.3


def test_cka_rotation_invariant_and_structure():
    rng = np.random.default_rng(6)
    A = rng.standard_normal((6, 200))
    R, _ = np.linalg.qr(rng.standard_normal((200, 200)))
    assert abs(g.linear_cka(A, A) - 1.0) < 1e-6
    assert abs(g.linear_cka(A, A @ R) - 1.0) < 1e-6           # CKA is rotation invariant
    # CKA measures shared similarity STRUCTURE: two different cluster groupings differ.
    base = rng.standard_normal((6, 200))
    g1 = np.array([0, 0, 0, 1, 1, 1])                          # grouping A: {0,1,2},{3,4,5}
    g2 = np.array([0, 1, 0, 1, 0, 1])                          # grouping B: interleaved
    Xa = base + 6.0 * np.eye(2)[g1] @ rng.standard_normal((2, 200))
    Xb = base + 6.0 * np.eye(2)[g2] @ rng.standard_normal((2, 200))
    assert g.linear_cka(Xa, Xb) < g.linear_cka(Xa, Xa) - 0.1


def test_crossnobis_recovers_structure():
    # two well-separated content clusters vs near-identical ones
    rng = np.random.default_rng(8)
    V = 100
    centers = rng.standard_normal((3, V)) * 5
    content, folds, X = [], [], []
    for c in range(3):
        for r in range(8):
            X.append(centers[c] + rng.standard_normal(V) * 0.5)
            content.append(c)
            folds.append(r % 4)
    X = np.array(X)
    content = np.array(content)
    folds = np.array(folds)
    D = g.crossnobis_rdm(X, content, folds)
    # off-diagonal distances positive and symmetric
    assert np.allclose(D, D.T)
    assert D[0, 1] > 0 and D[0, 2] > 0 and D[1, 2] > 0
    # RDM self-correlation is 1
    assert abs(g.rdm_correlation(D, D) - 1.0) < 1e-9


def test_noise_reduces_reliability():
    rng = np.random.default_rng(9)
    V = 150
    centers = rng.standard_normal((4, V)) * 3
    content, X = [], []
    for c in range(4):
        for _ in range(10):
            X.append(centers[c] + rng.standard_normal(V) * 0.3)
            content.append(c)
    X = np.array(X)
    content = np.array(content)
    rel0 = g.split_half_reliability(X, content, rng_seed=1, n_rep=60)
    Xn = g.add_isotropic_noise_to_reliability(X, content, target_reliability=rel0 * 0.5,
                                              rng_seed=2)
    rel1 = g.split_half_reliability(Xn, content, rng_seed=1, n_rep=60)
    assert rel1 < rel0
    assert rel1 < rel0 * 0.5 + 0.15


def test_subsample_matched_reports_ci():
    P = _iso(48, 200, 10)
    Im = _iso(96, 200, 11, scale=1.5)
    out = g.subsample_matched(g.participation_ratio, P, Im, 40, 80, seed=3)
    assert out["n_match"] == 40 and out["n_boot"] == 80
    assert out["diff_ci95"][0] <= out["diff_mean"] <= out["diff_ci95"][1]


@pytest.mark.skipif(not _MANIFEST.exists(), reason="C3G data manifest not present")
def test_data_contract_invariants():
    m = json.loads(_MANIFEST.read_text())
    st = m["states"]
    # exact expected counts and content balance (Set B: 6 content, vision 8 reps, imagery 16)
    assert st["setB_vision"]["shape"] == [48, 15587]
    assert st["setB_imagery"]["shape"] == [96, 15587]
    cv = Counter(st["setB_vision"]["content_pool_indices"])
    ci = Counter(st["setB_imagery"]["content_pool_indices"])
    assert set(cv) == {6, 7, 8, 9, 10, 11} and set(cv.values()) == {8}
    assert set(ci) == {6, 7, 8, 9, 10, 11} and set(ci.values()) == {16}
    # deterministic row order: strictly increasing beta_row_index, no duplicates
    for s in ("setB_vision", "setB_imagery", "setA_vision", "setA_imagery"):
        idx = st[s]["row_indices"]
        assert idx == sorted(idx) and len(set(idx)) == len(idx)
    # vision and imagery draw from disjoint beta rows (no state leakage)
    assert not (set(st["setB_vision"]["row_indices"]) & set(st["setB_imagery"]["row_indices"]))
    # anchor perception distinct and large
    assert m["anchor_perception_xp"]["shape"][0] == 6000
    # ROI families are non-empty and disjoint-labeled
    assert all(c > 0 for c in m["roi"]["counts"]["prf"].values())
    assert all(c > 0 for c in m["roi"]["counts"]["streams"].values())
