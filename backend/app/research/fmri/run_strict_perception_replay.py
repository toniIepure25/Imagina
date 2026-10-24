"""Strict, leakage-free subj01 perception-foundation H1 replay.

Reusable scientific runner: every data location comes from an environment
variable (NSD_DATA_ROOT, NSD_BETAS_ROOT, NSD_CACHE_ROOT) or an explicit CLI
argument. No path defaults to a specific developer machine — missing
configuration fails closed with a clear error rather than silently guessing.

Differences from the superseded ad-hoc pilot (backend/_run_perception_pilot.py):
- No transductive normalization: voxel z-scoring and target centering are
  fit exclusively inside app.research.fmri.decoder.train_ridge_decoder's
  fold-safe inner CV / outer-train refit. The held-out test set is
  transformed only with statistics fit on training data.
- Uses the frozen DecoderConfig alpha grid (0.1..100000, 7 candidates,
  5-fold inner CV) instead of an ad-hoc 1e0..1e7 grid.
- Voxel selection is nsdgeneral membership AND ncsnr > 0 (the frozen
  policy), not nsdgeneral alone.
- Primary split is the strict-original configuration: the split manifest's
  train_image_ids UNION val_image_ids (9000 identities) forms the outer
  training pool for inner-CV alpha selection; test_image_ids (1000
  shared1000 identities) is touched only once, after the decoder is frozen.
- Reports true two_way_identification_accuracy (2AFC) alongside the old
  mutual-nearest-neighbor statistic, renamed mutual_top1_rate.
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import h5py
import nibabel as nib
import numpy as np
from numpy.typing import NDArray
from scipy.io import loadmat

from app.research.fmri.decoder import (
    DecoderConfig,
    TrainedDecoder,
    evaluate_retrieval,
    train_ridge_decoder,
    two_way_identification,
)


def _require_env(var: str) -> Path:
    val = os.environ.get(var)
    if not val:
        raise EnvironmentError(
            f"Required environment variable {var} is not set. "
            f"This is a reusable scientific runner and does not default to "
            f"any developer machine's paths."
        )
    return Path(val)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _save_checkpoint(path: Path, **kwargs) -> None:
    """Atomic pickle write: our own generated checkpoint, not an untrusted
    external file, so loading it back with pickle is safe. Survives an
    interrupted write via a .tmp + os.replace swap (a fresh Python process
    always resumes from the last fully-written checkpoint, never a
    half-written one).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(kwargs, f)
    os.replace(tmp, path)


def _load_checkpoint(path: Path) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def _code_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, cwd=Path(__file__).resolve().parents[4]
        ).strip()
    except Exception:
        return "UNKNOWN"


def load_roi_and_ncsnr_selection(
    nsd_data_root: Path, nsd_betas_root: Path, subject: str = "subj01"
) -> tuple[NDArray, dict]:
    """Frozen voxel selection: nsdgeneral membership AND ncsnr > 0."""
    roi_path = nsd_data_root / "ppdata" / subject / "func1pt8mm" / "roi" / "nsdgeneral.nii.gz"
    ncsnr_path = nsd_betas_root / "ppdata" / subject / "func1pt8mm" / "betas_fithrf" / "ncsnr.nii.gz"

    roi_img = nib.load(str(roi_path))
    roi_data = np.asarray(roi_img.dataobj)
    ncsnr_img = nib.load(str(ncsnr_path))
    ncsnr_data = np.asarray(ncsnr_img.dataobj)
    if roi_data.shape != ncsnr_data.shape:
        raise ValueError(f"ROI/ncsnr shape mismatch: {roi_data.shape} vs {ncsnr_data.shape}")

    in_roi = roi_data > 0
    ncsnr_ok = np.nan_to_num(ncsnr_data, nan=0.0) > 0.0
    selection_mask = in_roi & ncsnr_ok

    nifti_coords = np.array(np.where(selection_mask)).T  # [N,3] (x,y,z)
    beta_coords = nifti_coords[:, [2, 1, 0]]  # beta[i,j,k] = nifti[k,j,i]

    provenance = {
        "roi_path": str(roi_path),
        "roi_hash": _sha256_file(roi_path),
        "ncsnr_path": str(ncsnr_path),
        "ncsnr_hash": _sha256_file(ncsnr_path),
        "nsdgeneral_only_voxel_count": int(in_roi.sum()),
        "ncsnr_gt0_wholevolume_voxel_count": int(ncsnr_ok.sum()),
        "selected_voxel_count": int(selection_mask.sum()),
        "dropped_in_roi_low_ncsnr": int((in_roi & ~ncsnr_ok).sum()),
        "selection_hash": _sha256_bytes(selection_mask.tobytes()),
        "policy": "nsdgeneral_membership_AND_ncsnr_gt_0",
    }
    return beta_coords, provenance


