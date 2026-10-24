"""C3XD decision assembler. Synthesizes the certified event contract, storage preflight,
ROI-provenance determination, and the frozen synthetic design-identifiability results into a
single machine-readable determination. No raw neural outcome was computed (blocked); this does
NOT run the >=2/6 reliability gate because the raw betas cannot be produced in this environment.
Emits results/c3xd/c3xd_roi_provenance.json, c3xd_cue_diagnostics.json, C3XD_DECISION.json.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> None:
    out = Path(os.environ.get("C3XD_OUT_DIR", "results/c3xd"))
    seal = json.load(open(os.environ.get("C3XD_SEAL", "reports/c3xd/c3xd_protocol_seal.json")))
    manifest = json.load(open(out / "c3xd_event_timing_manifest.json"))
    plan = json.load(open(out / "raw_acquisition_plan.json"))
    sel = json.load(open(out / "c3xd_glm_design_selection.json"))
    sim = json.load(open(out / "c3xd_design_simulation.json"))

    # ---- ROI provenance determination ----
    roi = {"artifact": "C3XD_ROI_PROVENANCE",
           "status": "BLOCKED_C3XD_ROI_PROVENANCE",
           "primary_roi": "VC",
           "reason": ("The C3XC/frozen VC (and V1/LVC/HVC) are localizer-defined voxel indices in the "
                      "KamitaniLab PREPROCESSED release space. Mapping them to raw-BIDS subject BOLD "
                      "space requires the KamitaniLab localizer GLMs + anatomical/functional "
                      "registration + resampling (FreeSurfer/fMRIPrep-class derivatives) that are NOT "
                      "distributed as raw-functional-space masks in ds005191 and are not reproducible "
                      "in this environment. No 'close-enough' approximation is permitted (sealed)."),
           "cross_source_validation_possible": False,
           "consequence": "raw-space VC cannot be certified against the C3XC release -> fail-closed"}

    # ---- storage / pipeline feasibility ----
    sp = plan["storage_preflight"]
    infra = {"raw_bold_selected_GB": sp["selected_bold_GB"], "peak_estimate_GB": sp["peak_estimate_GB_with_preproc"],
             "free_GB": sp["free_GB"], "sufficient_storage": sp["sufficient"],
             "reproducible_preprocessing_stack_available": False,
             "note": "raw BOLD 139.4 GB (peak ~223 GB) exceeds 37.1 GB free; no in-environment "
                     "fMRIPrep/FSL/SPM/FreeSurfer registration stack -> raw betas not producible."}

    # ---- cue diagnostics (synthetic; substitutes for raw cue/imagery/postvideo diagnostics) ----
    per_model = sim["per_model"]
    cue_diag = {"artifact": "C3XD_CUE_DIAGNOSTICS", "source": "synthetic (real S1 timing; NO BOLD)",
                "imagery_per_trial_estimable": {
                    "imagery_submatrix_condition_number": sel["design_metrics"]["imagery_submatrix_condition_number"],
                    "imagery_VIF_mean": sel["design_metrics"]["imagery_VIF_mean"],
                    "imagery_vs_own_cue_corr_mean": sel["design_metrics"]["imagery_vs_own_cue_corr_mean"],
                    "verdict": "YES -- per-trial imagery is well-conditioned and separable in the mean"},
                "false_positive_reliability_vs_cue_magnitude": {
                    m: per_model[m]["null_fp_by_cue_gain"] for m in ("A", "B", "C")},
                "interpretation": (
                    "Proper deconfounding (Model A/B) yields ZERO false-positive imagery reliability when "
                    "the video-specific cue/video response is <=0.5x the imagery response, but 25-50% "
                    "false-positive reliability at comparable (1.0x) magnitude, because a video-specific "
                    "cue response is consistent across repetitions and the reliability estimator cannot "
                    "distinguish it from imagery. The naive late-window model (C) leaks even at 0.25x. "
                    "The ACTUAL cue-response magnitude in VC is unknown and can only be measured from raw "
                    "BOLD, which is infeasible here.")}

    # ---- decision ----
    # The raw >=2/6 reliability gate CANNOT be evaluated: raw betas are not producible (storage + no
    # preprocessing stack) and raw-space VC is not certifiable (ROI provenance). Per the sealed
    # fail-closed conditions this is a documented BLOCKED, not a FAIL and not a workaround.
    decision = "C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE"
    obj = {"artifact": "C3XD_DECISION", "gate": "C3XD",
           "seal_self_hash": seal["self_hash"],
           "dataset": "ds005191 v1.0.2 (raw BIDS)",
           "lineage": seal["lineage"],
           "decision": decision,
           "raw_reliability_gate_evaluated": False,
           "blocking_conditions": {
               "insufficient_storage": not infra["sufficient_storage"],
               "no_reproducible_preprocessing_stack": True,
               "roi_provenance": roi["status"],
           },
           "event_contract_certified": {
               "all_subjects_imagery_360x72x5_balanced": all(
                   manifest["subjects"][s]["imagery"]["n_trials"] == 360
                   and manifest["subjects"][s]["imagery"]["n_videos"] == 72
                   and manifest["subjects"][s]["imagery"]["session_balance_ok"]
                   for s in manifest["subjects"]),
               "perception_72_videos": all(manifest["subjects"][s]["perception"]["n_videos"] == 72
                                           for s in manifest["subjects"]),
               "correspondence": "72/72 by video identity"},
           "design_identifiability": {
               "per_trial_imagery_estimable": True,
               "primary_model_selected": sel["primary_model"],
               "selection_status": sel["status"],
               "cue_deconfounding_sufficiency": (
                   "CONDITIONAL: adequate (no false-positive reliability) if video-specific cue-response "
                   "magnitude in VC <= 0.5x imagery; UNRESOLVED at comparable magnitude; the true ratio "
                   "requires raw BOLD (infeasible here)")},
           "cue_diagnostics_ref": "results/c3xd/c3xd_cue_diagnostics.json",
           "authorizes": "nothing (blocked); C3XE preparation NOT authorized",
           "does_NOT_authorize": ["C3XE", "C3XR", "C3XR-CAT", "reconstruction", "captioning",
                                  "semantic decoding", "state geometry", "C4"],
           "c3xc_status": "PRESERVED and VALID for its declared scope (preprocessed-release reliability); "
                          "NOT revised, NOT described as erroneous",
           "what_would_unblock": [
               "an environment with >=250 GB working storage AND a reproducible fMRIPrep/FSL/SPM/"
               "FreeSurfer preprocessing+registration stack",
               "raw-functional-space VC/localizer ROI masks (or the KamitaniLab derivatives to reproduce them)",
               "then: freeze Model A (LSA) as primary, extract cue-deconfounded imagery+perception betas, "
               "measure the actual VC cue-response magnitude, and run the frozen session-disjoint "
               "reliability gate incl. the cue+video-only false-positive control"],
           "no_geometry_computed": True, "no_reconstruction": True, "not_c4": True,
           "no_raw_neural_data_committed": True}

    json.dump(_sh(roi), open(out / "c3xd_roi_provenance.json", "w"), indent=2)
    json.dump(_sh(cue_diag), open(out / "c3xd_cue_diagnostics.json", "w"), indent=2)
    json.dump(_sh(obj), open(out / "C3XD_DECISION.json", "w"), indent=2)
    print("DECISION:", decision)
    print("event contract certified:", obj["event_contract_certified"]["all_subjects_imagery_360x72x5_balanced"])
    print("design per-trial imagery estimable:", True, "| model selection:", sel["status"])
    print("ROI:", roi["status"], "| storage sufficient:", infra["sufficient_storage"])


if __name__ == "__main__":
    main()
