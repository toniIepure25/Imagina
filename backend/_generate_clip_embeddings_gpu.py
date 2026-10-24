"""Generate frozen CLIP embeddings for all 10,000 subj01 perception stimuli.

GPU-accelerated variant intended to run on the remote A100 pod. Reads images
directly from the official NSD stimuli release (nsd_stimuli.hdf5 imgBrick
dataset) rather than the locally-reconstructed PNG cache, which is a strictly
more authoritative source (no reconstruction/verification step needed).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import h5py
import numpy as np
import torch
from PIL import Image
from scipy.io import loadmat
from transformers import CLIPModel, CLIPProcessor


def main():
    data_root = Path(os.environ.get(
        "NSD_DATA_ROOT", "/home/jovyan/work/data/nsd/nsddata"
    ))
    stim_hdf5 = Path(os.environ.get(
        "NSD_STIMULI_HDF5",
        "/home/jovyan/work/data/nsd/nsddata_stimuli/stimuli/nsd/nsd_stimuli.hdf5",
    ))
    imagina_data_root = Path(os.environ.get(
        "IMAGINA_DATA_ROOT", "/home/jovyan/work/IMAGINA/data/nsd"
    ))
    results_dir = Path(os.environ.get(
        "RESULTS_DIR", "/home/jovyan/work/IMAGINA/repo/results"
    ))

    clip_dir = imagina_data_root / "cache" / "clip"
    clip_dir.mkdir(parents=True, exist_ok=True)
    output_path = clip_dir / "subj01_perception_clip_vitl14.npy"

    mat = loadmat(str(data_root / "experiments" / "nsd" / "nsd_expdesign.mat"))
    subjectim = mat["subjectim"]
    sorted_nsd_ids = sorted(set(int(subjectim[0, i]) - 1 for i in range(10000)))
    print(f"Participant image IDs: {len(sorted_nsd_ids)} (range {sorted_nsd_ids[0]}-{sorted_nsd_ids[-1]})", flush=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}", flush=True)
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)

    model_name = "openai/clip-vit-large-patch14"
    print(f"Loading CLIP model: {model_name}", flush=True)
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()

    import PIL
    import transformers

    model_config_hash = hashlib.sha256(
        json.dumps(model.config.to_dict(), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    batch_size = 128
    checkpoint_path = clip_dir / "subj01_perception_clip_vitl14.checkpoint.npz"

    embeddings = np.zeros((10000, 768), dtype=np.float32)
    resume_from = 0
    if checkpoint_path.exists():
        ckpt = np.load(checkpoint_path)
        if ckpt["embeddings"].shape == (10000, 768):
            embeddings = ckpt["embeddings"]
            resume_from = int(ckpt["next_index"])
            print(f"Resuming from checkpoint: {resume_from}/10000 already computed", flush=True)

    print(f"Computing embeddings (batch_size={batch_size}, resume_from={resume_from})...", flush=True)
    start = time.time()
    with h5py.File(str(stim_hdf5), "r") as hf:
        img_brick = hf["imgBrick"]
        for batch_start in range(resume_from, 10000, batch_size):
            batch_end = min(batch_start + batch_size, 10000)
            batch_ids = sorted_nsd_ids[batch_start:batch_end]
            images = [Image.fromarray(img_brick[nid]).convert("RGB") for nid in batch_ids]

            inputs = processor(images=images, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = model.get_image_features(**inputs)
            if torch.is_tensor(outputs):
                features = outputs
            elif getattr(outputs, "image_embeds", None) is not None:
                features = outputs.image_embeds
            else:
                features = outputs.pooler_output

            features = features / features.norm(dim=-1, keepdim=True)
            embeddings[batch_start:batch_end] = features.detach().cpu().numpy()

            # Checkpoint every batch: write to a .tmp file via a file object
            # (np.savez appends .npz to bare path strings, which would break
            # the atomic rename), then os.replace for crash-safe resumption.
            tmp_path = checkpoint_path.with_suffix(".npz.tmp")
            with open(tmp_path, "wb") as f:
                np.savez(f, embeddings=embeddings, next_index=batch_end)
            os.replace(tmp_path, checkpoint_path)

            elapsed = time.time() - start
            done_this_run = batch_end - resume_from
            rate = done_this_run / elapsed if elapsed > 0 else 0
            eta = (10000 - batch_end) / rate if rate > 0 else 0
            print(f"  {batch_end}/10000 ({rate:.1f} img/s, ETA {eta:.0f}s) [checkpointed]", flush=True)

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.1f}s", flush=True)

    norms = np.linalg.norm(embeddings, axis=1)
    assert embeddings.shape == (10000, 768), f"Wrong shape: {embeddings.shape}"
    assert embeddings.dtype == np.float32
    assert np.all(np.isfinite(embeddings)), "Non-finite values found"
    assert np.allclose(norms, 1.0, atol=1e-5), f"Norms not 1: min={norms.min()}, max={norms.max()}"

    sample_idx = np.random.default_rng(42).choice(10000, size=500, replace=False)
    sample = embeddings[sample_idx]
    cos_sample = sample @ sample.T
    np.fill_diagonal(cos_sample, 0)
    max_sim = cos_sample.max()
    print(f"Max inter-image similarity (500 sample): {max_sim:.4f}", flush=True)
    assert max_sim < 0.999, "Possible duplicate embeddings detected"

    np.save(output_path, embeddings)
    print(f"Saved: {output_path}", flush=True)
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Removed checkpoint (run complete)", flush=True)

    emb_hash = hashlib.sha256(embeddings.tobytes()).hexdigest()
    id_order_hash = hashlib.sha256(json.dumps(sorted_nsd_ids).encode()).hexdigest()[:32]

    # Hash of the actual raw stimulus bytes used (official nsd_stimuli.hdf5
    # imgBrick source, not the locally-reconstructed PNG cache), so this
    # artifact's provenance chain stands on its own.
    with h5py.File(str(stim_hdf5), "r") as hf:
        img_brick = hf["imgBrick"]
        stim_hasher = hashlib.sha256()
        for nid in sorted_nsd_ids:
            stim_hasher.update(img_brick[nid].tobytes())
        stimulus_set_hash = stim_hasher.hexdigest()[:32]

    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_name,
        "model_config_hash": model_config_hash,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "pillow_version": PIL.__version__,
        "device": device,
        "gpu_name": torch.cuda.get_device_name(0) if device == "cuda" else None,
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
        "stimulus_set_hash": stimulus_set_hash,
        "stimulus_source": (
            "official NSD release nsd_stimuli.hdf5 (imgBrick dataset), "
            "not the locally-reconstructed PNG cache"
        ),
        "output_path": str(output_path),
        "computation_time_s": round(elapsed, 1),
        "n_images": 10000,
        "image_id_range": [sorted_nsd_ids[0], sorted_nsd_ids[-1]],
        "compute_location": "remote_gpu_pod",
        "compute_host": os.environ.get("HOSTNAME", "unknown"),
    }

    manifest_path = results_dir / "c3_perception_clip_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
