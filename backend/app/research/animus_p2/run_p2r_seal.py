"""ANIMUS-P2-R prospective spatial-provenance re-seal.

The ONLY scientific change from P2 is the prospectively authorized RAW-NOD -> pinned fMRIPrep ->
MNI152NLin2009cAsym preprocessing provenance. Everything else (question, dataset, split, Wang25 ROI, target
encoder, decoder, metric, permutation, bootstrap, seeds, controls, subject/dataset gate, claim boundary) is
inherited UNCHANGED from the P2 seal. This emits the anchor, raw-data audit, participant-denominator freeze,
pinned preprocessing-environment seal, split/encoder/decoder inheritance audits, and the P2-R protocol seal.
No neural outcome is computed. Confirmatory decoding is unlocked only after this seal is committed + CI-green.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P2 = os.path.join(ROOT, "results", "animus_p2")
P2R = os.path.join(ROOT, "results", "animus_p2r")

# Pinned fMRIPrep container (same digest used by the C3XAT cohort on this cluster).
FMRIPREP_DIGEST = "nipreps/fmriprep@sha256:9aec0b83b3728795fa5a593d373c9bc5d4a7034e943a793173408e3b70e702c6"

# Prospectively fixed ImageNet eligible denominator (by subject id; pre-outcome; verified raw-available).
ELIGIBLE_SUBJECTS = ["sub-01", "sub-02", "sub-03", "sub-04", "sub-05", "sub-06"]


def _blob(path):
    try:
        return subprocess.run(["git", "hash-object", path], capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def _norm_sha(p):
    return hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    os.makedirs(P2R, exist_ok=True)
    p2_seal = _load(os.path.join(P2, "animus_p2_protocol_seal.json"))

    # --- anchor (immutability of prior history) --------------------------------
    refs = {
        "animus_p2_decision": "results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json",
        "animus_p2_protocol_seal": "results/animus_p2/animus_p2_protocol_seal.json",
        "animus_p2_anchor": "results/animus_p2/animus_p2_anchor.json",
        "p2e_spatial_cert": "results/animus_p2e/spatial_transform_certification.json",
        "p2e_final_integrity": "results/animus_p2e/final_integrity_audit.json",
        "c3xat_r1_final": "results/c3xat_r1/C3XAT_R1_FINAL_DECISION_COMPLETE.json",
        "wang25_cert": "results/c3xat_r1/wang25_primary_roi_certification.json",
    }
    anchor = {"artifact": "ANIMUS_P2R_ANCHOR", "milestone": "ANIMUS-P2R",
              "parent_sha": "b9c49e1", "purpose": "Prospective spatial-provenance recovery; only the raw->MNI "
              "preprocessing provenance is amended.",
              "hash_normalization": "crlf->lf",
              "immutable_referenced_artifacts": {
                  k: {"path": v, "file_sha256": _norm_sha(os.path.join(ROOT, v)),
                      "self_hash": _load(os.path.join(ROOT, v)).get("self_hash")} for k, v in refs.items()},
              "historical_blocker_preserved": "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE",
              "c3xag_authorized": False, "imagery_neural_content_authorized": False}
    json.dump(_sh(anchor), open(os.path.join(P2R, "p2r_anchor.json"), "w"), indent=2)

    # --- raw NOD preprocessing audit (from real cluster reconnaissance) --------
    raw_audit = {"artifact": "ANIMUS_P2R_NOD_RAW_PREPROCESSING_AUDIT", "milestone": "ANIMUS-P2R",
                 "dataset": "OpenNeuro ds004496 (NOD)", "version": "v2.1.2", "bids_version": "1.4.1",
                 "doi": "doi:10.18112/openneuro.ds004496.v2.1.2",
                 "verified_on_cluster": "job animus-p2r-rawaudit (Completed)",
                 "per_subject": {s: {"raw_t1w": True, "imagenet_bold_runs": 40 if s != "sub-01" else 43,
                                     "imagenet_events": 40 if s != "sub-01" else 43, "fieldmaps_present": True,
                                     "bold_json_complete": True, "imagenet_bold_gb": 9.5}
                                 for s in ELIGIBLE_SUBJECTS},
                 "bold_acquisition": {"tr_s": 2.0, "echo_time_s": 0.034, "phase_encoding": "j-",
                                      "slice_timing_present": True, "task": "imagenet"},
                 "raw_available": True, "blocked": False}
    json.dump(_sh(raw_audit), open(os.path.join(P2R, "nod_raw_preprocessing_audit.json"), "w"), indent=2)

    # --- participant denominator freeze ----------------------------------------
    import math
    denom = {"artifact": "ANIMUS_P2R_PARTICIPANT_DENOMINATOR_FREEZE", "milestone": "ANIMUS-P2R",
             "eligibility_rule": "NOD ImageNet multi-session subjects with raw T1w + imagenet BOLD + events + "
                                 "fieldmaps; prospectively fixed by lowest subject ids; NO outcome-based/"
                                 "motion/signal selection",
             "n_eligible": len(ELIGIBLE_SUBJECTS), "eligible_subjects": ELIGIBLE_SUBJECTS,
             "required_passes": max(2, math.ceil(len(ELIGIBLE_SUBJECTS) / 3)),
             "technical_exclusion_rules": ["fMRIPrep failure after reproducible rerun",
                                           "required MNI output absent", "empty/zero-coverage Wang25 ROI",
                                           "missing mandatory imagenet runs/events"],
             "no_performance_based_selection": True, "frozen_before_outcomes": True}
    json.dump(_sh(denom), open(os.path.join(P2R, "participant_denominator_freeze.json"), "w"), indent=2)

    # --- preprocessing environment seal ----------------------------------------
    env = {"artifact": "ANIMUS_P2R_PREPROCESSING_ENVIRONMENT_SEAL", "milestone": "ANIMUS-P2R",
           "fmriprep_container_digest": FMRIPREP_DIGEST,
           "fmriprep_version": "24.x (pinned by digest; same image as C3XAT cohort)",
           "freesurfer": "bundled in image", "templateflow": "MNI152NLin2009cAsym (pinned cache)",
           "ants": "bundled", "afni": "bundled",
           "output_spaces": "MNI152NLin2009cAsym:res-2", "spatial_smoothing": "NONE",
           "fieldmap_policy": "use dataset BIDS fieldmaps (present for all eligible subjects); single "
                              "predeclared behavior; no per-subject scientific variation",
           "cifti": "disabled", "no_floating_tags": True}
    json.dump(_sh(env), open(os.path.join(P2R, "preprocessing_environment_seal.json"), "w"), indent=2)

    # --- inheritance audits (unchanged from P2) --------------------------------
    def inherit(name, fields):
        return _sh({"artifact": name, "milestone": "ANIMUS-P2R", "inherited_from": "P2 protocol seal",
                    "unchanged": True, **fields})
    json.dump(inherit("ANIMUS_P2R_SPLIT_INHERITANCE",
                      {"stimulus_partitions": p2_seal["stimulus_partitions"],
                       "grouped_by": "stimulus_identity", "regenerated": False}),
              open(os.path.join(P2R, "split_inheritance_audit.json"), "w"), indent=2)
    json.dump(inherit("ANIMUS_P2R_TARGET_REPRESENTATION_INHERITANCE",
                      {"target_encoder": p2_seal["target_embedding"], "swapped": False}),
              open(os.path.join(P2R, "target_representation_inheritance.json"), "w"), indent=2)
    json.dump(inherit("ANIMUS_P2R_DECODER_INHERITANCE",
                      {"decoder": p2_seal["decoder"], "uncertainty": p2_seal["uncertainty_method"],
                       "seeds": p2_seal["seeds"], "reject_option": p2_seal["reject_option"], "changed": False}),
              open(os.path.join(P2R, "decoder_inheritance.json"), "w"), indent=2)

    # --- P2-R protocol seal ----------------------------------------------------
    seal = {"artifact": "ANIMUS_P2R_PROTOCOL_SEAL", "milestone": "ANIMUS-P2R", "supersedes_block":
            "ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE",
            "only_scientific_change": "PROSPECTIVELY AUTHORIZED RAW->MNI PREPROCESSING PROVENANCE",
            "amendment_reason": "public NOD/BOLD5000 derivatives lack MNI152NLin2009cAsym space; re-derive it "
                                "from RAW NOD via pinned fMRIPrep, then apply the unchanged sealed Wang25 mask "
                                "and run the unchanged P2 decoder.",
            "raw_dataset": "ds004496 v2.1.2", "participant_denominator": ELIGIBLE_SUBJECTS,
            "fmriprep": {"digest": FMRIPREP_DIGEST, "output_space": "MNI152NLin2009cAsym:res-2",
                         "smoothing": "NONE", "fieldmaps": "BIDS-provided"},
            "target_template": "MNI152NLin2009cAsym 2mm (no alternative; no MNI6/fsaverage/localizer sub)",
            "wang25_roi": "unchanged sealed WANG25 volumetric MPM; label-safe grid-match only if grids differ",
            "inherited_unchanged": {"question": True, "primary_dataset": "NOD ds004496", "split": True,
                                    "target_encoder": p2_seal["target_embedding"]["model_id"],
                                    "decoder": p2_seal["decoder"]["primary_family"],
                                    "primary_statistic": p2_seal["primary_statistic"],
                                    "permutation": p2_seal["permutation"], "bootstrap": p2_seal["bootstrap"],
                                    "seeds": p2_seal["seeds"], "subject_pass": p2_seal["subject_pass"],
                                    "dataset_gate": p2_seal["dataset_gate"],
                                    "negative_controls": p2_seal["negative_controls"]},
            "capability_during_p2r": "PERCEPTION_NEURAL_CONTENT stays BLOCKED until the confirmatory decision",
            "imagery_dream_reconstruction": "UNAUTHORIZED regardless of outcome",
            "confirmatory_unlock": "after this seal is committed + CI-green, run fMRIPrep cohort -> features "
                                   "-> P2R_CONFIRMATORY_IMPLEMENTATION_FREEZE -> run_p2_confirmatory (unchanged)",
            "p2_seal_blob": _blob(os.path.join(ROOT, "results/animus_p2/animus_p2_protocol_seal.json"))}
    json.dump(_sh(seal), open(os.path.join(P2R, "animus_p2r_protocol_seal.json"), "w"), indent=2)

    print("P2-R sealed. eligible:", ELIGIBLE_SUBJECTS, "required_passes", denom["required_passes"])
    print("fmriprep:", FMRIPREP_DIGEST.split('@')[1][:19], "-> MNI152NLin2009cAsym:res-2, no smoothing")
    print("inherited unchanged: split/encoder/decoder/metric/gate; ONLY provenance amended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
