"""Freeze the winning C3M alignment pipeline and write the fail-closed
unblinding seal BEFORE any aligned-imagery result exists.

Records the hash of every frozen input (decoder, ROI selection, imagery betas,
candidate pool, event manifest, the rolling-extracted X_p sessions) and the
FROZEN alignment specification chosen SOLELY on held-out VISION performance
(M3 CORAL, shrinkage 0.1, perception rank 400). The imagery-transfer runner
fails closed unless this seal exists and is in state
SEALED_BEFORE_IMAGERY_UNBLINDING.

The primary MEOI, imagery subsets, permutation null, and baselines are frozen
here and are NOT revised after seeing any imagery result.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import time
from pathlib import Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def main() -> None:
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    decoder_path = Path(os.environ["C3M_DECODER"])
    pool_path = Path(os.environ["C3M_POOL"])
    manifest_path = Path(os.environ["C3M_EVENT_MANIFEST"])
    imagery_betas = Path(os.environ["NSD_IMAGERY_BETAS"])
    xp_extract_json = Path(os.environ["XP_EXTRACT_JSON"])

    frozen = pickle.load(open(decoder_path, "rb"))
    manifest = json.load(open(manifest_path))
    xp_extract = json.load(open(xp_extract_json))
    xp_session_hashes = {s: v["raw_sha256"] for s, v in xp_extract["sessions"].items()}

    seal = {
        "artifact": "C3M_ALIGNMENT_SEAL",
        "gate": "C3M",
        "subject": "subj01",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "vision_gate_decision": "PASS_SET_B_via_M3_CORAL_target_blind",
        "vision_gate_evidence": {
            "artifact": "results/c3m_vision_gate_m3m4.json",
            "robustness": "results/c3m_vision_robustness.json",
            "set_B_M3_mrr": 0.8052, "set_B_M3_dominant_fraction": 0.3125,
            "set_B_M3_two_afc": 0.8875, "set_B_M3_perm_p": 0.0013888888888888889,
            "capacity_control_max_mrr": 0.5534722222222223,
            "hyperparameter_sensitivity_pass": "16/16",
        },
        "frozen_alignment": {
            "method": "M3_coral",
            "shrinkage": 0.1,
            "perception_rank": 400,
            "session_stats_source_primary": "NSD-Imagery Set-B VISION betas (visB rows 192:240, "
                                            "48 trials, TARGET-BLIND: pooled distribution only)",
            "session_stats_source_secondary_exploratory": "NSD-Imagery Set-B IMAGERY betas "
                                            "(target-blind pooled distribution)",
            "perception_recolor": "X_p rolling-extracted betas_fithrf, subsample seed 20260822, "
                                  "size 2500 of 6000, top-400 perception PCs, shrinkage 0.1",
            "perception_mean": "frozen decoder voxel_mean (mu_p)",
            "applied_before_decoder_zscore": True,
        },
        "imagery_test_spec": {
            "primary_subset": "Set B complex imagery (imgB_1 rows 336:384 + imgB_2 rows 624:672 = "
                              "96 trials, 6 targets x 16 reps)",
            "secondary_subset_OOD": "Set A simple imagery (imgA_1 144:192 + imgA_2 576:624)",
            "candidate_cols_setB": [6, 7, 8, 9, 10, 11],
            "primary_metric": "within-set 6-candidate MRR (cosine retrieval)",
            "guard_conditions": ["dominant_fraction <= 0.5 (non-degenerate)", "2AFC > 0.5",
                                 "exact 6! permutation p < 0.05",
                                 "improvement over strict-C3 identity and matched-random",
                                 "not reproduced by mean-shift-only baseline"],
            "baselines": ["M0_identity (strict C3)", "M1_mean_shift (imagery, target-blind)",
                          "matched_random (>=200, capacity-matched)"],
            "permutation_null": "exact 6! = 720 whole-group target-identity permutations "
                                "(repeat-preserving), seed 20260724 (C3 convention)",
        },
        "frozen_input_hashes": {
            "frozen_decoder_weights_hash": frozen["weights_hash"],
            "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
            "imagery_betas_sha256": _sha256_file(imagery_betas),
            "candidate_pool_sha256": _sha256_file(pool_path),
            "event_manifest_hash": manifest.get("manifest_hash"),
            "xp_session_raw_sha256": xp_session_hashes,
        },
        "seeds": {"alignment_and_matched_random": 20260822, "imagery_permutation": 20260724},
        "anti_leakage_attestation": (
            "No imagery target/cue identity, no imagery CLIP embedding, and no imagery MRR was used "
            "to select the method (M3), the hyperparameters (shrinkage 0.1, rank 400), the ROI, the "
            "centering, or the perception reference. All selection used held-out VISION performance "
            "only. This seal is committed BEFORE any aligned-imagery metric is computed."
        ),
        "scope": "SINGLE_SUBJECT_subj01_ONLY_NOT_POPULATION_EVIDENCE",
        "code_sha": _code_sha(),
        "status": "SEALED_BEFORE_IMAGERY_UNBLINDING",
    }
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True, default=str).encode()).hexdigest()
    out = results_dir / "c3m_alignment_seal.json"
    json.dump(seal, open(out, "w"), indent=2)
    print(f"Wrote {out}")
    print(json.dumps({"status": seal["status"], "self_hash": seal["self_hash"],
                      "imagery_betas_sha256": seal["frozen_input_hashes"]["imagery_betas_sha256"][:16],
                      "vision_gate": seal["vision_gate_decision"]}, indent=2))


if __name__ == "__main__":
    main()
