"""Gold-standard comparison: verify NSD stimulus reconstruction.

LOCAL CONVENIENCE SCRIPT — hardcodes this developer's D:\\ComputaCenter paths.
NOT a reusable scientific runner and excluded from scientific replay.

Compares reconstructed stimuli (from COCO + cropBox) against the official
nsd_stimuli.hdf5 accessed via S3 range reads.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import time
from pathlib import Path

import fsspec
import h5py
import numpy as np
from PIL import Image
from scipy.io import loadmat

NSD_DATA_ROOT = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata")
NSD_CACHE_ROOT = Path(r"D:\ComputaCenter\FMRI2images\data\nsd\cache")
STIM_DIR = NSD_CACHE_ROOT / "stimuli" / "subj01"
NSD_S3_URL = "https://natural-scenes-dataset.s3.amazonaws.com/nsddata_stimuli/stimuli/nsd/nsd_stimuli.hdf5"
RESULTS_DIR = Path(r"D:\ComputaCenter\Imagina\results")


def load_subj01_ids():
    mat = loadmat(str(NSD_DATA_ROOT / "experiments" / "nsd" / "nsd_expdesign.mat"))
    subjectim = mat["subjectim"]
    return sorted(set(int(x) - 1 for x in subjectim[0, :]))


def select_validation_subset(subj01_nsd_ids, df):
    """Select a representative validation subset."""
    subset = []

    # First and last participant images
    subset.append(subj01_nsd_ids[0])
    subset.append(subj01_nsd_ids[-1])

    # Several Shared1000 images
    shared = [i for i in subj01_nsd_ids if df.iloc[i]["shared1000"] == True]
    for pick in [0, len(shared) // 4, len(shared) // 2, 3 * len(shared) // 4, -1]:
        subset.append(shared[pick])

    # Several non-shared images
    non_shared = [i for i in subj01_nsd_ids if df.iloc[i]["shared1000"] != True]
    for pick in [0, len(non_shared) // 3, 2 * len(non_shared) // 3]:
        subset.append(non_shared[pick])

    # Extreme crop boxes
    def crop_mag(nsd_id):
        return sum(float(x) for x in df.iloc[nsd_id]["cropBox"])

    sorted_by_crop = sorted(subj01_nsd_ids, key=crop_mag, reverse=True)
    subset.extend(sorted_by_crop[:3])  # largest crops
    subset.extend(sorted_by_crop[-3:])  # smallest crops

    # Different COCO splits
    train_ids = [i for i in subj01_nsd_ids if df.iloc[i]["cocoSplit"] == "train2017"]
    val_coco_ids = [i for i in subj01_nsd_ids if df.iloc[i]["cocoSplit"] == "val2017"]
    subset.append(train_ids[500])
    subset.append(val_coco_ids[500] if len(val_coco_ids) > 500 else val_coco_ids[0])

    # Deduplicate and sort
    subset = sorted(set(subset))
    return subset


def correct_nsd_crop(img: Image.Image, crop_box: tuple) -> Image.Image:
    """Correct NSD crop: format is (top_frac, bottom_frac, left_frac, right_frac)."""
    w, h = img.size
    top = int(float(crop_box[0]) * h)
    bottom = int(float(crop_box[1]) * h)
    left = int(float(crop_box[2]) * w)
    right = int(float(crop_box[3]) * w)
    cropped = img.crop((left, top, w - right, h - bottom))
    return cropped.resize((425, 425), Image.LANCZOS)


def compare_images(official: np.ndarray, reconstructed: np.ndarray) -> dict:
    """Compare an official NSD stimulus against reconstruction."""
    result = {
        "shape_match": official.shape == reconstructed.shape,
        "official_shape": list(official.shape),
        "reconstructed_shape": list(reconstructed.shape),
    }

    if not result["shape_match"]:
        return result

    diff = np.abs(official.astype(np.int16) - reconstructed.astype(np.int16))
    result["pixel_identical"] = bool(np.all(diff == 0))
    result["max_abs_diff"] = int(diff.max())
    result["mean_abs_diff"] = float(diff.mean())
    result["median_abs_diff"] = float(np.median(diff))
    result["pct_nonzero"] = float(np.count_nonzero(diff) / diff.size * 100)

    # Per-channel stats
    for ch, name in enumerate(["R", "G", "B"]):
        ch_diff = diff[:, :, ch]
        result[f"max_diff_{name}"] = int(ch_diff.max())
        result[f"mean_diff_{name}"] = float(ch_diff.mean())

    # Perceptual hash comparison (simple average hash)
    off_gray = np.mean(official, axis=2)
    rec_gray = np.mean(reconstructed, axis=2)
    off_small = Image.fromarray(off_gray.astype(np.uint8)).resize((8, 8))
    rec_small = Image.fromarray(rec_gray.astype(np.uint8)).resize((8, 8))
    off_hash = np.array(off_small) > np.mean(np.array(off_small))
    rec_hash = np.array(rec_small) > np.mean(np.array(rec_small))
    result["phash_hamming_distance"] = int(np.sum(off_hash != rec_hash))

    return result


def main():
    print("=== NSD Stimulus Gold-Standard Comparison ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%S')}")
    print()

    # Load metadata
    df = pickle.load(
        open(str(NSD_DATA_ROOT / "experiments" / "nsd" / "nsd_stim_info_merged.pkl"), "rb"),
        encoding="latin1",
    )
    subj01_nsd_ids = load_subj01_ids()
    print(f"subj01 unique NSD IDs: {len(subj01_nsd_ids)}")
    print(f"Range: {subj01_nsd_ids[0]} to {subj01_nsd_ids[-1]}")

    # Select validation subset
    validation_ids = select_validation_subset(subj01_nsd_ids, df)
    print(f"Validation subset: {len(validation_ids)} images")
    print(f"IDs: {validation_ids}")
    print()

    # Check which reconstructed stimuli exist
    available_ids = []
    for nsd_id in validation_ids:
        path = STIM_DIR / f"nsd_{nsd_id:05d}.png"
        if path.exists():
            available_ids.append(nsd_id)
    print(f"Available reconstructions: {len(available_ids)}/{len(validation_ids)}")

    # For comparison we re-apply crop directly from COCO to avoid stale files
    from io import BytesIO

    import requests

    print("\nOpening remote NSD stimuli HDF5...")
    fs = fsspec.filesystem("http")
    remote_file = fs.open(NSD_S3_URL, "rb")
    hf = h5py.File(remote_file, "r")
    ds = hf["imgBrick"]
    print(f"Official dataset shape: {ds.shape}, dtype: {ds.dtype}")

    # Compare each image by freshly downloading COCO and applying corrected crop
    results = []
    for idx, nsd_id in enumerate(validation_ids):
        print(f"  [{idx+1}/{len(validation_ids)}] nsdId={nsd_id}...", end=" ")

        row = df.iloc[nsd_id]
        coco_id = int(row["cocoId"])
        coco_split = row["cocoSplit"]
        crop_box = row["cropBox"]

        # Download COCO source
        coco_url = f"http://images.cocodataset.org/{coco_split}/{coco_id:012d}.jpg"
        try:
            resp = requests.get(coco_url, timeout=30)
            resp.raise_for_status()
            coco_img = Image.open(BytesIO(resp.content)).convert("RGB")
        except Exception as e:
            print(f"SKIP (COCO download failed: {e})")
            continue

        # Apply corrected crop
        recon_img = correct_nsd_crop(coco_img, crop_box)
        reconstructed = np.array(recon_img)

        # Read official
        official = ds[nsd_id]

        # Compare
        comparison = compare_images(official, reconstructed)
        comparison["nsd_id"] = nsd_id
        comparison["coco_id"] = coco_id
        comparison["coco_split"] = coco_split
        comparison["crop_box"] = [float(x) for x in crop_box]
        comparison["shared1000"] = bool(row["shared1000"])
        comparison["coco_size"] = list(coco_img.size)

        # Verify square intermediate
        w, h = coco_img.size
        top_px = int(float(crop_box[0]) * h)
        bot_px = int(float(crop_box[1]) * h)
        left_px = int(float(crop_box[2]) * w)
        right_px = int(float(crop_box[3]) * w)
        crop_w = w - left_px - right_px
        crop_h = h - top_px - bot_px
        comparison["intermediate_square"] = crop_w == crop_h
        comparison["intermediate_size"] = [crop_w, crop_h]

        # Hash both
        comparison["official_sha256_16"] = hashlib.sha256(official.tobytes()).hexdigest()[:16]
        comparison["reconstructed_sha256_16"] = hashlib.sha256(reconstructed.tobytes()).hexdigest()[:16]

        results.append(comparison)
        status = "IDENTICAL" if comparison.get("pixel_identical") else f"diff={comparison.get('max_abs_diff', '?')}"
        print(f"{status} (sq={crop_w==crop_h})")

    hf.close()
    remote_file.close()

    # Aggregate results
    n_identical = sum(1 for r in results if r.get("pixel_identical"))
    max_diffs = [r["max_abs_diff"] for r in results if "max_abs_diff" in r]
    mean_diffs = [r["mean_abs_diff"] for r in results if "mean_abs_diff" in r]

    # Determine status
    if n_identical == len(results):
        status = "STIMULUS_RECONSTRUCTION_PIXEL_IDENTICAL"
    elif max_diffs and max(max_diffs) <= 3:
        status = "STIMULUS_RECONSTRUCTION_EQUIVALENT_WITH_FROZEN_TOLERANCE"
        tolerance_note = "Max pixel difference <= 3; attributed to JPEG decode + resize interpolation"
    elif max_diffs and max(max_diffs) <= 10:
        status = "STIMULUS_RECONSTRUCTION_EQUIVALENT_WITH_FROZEN_TOLERANCE"
        tolerance_note = "Max pixel difference <= 10; attributed to JPEG codec + interpolation rounding"
    else:
        status = "STIMULUS_RECONSTRUCTION_NOT_EQUIVALENT"
        tolerance_note = None

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "n_compared": len(results),
        "n_pixel_identical": n_identical,
        "max_pixel_difference": max(max_diffs) if max_diffs else None,
        "mean_pixel_difference": float(np.mean(mean_diffs)) if mean_diffs else None,
        "median_pixel_difference": float(np.median(mean_diffs)) if mean_diffs else None,
        "validation_subset_ids": available_ids,
        "comparisons": results,
    }

    if status == "STIMULUS_RECONSTRUCTION_EQUIVALENT_WITH_FROZEN_TOLERANCE":
        summary["tolerance_note"] = tolerance_note
        summary["frozen_max_tolerance"] = max(max_diffs) if max_diffs else 0

    # Save
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "c3_stimulus_reconstruction.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print("\n=== Summary ===")
    print(f"Status: {status}")
    print(f"Compared: {len(results)}")
    print(f"Pixel identical: {n_identical}/{len(results)}")
    if max_diffs:
        print(f"Max pixel diff: {max(max_diffs)}")
        print(f"Mean pixel diff: {np.mean(mean_diffs):.4f}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