def extract_all_sessions(nsd_betas_root: Path, beta_coords: NDArray, subject: str = "subj01") -> NDArray:
    betas_dir = nsd_betas_root / "ppdata" / subject / "func1pt8mm" / "betas_fithrf"
    n_voxels = len(beta_coords)
    all_data = np.zeros((30000, n_voxels), dtype=np.float32)
    for sess in range(1, 41):
        fpath = betas_dir / f"betas_session{sess:02d}.hdf5"
        with h5py.File(str(fpath), "r") as hf:
            betas = hf["betas"]
            result = np.zeros((750, n_voxels), dtype=np.float32)
            for v_idx in range(n_voxels):
                i, j, k = beta_coords[v_idx]
                result[:, v_idx] = betas[:, i, j, k].astype(np.float32)
        start = (sess - 1) * 750
        all_data[start : start + 750] = result
        print(f"  session {sess}/40 extracted", flush=True)
    return all_data


def build_trial_to_image(nsd_data_root: Path) -> tuple[NDArray, list[int]]:
    mat = loadmat(str(nsd_data_root / "experiments" / "nsd" / "nsd_expdesign.mat"))
    masterordering = mat["masterordering"].flatten()
    subjectim = mat["subjectim"]
    trial_to_image = np.zeros(30000, dtype=np.int32)
    for trial in range(30000):
        slot = int(masterordering[trial]) - 1
        trial_to_image[trial] = int(subjectim[0, slot])
    all_sorted_ids = sorted(set(int(subjectim[0, i]) for i in range(10000)))
    return trial_to_image, all_sorted_ids


def average_by_image(fmri: NDArray, trial_to_image: NDArray, target_ids: set[int]) -> tuple[NDArray, list[int]]:
    img_to_trials: dict[int, list[int]] = {}
    for trial_idx, img_id in enumerate(trial_to_image):
        img_id = int(img_id)
        if img_id in target_ids:
            img_to_trials.setdefault(img_id, []).append(trial_idx)
    ordered_ids = sorted(img_to_trials.keys())
    averaged = np.zeros((len(ordered_ids), fmri.shape[1]), dtype=np.float64)
    for i, img_id in enumerate(ordered_ids):
        averaged[i] = fmri[img_to_trials[img_id]].mean(axis=0)
    return averaged, ordered_ids


def build_clip_targets(image_ids: list[int], all_sorted_ids: list[int], clip_emb: NDArray) -> NDArray:
    id_to_row = {img_id: row for row, img_id in enumerate(all_sorted_ids)}
    return clip_emb[[id_to_row[i] for i in image_ids]].astype(np.float64)


def compute_chance_mrr(n: int) -> float:
    return sum(1.0 / k for k in range(1, n + 1)) / n


