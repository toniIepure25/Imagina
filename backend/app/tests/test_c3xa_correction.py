"""C3XA target-contract-correction invariants (synthetic; no download).

Verifies the fixation exclusion, family stratification, the critical
family-separation confound guard, the corrected gate reuse, and the seal.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.research.fmri import c3x_reliability as X
from app.research.fmri import run_c3xa_corrected_screen as C

_SEAL = Path(__file__).resolve().parents[3] / "reports" / "c3xa" / "c3xa_correction_seal.json"
_CONTRACT = Path(__file__).resolve().parents[3] / "results" / "c3xa" / "c3xa_target_contract.json"


def test_contract_partition():
    # 26 blocks != 26 targets: 25 targets (10 natural + 15 artificial) + 1 fixation
    assert C.NATURAL == list(range(1, 11))
    assert C.ARTIFICIAL == list(range(11, 26))
    assert C.FIXATION == 26
    assert len(C.NATURAL) == 10 and len(C.ARTIFICIAL) == 15
    assert C.FIXATION not in C.NATURAL and C.FIXATION not in C.ARTIFICIAL


def test_fixation_excluded_counts():
    # synthetic 520-sample imagery: 26 labels x 20 runs
    content = np.tile(np.arange(1, 27), 20)
    run = np.repeat(np.arange(20), 26)
    X_ = np.zeros((520, 5))
    n_tgt = int(np.sum(np.isin(content, C.NATURAL + C.ARTIFICIAL)))
    n_fix = int(np.sum(content == C.FIXATION))
    assert n_tgt == 500 and n_fix == 20
    # subset must never include fixation
    _, csub, _ = C._subset(X_, content, run, C.NATURAL + C.ARTIFICIAL)
    assert C.FIXATION not in set(csub.tolist())


def _family_fixture(seed, within_noise, n_runs=10):
    """Two families; ZERO within-family stimulus structure (all contents in a
    family share one expected pattern) but a large STABLE between-family mean
    difference. Run structure present."""
    rng = np.random.default_rng(seed)
    V = 200
    famA_mean = rng.standard_normal(V)          # shared by all 10 natural contents
    famB_mean = rng.standard_normal(V) + 8.0    # shared by all 15 artificial, large offset
    Xr, content, run = [], [], []
    for r in range(n_runs):
        for lab in C.NATURAL:
            Xr.append(famA_mean + rng.standard_normal(V) * within_noise)
            content.append(lab)
            run.append(r)
        for lab in C.ARTIFICIAL:
            Xr.append(famB_mean + rng.standard_normal(V) * within_noise)
            content.append(lab)
            run.append(r)
    return np.array(Xr), np.array(content), np.array(run)


def test_family_separation_confound_guard():
    Xr, content, run = _family_fixture(seed=1, within_noise=1.0)
    # within-family reliability must be ~0 (no within-family stimulus structure)
    r_nat = X.run_disjoint_reliability(*C._subset(Xr, content, run, C.NATURAL), seed=7, n_rep=100)
    r_art = X.run_disjoint_reliability(*C._subset(Xr, content, run, C.ARTIFICIAL), seed=7, n_rep=100)
    assert abs(r_nat) < 0.25, r_nat
    assert abs(r_art) < 0.25, r_art
    # combined across families IS inflated by the stable family separation
    r_comb = X.run_disjoint_reliability(*C._subset(Xr, content, run, C.NATURAL + C.ARTIFICIAL),
                                        seed=7, n_rep=100)
    assert r_comb > r_nat + 0.3 and r_comb > r_art + 0.3
    # the corrected procedure (within-family) is NOT fooled: gate is not PASS on noise-only family
    out = X.reliability_with_inference(*C._subset(Xr, content, run, C.NATURAL), seed=7,
                                       n_perm=200, n_boot=200)
    assert X.subject_reliability_gate(out) != "SUBJECT_RELIABILITY_PASS"


def test_within_family_true_reliability_detected():
    # positive control: real within-family stimulus structure -> within-family PASS
    rng = np.random.default_rng(2)
    V = 200
    centers = rng.standard_normal((10, V)) * 3
    Xr, content, run = [], [], []
    for r in range(10):
        for i, lab in enumerate(C.NATURAL):
            Xr.append(centers[i] + rng.standard_normal(V) * 0.5)
            content.append(lab)
            run.append(r)
    out = X.reliability_with_inference(np.array(Xr), np.array(content), np.array(run), seed=7,
                                       n_perm=200, n_boot=200)
    assert out["reliability"] > 0.5 and out["perm_p_one_sided"] < 0.05
    assert X.subject_reliability_gate(out) == "SUBJECT_RELIABILITY_PASS"


def test_no_geometry_callable():
    for name in X.FORBIDDEN_GEOMETRY:
        assert not hasattr(C, name)
    lines = [ln for ln in Path(C.__file__).read_text().splitlines()
             if "geometry" in ln.lower() and "import" in ln.lower()]
    assert lines == []


@pytest.mark.skipif(not _SEAL.exists(), reason="seal absent")
def test_seal_and_contract():
    seal = json.loads(_SEAL.read_text())
    stored = seal.pop("self_hash")
    assert hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest() == stored
    assert seal["target_contract"]["fixation_label"] == 26
    assert seal["target_contract"]["natural_labels"] == list(range(1, 11))
    assert seal["target_contract"]["artificial_labels"] == list(range(11, 26))
    assert seal["primary_future_geometry_family"].startswith("natural_10")
    contract = json.loads(_CONTRACT.read_text())
    # condition-local Label equality is explicitly NOT accepted as identity evidence
    assert "NOT numeric-label equality" in contract["family_fixation_assignment"]["basis"]
    assert contract["certified_contract"]["target_samples_total"] == 500
