"""ANIMUS-P2 protocol seal + firewall audit + product-bridge validation (synthetic).

Writes the prospective protocol seal (all frozen choices, self-hashed) that MUST be committed + CI-green
before the confirmatory test partition is unlocked; records the firewall audit (test outcomes not accessed
before freeze); and validates the product-bridge machinery on synthetic data (neural initialization improves
an ANIMUS-style loop; fusion respects decoder uncertainty). No real neural outcomes here.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

from app.core.animus.p2 import gate
from app.core.animus.p2.decoder import ALPHAS, PRIMARY_FAMILY
from app.core.animus.p2.integration import (
    belief_fusion_respects_uncertainty,
    neural_initialization_experiment,
)
from app.core.animus.p2.metrics import SEEDS
from app.core.animus.p2.splits import TEST_FRAC, TRAIN_FRAC, VAL_FRAC
from app.core.animus.p2.synthetic import make_subject
from app.core.animus.p2.target_representation import target_representation_seal, unit_l2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")
SEAL = os.path.join(OUT, "animus_p2_protocol_seal.json")


def _native(o):
    if isinstance(o, dict):
        return {k: _native(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_native(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def _sh(o):
    o = _native(dict(o))
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def build_seal() -> dict:
    tr = target_representation_seal()
    return {
        "artifact": "ANIMUS_P2_PROTOCOL_SEAL", "milestone": "ANIMUS-P2",
        "scientific_parent": "a0b6ca7",
        "dataset": {"primary": "ds004496 (NOD)", "fallback": "ds001499 (BOLD5000)",
                    "selection": "results/animus_p2/perception_dataset_candidate_matrix.json",
                    "provenance_verified_at_staging": True},
        "participant_denominator": "fixed eligible subjects (prospective subset by subject id; no shrinkage)",
        "stimulus_partitions": {"grouped_by": "stimulus_identity", "train": TRAIN_FRAC, "val": VAL_FRAC,
                                "test": TEST_FRAC, "seal": "results/animus_p2/content_split_seal.json"},
        "roi": {"primary": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK", "secondary": ["V1/V2/V3", "whole_visual",
                "whole_GM", "size_matched_random_cortical"], "no_outcome_based_selection": True},
        "neural_preprocessing": {"reuse": "C3XRA/C3XAT reproducibility discipline",
                                 "beta_extraction": "dataset-provided beta IF exact/reproducible, else frozen "
                                 "LSA/GLM; never mixed across subjects",
                                 "voxel_order": "frozen per subject; no univariate outcome selection",
                                 "normalization": "fold-safe (train-only fit)"},
        "target_embedding": tr["primary_encoder"], "target_is_visual_not_caption": True,
        "decoder": {"primary_family": PRIMARY_FAMILY, "alpha_grid": ALPHAS,
                    "selection": "nested validation", "secondary": ["low_rank", "small_MLP (descriptive)"]},
        "uncertainty_method": "bootstrap decoder ensemble (predictive spread), calibrated on validation",
        "reject_option": "uncertainty>validation-threshold OR QC/ROI invalid OR OOD -> valid=false",
        "permutation": {"within_test_label_permutation": True, "n_perm": 1000},
        "bootstrap": {"identity_bootstrap": True, "n_boot": 1000},
        "seeds": list(SEEDS),
        "primary_statistic": "content margin M = mean(cos(p_i,t_i) - mean_{j!=i} cos(p_i,t_j)), held-out test",
        "subject_pass": "data_contract & atlas_qc & M>0 & perm_p<0.01 & bootstrap_ci_lower>0 & all_seeds_positive",
        "dataset_gate": "required_passes=max(2,ceil(N/3)); VALIDATED/LIMITED/FAIL/BLOCKED; fixed denominator",
        "negative_controls": ["label_permutation", "category_matched_decoys", "low_level_baseline",
                              "run_session_fingerprint", "within/cross-run shuffle"],
        "claim_authorization": "capability-scoped; success authorizes PERCEPTION_NEURAL_CONTENT ONLY; "
                               "imagery/dream/reconstruction remain unauthorized",
        "animus_integration_test": "neural-initialization experiment (uninformed vs neural vs fused) on "
                                   "held-out perception trials; product bridge cannot rescue a failed decoder",
        "confirmatory_command": "run_p2_confirmatory (unlocks frozen test only after this seal is CI-green)",
        "no_image_reconstruction_in_primary_gate": True,
    }


def bridge_validation() -> dict:
    """Synthetic validation of the product bridge: build synthetic held-out trials with a synthetic decoded
    latent (noisy version of the true target) and show neural initialization helps + fusion uses uncertainty."""
    subj = make_subject("bridge", n_identities=120, reps=1, dim=64, signal=1.6, seed=7)
    rng = np.random.default_rng(11)
    targets = subj.Y
    # synthetic 'decoded' latent = target corrupted by noise scaled per-trial; uncertainty ~ noise level.
    # noise range represents a DECENT validated decoder (2AFC ~0.7-0.9), the regime where the bridge applies.
    noise = rng.uniform(0.15, 0.55, size=len(targets))
    decoded = np.stack([unit_l2(targets[i] + noise[i] * rng.standard_normal(targets.shape[1]))
                        for i in range(len(targets))])
    exp = neural_initialization_experiment(decoded, noise, None, targets)
    fusion = belief_fusion_respects_uncertainty()
    exp["belief_fusion_respects_uncertainty"] = fusion
    exp["bridge_pass"] = bool(exp["neural_init_gain_positive"] and exp["neural_faster"]
                              and exp["fused_ge_both"] and fusion["pass"])
    return exp


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    seal = build_seal()
    json.dump(_sh(seal), open(SEAL, "w"), indent=2)

    # firewall audit — confirmatory test not accessed during seal construction
    from app.core.animus.p2.firewall import TestFirewall, write_audit
    fw = TestFirewall(seal_path=SEAL)  # seal now exists -> frozen True post-write, but no access attempted
    write_audit(fw, os.path.join(OUT, "firewall_audit.json"))

    bridge = bridge_validation()
    json.dump(_sh({"artifact": "ANIMUS_P2_BRIDGE_VALIDATION", "milestone": "ANIMUS-P2",
                   "synthetic_only": True, **bridge}),
              open(os.path.join(OUT, "bridge_validation.json"), "w"), indent=2)

    # required_passes sanity across small N
    rp = {str(n): gate.required_passes(n) for n in (3, 4, 6, 9)}

    print("protocol seal:", seal["primary_statistic"][:40], "...")
    print("bridge:", {k: bridge[k] for k in ("median_neural_initialization_gain", "neural_init_gain_positive",
          "neural_faster", "fused_ge_both", "bridge_pass")})
    print("required_passes:", rp)
    print("BRIDGE PASS:", bridge["bridge_pass"])
    return 0 if bridge["bridge_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
