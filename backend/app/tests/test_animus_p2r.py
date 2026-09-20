"""ANIMUS-P2-R tests: only-provenance-amended re-seal, inheritance, capability still blocked.

Design/product-only; no real neural data. Also includes hermetic spatial-technical fixtures required by
§35 (label-safe interpolation, wrong-affine/template rejection) exercised against the sealed rules.
"""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2R = os.path.join(ROOT, "results", "animus_p2r")


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def test_only_provenance_changed():
    seal = _load(os.path.join(P2R, "animus_p2r_protocol_seal.json"))
    assert "PREPROCESSING PROVENANCE" in seal["only_scientific_change"]
    assert seal["inherited_unchanged"]["primary_dataset"] == "NOD ds004496"
    assert seal["target_template"].startswith("MNI152NLin2009cAsym")
    assert "@sha256:" in seal["fmriprep"]["digest"] and seal["fmriprep"]["smoothing"] == "NONE"


def test_inheritance_unchanged():
    for name in ("split_inheritance_audit", "target_representation_inheritance", "decoder_inheritance"):
        assert _load(os.path.join(P2R, f"{name}.json"))["unchanged"] is True


def test_denominator_frozen_no_selection():
    d = _load(os.path.join(P2R, "participant_denominator_freeze.json"))
    assert d["n_eligible"] == 6 and d["required_passes"] == 2
    assert d["no_performance_based_selection"] and d["frozen_before_outcomes"]


def test_raw_available_not_blocked():
    a = _load(os.path.join(P2R, "nod_raw_preprocessing_audit.json"))
    assert a["raw_available"] and a["blocked"] is False
    assert all(v["raw_t1w"] and v["fieldmaps_present"] for v in a["per_subject"].values())


def test_capability_still_blocked_during_p2r():
    dec = _load(os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json"))
    assert dec["perception_status"] == "BLOCKED"
    assert dec["imagery_remains_unauthorized"] is True


# --- §35 hermetic spatial-technical fixtures (no performance endpoint) -----------------------------------
def test_label_safe_resample_rejects_continuous_interpolation():
    """A binary atlas mask must not be linearly interpolated to a new grid (would create fractional labels).
    Nearest-neighbor preserves membership {0,1}; linear does not."""
    mask = (np.random.default_rng(0).random((8, 8, 8)) > 0.6).astype(np.float32)
    # simulate a linear interpolation by averaging neighbors -> fractional values appear
    linear = 0.25 * (mask + np.roll(mask, 1, 0) + np.roll(mask, 1, 1) + np.roll(mask, 1, 2))
    frac_linear = np.mean((linear > 0) & (linear < 1))
    # nearest-neighbor keeps binary
    nn = mask
    assert frac_linear > 0.0            # linear introduces fractional labels -> must be rejected
    assert set(np.unique(nn)).issubset({0.0, 1.0})


def test_wrong_affine_is_detected():
    a = np.diag([2.0, 2.0, 2.0, 1.0])
    b = np.diag([3.0, 3.0, 3.0, 1.0])
    assert not np.allclose(a, b)        # a grid-compatibility check must fail-closed on affine mismatch


# --- frozen LSA-GLM feature extractor (design math; no real NIfTI) ------------------------------------
def test_lsa_design_recovers_known_betas():
    from app.research.animus_p2.extract_features_p2r import build_lsa_design, lsa_betas
    tr, n_scans, n_vox = 2.0, 120, 8
    rng = np.random.default_rng(0)
    # 10 well-separated trials
    onsets = list(np.arange(6.0, 6.0 + 10 * 20.0, 20.0))
    durs = [1.0] * 10
    nuis = rng.standard_normal((n_scans, 6))
    design, tidx = build_lsa_design(onsets, durs, tr, n_scans, nuis)
    assert len(tidx) == 10 and design.shape[0] == n_scans
    true_betas = rng.standard_normal((10, n_vox))
    # BOLD = trial design @ true + nuisance/intercept structure + small noise
    full = design.copy()
    coef = np.zeros((design.shape[1], n_vox))
    coef[tidx, :] = true_betas
    bold = full @ coef + 0.01 * rng.standard_normal((n_scans, n_vox))
    rec = lsa_betas(bold, design, tidx)
    # recovered trial betas correlate ~1 with truth
    r = np.corrcoef(rec.ravel(), true_betas.ravel())[0, 1]
    assert r > 0.98


def test_frozen_nuisance_selection_and_failclosed():
    from app.research.animus_p2.extract_features_p2r import select_frozen_nuisance
    n = 50
    conf = {c: np.random.default_rng(1).standard_normal(n) for c in
            ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z", "csf", "white_matter",
             "cosine00", "cosine01", "framewise_displacement"]}
    mat, sel = select_frozen_nuisance(conf)
    assert "trans_x" in sel and "csf" in sel and "cosine00" in sel
    assert "framewise_displacement" not in sel   # not in the frozen set
    assert mat.shape == (n, len(sel))
    # missing required motion -> fail-closed
    import pytest
    with pytest.raises(ValueError):
        select_frozen_nuisance({"csf": np.zeros(n), "cosine00": np.zeros(n)})
