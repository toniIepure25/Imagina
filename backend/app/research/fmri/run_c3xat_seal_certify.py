"""C3XAT — Atlas-defined Cue-Deconfounded Raw Imagery Qualification: seal + contract/provenance
assembler.

C3XAT is a NEW prospectively-sealed measurement-qualification family. It is NOT a continuation,
relaxation, or exact replication of the released KamitaniLab ROI analysis (that is C3XDR, which
remains provenance-blocked). C3XAT defines visual ROIs from independently published, fully
reproducible public atlases (Wang 2015 topographic MPM primary; Benson14 anatomy-predicted V1-V3
secondary) in a pinned MNI152NLin2009cAsym 2 mm fMRIPrep space.

This assembler emits the Phase-0 seal, the scope registry, and every publicly-verifiable contract /
provenance artifact, PLUS honest execution-state records. Confirmatory execution (selective raw
ds005191 acquisition + reproducible fMRIPrep preprocessing of S1-S6 + atlas ROI construction + spatial
QC + sealed reliability + cue/video falsification) requires the OrchestrAI cluster and cannot be
completed inside this session; the live kubeconfig is not present here (never committed, per policy).
Therefore NO R_I / R_P / falsification outcome is computed or fabricated: those records are emitted with
status EXECUTION_BLOCKED and null outcome fields, and the decision is C3XAT_BLOCKED_EXECUTION.

NO raw BOLD is inspected. NO geometry, decoding, reconstruction, or semantic features. Prior gates
(C3XC/C3XD/C3XDR/C3XDR-R1/C3XPR/C3XPA) are preserved unchanged. C3XAG is NOT authorized here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]
C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
C3XPA_PARENT = "bf58713"  # C3XPA final tip (docs-recorded CI-verified closeout)
SPLIT_BASE = 20260909
SPLIT_OFFSETS = [0, 100, 200]


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def _dump(obj, path: Path):
    json.dump(_sh(obj), open(path, "w"), indent=2)


def build(out: Path, reports: Path) -> str:
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    # ---- scope registry (created BEFORE anything else) -------------------------------------------
    scope = {
        "artifact": "C3XAT_SCOPE_REGISTRY",
        "C3XDR": "exact replay using original released KamitaniLab ROI definitions; still blocked by "
                 "missing released<->raw spatial provenance.",
        "C3XPA": "dormant author-artifact validator; may be resumed if authoritative spatial material "
                 "arrives.",
        "C3XAT": "new atlas-defined raw-fMRI analysis; does NOT reproduce the original ROI definition.",
        "no_historical_decision_superseded": True,
        "c3xdr_status": "PRESERVED, immutable, provenance-blocked",
        "c3xpa_status": "PRESERVED, immutable, dormant (C3XPA_NO_AUTHOR_ARTIFACT_RECEIVED)",
        "is_exact_replication_of_kamitani_roi": False,
        "is_continuation_or_relaxation_of_c3xdr": False,
    }
    _dump(scope, out / "c3xat_scope_registry.json")

    # ---- Phase-0 protocol seal -------------------------------------------------------------------
    seal = {
        "artifact": "C3XAT_PROTOCOL_SEAL", "gate": "C3XAT", "sealed_at": "2026-09-11",
        "family": "NEW prospectively-sealed atlas-defined measurement-qualification gate",
        "not_c3xdr_replay": True, "not_exact_kamitani_roi": True,
        "measurement_qualification_only": True,
        "no_geometry": True, "no_decoding": True, "no_reconstruction": True, "no_semantic_features": True,
        "branch": "research/d2-atlas-raw-imagery-c3xat",
        "lineage": {"c3xpa_parent": C3XPA_PARENT, "c3xdr_seal_unchanged": C3XDR_SEAL,
                    "prior_gates_immutable": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1", "C3XPR", "C3XPA"]},
        "frozen": {
            "dataset": {"source": "OpenNeuro ds005191", "version": "1.0.2", "subjects": SUBS,
                        "include": ["testImagery", "testPerception", "anat", "fieldmaps", "events",
                                    "sidecars"],
                        "exclude": ["trainPerception"],
                        "trainPerception_use": "excluded from analysis; if technically required it is used "
                                               "for NO neural/outcome/parameter-tuning purpose"},
            "preprocessing": {"tool": "fMRIPrep (single pinned workflow)",
                              "output_space": "MNI152NLin2009cAsym", "resolution_mm": 2,
                              "smoothing": "NONE (primary multivoxel reliability)",
                              "pinned_fields": ["fmriprep_version", "container_digest", "freesurfer_version",
                                                "templateflow_versions_hashes", "ants_version",
                                                "afni_version", "all_command_line_parameters",
                                                "all_output_space_parameters"],
                              "no_post_outcome_modification": True},
            "output_space": "MNI152NLin2009cAsym 2mm isotropic",
            "primary_roi": {"name": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK",
                            "source": "Wang et al. 2015 Probabilistic Maps of Visual Topography",
                            "representation": "volume-based MNI maximum-probability map (MPM)",
                            "use_complete_atlas": True, "maps": 25, "regions": 22,
                            "no_subselection_by_performance": True,
                            "terminology": "atlas-defined topographic visual network (NOT Kamitani VC)"},
            "secondary_rois": {"BENSON_V1V2V3": {
                "source": "Benson14 anatomy-predicted retinotopy via Neuropythy (pinned template)",
                "definition": "union of atlas-predicted V1+V2+V3, both hemispheres",
                "role": "SECONDARY; cannot rescue a failed primary gate; cannot change primary PASS"}},
            "whole_cortex_control": {"name": "CORTICAL_GRAY_MATTER",
                                     "source": "preprocessing tissue segmentation only",
                                     "role": "descriptive enrichment control; NOT a qualification ROI"},
            "GLM": {"model": "MODEL_A_LSA (frozen, reused from C3XD/C3XDR, unchanged)",
                    "definition": "per-trial cue + per-trial imagery + per-trial post-video + grouped "
                                  "evaluation + nuisance",
                    "no_model_reopening": True, "no_lss_switch_on_results": True},
            "nuisance": {"family": ["motion", "run/session intercepts", "drift/high-pass",
                                    "justified physiological/tissue nuisance"],
                         "never_regressed_from_imagery": ["video identity", "semantic embeddings",
                                                          "captions", "vividness", "accuracy"]},
            "reliability_estimator": {
                "callable": "c3xb_reliability.reliability_with_inference_pairs",
                "independent_unit": "imagery SESSION",
                "statistic": "R_I_ATLAS = Spearman-Brown corrected session-disjoint split-half reliability "
                             "of concatenated 72-video mean multivoxel patterns",
                "primary_roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK"},
            "null": {"scheme": "within-imagery-session video-label permutation",
                     "preserves": ["session", "trial count", "video count", "ROI data",
                                   "temporal structure"],
                     "no_cross_session_label_exchange": True, "n_perm": 1000},
            "bootstrap": {"scheme": "non-straddling hierarchical bootstrap",
                          "constraint": "no imagery session/trial in both halves of a split",
                          "safeguards": "C3R/C3XB bootstrap safeguards retained", "n_boot": 1000},
            "split_seeds": {"base": SPLIT_BASE, "offsets": SPLIT_OFFSETS, "n_rep_point": 200,
                            "no_seed_selection": True,
                            "new_namespace_rule": "if implementation requires a new seed namespace it is "
                                                  "sealed before outcomes"},
            "cue_video_falsification": {
                "mandatory": True, "conceptually_identical_to": "C3XDR",
                "diagnostics": ["G_cue", "G_imagery", "G_video", "cue_gain=G_cue/G_imagery",
                                "video_gain=G_video/G_imagery"],
                "operator": "propagate cue+post-video+nuisance through the exact Model-A imagery-beta "
                            "operator (no true imagery content imported)",
                "R_I_cuevideo_predicted": "reliability of that predicted signal",
                "Delta_I": "R_I_observed - R_I_cuevideo_predicted",
                "criterion": "subject does NOT pass on raw R_I alone; observed reliability must survive the "
                             "sealed cue/video falsification (Delta_I>0 AND randomization p<0.05 where "
                             "exchangeable, else sealed conservative sensitivity)"},
            "subject_primary_pass_requires_all": ["WANG25 R_I PASS", "WANG25 R_P PASS",
                                                  "cue/video contamination criterion PASS",
                                                  "unit contract PASS", "atlas mask QC PASS"],
            "subject_pass_statuses": ["PASS", "MARGINAL", "NOISE_FLOOR"],
            "dataset_decision_rule": {
                ">=2/6 primary PASS": "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED",
                "exactly 1/6": "C3XAT_D2_ATLAS_IMAGERY_LIMITED",
                "0/6 with valid measurement": "C3XAT_D2_ATLAS_IMAGERY_FAIL",
                "execution/provenance incomplete": "C3XAT_BLOCKED_*",
                "independent_of_c3xdr": True},
            "trial_contract": {"imagery": {"videos": 72, "reps_per_video": 5, "trials": 360,
                                           "imagery_sessions": 5},
                               "perception": {"videos": 72, "reps_per_video": 5},
                               "require": "72/72 exact video-identity correspondence; fail closed on "
                                          "contract violation"},
        },
        "authorization_on_qualified": "ONLY C3XAT_D2_ATLAS_IMAGERY_QUALIFIED authorizes PREPARING a new "
                                      "separately-sealed gate C3XAG (Atlas-defined Perception<->Imagery "
                                      "State Geometry). C3XAG is NOT executed here and is NOT C3XE / C3XR / "
                                      "C3XR-CAT / C3XDR-R2.",
        "forbidden_features": ["CLIP", "DINO", "TimeSformer", "DeBERTa", "LLMs", "captions",
                               "video embeddings", "semantic labels", "decoded features",
                               "Stable Diffusion", "reconstruction models"],
        "forbidden_geometry": ["G3", "G4", "G6", "G8", "CKA", "RDM geometry", "subspace overlap",
                               "state transform", "state transport"],
        "self_hash_field": "self_hash",
    }
    sealed = _sh(seal)
    json.dump(sealed, open(reports / "c3xat_protocol_seal.json", "w"), indent=2)
    seal_hash = sealed["self_hash"]

    # ---- dataset contract (publicly verifiable from ds005191 metadata; not requiring BOLD) -------
    dataset_contract = {
        "artifact": "C3XAT_DATASET_CONTRACT", "seal_self_hash": seal_hash,
        "dataset": "OpenNeuro ds005191", "version": "1.0.2", "subjects": SUBS,
        "include": ["testImagery", "testPerception", "anat", "fieldmaps", "events", "sidecars"],
        "exclude": ["trainPerception"],
        "trainPerception_parameter_tuning_forbidden": True,
        "imagery_contract": {"videos": 72, "reps_per_video": 5, "trials": 360, "imagery_sessions": 5},
        "perception_contract": {"videos": 72, "reps_per_video": 5},
        "video_identity_correspondence_required": "72/72",
        "fail_closed_on_violation": True,
        "contract_verified_against_events": False,
        "status": "SPEC_FROZEN_EVENTS_VERIFICATION_PENDING_EXECUTION",
        "note": "trial counts/correspondence are the sealed contract; empirical verification against the "
                "released events.tsv is part of confirmatory execution (BIDS events only; no BOLD).",
    }
    _dump(dataset_contract, out / "dataset_contract.json")

    # ---- preprocessing provenance (pinned intended spec) ----------------------------------------
    preprocessing = {
        "artifact": "C3XAT_PREPROCESSING_PROVENANCE", "seal_self_hash": seal_hash,
        "tool": "fMRIPrep", "workflow": "single pinned workflow",
        "output_space": "MNI152NLin2009cAsym", "resolution_mm": 2, "smoothing": "NONE",
        "pinned": {"fmriprep_version": "PINNED_AT_EXECUTION", "container_digest": "PINNED_AT_EXECUTION",
                   "freesurfer_version": "PINNED_AT_EXECUTION",
                   "templateflow_versions_hashes": "PINNED_AT_EXECUTION",
                   "ants_version": "PINNED_AT_EXECUTION", "afni_version": "PINNED_AT_EXECUTION",
                   "command_line_parameters": "PINNED_AT_EXECUTION",
                   "output_space_parameters": "PINNED_AT_EXECUTION"},
        "no_smoothing_unless_sealed": True, "no_post_outcome_modification": True,
        "status": "SPEC_FROZEN_PREPROCESSING_NOT_EXECUTED",
        "note": "the exact version/digest/hash strings are frozen to their concrete values at the moment "
                "the pinned container is pulled on the cluster; recorded here as a frozen requirement so "
                "the primary space cannot drift. No preprocessing was run in this session.",
    }
    _dump(preprocessing, out / "preprocessing_provenance.json")

    # ---- atlas provenance (canonical public identity; binary hashes verified at download) --------
    wang = {
        "artifact": "C3XAT_WANG2015_ATLAS_PROVENANCE", "seal_self_hash": seal_hash,
        "atlas": "Wang et al. 2015 Probabilistic Maps of Visual Topography in Human Cortex",
        "roi_name": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK",
        "representation": "volume-based MNI maximum-probability map (MPM)",
        "maps": 25, "regions": 22, "use_complete_atlas": True, "no_performance_subselection": True,
        "space": "MNI152 (resampled to MNI152NLin2009cAsym 2mm at ROI construction; transform pinned)",
        "pinned": {"source_url_or_repository": "PINNED_AT_DOWNLOAD", "file_version": "PINNED_AT_DOWNLOAD",
                   "download_date": None, "sha256": None, "md5": None,
                   "voxel_resolution": "PINNED_AT_DOWNLOAD", "label_table": "PINNED_AT_DOWNLOAD"},
        "outcome_independent": True, "version_pinned": True, "reproducible_from_public_data": True,
        "status": "PROVENANCE_SPEC_FROZEN_HASH_VERIFICATION_PENDING_DOWNLOAD",
        "note": "canonical public atlas; SHA-256/MD5 are recorded null here and set to the verified digest "
                "of the exact downloaded file at construction time. No hash is fabricated.",
    }
    _dump(wang, out / "wang2015_atlas_provenance.json")

    benson = {
        "artifact": "C3XAT_BENSON14_ATLAS_PROVENANCE", "seal_self_hash": seal_hash,
        "atlas": "Benson14 anatomy-predicted retinotopy", "tool": "Neuropythy (pinned)",
        "roi_name": "BENSON_V1V2V3", "definition": "union of atlas-predicted V1+V2+V3, both hemispheres",
        "role": "SECONDARY", "cannot_rescue_primary": True,
        "pinned": {"neuropythy_version": "PINNED_AT_EXECUTION", "benson_template_version": "PINNED_AT_EXECUTION",
                   "template_hashes": None, "download_date": None},
        "outcome_independent": True, "version_pinned": True, "reproducible_from_public_data": True,
        "status": "PROVENANCE_SPEC_FROZEN_HASH_VERIFICATION_PENDING_EXECUTION",
        "note": "Benson14 predicts V1-V3 retinotopic organization from cortical anatomy alone; applied "
                "prospectively. Hashes set to verified values at execution. No hash fabricated.",
    }
    _dump(benson, out / "benson14_atlas_provenance.json")

    # ---- infrastructure re-audit ----------------------------------------------------------------
    infra = {
        "artifact": "C3XAT_INFRASTRUCTURE_REAUDIT", "seal_self_hash": seal_hash,
        "certified_by": "C3XDR-R1 (C3XDR_R1_REMOTE_INFRA_PASS)",
        "kubernetes_available": True, "persistent_nfs_free_GB": 107000, "a100_available": True,
        "large_cpu_ram": True,
        "changed_since_c3xdr_r1": False,
        "live_reaudit_performed_this_session": False,
        "reason": "the OrchestrAI kubeconfig is not present in this session (never committed, per policy); "
                  "live re-audit requires it. No new scientific decision is derived from infrastructure "
                  "because availability is unchanged from the C3XDR-R1 certification.",
        "status": "INFRA_ASSUMED_UNCHANGED_LIVE_REAUDIT_REQUIRES_KUBECONFIG",
    }
    _dump(infra, out / "infrastructure_reaudit.json")

    # ---- ROI QC (per subject) -- not constructed (preprocessing not executed) --------------------
    qc_fields = ["wang25_voxel_count", "benson_v1_count", "benson_v2_count", "benson_v3_count",
                 "benson_v1v3_union_count", "cortical_gray_matter_count", "affine", "shape",
                 "orientation", "brain_mask_overlap", "left_right_balance", "finite_coverage",
                 "mask_sha256"]
    for s in SUBS:
        qc = {"artifact": "C3XAT_ROI_QC", "subject": s, "seal_self_hash": seal_hash,
              "status": "ROI_NOT_CONSTRUCTED_EXECUTION_BLOCKED",
              "masks_frozen_before_outcomes": None, "manual_editing": False,
              "subject_specific_modification": False}
        for f in qc_fields:
            qc[f] = None
        qc["note"] = ("atlas ROIs are constructed from fMRIPrep MNI outputs, which were not produced in "
                      "this session; QC counts/hashes are null (not fabricated) and are frozen before any "
                      "R_I is computed at execution time.")
        _dump(qc, out / f"roi_qc_{s}.json")

    # ---- reliability (per subject) -- execution blocked -----------------------------------------
    rel_fields = ["reliability", "bootstrap_ci95", "bootstrap_mean", "null_mean", "null_std",
                  "perm_p_one_sided", "split_seed_values", "split_seed_min", "split_seed_max"]
    for s in SUBS:
        rel = {"artifact": "C3XAT_RELIABILITY", "subject": s, "seal_self_hash": seal_hash,
               "roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK", "independent_unit": "imagery SESSION",
               "estimator": "c3xb_reliability.reliability_with_inference_pairs",
               "split_seeds": [SPLIT_BASE + o for o in SPLIT_OFFSETS],
               "n_perm": 1000, "n_boot": 1000, "n_rep_point": 200,
               "status": "EXECUTION_BLOCKED", "subject_status": None, "subject_primary_pass": None}
        for f in rel_fields:
            rel[f] = None
        rel["note"] = ("no raw BOLD available in this session; R_I not computed and NOT fabricated. The "
                       "frozen estimator + seeds will produce this record at confirmatory execution.")
        _dump(rel, out / f"reliability_{s}.json")

    # ---- perception reliability -----------------------------------------------------------------
    perc = {"artifact": "C3XAT_PERCEPTION_RELIABILITY", "seal_self_hash": seal_hash,
            "roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK", "statistic": "R_P_ATLAS",
            "independent_unit": "perception runs/sessions", "status": "EXECUTION_BLOCKED",
            "per_subject": {s: {"R_I": None, "R_P": None, "R_I_over_R_P_attenuation": None} for s in SUBS},
            "no_geometry_from_attenuation": True,
            "note": "matched perception reliability in the SAME atlas ROI; not computed (blocked)."}
    _dump(perc, out / "perception_reliability.json")

    # ---- cue/video falsification ----------------------------------------------------------------
    fals = {"artifact": "C3XAT_CUEVIDEO_FALSIFICATION", "seal_self_hash": seal_hash,
            "mandatory": True, "conceptually_identical_to": "C3XDR", "status": "EXECUTION_BLOCKED",
            "diagnostics": {s: {"G_cue": None, "G_imagery": None, "G_video": None,
                                "cue_gain": None, "video_gain": None,
                                "R_I_observed": None, "R_I_cuevideo_predicted": None,
                                "Delta_I": None, "criterion_passed": None} for s in SUBS},
            "criterion": "Delta_I>0 AND randomization p<0.05 where exchangeable, else sealed conservative "
                         "sensitivity; raw R_I reliability alone is NOT sufficient to pass.",
            "note": "cue+post-video+nuisance propagated through the exact Model-A imagery-beta operator; "
                    "not computed (blocked). No true imagery content imported into the predicted signal."}
    _dump(fals, out / "cuevideo_falsification.json")

    # ---- negative controls (sealed list; not executed) ------------------------------------------
    controls = {"artifact": "C3XAT_NEGATIVE_CONTROLS", "seal_self_hash": seal_hash,
                "status": "EXECUTION_BLOCKED", "no_semantic_models": True,
                "controls": ["video-label permutation", "session-only predictor", "trial-order predictor",
                             "motion/quality-only predictor", "global-mean-pattern control",
                             "ROI-size-matched random cortical mask",
                             "current/previous/next video contamination", "early-vs-late imagery control",
                             "cue-only predicted reliability", "post-video-only predicted reliability"],
                "results": {c: None for c in [
                    "video_label_permutation", "session_only", "trial_order", "motion_quality_only",
                    "global_mean_pattern", "roi_size_matched_random", "adjacent_video_contamination",
                    "early_vs_late", "cue_only_predicted", "post_video_only_predicted"]},
                "note": "sealed control battery; none executed (no BOLD). Values null, not fabricated."}
    _dump(controls, out / "negative_controls.json")

    # ---- secondary Benson results ---------------------------------------------------------------
    benson_res = {"artifact": "C3XAT_SECONDARY_BENSON_RESULTS", "seal_self_hash": seal_hash,
                  "roi": "BENSON_V1V2V3", "role": "SECONDARY", "cannot_change_primary_decision": True,
                  "status": "EXECUTION_BLOCKED",
                  "per_subject": {s: {"R_I_BENSON_V1V2V3": None, "R_P_BENSON_V1V2V3": None,
                                      "attenuation": None, "R_I_cuevideo_predicted": None,
                                      "Delta_I": None} for s in SUBS},
                  "answers": "is any reliable imagery signal already present in anatomy-predicted early "
                             "visual cortex? -- not evaluable (blocked).",
                  "note": "computed only AFTER the primary WANG25 decision is frozen, at execution."}
    _dump(benson_res, out / "secondary_benson_results.json")

    # ---- spatial enrichment control -------------------------------------------------------------
    enrich = {"artifact": "C3XAT_SPATIAL_ENRICHMENT_CONTROL", "seal_self_hash": seal_hash,
              "status": "EXECUTION_BLOCKED", "does_not_qualify_dataset": True,
              "compare": ["WANG25", "Benson V1-V3", "whole cortical gray matter",
                          "ROI-size-matched random cortical masks (prospectively specified)"],
              "purpose": "test whether reliability is enriched in visual cortex rather than a generic "
                         "whole-brain artifact.",
              "results": None, "note": "descriptive only; not executed."}
    _dump(enrich, out / "spatial_enrichment_control.json")

    # ---- decision -------------------------------------------------------------------------------
    decision = {
        "artifact": "C3XAT_DECISION", "gate": "C3XAT", "seal_self_hash": seal_hash,
        "decision": "C3XAT_BLOCKED_EXECUTION", "is_blocked_not_fail": True,
        "dataset_gate_evaluated": False, "subjects_processed": 0, "downloaded_bytes": 0,
        "why_blocked": "confirmatory execution (selective raw ds005191 acquisition + reproducible fMRIPrep "
                       "of S1-S6 + atlas ROI construction + spatial QC + sealed reliability + cue/video "
                       "falsification) requires the OrchestrAI cluster and cannot be completed in this "
                       "session; the live kubeconfig is not present here (never committed).",
        "what_would_unblock": [
            "run the sealed pipeline on the OrchestrAI cluster: pull the pinned fMRIPrep container, "
            "preprocess S1-S6 to MNI152NLin2009cAsym 2mm, construct WANG25 + Benson V1-V3 + gray-matter "
            "masks, certify spatial QC, then execute the frozen reliability + cue/video falsification.",
            "download and hash-verify the Wang2015 MPM and Benson14 template (fill the null sha256 fields)."],
        "no_outcome_fabricated": True, "no_roi_selected_by_performance": True,
        "primary_roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK",
        "secondary_roi_cannot_rescue_primary": True,
        "c3xdr_rescued": False, "kamitani_roi_replicated": False,
        "correct_wording": "The exact released-ROI replay remains provenance-blocked. C3XAT independently "
                           "tests the core imagery-measurement question using prospectively defined public "
                           "atlas ROIs. No original Kamitani localizer ROI is reproduced.",
        "c3xag_authorized": False,
        "c3xag_authorization_condition": "ONLY C3XAT_D2_ATLAS_IMAGERY_QUALIFIED authorizes PREPARING "
                                         "(not executing) the separately-sealed C3XAG gate.",
        "does_NOT_authorize": ["C3XAG execution", "C3XE", "C3XR", "C3XR-CAT", "C3XDR-R2", "geometry",
                               "decoding", "reconstruction", "C4"],
        "no_geometry": True, "no_decoding": True, "no_reconstruction": True, "no_semantic_features": True,
        "immutable_prior_gates": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1", "C3XPR", "C3XPA"],
        "c3xdr_seal_unchanged": C3XDR_SEAL,
    }
    _dump(decision, out / "C3XAT_DECISION.json")
    return decision["decision"]


def main() -> None:
    out = Path(os.environ.get("C3XAT_OUT_DIR", "results/c3xat"))
    reports = Path(os.environ.get("C3XAT_REPORTS_DIR", "reports/c3xat"))
    dec = build(out, reports)
    print("DECISION:", dec, "| C3XAG authorized: False | no outcome fabricated: True")


if __name__ == "__main__":
    main()
