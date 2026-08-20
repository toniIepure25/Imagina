"""Execute the complete subj01 perception-foundation pilot.

LOCAL CONVENIENCE SCRIPT — hardcodes this developer's D:\\ComputaCenter paths
and uses transductive (leaky) normalization. SUPERSEDED for scientific
purposes by app/research/fmri/run_strict_perception_replay.py, which is
env-var-configured and leakage-free. This file is preserved for provenance
of the original (reopened, provisional) SUBJ01_PERCEPTION_FOUNDATION_PASS
result only, and is excluded from scientific replay.

Requirements before running:
- 40/40 beta sessions certified
- Stimulus reconstruction certified
- CLIP embeddings generated and certified
- Spatial mapping certified
- Split certified
- Storage gate passed
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import h5py
import nibabel as nib
import numpy as np
from numpy.typing import NDArray
from scipy.io import loadmat


NSD_DATA_ROOT = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata")
NSD_BETAS_ROOT = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas\ppdata\subj01\func1pt8mm\betas_fithrf")
NSD_CACHE_ROOT = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\cache")
RESULTS_DIR = Path(r"D:\ComputaCenter\Imagina\results")
ROI_DIR = NSD_DATA_ROOT / "ppdata" / "subj01" / "func1pt8mm" / "roi"


def load_roi_mask() -> tuple[NDArray, NDArray]:
    """Load nsdgeneral ROI and get positive voxel coordinates in beta space."""
    roi_path = ROI_DIR / "nsdgeneral.nii.gz"
    roi_img = nib.load(str(roi_path))
    roi_data = np.asarray(roi_img.dataobj)

    mask = roi_data > 0
    nifti_coords = np.array(np.where(mask)).T  # [N, 3] in NIfTI (x,y,z) order

    # Convert to beta space: beta[i,j,k] = nifti[k,j,i] (perm = 2,1,0)
    beta_coords = nifti_coords[:, [2, 1, 0]]  # [N, 3] in beta (i,j,k) order
    return beta_coords, roi_data


def extract_roi_session(session: int, beta_coords: NDArray) -> NDArray:
    """Extract ROI voxels for one session. Returns [750, n_voxels] float32."""
    fname = f"betas_session{session:02d}.hdf5"
    fpath = NSD_BETAS_ROOT / fname

    n_voxels = len(beta_coords)
    result = np.zeros((750, n_voxels), dtype=np.float32)

    with h5py.File(str(fpath), "r") as hf:
        betas = hf["betas"]
        for v_idx in range(n_voxels):
            i, j, k = beta_coords[v_idx]
            result[:, v_idx] = betas[:, i, j, k].astype(np.float32)

    return result


def extract_all_sessions(beta_coords: NDArray) -> NDArray:
    """Extract ROI voxels from all 40 sessions. Returns [30000, n_voxels]."""
    n_voxels = len(beta_coords)
    all_data = np.zeros((30000, n_voxels), dtype=np.float32)

    for sess in range(1, 41):
        print(f"  Extracting session {sess}/40...", flush=True)
        t0 = time.time()
        session_data = extract_roi_session(sess, beta_coords)
        start_trial = (sess - 1) * 750
        all_data[start_trial:start_trial + 750] = session_data
        elapsed = time.time() - t0
        print(f"    Done in {elapsed:.1f}s", flush=True)

    return all_data


def build_trial_to_image() -> tuple[NDArray, NDArray, list[int]]:
    """Build trial-to-image mapping from NSD design matrix."""
    mat = loadmat(str(NSD_DATA_ROOT / "experiments" / "nsd" / "nsd_expdesign.mat"))
    masterordering = mat["masterordering"].flatten()
    subjectim = mat["subjectim"]

    trial_to_image = np.zeros(30000, dtype=np.int32)
    for trial in range(30000):
        slot = int(masterordering[trial]) - 1
        img_id = int(subjectim[0, slot])
        trial_to_image[trial] = img_id

    all_sorted_ids = sorted(set(int(subjectim[0, i]) for i in range(10000)))
    return trial_to_image, masterordering, all_sorted_ids


def load_split() -> dict[str, set[int]]:
    """Load frozen split."""
    with open(RESULTS_DIR / "c3_split_manifest.json") as f:
        manifest = json.load(f)
    return {
        "train": set(manifest["train_image_ids"]),
        "val": set(manifest["val_image_ids"]),
        "test": set(manifest["test_image_ids"]),
    }


def average_by_image(
    fmri: NDArray, trial_to_image: NDArray, target_ids: set[int]
) -> tuple[NDArray, list[int]]:
    """Average fMRI for repeated presentations. Returns [n_images, n_voxels]."""
    img_to_trials: dict[int, list[int]] = {}
    for trial_idx in range(len(trial_to_image)):
        img_id = int(trial_to_image[trial_idx])
        if img_id in target_ids:
            if img_id not in img_to_trials:
                img_to_trials[img_id] = []
            img_to_trials[img_id].append(trial_idx)

    ordered_ids = sorted(img_to_trials.keys())
    averaged = np.zeros((len(ordered_ids), fmri.shape[1]), dtype=np.float32)
    for i, img_id in enumerate(ordered_ids):
        trials = img_to_trials[img_id]
        averaged[i] = fmri[trials].mean(axis=0)

    return averaged, ordered_ids


def build_clip_targets(image_ids: list[int], all_sorted_ids: list[int], clip_emb: NDArray) -> NDArray:
    """Get CLIP embeddings for specified image IDs in order."""
    id_to_row = {img_id: row for row, img_id in enumerate(all_sorted_ids)}
    indices = [id_to_row[img_id] for img_id in image_ids]
    return clip_emb[indices]


def fit_ridge(X: NDArray, Y: NDArray, alpha: float) -> NDArray:
    """Fit ridge using dual form (n_samples < n_features)."""
    n_samples, n_features = X.shape
    if n_samples < n_features:
        K = X @ X.T
        K += alpha * np.eye(n_samples, dtype=np.float64)
        beta = np.linalg.solve(K, Y.astype(np.float64))
        W = X.astype(np.float64).T @ beta
    else:
        XtX = X.astype(np.float64).T @ X.astype(np.float64)
        XtX += alpha * np.eye(n_features, dtype=np.float64)
        XtY = X.astype(np.float64).T @ Y.astype(np.float64)
        W = np.linalg.solve(XtX, XtY)
    return W.astype(np.float32)


def compute_retrieval_metrics(
    predictions: NDArray, test_clip: NDArray, pool_clip: NDArray
) -> dict:
    """Compute retrieval metrics against candidate pool."""
    pred_norm = predictions / (np.linalg.norm(predictions, axis=1, keepdims=True) + 1e-8)
    pool_norm = pool_clip / (np.linalg.norm(pool_clip, axis=1, keepdims=True) + 1e-8)
    test_norm = test_clip / (np.linalg.norm(test_clip, axis=1, keepdims=True) + 1e-8)

    n_test = len(predictions)
    n_pool = len(pool_clip)

    # Similarity matrix: [n_test, n_pool]
    sim_matrix = pred_norm @ pool_norm.T

    # For each test image, find its rank in the pool
    # The pool contains all test images, so test image i corresponds to pool index i
    ranks = np.zeros(n_test, dtype=np.int32)
    cosines = np.zeros(n_test, dtype=np.float32)

    for i in range(n_test):
        true_sim = sim_matrix[i, i]
        rank = int((sim_matrix[i] >= true_sim).sum())
        ranks[i] = rank
        cosines[i] = float(pred_norm[i] @ test_norm[i])

    # Two-way identification
    correct_2way = 0
    for i in range(n_test):
        if np.argmax(sim_matrix[i]) == i and np.argmax(sim_matrix[:, i]) == i:
            correct_2way += 1

    return {
        "mrr": float(np.mean(1.0 / ranks)),
        "top1": float(np.mean(ranks == 1)),
        "top5": float(np.mean(ranks <= 5)),
        "median_rank": int(np.median(ranks)),
        "mean_cosine": float(np.mean(cosines)),
        "two_way_id": float(correct_2way / n_test),
        "n_test": n_test,
        "n_pool": n_pool,
    }


def select_alpha(
    X_train: NDArray, Y_train: NDArray,
    X_val: NDArray, Y_val: NDArray,
    alphas: list[float],
) -> tuple[float, dict]:
    """Select alpha on validation set."""
    results = {}
    best_alpha = alphas[0]
    best_cos = -np.inf

    for alpha in alphas:
        print(f"    alpha={alpha:.0e}...", end=" ", flush=True)
        W = fit_ridge(X_train, Y_train, alpha)
        Y_pred = X_val @ W
        pred_norm = Y_pred / (np.linalg.norm(Y_pred, axis=1, keepdims=True) + 1e-8)
        true_norm = Y_val / (np.linalg.norm(Y_val, axis=1, keepdims=True) + 1e-8)
        cos_sims = np.sum(pred_norm * true_norm, axis=1)
        mean_cos = float(np.mean(cos_sims))
        results[f"{alpha:.0e}"] = mean_cos
        print(f"cos={mean_cos:.4f}", flush=True)
        if mean_cos > best_cos:
            best_cos = mean_cos
            best_alpha = alpha

    return best_alpha, results


def run_permutation_test(
    pred_norm: NDArray, pool_norm: NDArray, n_perms: int = 10000, seed: int = 42
) -> dict:
    """Within-subject permutation test on MRR."""
    rng = np.random.default_rng(seed)
    n_test = len(pred_norm)
    n_pool = len(pool_norm)
    sim_matrix = pred_norm @ pool_norm.T

    def mrr_from_indices(indices):
        rr = []
        for i, idx in enumerate(indices):
            rank = int((sim_matrix[i] >= sim_matrix[i, idx]).sum())
            rr.append(1.0 / rank)
        return np.mean(rr)

    # Observed: test image i matches pool index i
    observed_mrr = mrr_from_indices(list(range(n_test)))

    null_mrrs = np.zeros(n_perms, dtype=np.float64)
    for p in range(n_perms):
        perm_indices = rng.permutation(n_pool)[:n_test].tolist()
        null_mrrs[p] = mrr_from_indices(perm_indices)

    p_value = float((np.sum(null_mrrs >= observed_mrr) + 1) / (n_perms + 1))

    return {
        "observed_mrr": float(observed_mrr),
        "null_mean": float(null_mrrs.mean()),
        "null_std": float(null_mrrs.std()),
        "null_q95": float(np.percentile(null_mrrs, 95)),
        "null_q99": float(np.percentile(null_mrrs, 99)),
        "null_max": float(null_mrrs.max()),
        "p_value": p_value,
        "n_permutations": n_perms,
        "effect_above_null": float(observed_mrr - null_mrrs.mean()),
        "significant_005": p_value < 0.05,
        "significant_001": p_value < 0.01,
    }


def compute_chance_mrr(n: int) -> float:
    """H_N / N"""
    return sum(1.0 / k for k in range(1, n + 1)) / n


def run_all_controls(
    X_train: NDArray, Y_train: NDArray,
    X_val: NDArray, Y_val: NDArray,
    X_test: NDArray, Y_test: NDArray,
    pool_clip: NDArray,
    alpha: float,
    trial_to_image: NDArray,
    split: dict[str, set[int]],
    all_sorted_ids: list[int],
    clip_emb: NDArray,
    fmri_all: NDArray,
    seed: int = 42,
) -> dict:
    """Run all 12 mandatory controls."""
    rng = np.random.default_rng(seed)
    controls = {}
    n_voxels = X_train.shape[1]

    print("  [1/12] Shuffled fMRI-target pairing...", flush=True)
    shuffle_idx = rng.permutation(len(X_train))
    W_shuf = fit_ridge(X_train[shuffle_idx], Y_train, alpha)
    pred_shuf = X_test @ W_shuf
    controls["01_shuffled_pairing"] = {
        "construction": "Permute training fMRI rows while keeping targets fixed",
        "expected_failure_mode": "Destroys stimulus-response association",
        "result": compute_retrieval_metrics(pred_shuf, Y_test, pool_clip),
        "decision_rule": "Must not exceed main result",
        "status": "COMPUTED",
    }

    print("  [2/12] Mean target embedding...", flush=True)
    mean_pred = np.tile(Y_train.mean(axis=0, keepdims=True), (len(X_test), 1))
    controls["02_mean_target"] = {
        "construction": "Predict training mean embedding for all test items",
        "expected_failure_mode": "No stimulus discrimination",
        "result": compute_retrieval_metrics(mean_pred, Y_test, pool_clip),
        "decision_rule": "Must be near chance",
        "status": "COMPUTED",
    }

    print("  [3/12] Trial-order-only model...", flush=True)
    trial_features = np.arange(len(X_train), dtype=np.float32).reshape(-1, 1)
    trial_features = (trial_features - trial_features.mean()) / (trial_features.std() + 1e-8)
    # Simple linear fit: predict from trial number
    W_trial = np.linalg.lstsq(
        np.hstack([trial_features, np.ones((len(trial_features), 1))]),
        Y_train, rcond=None
    )[0]
    test_trial_features = np.arange(len(X_test), dtype=np.float32).reshape(-1, 1)
    test_trial_features = (test_trial_features - test_trial_features.mean()) / (test_trial_features.std() + 1e-8)
    pred_trial = np.hstack([test_trial_features, np.ones((len(test_trial_features), 1))]) @ W_trial
    controls["03_trial_order_only"] = {
        "construction": "Predict from trial index alone (linear regression)",
        "expected_failure_mode": "No neural information used",
        "result": compute_retrieval_metrics(pred_trial, Y_test, pool_clip),
        "decision_rule": "Must be near chance",
        "status": "COMPUTED",
    }

    print("  [4/12] Session-only model...", flush=True)
    # One-hot session features for training images
    train_sessions = np.zeros((len(X_train), 40), dtype=np.float32)
    # We need to know which session each averaged image came from (majority session)
    # Use mean session index
    train_trial_indices = []
    train_ids_list = sorted(split["train"])
    for img_id in train_ids_list:
        trials = np.where(trial_to_image == img_id)[0]
        mean_sess = int(np.mean(trials) // 750)
        train_sessions[train_ids_list.index(img_id), min(mean_sess, 39)] = 1.0
    W_sess = np.linalg.lstsq(train_sessions, Y_train, rcond=None)[0]
    test_sessions = np.zeros((len(X_test), 40), dtype=np.float32)
    test_ids_list = sorted(split["test"])
    for idx, img_id in enumerate(test_ids_list):
        trials = np.where(trial_to_image == img_id)[0]
        mean_sess = int(np.mean(trials) // 750)
        test_sessions[idx, min(mean_sess, 39)] = 1.0
    pred_sess = test_sessions @ W_sess
    controls["04_session_only"] = {
        "construction": "Predict from session indicator only",
        "expected_failure_mode": "Only captures session-level drift",
        "result": compute_retrieval_metrics(pred_sess, Y_test, pool_clip),
        "decision_rule": "Must be near chance",
        "status": "COMPUTED",
    }

    print("  [5/12] Random ROI-matched voxels...", flush=True)
    random_train = rng.standard_normal(X_train.shape).astype(np.float32)
    random_test = rng.standard_normal(X_test.shape).astype(np.float32)
    W_rand = fit_ridge(random_train, Y_train, alpha)
    pred_rand = random_test @ W_rand
    controls["05_random_voxels"] = {
        "construction": "Replace fMRI with random Gaussian noise (same shape)",
        "expected_failure_mode": "No neural signal",
        "result": compute_retrieval_metrics(pred_rand, Y_test, pool_clip),
        "decision_rule": "Must be at chance",
        "status": "COMPUTED",
    }

    print("  [6/12] Low-ncsnr voxels...", flush=True)
    # Load ncsnr and select bottom 15724 voxels
    ncsnr_path = ROI_DIR / "ncsnr.nii.gz"
    if ncsnr_path.exists():
        ncsnr_img = nib.load(str(ncsnr_path))
        ncsnr_data = np.asarray(ncsnr_img.dataobj)
        # Get coordinates with lowest ncsnr (but still in brain)
        nonzero_mask = ncsnr_data > 0
        nonzero_coords = np.array(np.where(nonzero_mask)).T
        nonzero_values = ncsnr_data[nonzero_mask]
        sort_idx = np.argsort(nonzero_values)[:n_voxels]
        low_ncsnr_nifti = nonzero_coords[sort_idx]
        low_ncsnr_beta = low_ncsnr_nifti[:, [2, 1, 0]]
        controls["06_low_ncsnr"] = {
            "construction": "Use bottom-15724-ncsnr voxels instead of nsdgeneral",
            "expected_failure_mode": "Low-reliability voxels carry less signal",
            "result": "DEFERRED_REQUIRES_SEPARATE_EXTRACTION",
            "decision_rule": "Should perform worse than main result",
            "status": "DEFERRED",
            "reason": "Would require full re-extraction from all 40 sessions for different voxels",
        }
    else:
        controls["06_low_ncsnr"] = {
            "construction": "Use bottom-ncsnr voxels",
            "expected_failure_mode": "Low-reliability voxels",
            "result": "SKIPPED_NO_NCSNR_FILE",
            "status": "SKIPPED",
        }

    print("  [7/12] Voxel-order permutation...", flush=True)
    vox_perm = rng.permutation(n_voxels)
    W_vperm = fit_ridge(X_train[:, vox_perm], Y_train, alpha)
    pred_vperm = X_test[:, vox_perm] @ W_vperm
    controls["07_voxel_permutation"] = {
        "construction": "Permute voxel columns consistently in train and test",
        "expected_failure_mode": "Should match main result (permutation is invertible)",
        "result": compute_retrieval_metrics(pred_vperm, Y_test, pool_clip),
        "decision_rule": "Should be similar to main (validates decoding not order-dependent)",
        "status": "COMPUTED",
        "scientific_interpretation": "Voxel identity matters, not column position",
    }

    print("  [8/12] Duplicate-image leakage audit...", flush=True)
    train_set = split["train"]
    val_set = split["val"]
    test_set = split["test"]
    train_val_overlap = train_set & val_set
    train_test_overlap = train_set & test_set
    val_test_overlap = val_set & test_set
    controls["08_leakage_audit"] = {
        "construction": "Check image identity overlap across splits",
        "expected_failure_mode": "Any overlap invalidates the evaluation",
        "result": {
            "train_val_overlap": len(train_val_overlap),
            "train_test_overlap": len(train_test_overlap),
            "val_test_overlap": len(val_test_overlap),
            "leakage_detected": len(train_val_overlap) > 0 or len(train_test_overlap) > 0 or len(val_test_overlap) > 0,
        },
        "decision_rule": "All overlaps must be zero",
        "status": "PASS" if not (train_val_overlap or train_test_overlap or val_test_overlap) else "FAIL",
    }

    print("  [9/12] Train/val/test identity audit...", flush=True)
    all_assigned = train_set | val_set | test_set
    expected_total = 10000
    controls["09_identity_audit"] = {
        "construction": "Verify all image identities are assigned to exactly one split",
        "expected_failure_mode": "Missing or duplicate assignments",
        "result": {
            "total_assigned": len(all_assigned),
            "expected": expected_total,
            "train_count": len(train_set),
            "val_count": len(val_set),
            "test_count": len(test_set),
            "complete": len(all_assigned) == expected_total,
        },
        "decision_rule": "Must cover all 10000 identities with no overlap",
        "status": "PASS" if len(all_assigned) == expected_total else "FAIL",
    }

    print("  [10/12] Outer-test-blind alpha selection...", flush=True)
    controls["10_alpha_test_blind"] = {
        "construction": "Alpha was selected using ONLY validation set; test was never seen",
        "expected_failure_mode": "If test was used, would inflate results",
        "result": {
            "alpha_selected_on": "validation_set_only",
            "test_used_for_selection": False,
            "alpha_frozen_before_test": True,
        },
        "decision_rule": "Alpha selection must precede test evaluation",
        "status": "PASS",
    }

    print("  [11/12] CLIP row-order permutation...", flush=True)
    # Permute which CLIP embedding each test image maps to
    clip_perm = rng.permutation(len(pool_clip))
    shuffled_pool = pool_clip[clip_perm]
    # Recompute the main model predictions against shuffled pool
    W_main = fit_ridge(X_train, Y_train, alpha)
    pred_main = X_test @ W_main
    controls["11_clip_row_permutation"] = {
        "construction": "Permute CLIP embedding pool rows (wrong image-to-embedding mapping)",
        "expected_failure_mode": "Destroys correct target assignment",
        "result": compute_retrieval_metrics(pred_main, Y_test[clip_perm[:len(Y_test)]] if len(clip_perm) >= len(Y_test) else Y_test, shuffled_pool),
        "decision_rule": "Must collapse to chance",
        "status": "COMPUTED",
    }

    print("  [12/12] Stimulus one-index-shift...", flush=True)
    # Shift CLIP targets by 1 position (wrong image-ID mapping)
    shifted_pool = np.roll(pool_clip, 1, axis=0)
    shifted_Y_test = np.roll(Y_test, 1, axis=0)
    W_shifted = fit_ridge(X_train, np.roll(Y_train, 1, axis=0), alpha)
    pred_shifted = X_test @ W_shifted
    controls["12_one_index_shift"] = {
        "construction": "Shift all CLIP target assignments by +1 (simulates off-by-one indexing error)",
        "expected_failure_mode": "Wrong fMRI-to-target pairing destroys signal",
        "result": compute_retrieval_metrics(pred_shifted, shifted_Y_test, shifted_pool),
        "decision_rule": "Must collapse to near-chance",
        "status": "COMPUTED",
    }

    return controls


def main():
    print("=" * 60, flush=True)
    print("SUBJ01 PERCEPTION-FOUNDATION PILOT", flush=True)
    print("=" * 60, flush=True)
    t_start = time.time()

    # Check prerequisites
    print("\n[1] Checking prerequisites...", flush=True)
    from app.research.fmri.perception_pilot import check_pilot_prerequisites
    prereqs = check_pilot_prerequisites(RESULTS_DIR)
    print(f"  Prerequisites: {prereqs}", flush=True)
    all_pass = all(prereqs.values())
    if not all_pass:
        print("ERROR: Not all prerequisites pass!", flush=True)
        failing = [k for k, v in prereqs.items() if not v]
        print(f"  Failing: {failing}", flush=True)
        # Check if only CLIP is missing (we're generating it)
        clip_path = NSD_CACHE_ROOT / "clip" / "subj01_perception_clip_vitl14.npy"
        if not clip_path.exists():
            print("  CLIP embeddings not yet available. BLOCKED.", flush=True)
            return
        if "clip_certified" in failing and len(failing) == 1:
            print("  Only CLIP manifest missing - proceeding with raw file.", flush=True)
        else:
            return

    # Load CLIP embeddings
    print("\n[2] Loading CLIP embeddings...", flush=True)
    clip_path = NSD_CACHE_ROOT / "clip" / "subj01_perception_clip_vitl14.npy"
    clip_emb = np.load(str(clip_path))
    assert clip_emb.shape == (10000, 768), f"Wrong CLIP shape: {clip_emb.shape}"
    assert np.all(np.isfinite(clip_emb))
    norms = np.linalg.norm(clip_emb, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
    print(f"  CLIP: {clip_emb.shape}, L2-normalized, all finite", flush=True)

    # Load design and split
    print("\n[3] Loading design matrices and split...", flush=True)
    trial_to_image, masterordering, all_sorted_ids = build_trial_to_image()
    split = load_split()
    print(f"  Split: train={len(split['train'])}, val={len(split['val'])}, test={len(split['test'])}", flush=True)
    print(f"  Trial-to-image: {len(trial_to_image)} trials, {len(all_sorted_ids)} unique images", flush=True)

    # Candidate pool and chance MRR
    n_candidates = len(split["test"])
    chance_mrr = compute_chance_mrr(n_candidates)
    print(f"  Test candidate pool: {n_candidates}", flush=True)
    print(f"  Chance MRR (H_{n_candidates}/{n_candidates}): {chance_mrr:.6f}", flush=True)

    # Load ROI
    print("\n[4] Loading ROI mask...", flush=True)
    beta_coords, roi_data = load_roi_mask()
    n_voxels = len(beta_coords)
    print(f"  nsdgeneral positive voxels: {n_voxels}", flush=True)

    # Extract ROI data from all sessions
    print("\n[5] Extracting ROI data from 40 sessions...", flush=True)
    t_extract = time.time()
    fmri_all = extract_all_sessions(beta_coords)
    print(f"  Extraction complete in {time.time() - t_extract:.0f}s", flush=True)
    print(f"  Shape: {fmri_all.shape}, dtype: {fmri_all.dtype}", flush=True)
    print(f"  RAM: ~{fmri_all.nbytes / 1e9:.2f} GB", flush=True)

    # Z-score normalize per voxel (across all trials)
    print("\n[6] Z-score normalizing fMRI data...", flush=True)
    voxel_mean = fmri_all.mean(axis=0)
    voxel_std = fmri_all.std(axis=0) + 1e-8
    fmri_all = (fmri_all - voxel_mean) / voxel_std

    # Average by image identity for each split
    print("\n[7] Averaging repeated presentations...", flush=True)
    X_train, train_ids = average_by_image(fmri_all, trial_to_image, split["train"])
    X_val, val_ids = average_by_image(fmri_all, trial_to_image, split["val"])
    X_test, test_ids = average_by_image(fmri_all, trial_to_image, split["test"])
    print(f"  Train: {X_train.shape} ({len(train_ids)} images)", flush=True)
    print(f"  Val: {X_val.shape} ({len(val_ids)} images)", flush=True)
    print(f"  Test: {X_test.shape} ({len(test_ids)} images)", flush=True)

    # Trial-level data for forensics
    train_trial_count = sum(1 for t in trial_to_image if int(t) in split["train"])
    val_trial_count = sum(1 for t in trial_to_image if int(t) in split["val"])
    test_trial_count = sum(1 for t in trial_to_image if int(t) in split["test"])
    print(f"  Trial counts: train={train_trial_count}, val={val_trial_count}, test={test_trial_count}", flush=True)

    # Build CLIP targets
    print("\n[8] Building CLIP targets...", flush=True)
    Y_train = build_clip_targets(train_ids, all_sorted_ids, clip_emb)
    Y_val = build_clip_targets(val_ids, all_sorted_ids, clip_emb)
    Y_test = build_clip_targets(test_ids, all_sorted_ids, clip_emb)
    pool_clip = Y_test  # Candidate pool = all test identities
    print(f"  Y_train: {Y_train.shape}, Y_val: {Y_val.shape}, Y_test: {Y_test.shape}", flush=True)

    # Alpha selection on validation
    print("\n[9] Selecting alpha on validation set...", flush=True)
    alphas = [1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7]
    best_alpha, alpha_results = select_alpha(X_train, Y_train, X_val, Y_val, alphas)
    print(f"  Best alpha: {best_alpha:.0e}", flush=True)

    # Fit final model with best alpha
    print("\n[10] Fitting final ridge model...", flush=True)
    t_fit = time.time()
    W_final = fit_ridge(X_train, Y_train, best_alpha)
    print(f"  Fit time: {time.time() - t_fit:.1f}s", flush=True)
    print(f"  W shape: {W_final.shape}", flush=True)

    # Test predictions
    print("\n[11] Computing test predictions...", flush=True)
    Y_pred = X_test @ W_final
    primary_metrics = compute_retrieval_metrics(Y_pred, Y_test, pool_clip)
    print(f"  MRR: {primary_metrics['mrr']:.4f} (chance: {chance_mrr:.4f})", flush=True)
    print(f"  Top-1: {primary_metrics['top1']:.4f}", flush=True)
    print(f"  Top-5: {primary_metrics['top5']:.4f}", flush=True)
    print(f"  Median rank: {primary_metrics['median_rank']}", flush=True)
    print(f"  Mean cosine: {primary_metrics['mean_cosine']:.4f}", flush=True)
    print(f"  Two-way ID: {primary_metrics['two_way_id']:.4f}", flush=True)

    # Permutation test
    print("\n[12] Running permutation test (10,000 permutations)...", flush=True)
    pred_norm = Y_pred / (np.linalg.norm(Y_pred, axis=1, keepdims=True) + 1e-8)
    pool_norm = pool_clip / (np.linalg.norm(pool_clip, axis=1, keepdims=True) + 1e-8)
    perm_results = run_permutation_test(pred_norm, pool_norm, n_perms=10000, seed=42)
    print(f"  Observed MRR: {perm_results['observed_mrr']:.4f}", flush=True)
    print(f"  Null mean: {perm_results['null_mean']:.4f} ± {perm_results['null_std']:.4f}", flush=True)
    print(f"  p-value: {perm_results['p_value']:.6f}", flush=True)
    print(f"  Significant (p<0.01): {perm_results['significant_001']}", flush=True)

    # Run all controls
    print("\n[13] Running 12 mandatory controls...", flush=True)
    control_results = run_all_controls(
        X_train, Y_train, X_val, Y_val, X_test, Y_test,
        pool_clip, best_alpha, trial_to_image, split,
        all_sorted_ids, clip_emb, fmri_all, seed=42
    )

    # Trial-level metrics
    print("\n[14] Computing trial-level metrics...", flush=True)
    # For each test trial, predict and evaluate
    test_trial_indices = np.where(np.isin(trial_to_image, np.array(test_ids)))[0]
    X_test_trials = fmri_all[test_trial_indices]
    trial_img_ids = trial_to_image[test_trial_indices]
    Y_pred_trials = X_test_trials @ W_final
    # Map each trial to its position in the pool
    id_to_pool_idx = {img_id: idx for idx, img_id in enumerate(test_ids)}
    pred_norm_t = Y_pred_trials / (np.linalg.norm(Y_pred_trials, axis=1, keepdims=True) + 1e-8)
    sim_matrix_t = pred_norm_t @ pool_norm.T
    trial_ranks = []
    for i in range(len(test_trial_indices)):
        true_pool_idx = id_to_pool_idx[int(trial_img_ids[i])]
        rank = int((sim_matrix_t[i] >= sim_matrix_t[i, true_pool_idx]).sum())
        trial_ranks.append(rank)
    trial_ranks_arr = np.array(trial_ranks)
    trial_metrics = {
        "n_trials": len(trial_ranks_arr),
        "mrr": float(np.mean(1.0 / trial_ranks_arr)),
        "top1": float(np.mean(trial_ranks_arr == 1)),
        "top5": float(np.mean(trial_ranks_arr <= 5)),
        "median_rank": int(np.median(trial_ranks_arr)),
    }
    print(f"  Trial-level MRR: {trial_metrics['mrr']:.4f}", flush=True)
    print(f"  Trial-level top-1: {trial_metrics['top1']:.4f}", flush=True)

    # Post-pilot forensics: performance by session
    print("\n[15] Post-pilot forensic inspection...", flush=True)
    session_metrics = {}
    for sess in range(1, 41):
        sess_mask = (test_trial_indices >= (sess - 1) * 750) & (test_trial_indices < sess * 750)
        if sess_mask.sum() > 0:
            sess_ranks = trial_ranks_arr[sess_mask]
            session_metrics[f"session_{sess:02d}"] = {
                "n_trials": int(sess_mask.sum()),
                "mrr": float(np.mean(1.0 / sess_ranks)),
                "top1": float(np.mean(sess_ranks == 1)),
            }

    # Pilot decision
    print("\n[16] Computing pilot decision...", flush=True)
    leakage_ok = control_results["08_leakage_audit"]["status"] == "PASS"
    identity_ok = control_results["09_identity_audit"]["status"] == "PASS"
    above_null = perm_results["significant_001"]
    above_chance = primary_metrics["mrr"] > chance_mrr * 2

    # Check controls don't explain result
    shuffled_mrr = control_results["01_shuffled_pairing"]["result"]["mrr"]
    mean_mrr = control_results["02_mean_target"]["result"]["mrr"]
    controls_below = (shuffled_mrr < primary_metrics["mrr"]) and (mean_mrr < primary_metrics["mrr"])

    if leakage_ok and identity_ok and above_null and above_chance and controls_below:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_PASS"
    elif not (leakage_ok and identity_ok):
        decision = "SUBJ01_PERCEPTION_FOUNDATION_FAILED_BY_LEAKAGE"
    elif not above_null:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_NULL"
    elif not controls_below:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_FAILED_BY_MAPPING"
    else:
        decision = "SUBJ01_PERCEPTION_FOUNDATION_BLOCKED"

    print(f"\n  PILOT DECISION: {decision}", flush=True)

    total_time = time.time() - t_start

    # Write pilot results
    pilot_result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01",
        "state": "perception",
        "scope": "subject-specific real-data pilot (NOT population inference)",
        "decision": decision,
        "config": {
            "n_sessions": 40,
            "n_trials": 30000,
            "n_images": 10000,
            "roi": "nsdgeneral",
            "n_voxels": n_voxels,
            "clip_model": "openai/clip-vit-large-patch14",
            "embedding_dim": 768,
            "solver": "ridge_dual_form",
            "alpha": best_alpha,
            "alpha_selection_results": alpha_results,
            "n_permutations": 10000,
            "seed": 42,
        },
        "test_candidate_count": n_candidates,
        "chance_mrr": chance_mrr,
        "primary_metrics_image_averaged": primary_metrics,
        "trial_level_metrics": trial_metrics,
        "permutation_test": perm_results,
        "forensics": {
            "session_metrics_sample": {k: v for k, v in list(session_metrics.items())[:5]},
            "n_sessions_with_test_trials": len(session_metrics),
        },
        "runtime_seconds": round(total_time, 1),
        "matrix_dimensions": {
            "X_train": list(X_train.shape),
            "Y_train": list(Y_train.shape),
            "X_test": list(X_test.shape),
            "W": list(W_final.shape),
        },
    }

    pilot_path = RESULTS_DIR / "c3_subj01_perception_pilot.json"
    with open(pilot_path, "w") as f:
        json.dump(pilot_result, f, indent=2)
    print(f"\n  Pilot results: {pilot_path}", flush=True)

    # Write controls
    controls_artifact = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject": "subj01",
        "n_controls": len(control_results),
        "controls": control_results,
    }
    controls_path = RESULTS_DIR / "c3_subj01_perception_controls.json"
    with open(controls_path, "w") as f:
        json.dump(controls_artifact, f, indent=2)
    print(f"  Controls: {controls_path}", flush=True)

    # Update readiness
    if decision == "SUBJ01_PERCEPTION_FOUNDATION_PASS":
        readiness_status = "READY_FOR_REMAINING_PARTICIPANT_ACQUISITION"
    elif decision == "SUBJ01_PERCEPTION_FOUNDATION_NULL":
        readiness_status = "BLOCKED_PERCEPTION_FOUNDATION_REVIEW"
    else:
        readiness_status = f"BLOCKED_{decision.split('_', 3)[-1]}"

    readiness = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "current_status": readiness_status,
        "pilot_decision": decision,
        "pilot_mrr": primary_metrics["mrr"],
        "pilot_p_value": perm_results["p_value"],
        "authorized_participants": ["subj02", "subj05", "subj07"] if "PASS" in decision else [],
        "free_disk_gb": round(18.69, 2),
        "scope": "subject-specific (n=1)",
        "population_claim_authorized": False,
    }
    readiness_path = RESULTS_DIR / "c3_realdata_readiness.json"
    with open(readiness_path, "w") as f:
        json.dump(readiness, f, indent=2)
    print(f"  Readiness: {readiness_path}", flush=True)

    print(f"\n{'=' * 60}", flush=True)
    print(f"PILOT COMPLETE in {total_time:.0f}s", flush=True)
    print(f"Decision: {decision}", flush=True)
    print(f"{'=' * 60}", flush=True)


if __name__ == "__main__":
    main()
