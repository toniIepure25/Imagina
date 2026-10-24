"""C3XPR provenance-only invariants (hermetic; NO cluster/network/BOLD). Enforces: prior gates
immutable, no BOLD/reliability/geometry/semantic callable from C3XPR code, released-.mat inspection is
structural-only, exact reconstruction requires full grid provenance, approximate/substitute ROI fails
closed, manual-FreeSurfer dependency explicit, public vs author evidence separated, author request has
no outcome-selection language, and UNRECOVERABLE cannot be emitted without an authoritative response.
"""
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_R = _ROOT / "results" / "c3xpr"
_C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
_HASHED = [
    "reports/c3xpr/c3xpr_protocol_seal.json",
    "results/c3xpr/c3xdr_r1_blocker_clarification.json",
    "results/c3xpr/published_preprocessing_contract.json",
    "results/c3xpr/openneuro_spatial_inventory.json",
    "results/c3xpr/figshare_spatial_inventory.json",
    "results/c3xpr/zenodo_github_provenance.json",
    "results/c3xpr/released_mat_spatial_schema.json",
    "results/c3xpr/manual_freesurfer_dependency.json",
    "results/c3xpr/author_request_manifest.json",
    "results/c3xpr/C3XPR_DECISION.json",
]


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        o = json.load(open(p))
        if "self_hash" in o:
            assert _verify(o), rel


def test_prior_gates_immutable():
    # C3XDR-R1 decision + C3XDR seal still verify with unchanged hashes
    for rel in ("results/c3xdr_r1/C3XDR_R1_DECISION.json", "reports/c3xdr/c3xdr_execution_seal.json"):
        p = _ROOT / rel
        if p.exists():
            assert _verify(json.load(open(p))), rel
    s = _ROOT / "reports/c3xdr/c3xdr_execution_seal.json"
    if s.exists():
        assert json.load(open(s))["self_hash"] == _C3XDR_SEAL


def test_no_bold_reliability_geometry_semantic_callable():
    src = (_ROOT / "backend/app/research/fmri/run_c3xpr_audit.py").read_text()
    low = src.lower()
    # provenance-only: must not import/call any neural estimator or geometry/semantic module
    for bad in ("c3xb_reliability", "c3xc_fast", "c3x_reliability", "reliability_with_inference",
                "c3g_geometry", "participation_ratio", "subspace_overlap", "linear_cka", "procrustes",
                "crossnobis", "nibabel", "nilearn", "deberta", "timesformer", "braindat"):
        assert bad not in low, bad
    for bad in ("CLIP", "DINO"):
        assert bad not in src, bad


def test_released_mat_schema_structural_only():
    p = _R / "released_mat_spatial_schema.json"
    if not p.exists():
        return
    o = json.load(open(p))
    # must NOT contain neural-outcome fields
    blob = json.dumps(o).lower()
    for bad in ("r_i", "reliability", "condition_effect", "decoding", "geometry", "beta_value"):
        assert bad not in blob, bad
    # structural facts present
    assert o["roi_indices_are_masks_over_released_voxels"] is True
    assert o["voxel_coordinates_available"] is True


def test_exact_reconstruction_requires_full_grid_provenance():
    p = _R / "released_mat_spatial_schema.json"
    if not p.exists():
        return
    o = json.load(open(p))
    # exact release-frame mask is possible, but exact relation to raw requires grid+affine+reference,
    # which are absent -> must be False (fail-closed, no approximation)
    assert o["can_reconstruct_nifti_mask_in_released_frame_exactly"] is True
    if not (o["affine_known"] and o["full_parent_grid_known"] and o["boldref_identifier_known"]
            and o["world_frame_identified"]):
        assert o["can_relate_exactly_to_raw_native_functional_space_from_public_data"] is False


def test_manual_freesurfer_dependency_explicit():
    p = _R / "manual_freesurfer_dependency.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["status"] == "PUBLIC_PROVENANCE_DEPENDS_ON_UNRELEASED_MANUAL_FS_DERIVATIVE"
    assert o["bypassing_released_derivative_found"] is False


def test_public_vs_author_evidence_separated():
    seal = json.load(open(_ROOT / "reports/c3xpr/c3xpr_protocol_seal.json"))
    assert seal["obtained_non_public_artifact"] is False
    assert seal["silence_is_not_unrecoverable"] is True
    dec = _R / "C3XPR_DECISION.json"
    if dec.exists():
        d = json.load(open(dec))
        assert d["public_audit_exhaustive"] is True
        assert d["author_response_obtained"] is False


def test_author_request_no_outcome_language():
    for rel in ("reports/c3xpr/AUTHOR_REQUEST_EMAIL.md", "reports/c3xpr/GITHUB_ISSUE_DRAFT.md"):
        p = _ROOT / rel
        if not p.exists():
            continue
        low = p.read_text().lower().replace("*", "")  # strip markdown emphasis
        # must NOT ASK for outcomes/rankings
        for bad in ("which subject", "which roi", "perform best", "best-performing", "best roi",
                    "reliability result", "decoding accuracy", "performs best", "tell us which"):
            assert bad not in low, (rel, bad)
        # must explicitly DISCLAIM needing performance/ranking/features
        assert ("do not need" in low or "not need" in low) and ("ranking" in low or "features" in low), rel


def test_unrecoverable_requires_authoritative_response():
    p = _R / "C3XPR_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    if d["decision"] == "C3XPR_ROI_PROVENANCE_UNRECOVERABLE":
        assert d["author_response_obtained"] is True
    else:
        assert d["roi_provenance_unrecoverable"] is False


def test_decision_partial_and_no_c3xdr_r2_authorization():
    p = _R / "C3XPR_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert d["decision"] in ("C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED",
                             "C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL",
                             "C3XPR_PUBLIC_ROI_PROVENANCE_INSUFFICIENT")
    if d["decision"] != "C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED":
        assert d["c3xdr_r2_authorized"] is False
        assert d["state"] == "C3XPR_AUTHOR_ARTIFACT_REQUIRED"
    assert d["no_raw_bold"] and d["no_neural_outcomes"] and d["no_substitute_roi"]
