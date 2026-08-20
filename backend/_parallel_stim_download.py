"""Parallel NSD stimulus downloader using corrected v2 crop.

LOCAL CONVENIENCE SCRIPT — hardcodes this developer's D:\\ComputaCenter paths.
NOT a reusable scientific runner and excluded from scientific replay.
"""
from __future__ import annotations

import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from scipy.io import loadmat

NSD_PRESENTATION_SIZE = 425
N_WORKERS = 8


def apply_nsd_crop(img: Image.Image, crop_box: tuple) -> Image.Image:
    w, h = img.size
    sq = min(w, h)
    if w > h:
        x_start = round(float(crop_box[2]) * w)
        x_start = min(x_start, w - sq)
        cropped = img.crop((x_start, 0, x_start + sq, h))
    elif h > w:
        y_start = round(float(crop_box[0]) * h)
        y_start = min(y_start, h - sq)
        cropped = img.crop((0, y_start, w, y_start + sq))
    else:
        cropped = img
    return cropped.resize((NSD_PRESENTATION_SIZE, NSD_PRESENTATION_SIZE), Image.LANCZOS)


def download_one(nsd_id: int, row, output_dir: Path) -> tuple[int, bool, str]:
    out_path = output_dir / f"nsd_{nsd_id:05d}.png"
    if out_path.exists():
        return nsd_id, True, "skip"

    coco_id = int(row["cocoId"])
    coco_split = row["cocoSplit"]
    crop_box = row["cropBox"]
    url = f"http://images.cocodataset.org/{coco_split}/{coco_id:012d}.jpg"

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            stimulus = apply_nsd_crop(img, crop_box)
            stimulus.save(out_path, format="PNG")
            return nsd_id, True, "ok"
        except Exception as e:
            if attempt == 2:
                return nsd_id, False, str(e)
            time.sleep(1)
    return nsd_id, False, "max retries"


def main():
    data_root = Path(os.environ.get("NSD_DATA_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata"))
    cache_root = Path(os.environ.get("NSD_CACHE_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\cache"))

    mat = loadmat(str(data_root / "experiments" / "nsd" / "nsd_expdesign.mat"))
    subjectim = mat["subjectim"]
    subj01_nsd_ids = sorted(set(int(subjectim[0, i]) - 1 for i in range(10000)))

    pkl_path = data_root / "experiments" / "nsd" / "nsd_stim_info_merged.pkl"
    with open(pkl_path, "rb") as f:
        df = pickle.load(f, encoding="latin1")

    output_dir = cache_root / "stimuli" / "subj01"
    output_dir.mkdir(parents=True, exist_ok=True)

    existing = len(list(output_dir.glob("nsd_*.png")))
    print(f"Starting parallel download: {existing}/{len(subj01_nsd_ids)} already present")
    print(f"Workers: {N_WORKERS}")

    tasks = [(nsd_id, df.iloc[nsd_id]) for nsd_id in subj01_nsd_ids]
    downloaded = 0
    failed = 0
    skipped = 0

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
        futures = {
            executor.submit(download_one, nsd_id, row, output_dir): nsd_id
            for nsd_id, row in tasks
        }
        for i, future in enumerate(as_completed(futures)):
            nsd_id, success, msg = future.result()
            if msg == "skip":
                skipped += 1
            elif success:
                downloaded += 1
            else:
                failed += 1

            total_done = skipped + downloaded + failed
            if total_done % 200 == 0:
                elapsed = time.time() - start_time
                rate = (downloaded + skipped) / elapsed if elapsed > 0 else 0
                print(f"  Progress: {total_done}/10000 (dl={downloaded} skip={skipped} fail={failed}) {rate:.1f}/s")

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed:.0f}s: downloaded={downloaded}, skipped={skipped}, failed={failed}")
    total_files = len(list(output_dir.glob("nsd_*.png")))
    print(f"Total files: {total_files}/10000")


if __name__ == "__main__":
    main()
