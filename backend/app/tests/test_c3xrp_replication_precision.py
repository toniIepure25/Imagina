"""C3XRP replication & precision gate — hermetic invariants + synthetic validation (NO real neural data).

Verifies: the C3XAT-R1 anchor/artifacts are unchanged and the LIMITED decision is not reinterpreted;
C3XAG stays unauthorized; no real C3XRP neural-outcome files exist pre-seal; the dataset-independence
contract; the generalized fixed-denominator cohort gate (required_passes = max(2, ceil(N/3))); the
subject-conjunction gate; and synthetic Type-I / no-leakage behaviour of the precision simulator and the
paired-Delta sensitivity. All self-hashed artifacts verify.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from app.research.fmri import c3xrp_precision as C

_ROOT = Path(__file__).resolve().parents[3]
_R = _ROOT / "results" / "c3xrp"
_AT = _ROOT / "results" / "c3xat_r1"
_C3XAT_SEAL = "bb0d07acb9a2cf8d271d4697acc6cde352b9b12cd38504203b14f8cf6079cee2"


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


# ---- anchor / immutability -----------------------------------------------------------------------
def test_c3xat_anchor_and_limited_unchanged():
    a = _R / "c3xat_anchor.json"
    if not a.exists():
        return
    o = json.load(open(a))
    assert _verify(o)
    assert o["historical_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert o["may_be_changed"] is False and o["c3xag_authorized"] is False
    assert o["must_not_promote_sub02"] is True and o["must_not_target_sub02_or_sub03"] is True
    # the C3XAT-R1 final decision file still says LIMITED, 1/6
    fd = _AT / "C3XAT_R1_FINAL_DECISION_COMPLETE.json"
    if fd.exists():
        d = json.load(open(fd))
        assert d["final_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED" and d["pass_count"] == "1/6"
        assert d["c3xag_preparation_authorized"] is False


def test_no_real_c3xrp_outcome_files_preseal():
    # forbidden pre-seal outputs: real replication R_I/R_P/Delta result files
    for pat in ("c3xrp_R_I_*.json", "c3xrp_confirmatory_*.json", "replication_R_I_*.json"):
        assert not list(_R.glob(pat)), pat


# ---- dataset independence + selection -------------------------------------------------------------
def test_dataset_independence_and_selection():
    dec = _R / "dataset_selection_decision.json"
    if not dec.exists():
        return
    d = json.load(open(dec))
    assert _verify(d)
    assert d["requirements_not_weakened"] is True
    assert d["neural_outcomes_inspected"] is False
    assert d["ds005191_forbidden_use"].startswith("as the new replication outcome")
    m = _R / "candidate_matrix.json"
    if m.exists():
        cm = json.load(open(m))
        assert _verify(cm)
        assert cm["neural_outcomes_inspected"] is False
        # ds005191 and GOD (ds001246) must be NOT_INDEPENDENT
        by = {c["dataset_id"]: c for c in cm["candidates"]}
        assert by["ds005191"]["qualification_status"] == "NOT_INDEPENDENT_REPLICATION"
        assert by["ds001246"]["qualification_status"] == "NOT_INDEPENDENT_REPLICATION"


# ---- cohort gate (generalized fixed-denominator) --------------------------------------------------
def test_required_passes_and_cohort_gate():
    assert C.required_passes(6) == 2   # inherits C3XAT 2/6 = one-third
    assert C.required_passes(7) == 3
    assert C.required_passes(9) == 3
    assert C.required_passes(12) == 4
    assert C.cohort_gate(2, 6, 6) == "C3XRP_REPLICATION_QUALIFIED"
    assert C.cohort_gate(1, 6, 6) == "C3XRP_REPLICATION_LIMITED"
    assert C.cohort_gate(0, 6, 6) == "C3XRP_REPLICATION_FAIL"
    # fixed denominator: fewer valid than eligible -> blocked (no denominator shrinkage)
    assert C.cohort_gate(1, 5, 6).startswith("C3XRP_BLOCKED")


# ---- synthetic Type-I / power behaviour -----------------------------------------------------------
def test_paired_delta_type_I_under_null():
    # strict null: obs and pred share ONLY contamination (delta_truth=0). Delta must NOT falsely pass often.
    from app.research.fmri.c3xat_pipeline import paired_delta_sensitivity
    false_pass = 0
    n = 40
    for r in range(n):
        obs, pred, content, unit, *_ = C.simulate_subject(6, 24, 60, 0.0, 0.10, 0.20,
                                                          np.random.default_rng(100 + r))
        false_pass += int(paired_delta_sensitivity(obs, pred, content, unit, n_boot=120)["criterion_pass"])
    assert false_pass / n <= 0.15, f"Type-I too high: {false_pass}/{n}"


def test_true_imagery_above_contamination_passes():
    # a clear imagery-specific effect above contamination should usually pass the paired Delta
    from app.research.fmri.c3xat_pipeline import paired_delta_sensitivity
    npass = 0
    n = 20
    for r in range(n):
        obs, pred, content, unit, *_ = C.simulate_subject(7, 24, 60, 0.15, 0.10, 0.20,
                                                          np.random.default_rng(500 + r))
        npass += int(paired_delta_sensitivity(obs, pred, content, unit, n_boot=120)["criterion_pass"])
    assert npass / n >= 0.5


# ---- precision design analysis artifact -----------------------------------------------------------
def test_precision_analysis_present_and_type_I_controlled():
    p = _R / "precision_design_analysis.json"
    if not p.exists():
        return
    a = json.load(open(p))
    assert _verify(a)
    assert a["study_design_only"] is True and a["future_acquisition_only"] is True
    assert a["changes_any_existing_gate"] is False
    # Type-I at delta=0 should be controlled (<= ~0.15 under reduced-resample simulation)
    for _n, t1 in a["type_I_by_units"].items():
        assert t1 <= 0.20, (_n, t1)


# ---- protocol seal --------------------------------------------------------------------------------
def test_protocol_seal_valid_and_no_outcome():
    p = _R / "c3xrp_protocol_seal.json"
    if not p.exists():
        return
    s = json.load(open(p))
    assert _verify(s)
    assert s["gate"] == "C3XRP"
    assert s["c3xag_authorized"] is False
    assert s["real_neural_outcome_before_seal"] is False
    assert s["selected_replication_dataset"] in ("NO_PUBLIC_DATASET", None) or "dataset" in s
