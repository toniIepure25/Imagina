"""C3XPA author-spatial-artifact acceptance invariants (hermetic; NO cluster/network/BOLD).

Enforces, WITHOUT ever inspecting neural outcomes:
  * prior gates (C3XC/C3XD/C3XDR/C3XDR-R1/C3XPR) immutable; C3XDR seal unchanged;
  * assembler imports/calls no reliability/geometry/semantic/BOLD estimator (provenance-only);
  * every received artifact is hashed before processing;
  * validation certifies on EXACT 100% coordinate-set agreement only (Dice~1 insufficient);
  * no atlas/whole-brain substitution, no subject dropping, no outcome-based ROI acceptance;
  * C3XDR-R2 authorized ONLY on C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED (exact) under the C3XDR seal;
  * author silence != "provenance unavailable" != any certification state;
  * precondition-unmet closeout is internally consistent (gate not started; nothing fabricated);
  * all emitted artifacts carry valid self-hashes.
"""
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_R = _ROOT / "results" / "c3xpa"
_REP = _ROOT / "reports" / "c3xpa"
_C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
_C3XPR_SHA = "b42358dee4a05ad22b66d04c773e9af0ac2f979e"
_SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]
_HASHED = [
    "reports/c3xpa/c3xpa_protocol_seal.json",
    "results/c3xpa/author_response_provenance.json",
    "results/c3xpa/received_artifact_manifest.json",
    "results/c3xpa/reference_space_certification.json",
    "results/c3xpa/C3XPA_DECISION.json",
] + [f"results/c3xpa/spatial_correspondence_{s}.json" for s in _SUBS]


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
    for rel in ("results/c3xpr/C3XPR_DECISION.json",
                "results/c3xdr_r1/C3XDR_R1_DECISION.json",
                "reports/c3xdr/c3xdr_execution_seal.json"):
        p = _ROOT / rel
        if p.exists():
            assert _verify(json.load(open(p))), rel
    s = _ROOT / "reports/c3xdr/c3xdr_execution_seal.json"
    if s.exists():
        assert json.load(open(s))["self_hash"] == _C3XDR_SEAL


def test_assembler_is_provenance_only():
    src = (_ROOT / "backend/app/research/fmri/run_c3xpa_accept.py").read_text()
    low = src.lower()
    for bad in ("c3xb_reliability", "c3xc_fast", "c3xb_fast", "c3x_reliability",
                "reliability_with_inference", "c3g_geometry", "participation_ratio",
                "subspace_overlap", "linear_cka", "procrustes", "crossnobis",
                "nibabel", "nilearn", "deberta", "timesformer", "braindat", "decod"):
        assert bad not in low, bad
    for bad in ("CLIP", "DINO"):
        assert bad not in src, bad


def test_seal_declares_exact_match_and_forbidden_shortcuts():
    seal = json.load(open(_REP / "c3xpa_protocol_seal.json"))
    assert seal["provenance_validation_only"] is True
    assert seal["no_raw_bold"] and seal["no_neural_outcomes"] and seal["no_geometry"]
    assert seal["not_c3xdr_r2"] and seal["not_c4"]
    assert seal["no_atlas_substitution"] and seal["no_subject_dropping"]
    assert seal["no_outcome_based_roi_acceptance"] is True
    assert seal["author_silence_not_equals_unavailable"] is True
    assert "100%" in seal["exact_match_required"]
    assert "insufficient" in seal["exact_match_required"].lower()  # Dice~1 not enough
    assert seal["lineage"]["c3xpr_parent_sha"] == _C3XPR_SHA
    assert seal["lineage"]["c3xdr_seal"] == _C3XDR_SEAL


def test_precondition_unmet_closeout_consistent():
    p = _R / "C3XPA_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    if d["decision"] == "C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED":
        # gate did not start: not a certification state, nothing fabricated, R2 not authorized
        assert d["precondition_met"] is False
        assert d["is_certification_state"] is False
        assert d["author_response_obtained"] is False
        assert d["author_confirms_unavailable"] is False  # silence != unavailable
        assert d["per_subject_certified_exact"] == 0
        assert d["c3xdr_r2_authorized"] is False
        assert d["no_fabricated_artifact_or_correspondence"] is True


def test_received_manifest_hashed_before_processing():
    p = _R / "received_artifact_manifest.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["hashed_before_processing"] is True
    # empty at this run; if items ever present, each must carry a sha256
    for it in o.get("items", []):
        assert isinstance(it.get("sha256"), str) and len(it["sha256"]) == 64


def test_no_artifact_means_no_fabricated_correspondence():
    for s in _SUBS:
        p = _R / f"spatial_correspondence_{s}.json"
        if not p.exists():
            continue
        c = json.load(open(p))
        if c["status"] == "NO_ARTIFACT_RECEIVED":
            # every comparison field must be null and exact_match False (never invented numbers)
            for k in ("released_voxel_count", "recovered_voxel_count", "released_coordinate_hash",
                      "received_coordinate_hash", "n_exact_matches", "n_missing", "n_extra",
                      "affine", "orientation", "grid"):
                assert c[k] is None, (s, k)
            assert c["exact_match"] is False


def test_certification_requires_exact_match_not_dice():
    # A per-subject ROI may be certified EXACT only with zero missing/extra coordinates.
    for s in _SUBS:
        p = _R / f"spatial_correspondence_{s}.json"
        if not p.exists():
            continue
        c = json.load(open(p))
        if c["exact_match"] is True:
            assert c["n_missing"] == 0 and c["n_extra"] == 0
            assert c["released_coordinate_hash"] == c["received_coordinate_hash"]
            assert c["released_voxel_count"] == c["recovered_voxel_count"]


def test_c3xdr_r2_authorized_only_on_exact_recovery():
    p = _R / "C3XPA_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    if d["c3xdr_r2_authorized"] is True:
        # authorization is gated on the exact-recovery decision + full cohort certified
        assert d["decision"] == "C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED"
        assert d["per_subject_certified_exact"] == len(_SUBS)
    else:
        assert d["decision"] != "C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED"


def test_author_confirms_unavailable_requires_authoritative_statement():
    p = _R / "C3XPA_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    if d["decision"] == "C3XPA_AUTHOR_CONFIRMS_PROVENANCE_UNAVAILABLE":
        # only on an explicit authoritative response, never on silence
        assert d["author_response_obtained"] is True
        assert d["author_confirms_unavailable"] is True


def test_no_subject_dropping():
    p = _R / "C3XPA_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert d["cohort_required"] == _SUBS
