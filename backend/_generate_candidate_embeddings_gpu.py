"""Generate the frozen 12-image NSD-Imagery candidate-pool CLIP embeddings.

Runs the IDENTICAL CLIP pipeline used to produce the frozen perception
embeddings (transformers get_image_features -> image_embeds/pooler_output
-> L2 normalize), so the H2 candidate pool lives in exactly the same
embedding space the H1 decoder was trained to predict. Candidate order is
frozen from the authoritative A/B pair_list indices (Set A simple 0-5, then
Set B complex 6-11).
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
from transformers import CLIPModel, CLIPProcessor

# Frozen candidate order: (set, pair_list_index, filename, cue). Derived from
# the official A_pair_list.mat / B_pair_list.mat index ordering.
CANDIDATES = [
    ("A", 1, "bar_000.0deg_450L_43W.png", "H"),
    ("A", 2, "bar_045.0deg_450L_43W.png", "R"),
    ("A", 3, "bar_090.0deg_450L_43W.png", "V"),
    ("A", 4, "bar_135.0deg_450L_43W.png", "L"),
    ("A", 5, "crs_000.0deg_450L_43W.png", "P"),
    ("A", 6, "crs_045.0deg_450L_43W.png", "E"),
    ("B", 1, "shared0385_nsd28752.png", "W"),
    ("B", 2, "shared0413_nsd30857.png", "K"),
    ("B", 3, "shared0741_nsd53882.png", "B"),
    ("B", 4, "shared0842_nsd61178.png", "C"),
    ("B", 5, "shared0907_nsd65873.png", "D"),
    ("B", 6, "shared0000_nsd00000.png", "T"),
]


def main() -> None:
    raw_root = Path(os.environ["CANDIDATE_RAW_ROOT"])  # rawtargetimages dir with setA/ setB/
    out_dir = Path(os.environ["CANDIDATE_OUT_DIR"])
    out_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_name = "openai/clip-vit-large-patch14"
    print(f"Device: {device}; loading {model_name}", flush=True)
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)
    model.eval()

    import PIL
    import transformers

    embeddings = np.zeros((12, 768), dtype=np.float32)
    image_hashes = []
    for i, (set_letter, _idx, fname, _cue) in enumerate(CANDIDATES):
        path = raw_root / f"set{set_letter}" / fname
        img = Image.open(path).convert("RGB")
        with open(path, "rb") as f:
            image_hashes.append(hashlib.sha256(f.read()).hexdigest())
        inputs = processor(images=img, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
        if torch.is_tensor(outputs):
            feat = outputs
        elif getattr(outputs, "image_embeds", None) is not None:
            feat = outputs.image_embeds
        else:
            feat = outputs.pooler_output
        feat = feat / feat.norm(dim=-1, keepdim=True)
        embeddings[i] = feat.detach().cpu().numpy()[0]

    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
    assert np.all(np.isfinite(embeddings))

    out_path = out_dir / "c3_imagery_candidate_pool_clip_vitl14.npy"
    np.save(out_path, embeddings)

    pool_hash = hashlib.sha256(embeddings.tobytes()).hexdigest()
    manifest = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_name,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "pillow_version": PIL.__version__,
        "device": device,
        "pipeline": (
            "get_image_features -> image_embeds/pooler_output -> L2 normalize "
            "(identical to perception pipeline)"
        ),
        "embedding_shape": [12, 768],
        "candidate_order": [
            {"pool_index": i, "set": s, "pair_list_index": idx, "filename": f, "cue": c,
             "scientific_role": "SECONDARY_OOD_simple" if s == "A" else "PRIMARY_complex",
             "image_sha256": image_hashes[i]}
            for i, (s, idx, f, c) in enumerate(CANDIDATES)
        ],
        "candidate_pool_hash": pool_hash,
        "n_candidates": 12,
        "n_simple_setA": 6,
        "n_complex_setB": 6,
        "output_path": str(out_path),
    }
    with open(out_dir / "c3_imagery_candidate_pool_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved {out_path}", flush=True)
    print(f"candidate_pool_hash: {pool_hash}", flush=True)


if __name__ == "__main__":
    main()
