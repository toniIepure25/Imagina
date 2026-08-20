"""Generate frozen CLIP embeddings for all 10,000 subj01 perception stimuli.

LOCAL CONVENIENCE SCRIPT (CPU path) — defaults to this developer's
D:\\ComputaCenter paths (overridable via NSD_CACHE_ROOT/NSD_DATA_ROOT, but not
required to run). NOT a reusable scientific runner and excluded from
scientific replay. See _generate_clip_embeddings_gpu.py for the GPU variant
actually used to produce the certified embeddings.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from scipy.io import loadmat
from transformers import CLIPModel, CLIPProcessor


def main():
    cache_root = Path(os.environ.get(
        "NSD_CACHE_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\cache"
    ))
    data_root = Path(os.environ.get(
        "NSD_DATA_ROOT", r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata"
    ))
    results_dir = Path(r"D:\ComputaCenter\Imagina\results")

    stim_dir = cache_root / "stimuli" / "subj01"
    clip_dir = cache_root / "clip"
    clip_dir.mkdir(parents=True, exist_ok=True)
    output_path = clip_dir / "subj01_perception_clip_vitl14.npy"

    mat = loadmat(str(data_root / "experiments" / "nsd" / "nsd_expdesign.mat"))
    subjectim = mat["subjectim"]
    sorted_nsd_ids = sorted(set(int(subjectim[0, i]) - 1 for i in range(10000)))
    print(f"Participant image IDs: {len(sorted_nsd_ids)} (range {sorted_nsd_ids[0]}-{sorted_nsd_ids[-1]})")

    # Verify all files exist
    missing = [nid for nid in sorted_nsd_ids if not (stim_dir / f"nsd_{nid:05d}.png").exists()]
    if missing:
        print(f"ERROR: {len(missing)} missing stimuli")
        return

    model_name = "openai/clip-vit-large-patch14"
    print(f"Loading CLIP model: {model_name}")
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()

    import PIL
    import transformers

    model_config_hash = hashlib.sha256(
        json.dumps(model.config.to_dict(), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    batch_size = 16
    checkpoint_path = clip_dir / "subj01_perception_clip_vitl14.checkpoint.npz"

    embeddings = np.zeros((10000, 768), dtype=np.float32)
    resume_from = 0
    if checkpoint_path.exists():
        ckpt = np.load(checkpoint_path)
        if ckpt["embeddings"].shape == (10000, 768):
            embeddings = ckpt["embeddings"]
            resume_from = int(ckpt["next_index"])
            print(f"Resuming from checkpoint: {resume_from}/10000 already computed")

    print(f"Computing embeddings (batch_size={batch_size}, resume_from={resume_from})...")
    start = time.time()
    for batch_start in range(resume_from, 10000, batch_size):
        batch_end = min(batch_start + batch_size, 10000)
        batch_ids = sorted_nsd_ids[batch_start:batch_end]
        images = [Image.open(stim_dir / f"nsd_{nid:05d}.png").convert("RGB") for nid in batch_ids]

        inputs = processor(images=images, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)

        features = features / features.norm(dim=-1, keepdim=True)
        embeddings[batch_start:batch_end] = features.numpy()

        if batch_end % 160 == 0 or batch_end == 10000:
            # Checkpoint every ~10 batches (~160 images): write to a .tmp file
            # then atomically rename, so a mid-write interruption never
            # corrupts the checkpoint a future resume would read.
            tmp_path = checkpoint_path.with_suffix(".npz.tmp")
            with open(tmp_path, "wb") as f:
                np.savez(f, embeddings=embeddings, next_index=batch_end)
            os.replace(tmp_path, checkpoint_path)
            elapsed = time.time() - start
            done_this_run = batch_end - resume_from
            rate = done_this_run / elapsed if elapsed > 0 else 0
            eta = (10000 - batch_end) / rate if rate > 0 else 0
            print(f"  {batch_end}/10000 ({rate:.1f} img/s, ETA {eta:.0f}s) [checkpointed]")

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.1f}s")

    # Validate
    norms = np.linalg.norm(embeddings, axis=1)
    assert embeddings.shape == (10000, 768), f"Wrong shape: {embeddings.shape}"
    assert embeddings.dtype == np.float32
    assert np.all(np.isfinite(embeddings)), "Non-finite values found"
    assert np.allclose(norms, 1.0, atol=1e-5), f"Norms not 1: min={norms.min()}, max={norms.max()}"

    # Check for duplicates using a random sample (avoid full 10k x 10k matrix)
    sample_idx = np.random.default_rng(42).choice(10000, size=500, replace=False)
    sample = embeddings[sample_idx]
    cos_sample = sample @ sample.T
    np.fill_diagonal(cos_sample, 0)
    max_sim = cos_sample.max()
    print(f"Max inter-image similarity (500 sample): {max_sim:.4f}")
    assert max_sim < 0.999, "Possible duplicate embeddings detected"

    # Save
    np.save(output_path, embeddings)
    print(f"Saved: {output_path}")
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Removed checkpoint (run complete)")

    # Compute hashes
    emb_hash = hashlib.sha256(embeddings.tobytes()).hexdigest()
    id_order_hash = hashlib.sha256(
        json.dumps(sorted_nsd_ids).encode()
    ).hexdigest()[:32]

    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_name,
        "model_config_hash": model_config_hash,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "pillow_version": PIL.__version__,
        "device": "cpu",
        "dtype": "float32",
        "batch_size": batch_size,
        "embedding_shape": [10000, 768],
        "l2_normalized": True,
        "norm_min": float(norms.min()),
        "norm_max": float(norms.max()),
        "all_finite": True,
        "max_inter_similarity": float(max_sim),
        "embedding_pool_hash": emb_hash[:32],
        "ordered_image_identity_hash": id_order_hash,
        "stimulus_set_hash": "4d314a7b71ed7d601ecc6a86ac0e0050",
        "output_path": str(output_path),
        "computation_time_s": round(elapsed, 1),
        "n_images": 10000,
        "image_id_range": [sorted_nsd_ids[0], sorted_nsd_ids[-1]],
    }

    manifest_path = results_dir / "c3_perception_clip_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
