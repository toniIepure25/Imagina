"""ANIMUS-P2-XR pre-outcome protocol seal (§17).

Emits the prospective replication seal + supporting frozen artifacts, deterministically (so CI regenerates
and verifies them). The ONLY things that may differ from P2/P2-R are the dataset I/O adapters and the
per-dataset participant denominators; every scientific component (ROI, space, fMRIPrep digest, no smoothing,
target encoder + weights, decoder, normalization, regularization selection, uncertainty, reject, content
margin M, permutation/bootstrap counts, seeds, subject gate) is inherited UNCHANGED. Firewall: no real
replication decoding metric is computed here or before the seal is committed CI-green.
"""
from __future__ import annotations

import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2xr")
P2 = os.path.join(ROOT, "results", "animus_p2")
P2R = os.path.join(ROOT, "results", "animus_p2r")

FMRIPREP_DIGEST = "nipreps/fmriprep@sha256:9aec0b83b3728795fa5a593d373c9bc5d4a7034e943a793173408e3b70e702c6"
WANG25_SHA256 = "19b681ecba5c8d2aa323b8f6e15d36191d4036cea070d095663a790690c544fc"
P2R_PARENT_SHA = "71371b2fd74ab13a7cfc7e75937b27286d70381c"
SEEDS = [20260909, 20261009, 20261109]


def _load(p):
    return json.load(open(p, encoding="utf-8"))


def _norm_sha(rel):
    p = os.path.join(ROOT, rel)
    return hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def _sh(o):
    h = dict(o)
    h.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(h, sort_keys=True, default=str).encode()).hexdigest()
    return o


