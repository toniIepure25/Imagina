"""Build the authoritative 720-row NSD-Imagery beta-event manifest for subj01.

Within-block ordering (beta row k of a vision/imagery block == behavioral
trial k) is established in docs/research/C3_NSDIMAGERY_ROW_MAPPING_AMENDMENT.md
by pairing the design-matrix chronological onset order with the behavioral
trial order and confirming the column->CONDITION mapping is a consistent
function. Attention rows (scientifically excluded from H2) are classified by
design-matrix column group (cue epoch cols vs detection epoch cols) in
chronological onset order.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from app.research.fmri.nsdimagery_row_mapping import compute_run_blocks

# cue letter -> (target filename, candidate pool index). Set A 0-5, Set B 6-11.
# Set C cues (S,Z,M,Y,N,F) have no ground-truth image and no pool index.
CUE_TO_POOL = {
    "H": 0, "R": 1, "V": 2, "L": 3, "P": 4, "E": 5,   # Set A
    "W": 6, "K": 7, "B": 8, "C": 9, "D": 10, "T": 11,  # Set B
}
CUE_TO_TARGET = {
    "H": "bar_000.0deg_450L_43W.png", "R": "bar_045.0deg_450L_43W.png",
    "V": "bar_090.0deg_450L_43W.png", "L": "bar_135.0deg_450L_43W.png",
    "P": "crs_000.0deg_450L_43W.png", "E": "crs_045.0deg_450L_43W.png",
    "W": "shared0385_nsd28752.png", "K": "shared0413_nsd30857.png",
    "B": "shared0741_nsd53882.png", "C": "shared0842_nsd61178.png",
    "D": "shared0907_nsd65873.png", "T": "shared0000_nsd00000.png",
}


def _behavioral(data_root: Path, run_name: str) -> list[dict]:
    path = data_root / "bdata" / "nsdimagery" / f"nsdimagery_subj01_{run_name}.tsv"
    with open(path) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _design_onsets(stim, cell: int) -> list[tuple[int, int]]:
    m = stim[0, cell]
    active = np.where(m.sum(axis=0) > 0)[0]
    events = []
    for c in active:
        for tr in np.where(m[:, c] != 0)[0]:
            events.append((int(tr), int(c)))
    events.sort()
    return events


def build_manifest(data_root: Path) -> dict:
    mat = loadmat(str(data_root / "experiments" / "nsdimagery" / "designmatrixGLMsingle.mat"))
    stim = mat["stimulus"]
    blocks = compute_run_blocks()

    rows = []
    for cell, block in enumerate(blocks):
        behavioral = _behavioral(data_root, block.run_name)
        assert len(behavioral) == 48, f"{block.run_name}: expected 48 behavioral trials"
        onsets = _design_onsets(stim, cell)
        assert len(onsets) == block.n_betas, f"{block.run_name}: {len(onsets)} onsets != {block.n_betas} betas"

        if block.kind in ("vis", "img"):
            # Proven: beta row k (local) == behavioral trial k.
            for k in range(block.n_betas):
                trial = behavioral[k]
                cond = trial["CONDITION"]
                pool_idx = CUE_TO_POOL.get(cond)
                gt = pool_idx is not None
                if block.kind == "vis":
                    event_type = "vision"
                    role = "technical_validation" if gt else "excluded"
                else:
                    event_type = "imagery"
                    if not gt:
                        role = "excluded"  # Set C conceptual
                    elif block.stimulus_set == "B":
                        role = "primary_H2"
                    elif block.stimulus_set == "A":
                        role = "secondary_H2"
                    else:
                        role = "excluded"
                rows.append({
                    "beta_row_index": block.row_start + k,
                    "run_number": block.run_number, "run_name": block.run_name,
                    "run_local_beta_index": k, "event_type": event_type,
                    "behavioral_trial_index": k, "within_run_trial_index": k,
                    "cue": cond, "stimulus_set": block.stimulus_set,
                    "target_identity": CUE_TO_TARGET.get(cond),
                    "ground_truth_image_available": gt,
                    "candidate_pool_index": pool_idx,
                    "scientific_role": role,
                })
        else:
            # Attention: cols in the lower half of the active range are the cue
            # epoch, upper half the detection epoch. Both betas of one trial
            # share a behavioral_trial_index. Attention is excluded from H2.
            active_cols = sorted({c for _tr, c in onsets})
            n_half = len(active_cols) // 2
            cue_cols = set(active_cols[:n_half])
            # Pair each cue event with the detection event ~3 TR later at the
            # matching condition column (col + n_half). Assign trial indices in
            # chronological order of cue events.
            cue_events = [(tr, c) for tr, c in onsets if c in cue_cols]
            cue_events.sort()
            cue_tr_to_trial = {tr: i for i, (tr, c) in enumerate(cue_events)}
            for k, (tr, c) in enumerate(onsets):
                is_cue = c in cue_cols
                if is_cue:
                    trial_idx = cue_tr_to_trial[tr]
                    event_type = "attention_cue"
                else:
                    # nearest preceding cue event is this trial's cue (~3 TR back)
                    preceding = [ct for ct, _ in cue_events if ct <= tr]
                    trial_idx = cue_tr_to_trial[max(preceding)] if preceding else -1
                    event_type = "attention_detection"
                rows.append({
                    "beta_row_index": block.row_start + k,
                    "run_number": block.run_number, "run_name": block.run_name,
                    "run_local_beta_index": k, "event_type": event_type,
                    "behavioral_trial_index": trial_idx, "within_run_trial_index": trial_idx,
                    "cue": None, "stimulus_set": block.stimulus_set,
                    "target_identity": None, "ground_truth_image_available": False,
                    "candidate_pool_index": None, "scientific_role": "excluded",
                })

    # Aggregate counts
    counts = {
        "raw_beta_rows": len(rows),
        "vision_rows": sum(1 for r in rows if r["event_type"] == "vision"),
        "imagery_rows": sum(1 for r in rows if r["event_type"] == "imagery"),
        "attention_cue_rows": sum(1 for r in rows if r["event_type"] == "attention_cue"),
        "attention_detection_rows": sum(1 for r in rows if r["event_type"] == "attention_detection"),
        "primary_complex_imagery_rows": sum(1 for r in rows if r["scientific_role"] == "primary_H2"),
        "secondary_simple_imagery_rows": sum(1 for r in rows if r["scientific_role"] == "secondary_H2"),
        "excluded_rows": sum(1 for r in rows if r["scientific_role"] == "excluded"),
    }
    counts["attention_rows_total"] = counts["attention_cue_rows"] + counts["attention_detection_rows"]

    manifest_bytes = json.dumps(rows, sort_keys=True).encode()
    return {
        "artifact": "C3_NSDIMAGERY_BETA_EVENT_MANIFEST",
        "subject": "subj01",
        "counts": counts,
        "manifest_hash": hashlib.sha256(manifest_bytes).hexdigest(),
        "rows": rows,
    }


def main() -> None:
    data_root = Path(os.environ["NSD_DATA_ROOT"])
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    manifest = build_manifest(data_root)
    out = results_dir / "c3_nsdimagery_beta_event_manifest.json"
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {out}")
    print(json.dumps(manifest["counts"], indent=2))
    print("manifest_hash:", manifest["manifest_hash"])


if __name__ == "__main__":
    main()
