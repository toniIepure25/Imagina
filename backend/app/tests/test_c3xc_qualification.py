"""C3XC qualification invariants (synthetic + artifact integrity; no downloads).
Guards: session unit-balance / correspondence logic, ROI contract identity, seal
presence + self-hash, artifact self-hashes, decision gate logic, terminology.
Artifact checks are skip-if-absent so the suite is green before Phase 2/3 outputs.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from app.research.fmri.c3xb_reliability import subject_reliability_gate

_ROOT = Path(__file__).resolve().parents[3]
_SEAL = _ROOT / "reports" / "c3xc" / "c3xc_protocol_seal.json"
_HASHED = [
    "reports/c3xc/c3xc_protocol_seal.json",
    "results/c3xc/c3xc_candidate_inventory.json",
    "results/c3xc/subject_certification.json",
    "results/c3xc/correspondence_audit.json",
    "results/c3xc/C3XC_DECISION.json",
] + [f"results/c3xc/c3xc_reliability_S{i}.json" for i in range(1, 7)]


def _verify(obj):
    o = dict(obj)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_seal_present_and_self_hash():
    assert _SEAL.exists(), "C3XC seal must exist before neural outcomes"
    o = json.load(open(_SEAL))
    assert _verify(o)
    assert o["sealed_before_neural_outcomes"] is True
    assert o["no_reconstruction"] and o["not_c4"] and o["no_geometry_computed"]
    # downstream authorization never broadens
    never = o["downstream_authorization"]["never"]
    for x in ("C3XR", "C3XR-CAT", "reconstruction", "C4"):
        assert x in never


def test_roi_contract_lists():
    o = json.load(open(_SEAL))["roi_contract"]
    assert o["primary"] == "VC" and "VC only" in o["gating_roi"]
    assert set(o["earlyVC_V1_areas"]) == {"V1d", "V1v"}
    # early-visual areas are inside VC; non-visual localizer areas excluded from VC
    assert set(o["LVC_areas"]).issubset(set(o["VC_areas"]))
    for bad in ("frontal_language", "temporal_language", "medial_TOM"):
        assert bad not in o["VC_areas"] and bad in o["excluded_nonvisual_localizer"]


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        o = json.load(open(p))
        if "self_hash" in o:
            assert _verify(o), rel


def test_session_unit_balance_logic():
    # synthetic mimic of the certify unit-contract: each session all contents exactly once
    n_content, n_sessions = 72, 5
    content = np.tile(np.arange(n_content), n_sessions)
    sess = np.repeat(np.arange(n_sessions), n_content)
    ok = True
    for s in set(sess.tolist()):
        u, c = np.unique(content[sess == s], return_counts=True)
        ok &= (len(u) == n_content and (c == 1).all())
    assert ok
    # a broken session (missing one content twice) must fail
    content2 = content.copy()
    content2[0] = content2[1]  # session 0 now has a duplicate + a missing
    broke = False
    for s in set(sess.tolist()):
        u, c = np.unique(content2[sess == s], return_counts=True)
        if not (len(u) == n_content and (c == 1).all()):
            broke = True
    assert broke


def test_decision_gate_logic():
    p = _ROOT / "results/c3xc/C3XC_DECISION.json"
    if not p.exists():
        return
    o = json.load(open(p))
    n = o["n_imagery_and_perception_pass"]
    d = o["decision"]
    if o["cue_control_acceptable"] and all(
        v["contract"] == "CERTIFIED" for v in o["per_subject"].values()
    ):
        if n >= 2:
            assert d == "C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED"
        elif n == 1:
            assert d == "C3XC_D2_SEMANTIC_IMAGERY_LIMITED"
        else:
            assert d == "C3XC_D2_SEMANTIC_IMAGERY_FAIL"
    assert (d == "C3XC_D2_SEMANTIC_IMAGERY_QUALIFIED") == bool(o["dataset_qualified"])
    it = o["content_scope"].lower()
    assert "semantic" in it or "event" in it
    for bad in ("static-image", "exact-image", "category imagery"):
        assert bad not in it


def test_gate_helper_consistency():
    good = {"reliability": 0.4, "perm_p_one_sided": 0.001, "bootstrap_ci95": [0.1, 0.6],
            "split_seed_values": [0.4, 0.39, 0.41]}
    assert subject_reliability_gate(good) == "SUBJECT_RELIABILITY_PASS"
    marginal = {**good, "bootstrap_ci95": [-0.05, 0.6]}
    assert subject_reliability_gate(marginal) == "SUBJECT_RELIABILITY_MARGINAL"
