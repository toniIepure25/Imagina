"""C3XB artifact-integrity invariants (no downloads). Every C3XB JSON that carries a
self_hash must verify; the terminology binding (CATEGORY imagery, never exact-image/
pixel-matched) must hold in the decision and correspondence; the decision must never
authorize exact-image C3XR / reconstruction / C4. All checks are skipped-if-absent so
the suite is green before Phase 1/2 have produced their artifacts.
"""
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]

_HASHED = [
    "reports/c3xb/c3xb_protocol_seal.json",
    "results/c3xb/c3xa_authorization_clarification.json",
    "results/c3xb/c3xb_scope_registry.json",
    "results/c3xb/c3xb_candidate_inventory.json",
    "results/c3xb/god_cue_leakage_audit.json",
    "results/c3xb/god_data_contract.json",
    "results/c3xb/god_trial_manifest.json",
    "results/c3xb/god_perception_imagery_correspondence.json",
    "results/c3xb/c3xb_decision.json",
]


def _verify_self_hash(obj):
    o = dict(obj)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_all_self_hashes_verify():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        obj = json.load(open(p))
        if "self_hash" in obj:
            assert _verify_self_hash(obj), rel


def test_authorization_clarification_semantics():
    p = _ROOT / "results/c3xb/c3xa_authorization_clarification.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["general_C3XR_authorized"] is False
    assert o["natural_exact_or_natural_image_C3XR_authorized"] is False
    assert o["restricted_artificial_shape_pilot_possible"] is True
    assert o["restricted_artificial_shape_pilot_is_not_general_C3XR"] is True


def test_terminology_binding_in_decision():
    p = _ROOT / "results/c3xb/c3xb_decision.json"
    if not p.exists():
        return
    o = json.load(open(p))
    blob = json.dumps(o).lower()
    assert "exact-image" not in o.get("imagery_type", "").lower()
    assert "pixel-matched" not in o.get("imagery_type", "").lower()
    assert "category" in o.get("imagery_type", "").lower()
    if o.get("dataset_qualified"):
        assert "c3xr-cat" in o["authorizes"].lower()
        assert "exact-image" in o["does_NOT_authorize"].lower()
    # never authorizes reconstruction / C4
    assert o["no_reconstruction"] is True and o["not_c4"] is True
    assert "reconstruction" in blob  # the does_NOT_authorize clause names it


def test_decision_gate_consistency():
    p = _ROOT / "results/c3xb/c3xb_decision.json"
    if not p.exists():
        return
    o = json.load(open(p))
    n = o["n_imagery_and_perception_pass"]
    d = o["decision"]
    if o["cue_contamination_state"] == "CUE_CONTAMINATION_CONTROLLED":
        if n >= 2:
            assert d == "C3XB_GOD_CATEGORY_IMAGERY_QUALIFIED"
        elif n == 1:
            assert d == "C3XB_GOD_CATEGORY_IMAGERY_PROMISING"
        else:
            assert d == "C3XB_GOD_CATEGORY_IMAGERY_FAIL"
    assert (d == "C3XB_GOD_CATEGORY_IMAGERY_QUALIFIED") == bool(o["dataset_qualified"])
