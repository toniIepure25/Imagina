"""Persist the frozen H1 perception decoder for reuse by downstream H2/H4
stages, so they never need to refit it (and never touch perception test
data, imagery data, or any statistic beyond what H1 already froze).

Refits using exactly the same procedure, data, and seed as
run_strict_perception_replay.py's steps 1-6 (voxel selection, CLIP load,
split load, ROI extraction, fold-safe ridge fit on the strict-original
9000-image outer-train pool) - deterministic, so this reproduces the exact
H1 decoder bit-for-bit. Does not touch the outer-test set or run any
controls; only the main fit.
"""
from __future__ import annotations

import json
import os
import pickle
import time
from pathlib import Path

import numpy as np

from app.research.fmri.decoder import DecoderConfig, evaluate_retrieval, train_ridge_decoder
from app.research.fmri.run_strict_perception_replay import (
    _require_env,
    _sha256_bytes,
    average_by_image,
    build_clip_targets,
    build_trial_to_image,
    compute_chance_mrr,
    extract_all_sessions,
    load_roi_and_ncsnr_selection,
)


def main() -> None:
    t_start = time.time()
    nsd_data_root = _require_env("NSD_DATA_ROOT")
    nsd_betas_root = _require_env("NSD_BETAS_ROOT")
    nsd_cache_root = _require_env("NSD_CACHE_ROOT")
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    subject = "subj01"
    seed = 42

    out_path = Path(os.environ.get("FROZEN_DECODER_PATH", str(results_dir / "c3_subj01_frozen_perception_decoder.pkl")))
    if out_path.exists():
        print(f"Frozen decoder already exists at {out_path}; skipping refit.", flush=True)
        return

    print("[1] Voxel selection (nsdgeneral AND ncsnr>0)...", flush=True)
    beta_coords, roi_provenance = load_roi_and_ncsnr_selection(nsd_data_root, nsd_betas_root, subject)
    print(f"  selected voxels: {roi_provenance['selected_voxel_count']}", flush=True)

    print("[2] Loading CLIP embeddings...", flush=True)
    clip_path = nsd_cache_root / "clip" / "subj01_perception_clip_vitl14.npy"
    clip_emb = np.load(str(clip_path)).astype(np.float64)
    clip_hash = _sha256_bytes(clip_emb.tobytes())

    print("[3] Loading split manifest (strict-original 9000/1000 config)...", flush=True)
    with open(results_dir / "c3_split_manifest.json") as f:
        manifest = json.load(f)
    outer_train_ids = set(manifest["train_image_ids"]) | set(manifest["val_image_ids"])
    outer_test_ids = set(manifest["test_image_ids"])
    assert len(outer_train_ids) == 9000 and len(outer_test_ids) == 1000

    print("[4] Extracting ROI data from all 40 sessions...", flush=True)
    trial_to_image, all_sorted_ids = build_trial_to_image(nsd_data_root)
    fmri_all = extract_all_sessions(nsd_betas_root, beta_coords, subject)
    beta_manifest_hash = _sha256_bytes(fmri_all.tobytes())

    print("[5] Averaging repeated presentations...", flush=True)
    X_train, train_ids = average_by_image(fmri_all, trial_to_image, outer_train_ids)
    X_test, test_ids = average_by_image(fmri_all, trial_to_image, outer_test_ids)
    Y_train = build_clip_targets(train_ids, all_sorted_ids, clip_emb)
    Y_test = build_clip_targets(test_ids, all_sorted_ids, clip_emb)
    del fmri_all

    print("[6] Fold-safe ridge decoder training (frozen DecoderConfig)...", flush=True)
    config = DecoderConfig(roi_id="nsdgeneral", ncsnr_threshold=0.0, random_seed=seed)
    decoder = train_ridge_decoder(X_train, Y_train, config)
    print(f"  selected alpha: {decoder.alpha:.0e}", flush=True)

    print("[7] Sanity check against the frozen strict H1 result...", flush=True)
    predictions = decoder.predict(X_test)
    metrics = evaluate_retrieval(predictions, Y_test, Y_test, np.arange(len(Y_test)))
    chance = compute_chance_mrr(len(Y_test))
    print(f"  MRR: {metrics['mrr']:.6f} (expect ~0.077295, chance {chance:.6f})", flush=True)
    with open(results_dir / "c3_subj01_perception_strict_replay.json") as f:
        frozen = json.load(f)
    expected_mrr = frozen["primary_metrics"]["mrr"]
    if abs(metrics["mrr"] - expected_mrr) > 1e-6:
        raise RuntimeError(
            f"Refit decoder MRR ({metrics['mrr']}) does not match the committed strict H1 "
            f"result ({expected_mrr}) to 1e-6 - refuses to freeze a decoder that does not "
            f"reproduce the certified H1 result bit-for-bit."
        )
    print("  MATCH: refit decoder reproduces the certified H1 result exactly.", flush=True)

    weights_hash = _sha256_bytes(decoder.weights.tobytes())

    bundle = {
        "decoder": decoder,
        "beta_coords": beta_coords,
        "roi_provenance": roi_provenance,
        "clip_hash": clip_hash,
        "split_manifest_hash": manifest["manifest_hash"],
        "beta_manifest_hash": beta_manifest_hash,
        "weights_hash": weights_hash,
        "decoder_config_hash": config.spec_hash(),
        "reproduced_h1_mrr": metrics["mrr"],
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(bundle, f)
    os.replace(tmp, out_path)
    print(f"\nFrozen decoder saved: {out_path}", flush=True)
    print(f"  weights_hash: {weights_hash}", flush=True)
    print(f"Done in {time.time() - t_start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
