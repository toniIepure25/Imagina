"""Download and reconstruct NSD stimuli from COCO images.

NSD stimuli are center-cropped COCO images. This module downloads only
the 10,000 images needed for subj01 and applies the NSD crop transformation
to reconstruct the exact stimuli presented during the experiment.

Requires: NSD_CACHE_ROOT and NSD_DATA_ROOT environment variables.
The full 37 GB nsd_stimuli.hdf5 is NOT required.
"""
from __future__ import annotations

import hashlib
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image

NSD_PRESENTATION_SIZE = 425


def get_coco_url(coco_id: int, coco_split: str) -> str:
    return f"http://images.cocodataset.org/{coco_split}/{coco_id:012d}.jpg"


def apply_nsd_crop(img: Image.Image, crop_box: tuple) -> Image.Image:
    """Apply NSD crop box to a COCO image.

    crop_box format: (top_frac, left_frac, bottom_frac, right_frac)
    representing the fraction to remove from each side.
    """
    w, h = img.size
    top = int(float(crop_box[0]) * h)
    left = int(float(crop_box[1]) * w)
    bottom = int(float(crop_box[2]) * h)
    right = int(float(crop_box[3]) * w)

    cropped = img.crop((left, top, w - right, h - bottom))
    return cropped.resize((NSD_PRESENTATION_SIZE, NSD_PRESENTATION_SIZE), Image.LANCZOS)


def download_subj01_stimuli(
    stim_info_df,
    subj01_nsd_ids: list[int],
    output_dir: Path,
    max_retries: int = 3,
    timeout: int = 30,
) -> dict[str, Any]:
    """Download and crop COCO images for subj01's 10,000 stimuli."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {"downloaded": 0, "skipped": 0, "failed": 0, "errors": []}

    for idx, nsd_id in enumerate(subj01_nsd_ids):
        out_path = output_dir / f"nsd_{nsd_id:05d}.png"
        if out_path.exists():
            results["skipped"] += 1
            continue

        row = stim_info_df.iloc[nsd_id]
        coco_id = int(row["cocoId"])
        coco_split = row["cocoSplit"]
        crop_box = row["cropBox"]
        url = get_coco_url(coco_id, coco_split)

        for attempt in range(max_retries):
            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                stimulus = apply_nsd_crop(img, crop_box)
                stimulus.save(out_path, format="PNG")
                results["downloaded"] += 1
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    results["failed"] += 1
                    results["errors"].append({"nsd_id": nsd_id, "error": str(e)})

        if (idx + 1) % 500 == 0:
            total = results["downloaded"] + results["skipped"]
            print(f"  Progress: {total}/{len(subj01_nsd_ids)} ({total*100//len(subj01_nsd_ids)}%)")

    return results


def verify_stimulus_set(output_dir: Path, expected_count: int = 10000) -> dict[str, Any]:
    """Verify the reconstructed stimulus set."""
    files = sorted(output_dir.glob("nsd_*.png"))
    n_files = len(files)

    if n_files == 0:
        return {"status": "EMPTY", "count": 0}

    sample_sizes = set()
    for f in files[:10]:
        img = Image.open(f)
        sample_sizes.add(img.size)

    all_correct_size = len(sample_sizes) == 1 and (NSD_PRESENTATION_SIZE, NSD_PRESENTATION_SIZE) in sample_sizes

    content_hash = hashlib.sha256()
    for f in files:
        content_hash.update(f.name.encode())
        content_hash.update(str(f.stat().st_size).encode())

    return {
        "status": "COMPLETE" if n_files >= expected_count else "PARTIAL",
        "count": n_files,
        "expected": expected_count,
        "all_correct_size": all_correct_size,
        "sample_size": list(sample_sizes),
        "set_hash": content_hash.hexdigest()[:32],
    }


def main():
    import pickle

    from scipy.io import loadmat

    data_root = os.environ.get("NSD_DATA_ROOT")
    cache_root = os.environ.get("NSD_CACHE_ROOT")
    if not data_root or not cache_root:
        print("ERROR: NSD_DATA_ROOT and NSD_CACHE_ROOT must be set")
        return

    mat = loadmat(str(Path(data_root) / "experiments" / "nsd" / "nsd_expdesign.mat"))
    subjectim = mat["subjectim"]
    subj01_nsd_ids = sorted(set(int(subjectim[0, i]) - 1 for i in range(10000)))

    pkl_path = Path(data_root) / "experiments" / "nsd" / "nsd_stim_info_merged.pkl"
    with open(pkl_path, "rb") as f:
        df = pickle.load(f, encoding="latin1")

    output_dir = Path(cache_root) / "stimuli" / "subj01"
    print(f"Downloading {len(subj01_nsd_ids)} stimuli to: {output_dir}")

    results = download_subj01_stimuli(df, subj01_nsd_ids, output_dir)
    print(f"\nResults: {results['downloaded']} downloaded, {results['skipped']} skipped, {results['failed']} failed")

    verification = verify_stimulus_set(output_dir)
    print(f"Verification: {verification['status']} ({verification['count']}/{verification['expected']})")


if __name__ == "__main__":
    main()
