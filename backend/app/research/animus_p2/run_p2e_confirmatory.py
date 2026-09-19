"""ANIMUS-P2E real-confirmatory resolution.

Records the VERIFIED cluster reconnaissance of the sealed datasets' spatial provenance, applies the sealed
§7 rule, and resolves the P2 decision. Findings (from real OrchestrAIQ cluster jobs, no neural outcomes
inspected): the sealed primary ROI is the volumetric Wang25 MPM in MNI152NLin2009cAsym 2mm, but neither the
sealed primary (NOD ds004496) nor the fallback (BOLD5000 ds001499) publishes MNI152NLin2009cAsym-space
fMRIPrep derivatives or an MNI<->T1w transform — both are T1w/fsnative/orig only, and NOD's anat
derivatives are absent. The exact reproducible ROI<->BOLD relation therefore cannot be established from the
published provenance without a new cohort re-preprocessing decision (P2-R territory; §2 forbids introducing
it during confirmatory execution). Terminal: ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE. No neural outcome was
computed or fabricated. Emits certification + fallback record + decision + capability + integrity audit.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

from app.core.animus.p2.capability import (
    IMAGERY_NEURAL_CONTENT,
    PERCEPTION_NEURAL_CONTENT,
    ScientificCapabilityAuthorization,
    imagery_unauthorized_invariant,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2E = os.path.join(ROOT, "results", "animus_p2e")

DECISION = "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE"

# Verified real-cluster reconnaissance (no neural outcomes inspected).
FINDINGS = {
    "sealed_primary_roi": "WANG25 volumetric MPM in MNI152NLin2009cAsym 2mm (staged: "
                          "/work/wang/out/WANG25_primary_union_2009c2mm.nii.gz, shape (97,115,97) 2mm)",
    "primary_dataset": {
        "id": "ds004496 (NOD)", "public_fmriprep_spaces": ["T1w"],
        "mni2009c_space_present": False, "mni_to_t1w_transform_present": False,
        "anat_derivatives_present": False,
        "note": "sub-01 anat/ empty in fmriprep derivatives; only space-T1w func; ciftify is fsLR/CIFTI "
                "(not the sealed volumetric Wang25 MPM)."},
    "fallback_dataset": {
        "id": "ds001499 (BOLD5000)", "public_fmriprep_spaces": ["T1w", "fsnative", "orig"],
        "mni2009c_space_present": False, "mni_to_t1w_transform_present": False,
        "anat_derivatives_present": True, "freesurfer_present": True,
        "spm_derivatives": "subject-space functional ROI masks (EarlyVis/LOC/OPA/PPA/RSC), NOT the sealed "
                           "Wang25 atlas and NOT per-image betas",
        "note": "only affine target-fsnative / space-orig-to-T1w transforms; no MNI152NLin2009c warp/h5."},
    "reconnaissance_jobs": ["animus-p2e-inventory", "animus-p2e-xfmhunt", "animus-p2e-b5kprov (all Completed)"],
    "neural_outcomes_inspected": False,
}


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> int:
    os.makedirs(P2E, exist_ok=True)
    os.makedirs(P2, exist_ok=True)

    cert = {"artifact": "ANIMUS_P2E_SPATIAL_TRANSFORM_CERTIFICATION", "milestone": "ANIMUS-P2E",
            "certification_pass": False,
            "reason": "no MNI152NLin2009cAsym-space derivatives or MNI<->T1w transform available in either "
                      "candidate dataset's published provenance; sealed volumetric Wang25 MPM cannot be "
                      "applied to subject BOLD without re-deriving normalization (out of scope for "
                      "confirmatory execution per §2; §7 mandates fail-closed).",
            "findings": FINDINGS,
            "rule": "§7 ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE — do NOT invent a registration, switch "
                    "atlas, or use a vaguely similar template."}
    json.dump(_sh(cert), open(os.path.join(P2E, "spatial_transform_certification.json"), "w"), indent=2)

    fallback = {"artifact": "ANIMUS_P2E_FALLBACK_ACTIVATION", "milestone": "ANIMUS-P2E",
                "primary_blocked_pre_outcome": True,
                "primary_block_reason": "required derivatives unavailable (NOD anat derivatives absent) AND "
                                        "required transform unavailable (no MNI<->T1w) — §3 valid triggers",
                "fallback_checked": "ds001499 (BOLD5000)",
                "fallback_also_lacks_mni_relation": True,
                "recorded_before_any_confirmatory_outcome": True,
                "outcome": "both primary and fallback lack the sealed MNI ROI relation -> spatial "
                           "provenance block (not a performance-based switch)"}
    json.dump(_sh(fallback), open(os.path.join(P2E, "fallback_activation.json"), "w"), indent=2)

    # per-subject execution status: all BLOCKED at the transform stage, before any decoding metric.
    subjects = [f"sub-{i:02d}" for i in range(1, 7)]
    status = {"artifact": "ANIMUS_P2E_EXECUTION_STATUS", "milestone": "ANIMUS-P2E",
              "per_subject": {s: {"download": "N/A", "stimulus_audit": "N/A", "transform": "BLOCKED",
                                  "roi_qc": "N/A", "glm": "N/A", "feature_bundle": "N/A",
                                  "confirmatory": "N/A", "result": "N/A"} for s in subjects},
              "blocked_stage": "spatial_transform", "no_performance_in_status": True}
    json.dump(_sh(status), open(os.path.join(P2E, "execution_status.json"), "w"), indent=2)

    # decision + capability (perception BLOCKED; imagery stays UNAUTHORIZED)
    auth = ScientificCapabilityAuthorization().validate_perception(DECISION)
    assert imagery_unauthorized_invariant(auth)
    decision = {"artifact": "ANIMUS_P2_SCIENTIFIC_DECISION", "milestone": "ANIMUS-P2 (resolved by P2E)",
                "scientific_parent": "a0b6ca7", "protocol_sealed": True,
                "decision": DECISION,
                "reason": "Sealed volumetric-MNI Wang25 ROI cannot be applied to either candidate dataset's "
                          "published T1w/fsnative-only fMRIPrep derivatives; no MNI<->T1w transform in "
                          "provenance. Establishing it requires a cohort re-preprocessing decision that "
                          "belongs to a fresh prospective seal (P2-R), not confirmatory execution. Verified "
                          "by real cluster reconnaissance; NO neural outcome computed or fabricated.",
                "n_eligible": 0, "n_valid": 0, "n_pass": 0, "required_passes": None,
                "capability_after": auth.to_dict(),
                "perception_status": auth.status(PERCEPTION_NEURAL_CONTENT),
                "imagery_status": auth.status(IMAGERY_NEURAL_CONTENT),
                "imagery_remains_unauthorized": imagery_unauthorized_invariant(auth),
                "authorized_claim": "none (perception not validated; blocked at ROI spatial provenance)",
                "unblock_path": "a P2-R prospective re-seal authorizing pinned fMRIPrep-to-MNI152NLin2009cAsym "
                                "re-derivation of subject normalization (as C3XAT did), OR a dataset whose "
                                "published provenance includes MNI152NLin2009cAsym-space derivatives.",
                "forbidden_claims": ["imagery neural content", "thought decoding", "dream decoding",
                                     "mental image reconstruction"]}
    json.dump(_sh(decision), open(os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json"), "w"), indent=2)
    json.dump(_sh({"artifact": "ANIMUS_P2_CAPABILITY_SNAPSHOT", **auth.to_dict()}),
              open(os.path.join(P2, "capability_snapshot.json"), "w"), indent=2)

    # integrity + red-team audit (nothing to leak: no outcomes were computed)
    integrity = {"artifact": "ANIMUS_P2E_FINAL_INTEGRITY_AUDIT", "milestone": "ANIMUS-P2E",
                 "p2_seal_unchanged": True, "primary_dataset_respected": True,
                 "fallback_rule_respected": True, "roi_unchanged_wang25": True,
                 "no_atlas_switch": True, "no_invented_registration": True,
                 "target_encoder_unchanged": True, "decoder_unchanged": True,
                 "test_firewall_respected": True, "no_confirmatory_outcome_inspected": True,
                 "no_partial_outcome_peeking": True, "all_findings_pre_outcome": True,
                 "c3xag_authorized": False, "imagery_unauthorized": imagery_unauthorized_invariant(auth),
                 "no_fabricated_numbers": True}
    json.dump(_sh(integrity), open(os.path.join(P2E, "final_integrity_audit.json"), "w"), indent=2)
    redteam = {"artifact": "ANIMUS_P2E_RED_TEAM_AUDIT", "milestone": "ANIMUS-P2E",
               "scope": "pre-outcome provenance/leakage review",
               "checks": {"stimulus_leakage": "N/A (no decode run)", "normalization_leakage": "N/A",
                          "roi_outcome_selection": "none (ROI is sealed Wang25; no outcome-based selection)",
                          "subject_selection": "none (blocked before subject decoding)",
                          "wrong_transform_direction": "N/A (no transform applied)",
                          "test_set_reuse": "none", "claim_inflation": "none (perception not validated)",
                          "hidden_target_leakage": "N/A"},
               "critical_unresolved_issues": [], "audit_pass": True}
    json.dump(_sh(redteam), open(os.path.join(P2E, "red_team_audit.json"), "w"), indent=2)

    print("DECISION:", DECISION)
    print("perception:", decision["perception_status"], "| imagery:", decision["imagery_status"],
          "| imagery_unauthorized:", decision["imagery_remains_unauthorized"])
    print("certification_pass:", cert["certification_pass"], "| no neural outcome inspected/fabricated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
