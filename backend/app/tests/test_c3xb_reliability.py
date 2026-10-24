"""C3XB run-pair-disjoint estimator invariants (synthetic; NO OpenNeuro/figshare
download). Proves the estimator reduces EXACTLY to the frozen C3X run-disjoint
statistic, recovers reliable structure, sits at the noise floor on noise with a
non-inflated (non-straddling) bootstrap CI, permutes category identity within
run-pairs, and exposes no geometry.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from app.research.fmri import c3x_reliability as X
from app.research.fmri import c3xb_reliability as XB

_ROOT = Path(__file__).resolve().parents[3]
_SEAL = _ROOT / "reports" / "c3xb" / "c3xb_protocol_seal.json"


def _pairwise(n_content, n_pairs, V, seed, noise):
    """Reliable synthetic data with run-pair structure: each content appears once
    per run-pair (mirrors GOD: every 2-run pair covers all categories once)."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((n_content, V)) * 3
    X_, content, pair = [], [], []
    for p in range(n_pairs):
        order = rng.permutation(n_content)  # category order varies within a pair
        for k in order:
            X_.append(centers[k] + rng.standard_normal(V) * noise)
            content.append(int(k))
            pair.append(p)
    return np.array(X_), np.array(content), np.array(pair)


def test_no_geometry_exposed():
    for name in XB.FORBIDDEN_GEOMETRY:
        assert not hasattr(XB, name)
    import_lines = [ln for ln in Path(XB.__file__).read_text().splitlines()
                    if "c3g_geometry" in ln and "import" in ln]
    assert import_lines == []  # C3XB imports the C3X statistic, never geometry


def test_reduces_to_c3x_run_disjoint():
    """With pair-labelling == run-labelling, same seed and n_rep, the run-pair
    estimator is BIT-IDENTICAL to the frozen C3X run-disjoint estimator: same
    statistic, only the split unit is renamed."""
    Xr, c, run = _pairwise(6, 10, 120, seed=7, noise=0.5)
    pair = run.copy()  # each run-pair is a single acquisition unit here
    for seed in (1, 20260901, 999):
        a = XB.run_pair_disjoint_reliability(Xr, c, pair, seed, n_rep=200)
        b = X.run_disjoint_reliability(Xr, c, run, seed, n_rep=200)
        assert abs(a - b) < 1e-12, (seed, a, b)


def test_recovers_reliable_structure():
    Xr, c, pair = _pairwise(8, 10, 200, seed=3, noise=0.4)
    out = XB.reliability_with_inference_pairs(Xr, c, pair, seed=20260901, n_perm=200, n_boot=200)
    assert out["unit"] == "run_pair_disjoint"
    assert out["n_pairs"] == 10
    assert out["reliability"] > 0.5
    assert out["perm_p_one_sided"] < 0.05
    assert out["bootstrap_ci95"][0] > 0
    assert min(out["split_seed_values"]) > 0
    assert XB.subject_reliability_gate(out) == "SUBJECT_RELIABILITY_PASS"


def test_noise_floor_non_straddling_ci():
    rng = np.random.default_rng(11)
    n_content, n_pairs, V = 8, 10, 200
    Xr = rng.standard_normal((n_content * n_pairs, V))
    c = np.tile(np.arange(n_content), n_pairs)
    pair = np.repeat(np.arange(n_pairs), n_content)
    out = XB.reliability_with_inference_pairs(Xr, c, pair, seed=20260901, n_perm=200, n_boot=200)
    assert out["reliability"] < 0.2
    # non-straddling hierarchical bootstrap must NOT spuriously inflate the CI on noise
    assert out["bootstrap_ci95"][0] < 0.15
    assert XB.subject_reliability_gate(out) != "SUBJECT_RELIABILITY_PASS"


def test_permute_within_pairs_preserves_composition():
    _, c, pair = _pairwise(6, 10, 10, seed=5, noise=1.0)
    rng = np.random.default_rng(0)
    perm = XB._permute_within_pairs(c, pair, rng)
    assert perm.shape == c.shape
    for p in set(pair.tolist()):
        m = pair == p
        assert sorted(perm[m].tolist()) == sorted(c[m].tolist())  # same category multiset per pair
    assert not np.array_equal(perm, c)  # something actually moved


def test_dataset_gate_needs_two_subjects():
    Xr, c, pair = _pairwise(8, 10, 150, seed=2, noise=0.4)
    good = XB.reliability_with_inference_pairs(Xr, c, pair, seed=20260901, n_perm=150, n_boot=150)
    rng = np.random.default_rng(4)
    Xn = rng.standard_normal((80, 150))
    cn = np.tile(np.arange(8), 10)
    pn = np.repeat(np.arange(10), 8)
    bad = XB.reliability_with_inference_pairs(Xn, cn, pn, seed=20260901, n_perm=150, n_boot=150)
    two = {"s1": {"imagery": good, "vision": good}, "s2": {"imagery": good, "vision": good}}
    one = {"s1": {"imagery": good, "vision": good}, "s2": {"imagery": bad, "vision": good}}
    assert XB.dataset_gate(two) == "DATASET_RELIABILITY_PASS"
    assert XB.dataset_gate(one) in ("DATASET_RELIABILITY_PROMISING", "DATASET_RELIABILITY_FAIL")


def test_seal_self_hash_if_present():
    if not _SEAL.exists():
        return
    obj = json.load(open(_SEAL))
    h = obj.pop("self_hash")
    assert hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest() == h
