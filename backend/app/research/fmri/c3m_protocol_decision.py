"""Generate the C3M Phase-0 protocol decision (pre-registration).

Freezes, BEFORE any alignment is fitted or any result computed: the hypotheses,
the alignment method set and its supervision hierarchy, the anti-leakage rule,
the frozen MEOI (metric of interest) and success thresholds, the seeds, and the
decision rules. Writes results/c3m_protocol_decision.json with a self_hash so
the pre-registration is tamper-evident and can be referenced by later runners.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def build_decision() -> dict:
    decision = {
        "artifact": "C3M_PROTOCOL_DECISION",
        "gate": "C3M",
        "title": "Cross-Session Neural Alignment and Imagery-Transfer Mechanism",
        "branch": "research/cross-session-alignment-c3m",
        "source_sha": "1a3375549a1f42faa48965ede88d90b5793cab9a",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "PROTOCOL_FROZEN_BEFORE_ANY_ALIGNMENT_FIT",
        "does_not_modify_c3": True,
        "c3_accepted_decision": {
            "C3_PERCEPTION_DECODING": "PASS",
            "C3_IMAGERY_ROW_PROVENANCE": "PASS",
            "C3_ZERO_SHOT_IMAGERY_TRANSFER": "NULL_SUPPORTED_WITHIN_SENSITIVITY",
            "C3_STATE_TRANSPORT": "NULL_OR_INCONCLUSIVE",
            "C3_RECONSTRUCTION_READINESS": "BLOCKED",
            "C3": "COMPLETE_WITH_IMAGERY_TRANSFER_NULL",
        },
        "claim_boundary": (
            "C3 does NOT show imagery lacks decodable visual information; it shows the frozen "
            "perception decoder fails zero-shot AND collapses even on actually-seen NSD-Imagery "
            "vision trials (Set A 48/48, Set B 45/48 single-candidate collapse; imagery 2AFC < "
            "chance). Dominant unresolved mechanism = cross-session nonstationarity, upstream of "
            "the perception->imagery question."
        ),
        "primary_question": (
            "Can a low-capacity transformation learned WITHOUT imagery-content labels remove the "
            "NSD->NSD-Imagery session shift enough to restore stimulus-specific decoding of "
            "actually seen stimuli?"
        ),
        "secondary_question": (
            "If cross-session perception decoding is restored, does the SAME frozen session "
            "alignment reveal stimulus-specific perception->imagery transfer?"
        ),
        "hypotheses": {
            "C3M_H1": "Cross-session shift exists and explains the decoder collapse.",
            "C3M_H2": "PRIMARY GATE: low-capacity, imagery-label-free alignment restores "
                      "stimulus-specific decoding on held-out NSD-Imagery VISION targets.",
            "C3M_H3": "Improvement is content-independent (generalizes to held-out target "
                      "identities; not reproduced by a matched random transform).",
            "C3M_H4": "CONDITIONAL on H2 PASS only: frozen alignment applied to imagery betas "
                      "improves imagery retrieval vs strict-C3 identity, matched random, and "
                      "mean-shift baselines.",
        },
        "alignment_methods": {
            "family_A_target_blind": {
                "allowed": ["fMRI distributions", "run/session identity", "ROI coordinates",
                            "perception-training statistics (frozen decoder voxel_mean/std)"],
                "forbidden": ["imagery target identity", "imagery cue identity",
                              "imagery CLIP embeddings", "final vision-test target identity"],
                "methods": {
                    "M0": "identity (== strict C3)",
                    "M1": "global/per-voxel mean correction",
                    "M2": "per-voxel affine (shift + scale)",
                    "M3": "shrinkage covariance alignment / CORAL",
                    "M4": "low-rank distribution alignment",
                },
            },
            "family_B_vision_calibrated": {
                "allowed": ["training subset of NSD-Imagery VISION trials + their known seen "
                            "targets"],
                "forbidden": ["any imagery-state trial", "any held-out vision target"],
                "evaluated_on": "HELD-OUT VISION TARGET IDENTITIES only",
                "methods": {
                    "M5": "ridge voxel-space session map",
                    "M6": "regularized low-rank (reduced-rank) session map",
                    "M7": "orthogonal/Procrustes alignment (subspace)",
                },
            },
        },
        "anti_leakage_rule": {
            "imagery_labels": "SEALED throughout alignment development",
            "no_imagery_mrr_during_development": True,
            "method_selection_signal": "held-out VISION performance ONLY",
            "seal_artifact": "results/c3m_alignment_seal.json",
            "seal_must_exist_before_any_aligned_imagery_result": True,
            "unblinding_is_fail_closed": True,
        },
        "vision_splits": {
            "n_targets_total": 12,
            "set_A_simple_OOD": 6,
            "set_B_complex_primary": 6,
            "scheme": "nested leave-one-target-out (primary) + leave-two-targets-out (secondary)",
            "generalization_unit": "held-out target identity (never held-out repeats of a seen "
                                   "target)",
            "target_blind_global_stats_permitted": "Family A per-voxel global stats over pooled "
                                                    "UNLABELED vision betas only; rule frozen "
                                                    "prospectively, identical in every fold",
        },
        "frozen_MEOI": {
            "primary_metric": "aggregate held-out-target Set B MRR (6-candidate within-set), "
                              "under the chosen alignment, subject to ALL guard conditions",
            "guard_conditions_all_required": [
                "meaningful improvement over M0 identity",
                "no prediction collapse (dominant-candidate fraction <= 0.5 on held-out trials)",
                "true 2AFC > 0.5",
                "improvement holds on held-out targets",
                "matched random transform of same capacity does NOT reproduce it",
            ],
            "meaningful_improvement_definition": (
                "held-out-target Set B MRR exceeds M0 by more than the 95th percentile of the "
                "matched-random-transform improvement distribution AND aggregate held-out "
                "permutation p < 0.05"
            ),
            "degenerate_threshold_dominant_fraction": 0.5,
            "two_afc_chance": 0.5,
            "mrr_chance_6candidate": 0.408,
            "mrr_chance_12candidate": 0.2586,
        },
        "seeds": {
            "alignment_and_matched_random": 20260822,
            "imagery_monte_carlo_null": 20260724,
            "imagery_exact_null": "6! = 720 whole-group target-identity permutations "
                                  "(repeat-preserving)",
            "matched_random_transforms_min": 200,
        },
        "mechanism_decomposition": {
            "compare_sets": ["core-NSD perception (reference)", "NSD-Imagery vision",
                             "NSD-Imagery imagery"],
            "voxel_space": ["per-voxel mean", "per-voxel std", "covariance eigen-spectrum",
                            "ROI-wise distributions", "ncsnr-weighted shift"],
            "decoder_prenorm": ["z-score distribution under frozen perception stats",
                                "fraction outside perception train range"],
            "decoder_output": ["embedding norm", "output mean vector",
                               "output covariance effective rank", "pairwise cosine diversity",
                               "candidate-score entropy", "dominant-candidate fraction"],
            "counterfactual": "inject measured NSD-Imagery shift into held-out perception betas "
                              "(expect collapse) and remove it from imagery-vision betas (expect "
                              "restored diversity); MECHANISTIC perturbation, NOT confirmatory "
                              "imagery evidence",
            "artifact": "results/c3m_shift_mechanism.json",
        },
        "decision_rules": {
            "A": "vision PASS + aligned imagery PASS -> C3M_CROSS_SESSION_ALIGNMENT=PASS, "
                 "C3M_ALIGNED_IMAGERY_TRANSFER=PASS, C3M=COMPLETE_WITH_ALIGNED_IMAGERY_TRANSFER "
                 "(still do NOT begin C4; require multi-participant replication)",
            "B": "vision PASS + imagery NULL_SUPPORTED -> "
                 "C3M=COMPLETE_WITH_STATE_SPECIFIC_IMAGERY_NULL",
            "C": "vision alignment cannot be restored -> "
                 "C3M=COMPLETE_WITH_UNRESOLVED_SESSION_NONSTATIONARITY",
            "D": "works on seen targets but not held-out targets -> "
                 "C3M=FAILED_BY_TARGET_MEMORIZATION",
            "E": "leakage or post-hoc method selection -> C3M=FAILED_BY_LEAKAGE_OR_SELECTION_BIAS",
        },
        "prohibitions": [
            "generate images", "connect embeddings to diffusion", "start C4",
            "tune against imagery results", "change frozen C3 decoder weights",
            "train an imagery decoder", "claim mind reading",
            "claim population evidence from subj01", "adopt Spera's method and relabel as novel",
        ],
        "multiparticipant": {
            "prospectively_eligible": ["subj02", "subj05", "subj07"],
            "subj01_outcome_does_not_gate_them": True,
            "acquisition": "rolling extraction (download->certify->SHA256->extract ROI union->"
                           "hash->persist provenance->remove raw only once re-downloadable->next)",
            "roi_union_preserved": ["nsdgeneral", "V1", "V2", "V3", "hV4", "ventral", "lateral",
                                    "parietal", "low-ncsnr control"],
            "population_inference": "participant-level; subj01 alone never licenses a population "
                                    "claim",
        },
        "novelty_posture": (
            "No novelty claimed until the audit supports it. 'Functional alignment for imagery' "
            "is NOT novel (Spera et al. 2026). Candidate contributions: session-shift vs "
            "imagery-state decomposition + counterfactual; target-blind vision-first "
            "calibration; prediction-collapse as a first-class gate; held-out-target alignment "
            "evaluation; reconstruction-readiness gating. See C3M_NOVELTY_AND_OVERLAP.md."
        ),
        "code_sha": _code_sha(),
    }
    decision["self_hash"] = hashlib.sha256(
        json.dumps(decision, sort_keys=True).encode()
    ).hexdigest()
    return decision


def main() -> None:
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    decision = build_decision()
    out = results_dir / "c3m_protocol_decision.json"
    with open(out, "w") as f:
        json.dump(decision, f, indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": decision["status"], "self_hash": decision["self_hash"],
                      "code_sha": decision["code_sha"]}, indent=2))


if __name__ == "__main__":
    main()