def _write(name, obj):
    json.dump(_sh(obj), open(os.path.join(OUT, name), "w"), indent=2)
    print("wrote", name, obj["self_hash"][:12])


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    p2_decision = _load(os.path.join(P2, "ANIMUS_P2_SCIENTIFIC_DECISION.json"))
    split_seal = _load(os.path.join(OUT, "stimulus_split_seal.json"))
    dataset_audit = _load(os.path.join(OUT, "dataset_audit.json"))
    overlap = _load(os.path.join(OUT, "stimulus_overlap_audit.json"))
    power = _load(os.path.join(OUT, "power_audit.json"))

    # code files inherited UNCHANGED (normalized SHA pins) + the two new I/O adapters + decision
    inherited_code = {
        "gate": "backend/app/core/animus/p2/gate.py",
        "splits": "backend/app/core/animus/p2/splits.py",
        "decoder": "backend/app/core/animus/p2/decoder.py",
        "pipeline": "backend/app/core/animus/p2/pipeline.py",
        "metrics": "backend/app/core/animus/p2/metrics.py",
        "features": "backend/app/core/animus/p2/features.py",
        "target_representation": "backend/app/core/animus/p2/target_representation.py",
        "frozen_lsa_glm_extractor": "backend/app/research/animus_p2/extract_features_p2r.py",
    }
    p2xr_code = {
        "adapters": "backend/app/research/animus_p2xr/adapters.py",
        "decision": "backend/app/research/animus_p2xr/decision.py",
    }

    clip = {
        "artifact": "ANIMUS_P2XR_CLIP_TARGET_PROVENANCE", "milestone": "ANIMUS-P2XR",
        "model_id": "open_clip:ViT-B-32", "pretrained": "laion2b_s34b_b79k", "embedding_dim": 512,
        "input_preprocessing": "clip_bicubic_224_center_crop_openai_norm", "normalization": "unit_l2",
        "derived_from": "visual_stimulus_image (NOT caption)",
        "matches_p2_seal": True, "weights_sha256": "TO_PIN_AT_IMPLEMENTATION_FREEZE",
        "note": ("Exact P2 target encoder inherited; per-dataset stimulus-embedding SHAs are produced at "
                 "staging and pinned in P2XR_CONFIRMATORY_IMPLEMENTATION_FREEZE.json, not here."),
    }
    _write("clip_target_provenance.json", clip)

    denom = {
        "artifact": "ANIMUS_P2XR_PARTICIPANT_DENOMINATOR_FREEZE", "milestone": "ANIMUS-P2XR",
        "frozen_before_outcomes": True, "no_performance_based_selection": True,
        "datasets": {
            "ds001499": {"version": "v1.3.1", "subjects": ["sub-CSI1", "sub-CSI2", "sub-CSI3", "sub-CSI4"],
                         "n_eligible": 4},
            "ds004192": {"version": "v1.0.7", "subjects": ["sub-01", "sub-02", "sub-03"], "n_eligible": 3},
        },
        "total_denominator": 7,
        "exclusion_policy": ("only predeclared TECHNICAL invalidity (missing raw T1w/BOLD/events/fieldmaps, "
                             "failed atlas/grid QC, or measurement-contract incompatibility) may reduce "
                             "N_valid; never SNR/response/decoding performance."),
    }
    _write("participant_denominator_freeze.json", denom)

    anchor = {
        "artifact": "ANIMUS_P2XR_ANCHOR", "milestone": "ANIMUS-P2XR",
        "p2r_parent_sha": P2R_PARENT_SHA,
        "immutable_referenced_artifacts": {
            "p2r_remote_closeout": {"path": "results/animus_p2r/P2R_REMOTE_CLOSEOUT.json",
                                    "file_sha256": _norm_sha("results/animus_p2r/P2R_REMOTE_CLOSEOUT.json")},
            "p2_decision_snapshot": {"path": "results/animus_p2e/ANIMUS_P2E_DECISION_SNAPSHOT.json",
                                     "file_sha256": _norm_sha(
                                         "results/animus_p2e/ANIMUS_P2E_DECISION_SNAPSHOT.json")},
            "p2_validated_decision": {"path": "results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json",
                                      "file_sha256": _norm_sha(
                                          "results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json")},
        },
        "nod_closed_for_development": True, "c3xag_authorized": False,
        "imagery_neural_content_authorized": False,
    }
    _write("p2xr_anchor.json", anchor)

    seal = {
        "artifact": "ANIMUS_P2XR_PROTOCOL_SEAL", "milestone": "ANIMUS-P2XR",
        "primary_question": ("Does the exact frozen ANIMUS P2 perception->visual-latent decoding METHOD "
                             "replicate prospectively on independent cohorts, scanners/protocols and "
                             "stimulus datasets, without outcome-guided rescue?"),
        "p2r_parent_sha": P2R_PARENT_SHA,
        "p2_validated_decision_hash": p2_decision["self_hash"],
        "only_changes_vs_p2": "DATASET I/O ADAPTERS + per-dataset participant denominators (nothing else)",
        "nod_status": "CLOSED for development (immutable historical within-dataset evidence only)",
        "replication_datasets": {
            "ds001499": {"name": "BOLD5000", "version": "v1.3.1", "task": "task-5000scenes",
                         "n_subjects": 4, "tr_s": 2.0, "pe": "j-", "fieldmaps": "spinecho_epi",
                         "design": "slow_event_related", "measurement_contract_compatible": True},
            "ds004192": {"name": "THINGS-fMRI", "version": "v1.0.7", "task": "task-things",
                         "n_subjects": 3, "tr_s": 1.5, "pe": "j", "fieldmaps": "phasediff",
                         "design": "rapid_event_related", "measurement_contract_compatible": True,
                         "trial_types_kept": ["exp", "test"], "trial_types_excluded": ["catch"]},
        },
        "raw_preprocessing": "raw BIDS -> pinned fMRIPrep -> MNI152NLin2009cAsym:res-2 (PRIMARY path)",
        "fmriprep_digest": FMRIPREP_DIGEST, "smoothing": "NONE",
        "secondary_paths_declared": ("dataset-provided optimized betas (BOLD5000 GLMsingle / THINGS "
                                     "ICA-betas) permitted ONLY as prospectively declared SECONDARY; never "
                                     "the confirmatory primary, since they change the P2 estimand."),
        "roi": {"name": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK", "space": "MNI152NLin2009cAsym:res-2",
                "wang25_sha256": WANG25_SHA256, "expected_voxels": 7604},
        "target_encoder": {"model_id": "open_clip:ViT-B-32", "pretrained": "laion2b_s34b_b79k",
                           "embedding_dim": 512, "normalization": "unit_l2",
                           "weights_sha256": "TO_PIN_AT_IMPLEMENTATION_FREEZE"},
        "feature_extraction": {"method": "frozen P2 LSA/GLM (canonical spm_hrf + per-trial boxcar + frozen "
                               "nuisance motion6 + csf/white_matter + cosine drift + run intercept)",
                               "unchanged_from_p2r": True},
        "decoder": {"family": "ridge_linear_multioutput", "alpha_selection": "nested-validation (inherited)",
                    "normalization": "fold-safe (inherited P2)", "uncertainty": "bootstrap-ensemble (20)",
                    "reject": "validation-calibrated uncertainty quantile (inherited)"},
        "primary_statistic": "content margin M (held-out unseen identities)",
        "permutation": {"within_test_label_permutation": True, "n_perm": 1000},
        "identity_bootstrap": {"n_boot": 1000}, "evaluation_seeds": SEEDS,
        "supporting_endpoints": ["2AFC", "retrieval_top1_top5_top10_mrr_median_rank"],
        "negative_controls": {
            "label_permutation": "both datasets",
            "category_matched_decoys": {"ds004192": "things_category_nr (concept)",
                                        "ds001499": "ImgType family + ImageNet synset (coarser; documented)"},
            "low_level_baseline": "both datasets (luminance/color/contrast/SF 8-dim)",
            "run_session_fingerprint": "both datasets", "within_cross_run_shuffle": "both datasets",
        },
        "subject_gate": "inherited P2: data_contract & atlas_qc & M>0 & perm_p<0.01 & boot_ci_lower>0 & "
                        "all_seeds_positive",
        "dataset_gate": "inherited P2: required_passes=max(2,ceil(N_valid/3)); per dataset independently",
        "cross_dataset_decision": {
            "PASS": "BOTH datasets VALIDATED", "LIMITED": "exactly ONE dataset VALIDATED",
            "FAIL": "NEITHER dataset VALIDATED", "BLOCKED": "genuine technical/provenance impossibility",
            "no_pooled_rescue": True},
        "stimulus_split_seal_hash": split_seal["self_hash"],
        "dataset_audit_hash": dataset_audit["self_hash"],
        "stimulus_overlap_audit_hash": overlap["self_hash"],
        "power_audit_hash": power["self_hash"], "power_audit_all_checks_pass": power["all_checks_pass"],
        "test_firewall": ("NO real M / 2AFC / retrieval / cos(pred,true) / subject_PASS / dataset_PASS "
                          "computed before this seal is committed CI-green and the implementation freeze "
                          "is committed CI-green; synthetic fixtures only."),
        "imagery_dream_reconstruction": "UNAUTHORIZED", "c3xag_authorized": False, "p3_execution": False,
        "inherited_code_norm_sha256": {k: _norm_sha(v) for k, v in inherited_code.items()},
        "p2xr_code_norm_sha256": {k: _norm_sha(v) for k, v in p2xr_code.items()},
    }
    _write("animus_p2xr_protocol_seal.json", seal)
    print("SEAL_DONE only-change: dataset adapters + denominators; everything else inherited unchanged")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
