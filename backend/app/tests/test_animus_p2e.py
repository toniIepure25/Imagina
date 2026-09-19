"""ANIMUS-P2E tests: seal inheritance, spatial-provenance block resolution, capability isolation.

Design/product-only; no real neural data. Verifies the P2E resolution is internally consistent and that the
ROI spatial-provenance block keeps perception BLOCKED and imagery UNAUTHORIZED.
"""
from __future__ import annotations

import json
import os

from app.core.animus.p2.capability import (
    IMAGERY_NEURAL_CONTENT,
    PERCEPTION_NEURAL_CONTENT,
    ScientificCapabilityAuthorization,
    imagery_unauthorized_invariant,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2E = os.path.join(ROOT, "results", "animus_p2e")


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def test_seal_inheritance_audit_pass():
    a = _load(os.path.join(P2E, "P2_SEAL_INHERITANCE_AUDIT.json"))
    assert a["seal_inheritance_pass"] is True
    assert a["seal_unchanged"] is True and a["no_new_protocol"] is True


def test_spatial_certification_fails_closed():
    c = _load(os.path.join(P2E, "spatial_transform_certification.json"))
    assert c["certification_pass"] is False
    assert c["findings"]["primary_dataset"]["mni2009c_space_present"] is False
    assert c["findings"]["fallback_dataset"]["mni2009c_space_present"] is False
    assert c["findings"]["neural_outcomes_inspected"] is False


def test_decision_is_roi_spatial_provenance_block():
    d = _load(os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json"))
    assert d["decision"] == "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE"
    assert d["perception_status"] == "BLOCKED"
    assert d["imagery_remains_unauthorized"] is True
    assert d["n_pass"] == 0 and d["authorized_claim"].startswith("none")


def test_block_keeps_capabilities_correct():
    auth = ScientificCapabilityAuthorization().validate_perception(
        "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE")
    assert auth.status(PERCEPTION_NEURAL_CONTENT) == "BLOCKED"
    assert not auth.is_usable(PERCEPTION_NEURAL_CONTENT)
    assert not auth.is_usable(IMAGERY_NEURAL_CONTENT)
    assert imagery_unauthorized_invariant(auth)


def test_no_fabricated_outcomes_in_execution_status():
    s = _load(os.path.join(P2E, "execution_status.json"))
    assert s["blocked_stage"] == "spatial_transform"
    for st in s["per_subject"].values():
        assert st["result"] == "N/A" and st["confirmatory"] == "N/A"


def test_integrity_and_red_team_pass():
    i = _load(os.path.join(P2E, "final_integrity_audit.json"))
    assert i["no_invented_registration"] and i["roi_unchanged_wang25"] and i["no_atlas_switch"]
    assert i["no_confirmatory_outcome_inspected"] and i["no_fabricated_numbers"]
    r = _load(os.path.join(P2E, "red_team_audit.json"))
    assert r["audit_pass"] and r["critical_unresolved_issues"] == []
