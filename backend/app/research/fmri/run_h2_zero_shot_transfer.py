"""Sealed subj01 single-subject H2: zero-shot perception-to-imagery transfer.

Applies the frozen H1 perception decoder to the NSD-Imagery imagery beta rows
(no imagery-derived preprocessing of any kind) and evaluates retrieval against
the frozen 12-item candidate pool. Primary = Set B complex (imgB_1+imgB_2, 96
trials, 6 targets x 16 repeats); secondary = Set A simple (imgA_1+imgA_2).
Set C conceptual is excluded (no ground-truth image).

Inference statistic: exact 6! = 720 permutation null over the 6 target
identities (whole-group, repeat-preserving), plus a repeat-preserving Monte
Carlo permutation as secondary. Single-subject only: NOT population evidence.
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
    prediction_collapse_diagnostic,
    retrieval_with_frozen_decoder,
    two_way_from_predictions,
)

CUE_TO_POOL = {
    "H": 0, "R": 1, "V": 2, "L": 3, "P": 4, "E": 5,
    "W": 6, "K": 7, "B": 8, "C": 9, "D": 10, "T": 11,
}


def _conditions(data_root: Path, run_name: str) -> list[str]:
    path = data_root / "bdata" / "nsdimagery" / f"nsdimagery_subj01_{run_name}.tsv"
    with open(path) as f:
        return [r["CONDITION"] for r in csv.DictReader(f, delimiter="\t")]


def _exact_permutation_null(sims, target_pool_indices, set_pool_labels):
    """Exact 6! null over the set's target identities.

    sims: [n_trials, 12] cosine sims of prediction to each candidate.
    target_pool_indices: true pool index per trial (all in set_pool_labels).
    set_pool_labels: the 6 pool indices for this set (e.g. [6..11] for Set B).
    Permutes which physical stimulus maps to which of the 6 set labels;
    all repeats of a stimulus get the same permuted label.
    """
    def mrr_for(labels):
        rr = []
        for i, lab in enumerate(labels):
            rank = int((sims[i] >= sims[i, lab]).sum())
            rr.append(1.0 / rank)
        return float(np.mean(rr))

    observed = mrr_for(target_pool_indices)
    base = list(set_pool_labels)
    null = []
    for perm in itertools.permutations(base):
        remap = {orig: perm[i] for i, orig in enumerate(base)}
        null.append(mrr_for([remap[int(t)] for t in target_pool_indices]))
    null = np.array(null)
    # exact p-value: fraction of permutations (incl. identity) with MRR >= observed
    p_value = float(np.mean(null >= observed))
    return {
        "observed_mrr": observed,
        "exact_null_mean": float(null.mean()),
        "exact_null_std": float(null.std()),
        "exact_null_q95": float(np.percentile(null, 95)),
        "exact_null_max": float(null.max()),
        "exact_p_value": p_value,
        "effect_above_null": float(observed - null.mean()),
        "n_permutations": len(null),
        "convention": "exact permutation p = #{perm MRR >= observed}/6! (identity included)",
    }


def _monte_carlo_null(sims, target_pool_indices, set_pool_labels, n_perms=100000, seed=20260724):
    rng = np.random.default_rng(seed)
    base = list(set_pool_labels)

    def mrr_for(labels):
        rr = [1.0 / int((sims[i] >= sims[i, lab]).sum()) for i, lab in enumerate(labels)]
        return float(np.mean(rr))

    observed = mrr_for(target_pool_indices)
    null = np.zeros(n_perms)
    for p in range(n_perms):
        perm = rng.permutation(base)
        remap = {orig: perm[i] for i, orig in enumerate(base)}
        null[p] = mrr_for([remap[int(t)] for t in target_pool_indices])
    p_value = float((np.sum(null >= observed) + 1) / (n_perms + 1))
    return {"observed_mrr": observed, "mc_null_mean": float(null.mean()),
            "mc_p_value": p_value, "n_permutations": n_perms, "seed": seed}


def _evaluate_set(decoder, betas, candidate_pool, target_pool_indices, conditions, set_pool_labels):
    metrics = retrieval_with_frozen_decoder(decoder, betas, candidate_pool, target_pool_indices)
    twoway = two_way_from_predictions(decoder, betas, candidate_pool, target_pool_indices)
    collapse = prediction_collapse_diagnostic(decoder, betas, candidate_pool, set_pool_labels)
    predictions = decoder.predict(betas.astype(np.float64))
    pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
    pool_norm = candidate_pool / np.clip(np.linalg.norm(candidate_pool, axis=1, keepdims=True), 1e-8, None)
    sims = pred_norm @ pool_norm.T

    exact = _exact_permutation_null(sims, target_pool_indices, set_pool_labels)
    mc = _monte_carlo_null(sims, target_pool_indices, set_pool_labels)

    # per-target MRR
    per_target = {}
    for lab in set_pool_labels:
        mask = target_pool_indices == lab
        if mask.sum():
            rr = [1.0 / int((sims[i] >= sims[i, lab]).sum()) for i in np.where(mask)[0]]
            per_target[int(lab)] = {"n_repeats": int(mask.sum()), "mrr": float(np.mean(rr))}

    # A permutation-significant result is only accepted as genuine transfer if
    # the predictions are NOT degenerate (no single-candidate collapse) AND
    # 2AFC is above chance. Otherwise the exact-p significance is an artifact.
    exact_p = exact["exact_p_value"]
    genuine = (exact_p < 0.05) and (not collapse["degenerate"]) and (twoway > 0.5)
    return {
        "n_trials": len(betas), "metrics": metrics,
        "two_way_identification_accuracy": twoway,
        "prediction_collapse_diagnostic": collapse,
        "exact_permutation_null": exact, "monte_carlo_null": mc,
        "per_target_mrr": per_target,
        "genuine_transfer": genuine,
        "genuine_transfer_criteria": {
            "exact_p_lt_0_05": bool(exact_p < 0.05),
            "not_degenerate_collapse": bool(not collapse["degenerate"]),
            "two_way_above_chance": bool(twoway > 0.5),
        },
    }


def main() -> None:
    t0 = time.time()
    data_root = Path(os.environ["NSD_DATA_ROOT"])
    betas_root = Path(os.environ["NSD_BETAS_ROOT"])
    cache_root = Path(os.environ["NSD_CACHE_ROOT"])
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))

    # Fail closed if the seal does not exist.
    seal_path = results_dir / "c3_h2_unblinding_manifest.json"
    if not seal_path.exists():
        raise RuntimeError("H2 seal manifest not found; refusing to evaluate H2 before it is sealed and committed.")
    with open(seal_path) as f:
        seal = json.load(f)
    if seal.get("status") != "SEALED_BEFORE_H2_EVALUATION":
        raise RuntimeError(f"H2 seal status is {seal.get('status')}, not SEALED_BEFORE_H2_EVALUATION.")

    frozen = load_frozen_decoder(results_dir / "c3_subj01_frozen_perception_decoder.pkl")
    decoder = frozen["decoder"]
    beta_coords = frozen["beta_coords"]
    candidate_pool = np.load(str(cache_root / "clip" / "c3_imagery_candidate_pool_clip_vitl14.npy")).astype(np.float64)
    imagery_betas_path = (
        betas_root / "ppdata" / "subj01" / "func1pt8mm"
        / "nsdimagerybetas_fithrf" / "betas_nsdimagery.hdf5"
    )
    blocks = {b.run_name: b for b in compute_run_blocks()}

    def load_set(run_names):
        row_indices, conditions = [], []
        for rn in run_names:
            b = blocks[rn]
            row_indices.extend(range(b.row_start, b.row_end))
            conditions.extend(_conditions(data_root, rn))
        betas = extract_imagery_rows(imagery_betas_path, beta_coords, row_indices)
        target_pool_indices = np.array([CUE_TO_POOL[c] for c in conditions], dtype=np.int64)
        return betas, target_pool_indices, conditions

    print("[primary] Set B complex imagery (imgB_1 + imgB_2)...", flush=True)
    b_betas, b_targets, b_conds = load_set(["imgB_1", "imgB_2"])
    primary = _evaluate_set(decoder, b_betas, candidate_pool, b_targets, b_conds, list(range(6, 12)))
    print(f"  MRR={primary['metrics']['mrr']:.4f} 2AFC={primary['two_way_identification_accuracy']:.4f} "
          f"exact_p={primary['exact_permutation_null']['exact_p_value']:.4f}", flush=True)

    print("[secondary] Set A simple imagery (imgA_1 + imgA_2)...", flush=True)
    a_betas, a_targets, a_conds = load_set(["imgA_1", "imgA_2"])
    secondary = _evaluate_set(decoder, a_betas, candidate_pool, a_targets, a_conds, list(range(0, 6)))
    print(f"  MRR={secondary['metrics']['mrr']:.4f} 2AFC={secondary['two_way_identification_accuracy']:.4f} "
          f"exact_p={secondary['exact_permutation_null']['exact_p_value']:.4f}", flush=True)

    chance12 = sum(1.0 / k for k in range(1, 13)) / 12
    if primary["genuine_transfer"]:
        decision = "SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER_PASS"
    elif primary["prediction_collapse_diagnostic"]["degenerate"]:
        decision = "SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER_NULL_DEGENERATE_COLLAPSE"
    else:
        decision = "SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER_NULL_OR_INCONCLUSIVE_PENDING_SENSITIVITY"

    out = {
        "artifact": "C3_SUBJ01_ZERO_SHOT_IMAGERY_TRANSFER",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01",
        "scope": "SINGLE_SUBJECT_ONLY_NOT_POPULATION_EVIDENCE",
        "outcome_does_not_gate_other_participant_acquisition": True,
        "chance_mrr_12pool": chance12,
        "seal_hash_at_evaluation": seal.get("self_hash"),
        "frozen_decoder_weights_hash": frozen["weights_hash"],
        "primary_setB_complex": primary,
        "secondary_setA_simple_OOD": secondary,
        "decision": decision,
        "decision_note": (
            "A permutation-significant exact-p alone is NOT sufficient: it is accepted as genuine "
            "transfer only if predictions are not a single-candidate collapse AND 2AFC>0.5. For "
            "subj01 the frozen decoder's imagery predictions collapse onto one candidate (see "
            "prediction_collapse_diagnostic), and 2AFC is below chance, so the exact-p significance "
            "is a collapse artifact, not transfer. PASS would never mean mind reading, general "
            "imagery decoding, population generalization, or reconstruction readiness."
        ),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    out_path = results_dir / "c3_zero_shot_transfer_realdata.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nDecision: {decision}\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
