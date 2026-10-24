"""C3XPR provenance-only assembler. Emits the seal + spatial-provenance evidence + decision from the
completed PUBLIC audit (OpenNeuro ds005191, Figshare 25808179 v1/v2, Zenodo 15686864, horikawa-t/
MindCaptioning tree+history, released .mat structural schema). NO raw BOLD, NO neural values, NO
reliability/geometry. Nothing non-public was obtained. Self-hashes every artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> None:
    out = Path(os.environ.get("C3XPR_OUT_DIR", "results/c3xpr"))
    reports = Path(os.environ.get("C3XPR_REPORTS_DIR", "reports/c3xpr"))
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    seal = {
        "artifact": "C3XPR_PROTOCOL_SEAL", "gate": "C3XPR", "sealed_at": "2026-09-11",
        "provenance_only": True, "obtained_non_public_artifact": False,
        "no_raw_bold": True, "no_neural_outcomes": True, "no_reliability": True, "no_geometry": True,
        "not_c3xdr_r2": True, "not_c3xe": True, "not_c4": True,
        "branch": "research/d2-roi-provenance-recovery-c3xpr",
        "lineage": {"c3xdr_r1_decision": "C3XDR_R1_BLOCKED_ROI_PROVENANCE", "c3xdr_seal": C3XDR_SEAL,
                    "c3xc_c3xd_c3xdr_immutable": True},
        "allowed_recovery_routes": [
            "1 exact released ROI masks + reference BOLD/EPI",
            "2 exact ROI voxel coordinates + parent grid + affine",
            "3 exact released-space reference + raw->released transform chain",
            "4 preprocessing/registration derivatives sufficient to recreate the released space",
            "5 released retinotopy/localizer derivatives sufficient to regenerate exact ROIs"],
        "approximate_or_substitute_roi_forbidden": True,
        "exact_requirements": ["coordinate round-trip", "exact voxel counts", "exact affine/grid agreement",
                               "100% in-brain validity", "same method every subject"],
        "decision_states": ["C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED", "C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL",
                            "C3XPR_PUBLIC_ROI_PROVENANCE_INSUFFICIENT", "C3XPR_AUTHOR_ARTIFACT_REQUIRED",
                            "C3XPR_ROI_PROVENANCE_UNRECOVERABLE (only w/ authoritative author response)"],
        "silence_is_not_unrecoverable": True,
        "self_hash_field": "self_hash"}

    blocker = {
        "artifact": "C3XDR_R1_BLOCKER_CLARIFICATION",
        "misreading": "'no preprocessing pipeline exists'",
        "accurate_blocker": "ROI/SPATIAL PROVENANCE insufficiency: the released ROIs are voxel-index masks "
                            "in an unidentified released functional space; the exact correspondence to a "
                            "raw-derived native functional space is not publicly reconstructable.",
        "paper_specifies_preprocessing": True,
        "note": "The publication provides substantial preprocessing methodology; the gap is the spatial "
                "reference/transform + ROI-defining derivatives, not the method description."}

    prep = {
        "artifact": "C3XPR_PUBLISHED_PREPROCESSING_CONTRACT",
        "source": "Horikawa 2025 Science Advances (10.1126/sciadv.adw1464) methods + released metadata",
        "PUBLICLY_SPECIFIED": ["functional preprocessing methodology described in the paper",
                               "manual correction of FreeSurfer segmentation is reported",
                               "released functional data on a regular 2 mm isotropic world lattice (from .mat xyz)"],
        "PUBLICLY_UNSPECIFIED_OR_UNVERIFIED": ["exact fMRIPrep/FreeSurfer/AFNI/ANTs versions not machine-verified here",
                                               "identity of the released world frame (native-anat vs MNI) not labelled in release",  # noqa: E501
                                               "no released reference EPI/BOLDref image", "no released affine/header",
                                               "no released raw->released transform chain"],
        "REQUIRES_DERIVATIVE": ["manually-corrected FreeSurfer surfaces (unreleased) that determine bbregister/"
                                "surface geometry/retinotopic + localizer ROI boundaries",
                                "localizer/retinotopy runs+GLMs that defined V1/LOC/FFA/PPA/VC (absent from ds005191)"],
        "note": "paper-method fidelity is not the blocker; the spatial reference + ROI-defining derivatives are."}

    openneuro = {
        "artifact": "C3XPR_OPENNEURO_SPATIAL_INVENTORY", "dataset": "ds005191 v1.0.2",
        "subjects": ["sub-01..sub-06"],
        "present": {"T1w": True, "inplaneT2": True, "fieldmaps": True,
                    "testImagery": True, "testPerception": True, "trainPerception": True},
        "absent": {"retinotopy": True, "pRF": True, "visual_localizer": True, "category_localizer": True,
                   "MT_localizer": True, "language_localizer": True},
        "localizer_retinotopy_hits": 0,
        "consequence": "route 5 (regenerate ROIs from localizer/retinotopy) is NOT available publicly: the "
                       "runs that defined the ROIs are not in the public raw dataset."}

    figshare = {
        "artifact": "C3XPR_FIGSHARE_SPATIAL_INVENTORY", "article": 25808179, "versions": [1, 2],
        "files": ["testImagery_S1..6.mat", "testPerception_S1..6.mat", "trainPerception_S1..6.mat",
                  "decfeat_wb.zip", "feature.zip", "res_encoding.zip", "res_textgen.zip", "Supplementary_Video1..3.mov"],  # noqa: E501
        "spatial_support_files": {"roi_masks": False, "reference_epi": False, "affine": False,
                                  "transform": False, "surface": False, "localizer": False, "retinotopy": False},
        "conclusion": "no spatial support artifact beyond what is embedded in the .mat (routes 1 & 3 not satisfied)."}

    zg = {
        "artifact": "C3XPR_ZENODO_GITHUB_PROVENANCE",
        "zenodo": {"record": "15686864", "content": "horikawa-t/MindCaptioning code snapshot zip (v1.0.0)",
                   "spatial_artifacts": False},
        "github": {"repo": "horikawa-t/MindCaptioning", "nature": "analysis code (decoding/encoding/text-gen)",
                   "getRoiVoxelIdx": "reads ROI indices ONLY from released .mat metainf; does not define/map from raw",
                   "history_commits_scanned": 100,
                   "spatial_artifacts_in_history": "NONE (no masks/reference/transform/preproc/localizer files)"}}

    mat = {
        "artifact": "C3XPR_RELEASED_MAT_SPATIAL_SCHEMA", "inspected_file": "testImagery_S1.mat (structural-only)",
        "metainf_fields": ["Block", "Label", "Run", "Session", "label_type", "roiind_value", "roiname",
                           "roiname_excluded", "roiname_used", "volInds", "voxind_all", "xyz"],
        "roi_indices_are_masks_over_released_voxels": True,
        "roiind_value_shape": [148513, 1853], "n_roinames": 1853, "n_roinames_used": 1679,
        "voxel_coordinates_available": True, "xyz_shape": [148513, 3], "xyz_units": "world millimetres",
        "world_coordinates_available": True, "voxel_ijk_field": False,
        "regular_lattice": True, "voxel_size_mm": 2.0, "lattice_roundtrip_residual": 0.0,
        "occupied_bbox_dims": [78, 86, 63],
        "full_parent_grid_known": False, "affine_known": False, "boldref_identifier_known": False,
        "world_frame_identified": False,
        "can_reconstruct_nifti_mask_in_released_frame_exactly": True,
        "can_relate_exactly_to_raw_native_functional_space_from_public_data": False,
        "why": "world coords + membership + 2 mm lattice permit an EXACT mask in the released (unlabelled) "
               "world frame, but no affine/space-identity/reference-EPI/transform is released, so exact "
               "reproducible correspondence to a fresh raw-derived native functional space is not publicly "
               "achievable; resampling into a new space would be approximate (forbidden)."}

    fs = {
        "artifact": "C3XPR_MANUAL_FREESURFER_DEPENDENCY",
        "status": "PUBLIC_PROVENANCE_DEPENDS_ON_UNRELEASED_MANUAL_FS_DERIVATIVE",
        "paper_reports_manual_fs_correction": True,
        "affects": ["bbregister functional<->anatomical registration", "surface geometry",
                    "retinotopic boundaries", "localizer ROI definitions", "VC/LVC/HVC voxel membership"],
        "bypassing_released_derivative_found": False,
        "note": "vanilla recon-all is NOT a permitted substitute; exact ROI reproduction depends on the "
                "unreleased manually-corrected FreeSurfer derivative."}

    author = {
        "artifact": "C3XPR_AUTHOR_REQUEST_MANIFEST",
        "smallest_unblocking_artifact": "per-subject VC/LVC/HVC NIfTI masks + matching native-space BOLD "
                                        "reference image (S1-S6)",
        "acceptable_alternatives": ["ROI voxel coordinates + parent-grid dims + affine",
                                    "released BOLDref + raw->released transform chain",
                                    "manually-corrected FreeSurfer derivative used for registration",
                                    "retinotopy/localizer derivative masks"],
        "explicitly_not_needed": ["semantic features", "captions", "decoder outputs", "model checkpoints",
                                  "subject rankings", "best-ROI recommendations", "any neural outcomes"],
        "email": "reports/c3xpr/AUTHOR_REQUEST_EMAIL.md", "issue": "reports/c3xpr/GITHUB_ISSUE_DRAFT.md",
        "auto_send": False}

    decision = {
        "artifact": "C3XPR_DECISION", "gate": "C3XPR",
        "seal_self_hash": None,
        "public_audit_exhaustive": True,
        "exact_mask_reconstructable_in_released_frame": True,
        "exact_relation_to_raw_native_functional_space_public": False,
        "vc_mask_publicly_reconstructable_in_native_raw_space": False,
        "lvc_hvc_mask_publicly_reconstructable_in_native_raw_space": False,
        "decision": "C3XPR_PUBLIC_ROI_PROVENANCE_PARTIAL",
        "state": "C3XPR_AUTHOR_ARTIFACT_REQUIRED",
        "roi_provenance_unrecoverable": False,
        "reason_not_unrecoverable": "no authoritative author response yet; silence != unrecoverable",
        "minimal_missing_artifact": author["smallest_unblocking_artifact"],
        "author_request_prepared": True, "author_request_sent": False, "author_response_obtained": False,
        "c3xdr_r2_authorized": False,
        "c3xdr_r2_authorization_condition": "only upon C3XPR_PUBLIC_ROI_PROVENANCE_RECOVERED or receipt of "
                                            "the requested authoritative spatial artifacts (a future gate)",
        "immutable_prior_gates": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1"],
        "no_raw_bold": True, "no_neural_outcomes": True, "no_geometry": True, "no_substitute_roi": True}

    sealed = _sh(seal)
    decision["seal_self_hash"] = sealed["self_hash"]
    for name, obj in [("c3xpr_protocol_seal.json", sealed), ("c3xdr_r1_blocker_clarification.json", blocker),
                      ("published_preprocessing_contract.json", prep), ("openneuro_spatial_inventory.json", openneuro),
                      ("figshare_spatial_inventory.json", figshare), ("zenodo_github_provenance.json", zg),
                      ("released_mat_spatial_schema.json", mat), ("manual_freesurfer_dependency.json", fs),
                      ("author_request_manifest.json", author), ("C3XPR_DECISION.json", decision)]:
        target = reports if name == "c3xpr_protocol_seal.json" else out
        target.mkdir(parents=True, exist_ok=True)
        json.dump(_sh(obj) if name != "c3xpr_protocol_seal.json" else obj,
                  open(target / name, "w"), indent=2)
    print("DECISION:", decision["decision"], "|", decision["state"], "| C3XDR-R2 authorized:", decision["c3xdr_r2_authorized"])  # noqa: E501


if __name__ == "__main__":
    main()
