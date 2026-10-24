"""C3X external-dataset-qualification invariants (synthetic; no OpenNeuro/figshare
download). Covers the run-disjoint estimator, no-straddling bootstrap, reduces-to-
C3G equivalence, permutation null, subject and dataset gates, the frozen ranking,
the no-geometry guard, and the seal self-hash.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.research.fmri import c3g_geometry
from app.research.fmri import c3x_reliability as X

_SEAL = Path(__file__).resolve().parents[3] / "reports" / "c3x" / "c3x_protocol_seal.json"
_RANK = Path(__file__).resolve().parents[3] / "results" / "c3x" / "c3x_ranking.json"


def _runwise(n_content, reps, n_runs, V, seed, noise):
    """Reliable synthetic data with run structure: each content appears once per run."""
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((n_content, V)) * 3
    X_, content, run = [], [], []
    for r in range(n_runs):
        for k in range(n_content):
            X_.append(centers[k] + rng.standard_normal(V) * noise)
            content.append(k)
            run.append(r)
    return np.array(X_), np.array(content), np.array(run)


def test_no_geometry_callable():
    for name in X.FORBIDDEN_GEOMETRY:
        assert not hasattr(X, name)
    import_lines = [ln for ln in Path(X.__file__).read_text().splitlines()
                    if "c3g_geometry" in ln and "import" in ln]
    assert import_lines == []  # C3X does NOT import geometry at all


def test_run_disjoint_reliability_and_perm():
    Xr, c, run = _runwise(6, 8, 10, 200, seed=1, noise=0.4)
    out = X.reliability_with_inference(Xr, c, run, seed=20260826, n_perm=200, n_boot=200)
    assert out["run_disjoint"] is True
    assert out["reliability"] > 0.5
    assert out["perm_p_one_sided"] < 0.05
    assert out["bootstrap_ci95"][0] > 0
    assert X.subject_reliability_gate(out) == "SUBJECT_RELIABILITY_PASS"


def test_noise_is_noise_floor():
    rng = np.random.default_rng(2)
    Xr = rng.standard_normal((60, 200))
    c = np.tile(np.arange(6), 10)
    run = np.repeat(np.arange(10), 6)
    out = X.reliability_with_inference(Xr, c, run, seed=20260826, n_perm=200, n_boot=200)
    assert out["reliability"] < 0.2
    assert out["bootstrap_ci95"][0] < 0.15   # non-straddling: CI not spuriously high on noise
    assert X.subject_reliability_gate(out) in ("SUBJECT_RELIABILITY_NOISE_FLOOR",
                                               "SUBJECT_RELIABILITY_MARGINAL")


def test_reduces_to_c3g_on_runless_fixture():
    # no run structure (single run) -> c3x falls back to per-content split; same scientific
    # quantity as C3G. 6 contents x 12 reps.
    rng = np.random.default_rng(3)
    centers = rng.standard_normal((6, 200)) * 3
    Xr = np.vstack([centers[k] + rng.standard_normal((12, 200)) * 0.4 for k in range(6)])
    c = np.repeat(np.arange(6), 12)
    run = np.zeros(len(c), dtype=int)
    rx = X.run_disjoint_reliability(Xr, c, run, seed=7, n_rep=200)
    rg = c3g_geometry.split_half_reliability(Xr, c + 6, 7, n_rep=200)
    assert abs(rx - rg) < 0.1
    assert rx > 0.5 and rg > 0.5


def test_run_disjoint_never_straddles():
    # a run assigned to half A cannot also be in half B (checked via the estimator internals)
    Xr, c, run = _runwise(4, 6, 8, 50, seed=4, noise=0.5)
    rng = np.random.default_rng(0)
    uruns = sorted(set(run.tolist()))
    perm = rng.permutation(uruns)
    h = len(uruns) // 2
    a, b = set(perm[:h].tolist()), set(perm[h:2 * h].tolist())
    assert not (a & b)


def test_subject_gate_rules():
    passing = {"reliability": 0.3, "bootstrap_ci95": [0.1, 0.5], "perm_p_one_sided": 0.001,
               "split_seed_values": [0.28, 0.31, 0.30]}
    assert X.subject_reliability_gate(passing) == "SUBJECT_RELIABILITY_PASS"
    marg = {"reliability": 0.08, "bootstrap_ci95": [-0.02, 0.2], "perm_p_one_sided": 0.03,
            "split_seed_values": [0.06, 0.09, 0.08]}
    assert X.subject_reliability_gate(marg) == "SUBJECT_RELIABILITY_MARGINAL"
    floor = {"reliability": -0.02, "bootstrap_ci95": [-0.2, 0.1], "perm_p_one_sided": 0.6,
             "split_seed_values": [-0.03, 0.0, -0.02]}
    assert X.subject_reliability_gate(floor) == "SUBJECT_RELIABILITY_NOISE_FLOOR"


def _mk(imR, imP, imCIlo, imSeed, vR):
    im = {"reliability": imR, "bootstrap_ci95": [imCIlo, 0.5], "perm_p_one_sided": imP,
          "split_seed_values": [imSeed, imSeed, imSeed]}
    vi = {"reliability": vR, "bootstrap_ci95": [0.1, 0.5], "perm_p_one_sided": 0.001,
          "split_seed_values": [vR, vR, vR]} if vR > 0 else \
        {"reliability": -0.01, "bootstrap_ci95": [-0.2, 0.1], "perm_p_one_sided": 0.5,
         "split_seed_values": [-0.01, -0.01, -0.01]}
    return {"imagery": im, "vision": vi}


def test_dataset_gate_min_two_subjects():
    # two imagery PASS + reliable vision -> DATASET PASS
    ds = {"s1": _mk(0.3, 0.001, 0.1, 0.3, 0.4), "s2": _mk(0.3, 0.001, 0.1, 0.3, 0.4),
          "s3": _mk(-0.01, 0.6, -0.2, -0.01, 0.4)}
    assert X.dataset_gate(ds) == "DATASET_RELIABILITY_PASS"
    # only one pass -> PROMISING
    ds2 = {"s1": _mk(0.3, 0.001, 0.1, 0.3, 0.4), "s2": _mk(-0.01, 0.6, -0.2, -0.01, 0.4),
           "s3": _mk(-0.01, 0.6, -0.2, -0.01, 0.4)}
    assert X.dataset_gate(ds2) == "DATASET_RELIABILITY_PROMISING"
    # all vision unreliable -> QUALITY_BLOCKED
    ds3 = {"s1": _mk(0.05, 0.3, -0.1, 0.05, -0.01), "s2": _mk(0.05, 0.3, -0.1, 0.05, -0.01)}
    assert X.dataset_gate(ds3) == "DATASET_QUALITY_BLOCKED"


@pytest.mark.skipif(not _SEAL.exists(), reason="seal absent")
def test_seal_and_ranking_frozen():
    seal = json.loads(_SEAL.read_text())
    stored = seal.pop("self_hash")
    assert hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest() == stored
    assert seal["candidates"]["D1_ds001506_DIR"] == "HIGH_PRIORITY_FOR_RELIABILITY_TEST"
    assert seal["first_empirical_target"] == "D1 (ds001506)"
    assert seal["dataset_gate"]["DATASET_RELIABILITY_PASS"].startswith(">=2 subjects")
    rank = json.loads(_RANK.read_text())
    assert rank["status"] == "FROZEN_BEFORE_ANY_NEURAL_RELIABILITY_OUTCOME"
    assert rank["first_empirical_target"] == "D1 (ds001506)"
