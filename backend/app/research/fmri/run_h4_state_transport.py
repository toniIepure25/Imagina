"""C3-H4: low-capacity imagery state transport (held-out-TARGET).

Executed because zero-shot H2 is null. The frozen H1 perception decoder stays
unchanged; a minimal calibration layer (identity / mean-correction / affine
ridge / strict low-rank / matched random low-rank) is fit ONLY inside imagery
calibration folds and evaluated on a HELD-OUT TARGET (nested leave-one-target-
out: a target present in calibration never appears in the test fold).

Primary estimand:
  Delta_transport = held-out-target MRR(calibrated) - held-out-target MRR(identity)

Primary subset = Set B complex imagery. Single-subject only.
"""
from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path

import numpy as np

from app.research.fmri.nsdimagery_row_mapping import compute_run_blocks
from app.research.fmri.nsdimagery_transfer import extract_imagery_rows, load_frozen_decoder
from app.research.fmri.transport import evaluate_transport_loso

CUE_TO_POOL = {"W": 6, "K": 7, "B": 8, "C": 9, "D": 10, "T": 11}


def _conditions(data_root: Path, run_name: str) -> list[str]:
    path = data_root / "bdata" / "nsdimagery" / f"nsdimagery_subj01_{run_name}.tsv"
    with open(path) as f:
        return [r["CONDITION"] for r in csv.DictReader(f, delimiter="\t")]


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

    # Primary: Set B complex imagery
    row_indices, conditions = [], []
    for rn in ["imgB_1", "imgB_2"]:
        b = blocks[rn]
        row_indices.extend(range(b.row_start, b.row_end))
        conditions.extend(_conditions(data_root, rn))
    betas = extract_imagery_rows(imagery_betas_path, beta_coords, row_indices)
    predictions = decoder.predict(betas.astype(np.float64))

    target_indices = np.array([CUE_TO_POOL[c] for c in conditions], dtype=np.int64)
    target_embeddings = candidate_pool[target_indices]
    # stimulus id = pool index (one physical stimulus per Set-B target identity)
    stimulus_ids = target_indices.copy()

    # Low-capacity: rank strictly below the 5 calibration targets available at
    # each held-out-target fold; alpha strong for a minimal layer.
    result = evaluate_transport_loso(
        predictions, target_embeddings, candidate_pool, target_indices, stimulus_ids,
        alpha=1000.0, rank=3,
    )

    identity_mrr = result["methods"]["identity"]["mean_mrr"]
    deltas = {}
    for method in ["mean_correction", "affine_ridge", "low_rank"]:
        deltas[method] = result["methods"][method].get("delta_vs_identity")

    best_method = max(deltas, key=lambda m: deltas[m])
    best_delta = deltas[best_method]
    # Held-out-target improvement must be positive AND beat the matched random
    # low-rank control to claim any state transport.
    random_mrr = result["methods"]["random_low_rank"]["mean_mrr"]
    beats_random = result["methods"][best_method]["mean_mrr"] > random_mrr
    if best_delta is not None and best_delta > 0 and beats_random:
        decision = "SUBJ01_STATE_TRANSPORT_HELD_OUT_TARGET_IMPROVEMENT"
    else:
        decision = "SUBJ01_STATE_TRANSPORT_NULL_OR_INCONCLUSIVE"

    out = {
        "artifact": "C3_SUBJ01_STATE_TRANSPORT",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01",
        "scope": "SINGLE_SUBJECT_ONLY",
        "executed_because": "zero-shot H2 is null (degenerate collapse)",
        "primary_subset": "Set B complex imagery, nested leave-one-target-out (held-out TARGET)",
        "estimand": "Delta_transport = held-out-target MRR(calibrated) - held-out-target MRR(identity)",
        "transport_capacity": {"alpha": 1000.0, "low_rank": 3, "note": "rank < 5 calibration targets"},
        "frozen_decoder_weights_hash": frozen["weights_hash"],
        "identity_mrr": identity_mrr,
        "chance_mrr_12pool": sum(1.0 / k for k in range(1, 13)) / 12,
        "per_method": result["methods"],
        "delta_vs_identity": deltas,
        "matched_random_low_rank_mrr": random_mrr,
        "best_method": best_method, "best_delta_transport": best_delta,
        "beats_matched_random": bool(beats_random),
        "decision": decision,
        "decision_note": (
            "Held-out-TARGET improvement (not merely held-out-trial) that also beats the "
            "matched random low-rank control is required to claim any state transport. Given the "
            "zero-shot prediction collapse, the frozen decoder's imagery outputs carry little "
            "target-specific variance for a transport layer to exploit on unseen targets."
        ),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    out_path = results_dir / "c3_state_transport_realdata.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"identity_mrr={identity_mrr:.4f}", flush=True)
    for m, d in deltas.items():
        print(f"  {m}: mrr={result['methods'][m]['mean_mrr']:.4f} delta={d:+.4f}", flush=True)
    print(f"random_low_rank mrr={random_mrr:.4f}", flush=True)
    print(f"\nDecision: {decision}\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
