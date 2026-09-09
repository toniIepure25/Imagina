"""C3XDR decision assembler. The Section-1 infrastructure gate failed (no >=300 GB storage,
no reproducible preprocessing/registration stack, no container runtime, no reachable remote
compute), so no raw data was downloaded and no raw neural outcome was produced. This emits the
BLOCKED decision plus the required artifacts as explicit NOT_EXECUTED_BLOCKED records (nothing
fabricated). The frozen execution seal (Model A, estimator, ROI/cue contracts) stands as the
replayable plan for a future adequate-infrastructure run.
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
    out = Path(os.environ.get("C3XDR_OUT_DIR", "results/c3xdr"))
    out.mkdir(parents=True, exist_ok=True)
    seal = json.load(open(os.environ.get("C3XDR_SEAL", "reports/c3xdr/c3xdr_execution_seal.json")))
    infra = json.load(open(out / "infrastructure_audit.json"))

    BLOCK = "execution not performed: C3XDR_BLOCKED_STORAGE (Section-1 infrastructure gate failed)."

    stubs = {
        "raw_acquisition_manifest.json": {
            "artifact": "C3XDR_RAW_ACQUISITION_MANIFEST", "status": "NOT_ACQUIRED_BLOCKED",
            "planned_subset": seal["selective_acquisition"], "downloaded_bytes": 0,
            "reason": BLOCK + " No large download attempted (per Section 1)."},
        "c3xdr_preprocessing_spec.json": {
            "artifact": "C3XDR_PREPROCESSING_SPEC", "status": "NOT_EXECUTED_BLOCKED",
            "policy": seal["preprocessing_provenance"]["policy"],
            "container_runtime_available": False,
            "reason": BLOCK + " No container runtime (docker/apptainer/singularity) and no "
                              "fMRIPrep/FSL/SPM/FreeSurfer/nipype available -> pipeline not runnable."},
        "c3xdr_roi_provenance.json": {
            "artifact": "C3XDR_ROI_PROVENANCE", "status": "NOT_EXECUTED_BLOCKED",
            "primary_roi": "VC", "would_require": seal["roi_contract"]["mapping"],
            "reason": BLOCK + " Raw functional space not produced (no preprocessing) -> ROI transform "
                              "not attempted; remains the C3XD BLOCKED_C3XD_ROI_PROVENANCE risk."},
        "c3xdr_imagery_manifest.json": {
            "artifact": "C3XDR_IMAGERY_MANIFEST", "status": "NOT_PRODUCED_BLOCKED",
            "required_contract": seal["contracts"]["imagery"],
            "event_certified_by_c3xd": {"trials": 360, "videos": 72, "reps": 5, "sessions": 5, "balanced": True},
            "reason": BLOCK + " No raw betas produced. Event/unit contract already certified in C3XD."},
        "c3xdr_perception_manifest.json": {
            "artifact": "C3XDR_PERCEPTION_MANIFEST", "status": "NOT_PRODUCED_BLOCKED",
            "required_contract": seal["contracts"]["perception"], "reason": BLOCK},
        "c3xdr_cue_magnitude.json": {
            "artifact": "C3XDR_CUE_MAGNITUDE", "status": "NOT_MEASURED_BLOCKED",
            "would_report": ["cue_gain_empirical=G_cue/G_img", "video_gain_empirical", "R_cue", "R_postvideo"],
            "reason": BLOCK + " Requires raw VC betas (needs the raw pipeline)."},
        "c3xdr_cuevideo_falsification.json": {
            "artifact": "C3XDR_CUEVIDEO_FALSIFICATION", "status": "NOT_EXECUTED_BLOCKED",
            "would_compute": ["R_I_observed", "R_I_cuevideo_predicted", "Delta_I", "randomization p/CI"],
            "reason": BLOCK},
        "c3xdr_temporal_controls.json": {
            "artifact": "C3XDR_TEMPORAL_CONTROLS", "status": "NOT_EXECUTED_BLOCKED",
            "would_compute": ["early-vs-late FIR imagery reliability", "current/previous/next-video contamination"],
            "reason": BLOCK},
    }
    for s in range(1, 7):
        stubs[f"c3xdr_reliability_S{s}.json"] = {
            "artifact": "C3XDR_RELIABILITY", "subject": f"S{s}", "status": "NOT_PRODUCED_BLOCKED",
            "estimator": seal["reliability_estimator"]["normative"], "reason": BLOCK}
    for name, obj in stubs.items():
        json.dump(_sh(obj), open(out / name, "w"), indent=2)

    decision = {
        "artifact": "C3XDR_DECISION", "gate": "C3XDR",
        "execution_seal_self_hash": seal["self_hash"],
        "lineage": seal["lineage"],
        "decision": "C3XDR_BLOCKED_STORAGE",
        "is_blocked_not_fail": True,
        "infrastructure_gate": {
            "required_storage_GB": 300, "best_free_GB": infra["best_free_GB"],
            "requirement_met": infra["requirement_met"], "shortfalls": infra["shortfalls"]},
        "raw_reliability_gate_evaluated": False,
        "subjects_processed": 0,
        "downloaded_bytes": 0,
        "primary_model_frozen": seal["primary_estimator_frozen"]["model"],
        "model_selection_touched_real_bold": False,
        "authorizes": "nothing (blocked); C3XE preparation NOT authorized",
        "does_NOT_authorize": ["C3XE", "C3XR", "C3XR-CAT", "reconstruction", "captioning",
                               "semantic decoding", "state geometry", "C4"],
        "c3xc_status": "PRESERVED, immutable, valid for its declared preprocessed-release scope",
        "c3xd_status": "PRESERVED, immutable; C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE stands",
        "what_would_unblock": [
            "an execution host with >=300 GB (pref >=500) usable persistent storage",
            "a reproducible container-pinned preprocessing/registration stack (fMRIPrep/FSL/SPM/"
            "FreeSurfer or KamitaniLab code) producing a space compatible with the released ROIs",
            "then replay the frozen execution seal: selective raw acquisition (trainPerception "
            "excluded), Model-A LSA betas, certified VC ROI mapping, and the frozen session-disjoint "
            "reliability gate + cue+video-only falsification"],
        "no_geometry_computed": True, "no_reconstruction": True, "not_c4": True,
        "no_raw_neural_data_committed": True, "no_large_download_attempted": True,
    }
    json.dump(_sh(decision), open(out / "C3XDR_DECISION.json", "w"), indent=2)
    print("DECISION:", decision["decision"], "| best_free_GB", infra["best_free_GB"],
          "| requirement_met", infra["requirement_met"])


if __name__ == "__main__":
    main()
