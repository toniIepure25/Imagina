"""Download NSD stimulus metadata and compute CLIP embeddings for imagery targets.

Downloads:
- nsd_expdesign.mat (trial->image mapping)
- nsd_stim_info_merged.csv (image metadata) from local cache

Computes:
- CLIP ViT-L/14 embeddings for the 12 NSD-Imagery target images
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

S3_BASE = "https://natural-scenes-dataset.s3.amazonaws.com"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  Already present: {dest.name}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading: {url}")
    try:
        urllib.request.urlretrieve(url, str(dest))
        print(f"  OK: {dest.stat().st_size / 1024:.1f} KB")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def download_stimulus_metadata():
    data_root = Path(os.environ.get("NSD_DATA_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata"))
    exp_dir = data_root / "experiments" / "nsd"
    exp_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "nsd_expdesign.mat": f"{S3_BASE}/nsddata/experiments/nsd/nsd_expdesign.mat",
        "nsd_stim_info_merged.pkl": f"{S3_BASE}/nsddata/experiments/nsd/nsd_stim_info_merged.pkl",
    }

    results = {}
    for fname, url in files.items():
        dest = exp_dir / fname
        ok = download_file(url, dest)
        if ok:
            results[fname] = {
                "path": str(dest),
                "size": dest.stat().st_size,
                "sha256": sha256_file(dest),
                "status": "OK",
            }
        else:
            results[fname] = {"status": "FAILED", "url": url}
    return results


def load_expdesign(mat_path: Path) -> dict:
    """Load NSD experiment design from .mat file."""
    from scipy.io import loadmat

    mat = loadmat(str(mat_path), squeeze_me=True)
    return {
        "masterordering": mat.get("masterordering"),
        "subjectim": mat.get("subjectim"),
        "sharedix": mat.get("sharedix"),
    }


def compute_imagery_target_embeddings():
    """Compute CLIP embeddings for the 12 NSD-Imagery target images."""
    stimuli_root = Path(os.environ.get(
        "NSD_STIMULI_ROOT",
        r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata\experiments\nsdimagery\rawtargetimages"
    ))

    if not stimuli_root.exists():
        return {"status": "STIMULI_NOT_FOUND", "path": str(stimuli_root)}

    # Find target images
    target_images = []
    for set_dir in sorted(stimuli_root.iterdir()):
        if set_dir.is_dir():
            for img_file in sorted(set_dir.iterdir()):
                if img_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
                    target_images.append(img_file)

    if not target_images:
        return {"status": "NO_TARGET_IMAGES_FOUND", "path": str(stimuli_root)}

    print(f"\n  Found {len(target_images)} target images:")
    for img in target_images:
        print(f"    {img.relative_to(stimuli_root)}")

    # Try to load CLIP
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        model_name = "openai/clip-vit-large-patch14"
        print(f"\n  Loading CLIP model: {model_name}")
        processor = CLIPProcessor.from_pretrained(model_name)
        model = CLIPModel.from_pretrained(model_name)
        model.eval()

        from PIL import Image

        embeddings = []
        image_info = []
        for img_path in target_images:
            img = Image.open(img_path).convert("RGB")
            inputs = processor(images=img, return_tensors="pt")
            with torch.no_grad():
                outputs = model.get_image_features(**inputs)
                emb = outputs[0].cpu().numpy()
                emb = emb / np.linalg.norm(emb)  # L2 normalize
            embeddings.append(emb)
            image_info.append({
                "path": str(img_path),
                "filename": img_path.name,
                "set": img_path.parent.name,
                "sha256": sha256_file(img_path),
            })

        embeddings_array = np.stack(embeddings)
        pool_hash = hashlib.sha256(embeddings_array.tobytes()).hexdigest()

        # Save embeddings
        cache_dir = Path(os.environ.get("NSD_CACHE_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\cache"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        emb_path = cache_dir / "imagery_target_clip_embeddings.npy"
        np.save(emb_path, embeddings_array)

        return {
            "status": "OK",
            "model": model_name,
            "n_images": len(target_images),
            "embedding_dim": int(embeddings_array.shape[1]),
            "normalization": "L2",
            "pool_hash": pool_hash,
            "embeddings_path": str(emb_path),
            "images": image_info,
        }

    except ImportError as e:
        return {
            "status": "CLIP_NOT_AVAILABLE",
            "error": str(e),
            "n_target_images_found": len(target_images),
            "images": [{"path": str(p), "filename": p.name, "set": p.parent.name} for p in target_images],
        }


def main():
    print("=" * 60)
    print("NSD Stimulus Metadata & CLIP Embedding Preparation")
    print("=" * 60)

    report = {"date": time.strftime("%Y-%m-%dT%H:%M:%S")}

    print("\n[1/3] Downloading NSD experiment design...")
    report["metadata"] = download_stimulus_metadata()

    print("\n[2/3] Loading experiment design to verify...")
    exp_dir = Path(os.environ.get("NSD_DATA_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata"))
    mat_path = exp_dir / "experiments" / "nsd" / "nsd_expdesign.mat"
    if mat_path.exists():
        try:
            from scipy.io import loadmat
            mat = loadmat(str(mat_path), squeeze_me=True)
            report["expdesign"] = {
                "masterordering_shape": list(mat["masterordering"].shape) if "masterordering" in mat else None,
                "subjectim_shape": list(mat["subjectim"].shape) if "subjectim" in mat else None,
                "sharedix_shape": list(mat["sharedix"].shape) if "sharedix" in mat else None,
                "keys": [k for k in mat.keys() if not k.startswith("__")],
            }
            print(f"  masterordering shape: {report['expdesign']['masterordering_shape']}")
            print(f"  subjectim shape: {report['expdesign']['subjectim_shape']}")
        except ImportError:
            report["expdesign"] = {"status": "SCIPY_NOT_AVAILABLE"}
            print("  scipy not available — skipping mat validation")
    else:
        report["expdesign"] = {"status": "FILE_NOT_FOUND"}

    print("\n[3/3] Computing CLIP embeddings for imagery targets...")
    report["clip_embeddings"] = compute_imagery_target_embeddings()

    out_path = Path("results/c3_stimulus_alignment.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport: {out_path}")


if __name__ == "__main__":
    main()
