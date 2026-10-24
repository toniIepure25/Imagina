"""C3R imagery-reliability-screen invariants (synthetic; no NSD download).

Covers the sealed contract: fixed subject set, 720-row imagery mapping, the
INHERITED C3G reliability estimator, the stimulus-label null, bootstrap
determinism, the reliability-gate rules, vision/imagery classification, the
no-geometry guard, and the seal self-hash.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.research.fmri import c3g_geometry
from app.research.fmri import c3r_reliability as R

_SEAL = Path(__file__).resolve().parents[3] / "reports" / "c3r" / "c3r_protocol_seal.json"


def _reliable(n_content=6, reps=16, V=150, seed=0, noise=0.3):
    rng = np.random.default_rng(seed)
    centers = rng.standard_normal((n_content, V)) * 3
    X, c = [], []
    for k in range(n_content):
        for _ in range(reps):
            X.append(centers[k] + rng.standard_normal(V) * noise)
            c.append(k + 6)
    return np.array(X), np.array(c)


def _noise(n_content=6, reps=16, V=150, seed=1):
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n_content * reps, V)), np.repeat(np.arange(6) + 6, reps)


def test_estimator_is_inherited_from_c3g():
    assert R.split_half_reliability is c3g_geometry.split_half_reliability


def test_no_geometry_callable_from_c3r():
    # No geometry endpoint is exposed as a C3R attribute.
    for name in R.FORBIDDEN_GEOMETRY:
        assert not hasattr(R, name), f"C3R must not expose geometry endpoint {name}"
    # The ONLY symbol imported from c3g_geometry is the reliability estimator.
    import_lines = [ln for ln in Path(R.__file__).read_text().splitlines()
                    if "c3g_geometry" in ln and "import" in ln]
    assert import_lines == ["from app.research.fmri.c3g_geometry import split_half_reliability"]


def test_null_destroys_reliability_and_pass():
    X, c = _reliable(seed=2, noise=0.3)
    out = R.reliability_with_inference(X, c, seed=20260826, n_perm=200, n_boot=200)
    assert out["reliability"] > 0.5
    assert out["null_mean"] < 0.2                       # permuting content destroys reliability
    assert out["perm_p_one_sided"] < 0.05
    assert out["bootstrap_ci95"][0] > 0
    assert R.reliability_gate(out) == "RELIABILITY_PASS"


def test_noise_floor_gate():
    X, c = _noise(seed=3)
    out = R.reliability_with_inference(X, c, seed=20260826, n_perm=200, n_boot=200)
    assert out["reliability"] < 0.2
    assert R.reliability_gate(out) in ("RELIABILITY_NOISE_FLOOR", "RELIABILITY_MARGINAL")


def test_bootstrap_ci_not_inflated_on_noise():
    # Regression: the split-half bootstrap must NOT straddle (a physical trial in
    # both halves would spuriously inflate the CI). On pure noise the CI must span
    # ~0, not sit far above the near-zero point estimate.
    X, c = _noise(seed=5)
    out = R.reliability_with_inference(X, c, seed=20260826, n_perm=100, n_boot=300)
    lo, hi = out["bootstrap_ci95"]
    assert lo < 0.15, f"bootstrap CI lower bound spuriously high on noise: {lo}"
    assert lo <= out["reliability"] + 0.2


def test_bootstrap_determinism():
    X, c = _reliable(seed=4)
    a = R.reliability_with_inference(X, c, seed=7, n_perm=50, n_boot=100)
    b = R.reliability_with_inference(X, c, seed=7, n_perm=50, n_boot=100)
    assert a == b


def test_gate_rules_on_crafted_dicts():
    passing = {"reliability": 0.3, "bootstrap_ci95": [0.1, 0.5], "perm_p_one_sided": 0.001,
               "split_seed_values": [0.28, 0.31, 0.30]}
    assert R.reliability_gate(passing) == "RELIABILITY_PASS"
    marginal_ci = {"reliability": 0.06, "bootstrap_ci95": [-0.02, 0.15], "perm_p_one_sided": 0.03,
                   "split_seed_values": [0.05, 0.07, 0.06]}
    assert R.reliability_gate(marginal_ci) == "RELIABILITY_MARGINAL"
    marginal_p = {"reliability": 0.06, "bootstrap_ci95": [0.01, 0.15], "perm_p_one_sided": 0.2,
                  "split_seed_values": [0.05, 0.07, 0.06]}
    assert R.reliability_gate(marginal_p) == "RELIABILITY_MARGINAL"
    floor = {"reliability": -0.01, "bootstrap_ci95": [-0.1, 0.05], "perm_p_one_sided": 0.6,
             "split_seed_values": [-0.02, 0.0, -0.01]}
    assert R.reliability_gate(floor) == "RELIABILITY_NOISE_FLOOR"


def test_vision_imagery_classification():
    pas = {"reliability": 0.3, "bootstrap_ci95": [0.1, 0.5], "perm_p_one_sided": 0.001,
           "split_seed_values": [0.3, 0.3, 0.3]}
    floor = {"reliability": -0.01, "bootstrap_ci95": [-0.1, 0.05], "perm_p_one_sided": 0.6,
             "split_seed_values": [-0.02, 0.0, -0.01]}
    assert R.vision_imagery_quality(pas, pas) == "VISION_RELIABLE_IMAGERY_RELIABLE"
    assert R.vision_imagery_quality(pas, floor) == "VISION_RELIABLE_IMAGERY_NOISE_FLOOR"
    assert R.vision_imagery_quality(floor, floor) == "VISION_UNRELIABLE_SESSION_QUALITY_BLOCKER"


def test_practical_effect_flags():
    f = R.practical_effect_flags(0.12)
    assert f == {"R_gt_0p05": True, "R_gt_0p10": True, "R_gt_0p20": False}


@pytest.mark.skipif(not _SEAL.exists(), reason="C3R seal not present")
def test_seal_self_hash_and_contract():
    seal = json.loads(_SEAL.read_text())
    stored = seal.pop("self_hash")
    recomputed = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    assert recomputed == stored
    assert seal["subjects"] == ["subj02", "subj05", "subj07"]
    rm = seal["row_mapping"]
    assert rm["visB"] == "192:240" and rm["imgB_1"] == "336:384" and rm["imgB_2"] == "624:672"
    assert rm["setB_vision_trials"] == 48 and rm["setB_imagery_trials"] == 96
    assert rm["contents"] == 6 and rm["repeats_per_content"] == 16
    assert seal["null_construction"]["n_perm"] == 1000 and seal["bootstrap"]["n_boot"] == 1000
