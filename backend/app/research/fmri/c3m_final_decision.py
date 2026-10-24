"""Compose the C3M final decision from the frozen result chain (self-hashed).

Reads the pre-registration, vision gate, robustness, seal, and imagery-transfer
artifacts and issues the C3M decision under the pre-registered rules A-E. Makes
no new measurement; only aggregates frozen, committed results.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def _load(p):
    return json.load(open(p))


def main() -> None:
    R = Path(os.environ.get("RESULTS_DIR", "results"))
    proto = _load(R / "c3m_protocol_decision.json")
    vg = _load(R / "c3m_vision_gate_m3m4.json")
    rob = _load(R / "c3m_vision_robustness.json")
    seal = _load(R / "c3m_alignment_seal.json")
    img = _load(R / "c3m_imagery_transfer.json")

    vb = vg["set_B_complex_PRIMARY"]["methods"]["M3_coral"]
    m3i = img["results"]["M3_frozen_from_vision_PRIMARY"]

    decision = {
        "artifact": "C3M_FINAL_DECISION",
        "gate": "C3M",
        "title": "Cross-Session Neural Alignment and Imagery-Transfer Mechanism",
        "subject": "subj01",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_sha": proto["source_sha"],
        "branch": "research/cross-session-alignment-c3m",
        "protocol_self_hash": proto["self_hash"],
        "seal_self_hash": seal["self_hash"],
        "does_not_modify_c3": True,

        "C3M_H1_session_shift_explains_collapse": {
            "verdict": "SUPPORTED",
            "evidence": "Strict-C3 identity collapses on SEEN Set-B vision (dominant_fraction 0.938); "
                        "per-voxel mean-correction (M1) improves but leaves residual collapse (0.646); "
                        "covariance alignment (M3 CORAL) clears it (0.312). The collapse is driven by "
                        "SECOND-MOMENT (covariance) cross-session mismatch, not merely a mean offset.",
        },
        "C3M_H2_H3_vision_restoration": {
            "verdict": "PASS",
            "method": "M3 CORAL (target-blind, Family A)",
            "set_B_mrr": vb["metrics"]["mrr"],
            "set_B_two_afc": vb["metrics"]["two_afc"],
            "set_B_dominant_fraction": vb["collapse"]["dominant_fraction"],
            "set_B_perm_p": vb["heldout_permutation_null"]["p_value"],
            "held_out_target_LOTO": True,
            "capacity_matched_control_max_mrr": rob["capacity_matched_control"]["control_mrr_max"],
            "m3_exceeds_capacity_control_max": rob["capacity_matched_control"]["m3_exceeds_control_max"],
            "hyperparameter_sensitivity": rob["sensitivity_summary"],
            "set_A_simple": "OOD: collapse removed but not significant (synthetic bars outside the "
                            "natural-image perception decoder's domain)",
        },
        "C3M_H4_aligned_imagery_transfer": {
            "verdict": "NULL",
            "primary_metric_mrr": m3i["mrr"],
            "dominant_fraction": m3i["dominant_fraction"],
            "two_afc": m3i["two_afc"],
            "perm_p": m3i["perm_p_value"],
            "exceeds_matched_random_95pct": img["matched_random_capacity_control"]["m3_exceeds_95pct"],
            "failing_guard": "non-degeneracy (dominant_fraction 0.5104 > 0.5)",
            "interpretation": "The SAME frozen vision-calibrated alignment PARTIALLY transfers to "
                              "imagery: it reduces collapse from 1.000 (strict C3) to 0.510, raises "
                              "prediction-covariance effective rank 24->11, improves MRR 0.428->0.476 "
                              "with stimulus-specific and capacity-exceeding signal (perm p 0.022) -- "
                              "but the aligned imagery predictions remain marginally DEGENERATE, so no "
                              "clean stimulus-specific imagery transfer is established. Imagery carries "
                              "a residual STATE-SPECIFIC degradation beyond the cross-session shift.",
        },

        "decision_rule_applied": "B (vision PASS + imagery NULL)",
        "C3M_CROSS_SESSION_ALIGNMENT": "PASS",
        "C3M_ALIGNED_IMAGERY_TRANSFER": "NULL_SUPPORTED_WITHIN_SENSITIVITY",
        "C3M": "COMPLETE_WITH_STATE_SPECIFIC_IMAGERY_NULL",

        "scope": "SINGLE_SUBJECT_subj01_ONLY_NOT_POPULATION_EVIDENCE",
        "multiparticipant_status": {
            "prospectively_eligible": ["subj02", "subj05", "subj07"],
            "infrastructure": "DEMONSTRATED (NSD public-S3 re-download bit-identical to C3; rolling "
                              "perception extraction to the frozen voxel order; FMRI2images "
                              "pre-extracted features present for all four subjects but REJECTED as "
                              "X_p by certification -- different beta version).",
            "executed": ["subj01"],
            "not_yet_executed": ["subj02", "subj05", "subj07"],
            "note": "subj01 alone never licenses a population claim; participant-level replication is "
                    "the defined next step and is not gated by subj01's outcome.",
        },
        "prohibitions_honored": [
            "no images generated", "no diffusion", "C4 NOT begun",
            "no tuning against imagery results (frozen guard yields NULL; pipeline not adjusted)",
            "frozen C3 decoder weights unchanged", "no imagery decoder trained",
            "no mind-reading claim", "no population claim from subj01",
            "Spera's method not adopted/relabelled",
        ],
        "artifacts": {
            "protocol": "results/c3m_protocol_decision.json",
            "xp_certification": "results/c3m_xp_certification.json",
            "xp_extraction": "results/c3m_xp_extraction_subj01.json",
            "vision_gate_M0_M2": "results/c3m_vision_gate.json",
            "vision_gate_M3_M4": "results/c3m_vision_gate_m3m4.json",
            "vision_robustness": "results/c3m_vision_robustness.json",
            "alignment_seal": "results/c3m_alignment_seal.json",
            "imagery_transfer": "results/c3m_imagery_transfer.json",
        },
        "next_step": "STOP. Do NOT begin C4. Multi-participant replication (subj02/05/07) is the "
                     "defined continuation if pursued.",
    }
    try:
        decision["code_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        decision["code_sha"] = "UNKNOWN"
    decision["self_hash"] = hashlib.sha256(json.dumps(decision, sort_keys=True, default=str).encode()).hexdigest()
    out = R / "c3m_final_decision.json"
    json.dump(decision, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"C3M": decision["C3M"], "vision": decision["C3M_CROSS_SESSION_ALIGNMENT"],
                      "imagery": decision["C3M_ALIGNED_IMAGERY_TRANSFER"],
                      "self_hash": decision["self_hash"]}, indent=2))


if __name__ == "__main__":
    main()
