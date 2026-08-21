"""NSD-Imagery VISION cross-session validation (runs BEFORE H2 unblinding).

Applies the frozen H1 perception decoder to the NSD-Imagery vision beta rows
(the participant actually saw these images in a separate scanning session)
and evaluates retrieval against the frozen 12-item candidate pool. This
certifies the row mapping, ROI extraction, cross-session alignment, and
frozen preprocessing WITHOUT touching mental imagery. No NSD-Imagery
statistic is fit.
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.nsdimagery_row_mapping import compute_run_blocks
from app.research.fmri.nsdimagery_transfer import (
    extract_imagery_rows,
    load_frozen_decoder,
    retrieval_with_frozen_decoder,
    two_way_from_predictions,
)

CUE_TO_POOL = {
    "H": 0, "R": 1, "V": 2, "L": 3, "P": 4, "E": 5,
    "W": 6, "K": 7, "B": 8, "C": 9, "D": 10, "T": 11,
}


def _behavioral_conditions(data_root: Path, run_name: str) -> list[str]:
    path = data_root / "bdata" / "nsdimagery" / f"nsdimagery_subj01_{run_name}.tsv"
    with open(path) as f:
        return [r["CONDITION"] for r in csv.DictReader(f, delimiter="\t")]


def _exact_target_label_null(predictions, candidate_pool, target_pool_indices):
    """Exact repeat-preserving permutation null: enumerate all permutations of
    the distinct target identities (whole groups, all repeats of a stimulus
    get the same permuted label) and recompute MRR. With 6 distinct targets
    per set this is exactly 6! = 720 permutations.
    """
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    sims = pred_norm @ pool_norm.T

    def mrr_for(labels):
        rr = [1.0 / int((sims[i] >= sims[i, lab]).sum()) for i, lab in enumerate(labels)]
        return float(np.mean(rr))

    observed = mrr_for(target_pool_indices)
    unique_targets = sorted(set(int(t) for t in target_pool_indices))
    null = []
    for perm in itertools.permutations(unique_targets):
        remap = {orig: perm[i] for i, orig in enumerate(unique_targets)}
        null.append(mrr_for([remap[int(t)] for t in target_pool_indices]))
    null = np.array(null)
    p_value = float(np.mean(null >= observed))  # exact: identity permutation included
    return {
        "observed_mrr": observed, "null_mean": float(null.mean()),
        "null_std": float(null.std()), "exact_p_value": p_value,
        "n_permutations": len(null),
        "convention": "exact p = #{perm MRR >= observed}/n! (identity included)",
    }


def main() -> None:
    t0 = time.time()
    data_root = Path(os.environ["NSD_DATA_ROOT"])
    betas_root = Path(os.environ["NSD_BETAS_ROOT"])
    cache_root = Path(os.environ["NSD_CACHE_ROOT"])
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))

    frozen = load_frozen_decoder(results_dir / "c3_subj01_frozen_perception_decoder.pkl")
    decoder = frozen["decoder"]
    beta_coords = frozen["beta_coords"]

    candidate_pool = np.load(str(cache_root / "clip" / "c3_imagery_candidate_pool_clip_vitl14.npy")).astype(np.float64)
    imagery_betas_path = (
        betas_root / "ppdata" / "subj01" / "func1pt8mm"
        / "nsdimagerybetas_fithrf" / "betas_nsdimagery.hdf5"
    )

    blocks = {b.run_name: b for b in compute_run_blocks()}
    results = {}

    for set_letter, run_name in [("A", "visA"), ("B", "visB")]:
        block = blocks[run_name]
        conditions = _behavioral_conditions(data_root, run_name)
        target_pool_indices = np.array([CUE_TO_POOL[c] for c in conditions], dtype=np.int64)
        row_indices = list(range(block.row_start, block.row_end))
        print(f"[{run_name}] extracting {len(row_indices)} vision rows...", flush=True)
        betas = extract_imagery_rows(imagery_betas_path, beta_coords, row_indices)

        metrics = retrieval_with_frozen_decoder(decoder, betas, candidate_pool, target_pool_indices)
        twoway = two_way_from_predictions(decoder, betas, candidate_pool, target_pool_indices)
        predictions = decoder.predict(betas.astype(np.float64))
        perm = _exact_target_label_null(predictions, candidate_pool, target_pool_indices)

        label = "primary_technical_validation_setB_complex" if set_letter == "B" else "setA_simple_OOD"
        results[run_name] = {
            "stimulus_set": set_letter, "label": label, "n_trials": len(row_indices),
            "beta_rows": [block.row_start, block.row_end],
            "metrics": metrics, "two_way_identification_accuracy": twoway,
            "exact_target_label_permutation": perm,
        }
        print(f"  {run_name}: MRR={metrics['mrr']:.4f} top1={metrics['top1_accuracy']:.4f} "
              f"2AFC={twoway:.4f} exact_perm_p={perm['exact_p_value']:.5f}", flush=True)

    # Decision criterion (pre-specifiable, aligned with the mission's directive
    # to emphasize the naturalistic Set B and to use repeat-preserving target-
    # label permutations): the row mapping + frozen-decoder cross-session
    # transfer is certified if the PRIMARY naturalistic Set B shows retrieval
    # significantly above its exact repeat-preserving permutation null
    # (p < 0.05). Set A (geometric bars/crosses) is extreme out-of-distribution
    # for a decoder trained on natural scenes; its being at chance is EXPECTED
    # and is not a mapping failure - it is reported for completeness but does
    # not gate the decision.
    chance12 = sum(1.0 / k for k in range(1, 13)) / 12
    setb_p = results["visB"]["exact_target_label_permutation"]["exact_p_value"]
    setb_above = setb_p < 0.05
    status = "VISION_CROSS_SESSION_VALIDATION_PASS" if setb_above else "BLOCKED_CROSS_SESSION_VISION_VALIDATION"

    out = {
        "artifact": "C3_SUBJ01_NSDIMAGERY_VISION_VALIDATION",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01",
        "purpose": (
            "cross-session technical validation of row mapping + frozen decoder transfer to "
            "actually-SEEN NSD-Imagery vision trials; NOT mental imagery, NOT H2"
        ),
        "frozen_decoder_weights_hash": frozen["weights_hash"],
        "candidate_pool_hash": frozen.get("candidate_pool_hash"),
        "chance_mrr_12pool": chance12,
        "decision_criterion": (
            "PRIMARY naturalistic Set B retrieval significantly above its exact repeat-preserving "
            "target-label permutation null (p<0.05). Set A geometric stimuli are extreme OOD; "
            "at-chance Set A is expected and does not gate the decision."
        ),
        "setB_exact_permutation_p": setb_p,
        "setA_note": "geometric bars/crosses, extreme OOD for a natural-scene decoder; at-chance expected",
        "runs": results,
        "status": status,
        "runtime_seconds": round(time.time() - t0, 1),
    }
    out_path = results_dir / "c3_subj01_nsdimagery_vision_validation.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nStatus: {status}\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
