"""C3XPA author-spatial-artifact acceptance assembler.

HARD PRECONDITION: this gate validates author-provided spatial material ONLY after it is received.
At this run NO authoritative response or spatial artifact has been received (the C3XPR request was
prepared but not sent; no ROI masks/BOLDref/coordinates/transform/FreeSurfer derivative/reply exist).
Therefore this emits the Phase-0 seal and honest NO_ARTIFACT_RECEIVED records ONLY -- it does NOT
fabricate a received artifact, spatial correspondence, or any certification. No raw BOLD, no neural
values, no reliability/geometry. C3XDR-R2 remains NOT authorized.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
C3XPR_SHA = "b42358dee4a05ad22b66d04c773e9af0ac2f979e"
SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> None:
    out = Path(os.environ.get("C3XPA_OUT_DIR", "results/c3xpa"))
    reports = Path(os.environ.get("C3XPA_REPORTS_DIR", "reports/c3xpa"))
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    seal = {
        "artifact": "C3XPA_PROTOCOL_SEAL", "gate": "C3XPA", "sealed_at": "2026-09-11",
        "provenance_validation_only": True, "no_raw_bold": True, "no_neural_outcomes": True,
        "no_reliability": True, "no_geometry": True, "not_c3xdr_r2": True, "not_c3xe": True, "not_c4": True,
        "branch": "research/d2-author-spatial-artifact-c3xpa",
        "lineage": {"c3xpr_parent_sha": C3XPR_SHA, "c3xpr_decision": "C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL",
                    "c3xpr_state": "C3XPR_AUTHOR_ARTIFACT_REQUIRED", "c3xdr_seal": C3XDR_SEAL,
                    "prior_gates_immutable": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1", "C3XPR"]},
        "hard_precondition": "run ONLY after an authoritative author response/spatial artifact is received; "
                             "NOT merely because a request was prepared or sent",
        "precondition_status_at_seal": "UNMET",
        "exact_match_required": "100% released coordinate-set agreement; Dice~1 insufficient; no approximation",
        "no_atlas_substitution": True, "no_subject_dropping": True, "no_outcome_based_roi_acceptance": True,
        "author_silence_not_equals_unavailable": True,
        "authorizes_on_exact_recovery": "preparation of C3XDR-R2 under the SAME frozen C3XDR seal (does NOT execute it)",  # noqa: E501
        "self_hash_field": "self_hash"}
    sealed = _sh(seal)
    json.dump(sealed, open(reports / "c3xpa_protocol_seal.json", "w"), indent=2)

    resp = {
        "artifact": "C3XPA_AUTHOR_RESPONSE_PROVENANCE", "status": "NONE_RECEIVED",
        "c3xpr_request_sent": False, "c3xpr_auto_send": False, "author_response_obtained": False,
        "received_date": None, "sender_identity": None, "delivery_mechanism": None,
        "search_performed": True,
        "searched_locations": ["Downloads", "$HOME", "$HOME/Downloads"],
        "found_spatial_artifacts": [],
        "note": "No authoritative response or spatial artifact received. The C3XPR request was prepared "
                "(AUTHOR_REQUEST_EMAIL.md / GITHUB_ISSUE_DRAFT.md) but not sent per protocol; silence is "
                "NOT 'unavailable'."}

    manifest = {
        "artifact": "C3XPA_RECEIVED_ARTIFACT_MANIFEST", "status": "NO_ARTIFACT_RECEIVED",
        "items": [], "n_items": 0, "hashed_before_processing": True,
        "note": "empty: nothing was received to hash/validate."}

    refspace = {
        "artifact": "C3XPA_REFERENCE_SPACE_CERTIFICATION", "status": "NOT_APPLICABLE_NO_ARTIFACT",
        "reason": "no BOLDref/EPI or reference image received; cannot certify reference space."}

    for s in SUBS:
        corr = {
            "artifact": "C3XPA_SPATIAL_CORRESPONDENCE", "subject": s, "status": "NO_ARTIFACT_RECEIVED",
            "roi_names": ["VC", "LVC", "HVC", "V1"],
            "released_voxel_count": None, "recovered_voxel_count": None,
            "released_coordinate_hash": None, "received_coordinate_hash": None,
            "n_exact_matches": None, "n_missing": None, "n_extra": None,
            "affine": None, "orientation": None, "grid": None,
            "exact_match": False,
            "reason": "no author artifact received; per-subject provenance not evaluable (not fabricated)."}
        json.dump(_sh(corr), open(out / f"spatial_correspondence_{s}.json", "w"), indent=2)

    decision = {
        "artifact": "C3XPA_DECISION", "gate": "C3XPA", "seal_self_hash": sealed["self_hash"],
        "precondition_met": False,
        "decision": "C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED",
        "is_certification_state": False,
        "clarification": "This is NOT a certification outcome (RECOVERED/PARTIAL/CONTRADICTION/UNAVAILABLE), "
                         "each of which requires received material. The gate did not start because no "
                         "authoritative artifact was received.",
        "author_response_obtained": False, "author_confirms_unavailable": False,
        "per_subject_certified_exact": 0, "cohort_required": SUBS,
        "c3xdr_r2_authorized": False,
        "c3xdr_r2_authorization_condition": "C3XPA_AUTHOR_ROI_PROVENANCE_RECOVERED (exact 100% released "
                                            "coordinate-set agreement + certified native-reference relationship, "
                                            "cohort satisfiable) under the unchanged C3XDR seal",
        "immutable_prior_gates": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1", "C3XPR"],
        "no_raw_bold": True, "no_neural_outcomes": True, "no_geometry": True,
        "no_fabricated_artifact_or_correspondence": True,
        "next_action": "if/when the authors provide VC/LVC/HVC(+V1) masks + native BOLD reference (or an "
                       "acceptable route B/C/D/E artifact), re-run C3XPA validation on the received material."}
    json.dump(_sh(resp), open(out / "author_response_provenance.json", "w"), indent=2)
    json.dump(_sh(manifest), open(out / "received_artifact_manifest.json", "w"), indent=2)
    json.dump(_sh(refspace), open(out / "reference_space_certification.json", "w"), indent=2)
    json.dump(_sh(decision), open(out / "C3XPA_DECISION.json", "w"), indent=2)
    print("DECISION:", decision["decision"], "| precondition_met:", decision["precondition_met"],
          "| C3XDR-R2 authorized:", decision["c3xdr_r2_authorized"])


if __name__ == "__main__":
    main()