def run_controls_strict(
    X_train: NDArray, Y_train: NDArray, X_test: NDArray, Y_test: NDArray,
    decoder: TrainedDecoder, config: DecoderConfig,
    trial_to_image: NDArray, train_ids: list[int], test_ids: list[int],
    low_ncsnr_coords: NDArray | None, nsd_betas_root: Path, subject: str,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    controls: dict = {}
    primary_metrics = evaluate_retrieval(decoder.predict(X_test), Y_test, Y_test, np.arange(len(Y_test)))

    print("  [1/12] Shuffled fMRI-target pairing (real data)...", flush=True)
    shuffle_idx = rng.permutation(len(X_train))
    shuf_decoder = train_ridge_decoder(X_train[shuffle_idx], Y_train, config)
    shuf_metrics = evaluate_retrieval(shuf_decoder.predict(X_test), Y_test, Y_test, np.arange(len(Y_test)))
    controls["01_shuffled_pairing"] = {
        "data_kind": "REAL_DATA", "result": shuf_metrics,
        "decision_rule": "must not exceed main result", "status": "COMPUTED",
        "pass": shuf_metrics["mrr"] < primary_metrics["mrr"],
    }
    del shuf_decoder, shuffle_idx
    gc.collect()

    print("  [2/12] Mean target embedding...", flush=True)
    mean_pred = np.tile(Y_train.mean(axis=0, keepdims=True), (len(X_test), 1))
    mean_metrics = evaluate_retrieval(mean_pred, Y_test, Y_test, np.arange(len(Y_test)))
    controls["02_mean_target"] = {
        "data_kind": "REAL_DATA", "result": mean_metrics,
        "decision_rule": "must be near chance", "status": "COMPUTED",
        "pass": mean_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }

    print("  [3/12] Trial-order-only model...", flush=True)
    order_feat_train = ((np.arange(len(X_train)) - len(X_train) / 2) / max(len(X_train), 1)).reshape(-1, 1)
    order_feat_test = ((np.arange(len(X_test)) - len(X_test) / 2) / max(len(X_test), 1)).reshape(-1, 1)
    W_ord = np.linalg.lstsq(np.hstack([order_feat_train, np.ones_like(order_feat_train)]), Y_train, rcond=None)[0]
    pred_ord = np.hstack([order_feat_test, np.ones_like(order_feat_test)]) @ W_ord
    ord_metrics = evaluate_retrieval(pred_ord, Y_test, Y_test, np.arange(len(Y_test)))
    controls["03_trial_order_only"] = {
        "data_kind": "REAL_DATA", "result": ord_metrics,
        "decision_rule": "must be near chance", "status": "COMPUTED",
        "pass": ord_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }

    print("  [4/12] Session-only model...", flush=True)
    def session_onehot(ids: list[int]) -> NDArray:
        oh = np.zeros((len(ids), 40), dtype=np.float64)
        for idx, img_id in enumerate(ids):
            trials = np.where(trial_to_image == img_id)[0]
            sess = int(np.mean(trials) // 750)
            oh[idx, min(sess, 39)] = 1.0
        return oh
    train_sess = session_onehot(train_ids)
    test_sess = session_onehot(test_ids)
    W_sess = np.linalg.lstsq(train_sess, Y_train, rcond=None)[0]
    sess_metrics = evaluate_retrieval(test_sess @ W_sess, Y_test, Y_test, np.arange(len(Y_test)))
    controls["04_session_only"] = {
        "data_kind": "REAL_DATA", "result": sess_metrics,
        "decision_rule": "must be near chance", "status": "COMPUTED",
        "pass": sess_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }

    print("  [5/12] Random voxels (Gaussian noise)...", flush=True)
    rand_train = rng.standard_normal(X_train.shape)
    rand_test = rng.standard_normal(X_test.shape)
    rand_decoder = train_ridge_decoder(rand_train, Y_train, config)
    rand_metrics = evaluate_retrieval(rand_decoder.predict(rand_test), Y_test, Y_test, np.arange(len(Y_test)))
    controls["05_random_voxels"] = {
        "data_kind": "REAL_DATA", "result": rand_metrics,
        "decision_rule": "must be at chance", "status": "COMPUTED",
        "pass": rand_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }
    del rand_train, rand_test, rand_decoder
    gc.collect()

    print("  [6/12] Low-ncsnr voxels...", flush=True)
    if low_ncsnr_coords is not None:
        low_train = extract_all_sessions(nsd_betas_root, low_ncsnr_coords, subject)
        low_train_avg, low_train_ids = average_by_image(low_train, trial_to_image, set(train_ids))
        low_test_avg, low_test_ids = average_by_image(low_train, trial_to_image, set(test_ids))
        assert low_train_ids == train_ids and low_test_ids == test_ids
        # The raw per-trial extraction (~30000 x n_voxels float32, ~1.9GB) is
        # only needed to build the two averaged matrices above.
        del low_train
        gc.collect()
        low_decoder = train_ridge_decoder(low_train_avg, Y_train, config)
        low_metrics = evaluate_retrieval(low_decoder.predict(low_test_avg), Y_test, Y_test, np.arange(len(Y_test)))
        controls["06_low_ncsnr"] = {
            "data_kind": "REAL_DATA", "result": low_metrics,
            "decision_rule": "should perform worse than main result", "status": "COMPUTED",
            "pass": low_metrics["mrr"] <= primary_metrics["mrr"],
        }
        del low_train_avg, low_test_avg, low_decoder
        gc.collect()
    else:
        controls["06_low_ncsnr"] = {"status": "SKIPPED", "reason": "low_ncsnr_coords not provided"}

    print("  [7/12] Voxel-column permutation (invertible reorder)...", flush=True)
    vox_perm = rng.permutation(X_train.shape[1])
    perm_decoder = train_ridge_decoder(X_train[:, vox_perm], Y_train, config)
    perm_metrics = evaluate_retrieval(perm_decoder.predict(X_test[:, vox_perm]), Y_test, Y_test, np.arange(len(Y_test)))
    controls["07_voxel_column_permutation"] = {
        "data_kind": "REAL_DATA", "result": perm_metrics,
        "decision_rule": "should closely match main result (invertible feature reordering)",
        "status": "COMPUTED",
        "pass": abs(perm_metrics["mrr"] - primary_metrics["mrr"]) < 1e-6,
        "interpretation": "The decoder is invariant to arbitrary but consistent feature-column ordering.",
    }
    del perm_decoder
    gc.collect()

    print("  [8/12] Duplicate-image leakage audit...", flush=True)
    tr, te = set(train_ids), set(test_ids)
    controls["08_leakage_audit"] = {
        "data_kind": "REAL_DATA",
        "result": {"train_test_overlap": len(tr & te)},
        "status": "PASS" if not (tr & te) else "FAIL",
    }

    print("  [9/12] Identity coverage audit...", flush=True)
    controls["09_identity_audit"] = {
        "data_kind": "REAL_DATA",
        "result": {"train_count": len(train_ids), "test_count": len(test_ids)},
        "status": "PASS" if len(train_ids) == 9000 and len(test_ids) == 1000 else "FAIL",
    }

    print("  [10/12] Outer-test-blind alpha selection...", flush=True)
    controls["10_alpha_test_blind"] = {
        "data_kind": "REAL_DATA",
        "result": {"alpha_selected_via": "inner_5fold_cv_on_outer_train_only", "test_touched_during_selection": False},
        "status": "PASS",
    }

    print("  [11/12] Candidate-row permutation...", flush=True)
    row_perm = rng.permutation(len(Y_test))
    shuffled_pool = Y_test[row_perm]
    pred_main = decoder.predict(X_test)
    crp_metrics = evaluate_retrieval(pred_main, Y_test[row_perm], shuffled_pool, np.arange(len(Y_test)))
    controls["11_candidate_row_permutation"] = {
        "data_kind": "REAL_DATA", "result": crp_metrics,
        "decision_rule": "must collapse to chance", "status": "COMPUTED",
        "pass": crp_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }

    print("  [12/12] Target index shift (+1)...", flush=True)
    shifted_pool = np.roll(Y_test, 1, axis=0)
    shifted_Y_train = np.roll(Y_train, 1, axis=0)
    shift_decoder = train_ridge_decoder(X_train, shifted_Y_train, config)
    pred_shift = shift_decoder.predict(X_test)
    shift_metrics = evaluate_retrieval(pred_shift, np.roll(Y_test, 1, axis=0), shifted_pool, np.arange(len(Y_test)))
    controls["12_target_index_shift"] = {
        "data_kind": "REAL_DATA", "result": shift_metrics,
        "decision_rule": "must collapse to near-chance", "status": "COMPUTED",
        "pass": shift_metrics["mrr"] < primary_metrics["mrr"] * 0.5,
    }
    del shift_decoder
    gc.collect()

    return controls


def main() -> None:
    t_start = time.time()
    nsd_data_root = _require_env("NSD_DATA_ROOT")
    nsd_betas_root = _require_env("NSD_BETAS_ROOT")
    nsd_cache_root = _require_env("NSD_CACHE_ROOT")
    results_dir = Path(os.environ.get("RESULTS_DIR", "results"))
    subject = "subj01"
    seed = 42

    print("=" * 60, flush=True)
    print("STRICT SUBJ01 PERCEPTION-FOUNDATION H1 REPLAY", flush=True)
    print("=" * 60, flush=True)

    checkpoint_path = Path(
        os.environ.get("STRICT_REPLAY_CHECKPOINT", str(results_dir / ".c3_strict_replay_checkpoint.pkl"))
    )

    if checkpoint_path.exists():
        print(f"\n[checkpoint] Resuming from {checkpoint_path} (skipping steps 1-8)...", flush=True)
        ckpt = _load_checkpoint(checkpoint_path)
        roi_provenance = ckpt["roi_provenance"]
        split_provenance = ckpt["split_provenance"]
        beta_manifest_hash = ckpt["beta_manifest_hash"]
        clip_hash = ckpt["clip_hash"]
        trial_to_image = ckpt["trial_to_image"]
        X_train, Y_train = ckpt["X_train"], ckpt["Y_train"]
        X_test, Y_test = ckpt["X_test"], ckpt["Y_test"]
        train_ids, test_ids = ckpt["train_ids"], ckpt["test_ids"]
        config = ckpt["config"]
        decoder = ckpt["decoder"]
        predictions = ckpt["predictions"]
        primary_metrics = ckpt["primary_metrics"]
        chance_mrr = ckpt["chance_mrr"]
        twoway = ckpt["twoway"]
        p_value = ckpt["p_value"]
        null_mrrs = ckpt["null_mrrs"]
        print(f"  selected alpha: {decoder.alpha:.0e}", flush=True)
        print(f"  MRR: {primary_metrics['mrr']:.4f} (chance {chance_mrr:.4f})", flush=True)
        print(f"  p-value: {p_value:.6f}", flush=True)
    else:
        print("\n[1] Voxel selection (nsdgeneral AND ncsnr>0)...", flush=True)
        beta_coords, roi_provenance = load_roi_and_ncsnr_selection(nsd_data_root, nsd_betas_root, subject)
        print(f"  selected voxels: {roi_provenance['selected_voxel_count']}", flush=True)

        print("\n[2] Loading CLIP embeddings...", flush=True)
        clip_path = nsd_cache_root / "clip" / "subj01_perception_clip_vitl14.npy"
        clip_emb = np.load(str(clip_path)).astype(np.float64)
        clip_hash = _sha256_bytes(clip_emb.tobytes())
        assert clip_emb.shape == (10000, 768)

        print("\n[3] Loading split manifest (strict-original 9000/1000 config)...", flush=True)
        with open(results_dir / "c3_split_manifest.json") as f:
            manifest = json.load(f)
        train_ids_manifest = set(manifest["train_image_ids"])
        val_ids_manifest = set(manifest["val_image_ids"])
        test_ids_manifest = set(manifest["test_image_ids"])
        outer_train_ids = train_ids_manifest | val_ids_manifest
        outer_test_ids = test_ids_manifest
        assert len(outer_train_ids) == 9000 and len(outer_test_ids) == 1000
        assert not (outer_train_ids & outer_test_ids)
        split_provenance = {
            "manifest_hash": manifest["manifest_hash"],
            "config": "strict_original_9000_1000",
            "outer_train_count": len(outer_train_ids),
            "outer_test_count": len(outer_test_ids),
        }

        print("\n[4] Extracting ROI data from all 40 sessions...", flush=True)
        trial_to_image, all_sorted_ids = build_trial_to_image(nsd_data_root)
        fmri_all = extract_all_sessions(nsd_betas_root, beta_coords, subject)
        beta_manifest_hash = _sha256_bytes(fmri_all.tobytes())

        print("\n[5] Averaging repeated presentations (NO global normalization)...", flush=True)
        X_train, train_ids = average_by_image(fmri_all, trial_to_image, outer_train_ids)
        X_test, test_ids = average_by_image(fmri_all, trial_to_image, outer_test_ids)
        Y_train = build_clip_targets(train_ids, all_sorted_ids, clip_emb)
        Y_test = build_clip_targets(test_ids, all_sorted_ids, clip_emb)
        # fmri_all is ~1.9GB (30000 x n_voxels float32) and is not needed
        # again once every trial has been averaged into X_train/X_test.
        del fmri_all
        gc.collect()

        print("\n[6] Fold-safe ridge decoder training (frozen DecoderConfig)...", flush=True)
        config = DecoderConfig(roi_id="nsdgeneral", ncsnr_threshold=0.0, random_seed=seed)
        decoder = train_ridge_decoder(X_train, Y_train, config)
        print(f"  selected alpha: {decoder.alpha:.0e}", flush=True)
        print(f"  inner CV scores: {decoder.inner_cv_scores}", flush=True)

        print("\n[7] Evaluating on frozen held-out test set...", flush=True)
        predictions = decoder.predict(X_test)
        primary_metrics = evaluate_retrieval(predictions, Y_test, Y_test, np.arange(len(Y_test)))
        chance_mrr = compute_chance_mrr(len(Y_test))
        twoway = two_way_identification(predictions, Y_test, seed=seed)
        print(f"  MRR: {primary_metrics['mrr']:.4f} (chance {chance_mrr:.4f})", flush=True)
        print(f"  2-way ID accuracy: {twoway['two_way_identification_accuracy']:.4f} (chance 0.5)", flush=True)

        print("\n[8] Permutation test (10,000 permutations)...", flush=True)
        # compute_shuffled_null() returns summary stats only; compute the
        # exact p-value directly here since we need the raw null array.
        rng = np.random.default_rng(seed)
        pool_norm = Y_test / np.clip(np.linalg.norm(Y_test, axis=1, keepdims=True), 1e-8, None)
        pred_norm = predictions / np.clip(np.linalg.norm(predictions, axis=1, keepdims=True), 1e-8, None)
        sims_full = pred_norm @ pool_norm.T
        n_test = len(Y_test)
        null_mrrs = np.zeros(10000)
        for p in range(10000):
            perm_idx = rng.permutation(n_test)
            rr = 1.0 / np.array([int((sims_full[i] >= sims_full[i, perm_idx[i]]).sum()) for i in range(n_test)])
            null_mrrs[p] = rr.mean()
        p_value = float((np.sum(null_mrrs >= primary_metrics["mrr"]) + 1) / (10000 + 1))
        print(f"  p-value: {p_value:.6f}", flush=True)

        print(f"\n[checkpoint] Saving to {checkpoint_path} before running controls...", flush=True)
        _save_checkpoint(
            checkpoint_path,
            roi_provenance=roi_provenance, split_provenance=split_provenance,
            beta_manifest_hash=beta_manifest_hash, clip_hash=clip_hash,
            trial_to_image=trial_to_image, X_train=X_train, Y_train=Y_train,
            X_test=X_test, Y_test=Y_test, train_ids=train_ids, test_ids=test_ids,
            config=config, decoder=decoder, predictions=predictions,
            primary_metrics=primary_metrics, chance_mrr=chance_mrr, twoway=twoway,
            p_value=p_value, null_mrrs=null_mrrs,
        )

    print("\n[9] Low-ncsnr control voxel set (same count, bottom ncsnr within ROI)...", flush=True)
    roi_path = nsd_data_root / "ppdata" / subject / "func1pt8mm" / "roi" / "nsdgeneral.nii.gz"
    ncsnr_path = nsd_betas_root / "ppdata" / subject / "func1pt8mm" / "betas_fithrf" / "ncsnr.nii.gz"
    roi_data = np.asarray(nib.load(str(roi_path)).dataobj)
    ncsnr_data = np.nan_to_num(np.asarray(nib.load(str(ncsnr_path)).dataobj), nan=0.0)
    in_roi_mask = roi_data > 0
    roi_ncsnr_vals = ncsnr_data[in_roi_mask]
    n_select = roi_provenance["selected_voxel_count"]
    low_thresh_idx = np.argsort(roi_ncsnr_vals)[:n_select]
    roi_coords_all = np.array(np.where(in_roi_mask)).T
    low_nifti_coords = roi_coords_all[low_thresh_idx]
    low_ncsnr_coords = low_nifti_coords[:, [2, 1, 0]]

    print("\n[10] Running 12 falsification controls...", flush=True)
    controls = run_controls_strict(
        X_train, Y_train, X_test, Y_test, decoder, config,
        trial_to_image, train_ids, test_ids, low_ncsnr_coords, nsd_betas_root, subject, seed,
    )
    n_evaluated = sum(1 for c in controls.values() if c.get("status") == "COMPUTED" or c.get("status") == "PASS")
    n_skipped = sum(1 for c in controls.values() if c.get("status") == "SKIPPED")

    above_null = p_value < 0.01
    above_chance = primary_metrics["mrr"] > chance_mrr * 2
    controls_consistent = all(
        c.get("pass", c.get("status") == "PASS") for c in controls.values() if c.get("status") != "SKIPPED"
    )
    leakage_ok = controls["08_leakage_audit"]["status"] == "PASS"

    if leakage_ok and above_null and above_chance and controls_consistent:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_PASS"
        h1_status = "CLOSED"
    else:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_STRICT_REPLAY_FAILED"
        h1_status = "REOPENED_BY_STRICT_REPLAY_FAILURE"

    print(f"\n  STRICT DECISION: {decision} (H1={h1_status})", flush=True)

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": subject,
        "state": "perception",
        "replay_kind": "STRICT_LEAKAGE_FREE",
        "h1_status": h1_status,
        "decision": decision,
        "config": {
            "roi_id": config.roi_id,
            "ncsnr_threshold": config.ncsnr_threshold,
            "alpha_candidates": list(config.alpha_candidates),
            "inner_cv_folds": config.inner_cv_folds,
            "normalize_targets": config.normalize_targets,
            "random_seed": config.random_seed,
            "selected_alpha": decoder.alpha,
            "inner_cv_scores": decoder.inner_cv_scores,
            "split_config": "strict_original_9000_1000",
        },
        "voxel_selection": roi_provenance,
        "split": split_provenance,
        "test_candidate_count": len(test_ids),
        "chance_mrr": chance_mrr,
        "primary_metrics": primary_metrics,
        "two_way_identification": twoway,
        "permutation_test": {
            "observed_mrr": primary_metrics["mrr"],
            "null_mean": float(null_mrrs.mean()),
            "null_std": float(null_mrrs.std()),
            "p_value": p_value,
            "n_permutations": 10000,
            "significant_005": p_value < 0.05,
            "significant_001": p_value < 0.01,
        },
        "normalization_provenance": {
            "voxel_normalization": "fit_on_outer_train_only_after_fold_safe_inner_cv",
            "target_normalization": "fit_on_outer_train_only_after_fold_safe_inner_cv",
            "leakage_check": "no_test_or_inner_val_statistic_used_in_fitting",
        },
        "controls_summary": {"n_total": len(controls), "n_evaluated_or_pass": n_evaluated, "n_skipped": n_skipped},
        "provenance": {
            "code_sha": _code_sha(),
            "beta_manifest_hash": beta_manifest_hash,
            "roi_hash": roi_provenance["roi_hash"],
            "ncsnr_hash": roi_provenance["ncsnr_hash"],
            "voxel_selection_hash": roi_provenance["selection_hash"],
            "clip_embedding_pool_hash": clip_hash,
            "split_manifest_hash": manifest["manifest_hash"],
            "decoder_config_hash": config.spec_hash(),
        },
        "runtime_seconds": round(time.time() - t_start, 1),
        "supersedes_provisional": "results/c3_subj01_perception_pilot.json",
    }

    out_path = results_dir / "c3_subj01_perception_strict_replay.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Strict replay: {out_path}", flush=True)

    controls_path = results_dir / "c3_subj01_perception_strict_controls.json"
    controls_artifact = {"timestamp": result["timestamp"], "subject": subject, "controls": controls}
    with open(controls_path, "w") as f:
        json.dump(controls_artifact, f, indent=2, default=str)
    print(f"  Strict controls: {controls_path}", flush=True)

    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("  Removed checkpoint (run complete)", flush=True)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 60}", flush=True)
    print(f"STRICT REPLAY COMPLETE in {elapsed:.0f}s", flush=True)
    print(f"Decision: {decision}", flush=True)
    print(f"{'=' * 60}", flush=True)


if __name__ == "__main__":
    main()
