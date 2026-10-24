"""Generate the H2 unblinding seal manifest.

Records the hash of every frozen input to the H2 evaluation BEFORE any
imagery performance is computed, so the analysis is provably pre-registered.
Must be committed before run_h2_zero_shot_transfer.py is executed (that runner
fails closed if this seal is absent or not in SEALED_BEFORE_H2_EVALUATION
state).
"""
from __future__ import annotations

import hashlib
import json
import os
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
    cache_root = Path(os.environ["NSD_CACHE_ROOT"])

    import pickle
    with open(results_dir / "c3_subj01_frozen_perception_decoder.pkl", "rb") as f:
        frozen = pickle.load(f)

    with open(results_dir / "c3_nsdimagery_beta_event_manifest.json") as f:
        event_manifest = json.load(f)

    candidate_pool_path = cache_root / "clip" / "c3_imagery_candidate_pool_clip_vitl14.npy"

    seal = {
        "artifact": "C3_H2_UNBLINDING_MANIFEST",
        "subject": "subj01",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "row_mapping_hash": _sha256_file(results_dir / "c3_nsdimagery_row_mapping.json"),
        "beta_event_manifest_hash": event_manifest["manifest_hash"],
        "frozen_decoder_hash": frozen["weights_hash"],
        "roi_selection_hash": frozen["roi_provenance"]["selection_hash"],
        "normalization_spec": {
            "voxel_mean_std": "frozen from H1 perception outer-train (no imagery statistic)",
            "target_mean": "frozen from H1 perception outer-train",
            "note": "zero-shot: NO imagery/vision-session/condition/run normalization is computed",
        },
        "clip_candidate_pool_hash": _sha256_file(candidate_pool_path),
        "randomization_spec": {
            "primary_null": "exact 6! = 720 whole-group target-identity permutation (repeat-preserving)",
            "secondary_null": "repeat-preserving Monte Carlo permutation",
            "seed": 20260724,
            "monte_carlo_permutations": 100000,
        },
        "primary_subset": "Set B complex imagery (imgB_1 + imgB_2 = 96 trials, 6 targets x 16 repeats)",
        "secondary_subset": "Set A simple imagery (imgA_1 + imgA_2 = 96 trials), labeled SECONDARY_OOD",
        "excluded": "Set C conceptual imagery (no ground-truth image); attention runs",
        "primary_metric": "mean reciprocal rank (MRR) against the frozen 12-item candidate pool",
        "candidate_pool_size": 12,
        "code_sha": _code_sha(),
        "scope": "SINGLE_SUBJECT_ONLY_NOT_POPULATION_EVIDENCE; outcome does not gate other-participant acquisition",
        "status": "SEALED_BEFORE_H2_EVALUATION",
    }
    # self hash over the sealed content (excluding the self_hash field itself)
    seal["self_hash"] = hashlib.sha256(json.dumps(seal, sort_keys=True).encode()).hexdigest()

    out = results_dir / "c3_h2_unblinding_manifest.json"
    with open(out, "w") as f:
        json.dump(seal, f, indent=2)
    print(f"Wrote {out}")
    print(json.dumps({k: seal[k] for k in ["frozen_decoder_hash", "beta_event_manifest_hash",
                                            "clip_candidate_pool_hash", "self_hash", "status"]}, indent=2))


if __name__ == "__main__":
    main()
