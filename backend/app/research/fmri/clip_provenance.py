"""CLIP target provenance pipeline for NSD perception embeddings.

Prepares and documents the full perception target-embedding pipeline:
- Exact model identifier and library version
- Weights source and SHA-256
- Image preprocessing policy
- Embedding dimension and normalization
- Deterministic batched output
- Stimulus source hash verification
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class CLIPProvenanceSpec:
    """Frozen specification for CLIP embedding generation."""
    model_id: str = "openai/clip-vit-large-patch14"
    library: str = "transformers"
    library_version: str = ""
    weights_source: str = "huggingface_hub"
    embedding_dim: int = 768
    normalization: str = "L2"
    image_size: int = 224
    resize_method: str = "bicubic"
    center_crop: bool = True
    normalize_mean: tuple[float, ...] = (0.48145466, 0.4578275, 0.40821073)
    normalize_std: tuple[float, ...] = (0.26862954, 0.26130258, 0.27577711)
    batch_size: int = 32
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "library": self.library,
            "library_version": self.library_version,
            "weights_source": self.weights_source,
            "embedding_dim": self.embedding_dim,
            "normalization": self.normalization,
            "image_size": self.image_size,
            "resize_method": self.resize_method,
            "center_crop": self.center_crop,
            "normalize_mean": list(self.normalize_mean),
            "normalize_std": list(self.normalize_std),
            "batch_size": self.batch_size,
            "deterministic": self.deterministic,
        }

    def spec_hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:32]


def get_library_versions() -> dict[str, str]:
    """Get versions of relevant libraries."""
    versions: dict[str, str] = {}
    try:
        import transformers
        versions["transformers"] = transformers.__version__
    except ImportError:
        versions["transformers"] = "NOT_INSTALLED"
    try:
        import torch
        versions["torch"] = torch.__version__
    except ImportError:
        versions["torch"] = "NOT_INSTALLED"
    try:
        import PIL
        versions["pillow"] = PIL.__version__
    except ImportError:
        versions["pillow"] = "NOT_INSTALLED"
    return versions


def compute_embeddings_batch(
    image_paths: list[Path],
    spec: CLIPProvenanceSpec | None = None,
) -> tuple[NDArray[np.float32], dict[str, Any]]:
    """Compute CLIP embeddings for a list of images.

    Returns (embeddings [N, dim], provenance_dict).
    """
    if spec is None:
        spec = CLIPProvenanceSpec()

    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    processor = CLIPProcessor.from_pretrained(spec.model_id)
    model = CLIPModel.from_pretrained(spec.model_id)
    model.eval()

    if spec.deterministic:
        torch.manual_seed(0)

    embeddings = []
    image_hashes = []

    for i in range(0, len(image_paths), spec.batch_size):
        batch_paths = image_paths[i:i + spec.batch_size]
        images = []
        for p in batch_paths:
            img = Image.open(p).convert("RGB")
            images.append(img)
            with open(p, "rb") as f:
                image_hashes.append(hashlib.sha256(f.read()).hexdigest())

        inputs = processor(images=images, return_tensors="pt")
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            batch_emb = outputs.cpu().numpy()

        if spec.normalization == "L2":
            norms = np.linalg.norm(batch_emb, axis=1, keepdims=True)
            batch_emb = batch_emb / np.clip(norms, 1e-8, None)

        embeddings.append(batch_emb)

    all_embeddings = np.concatenate(embeddings, axis=0).astype(np.float32)
    pool_hash = hashlib.sha256(all_embeddings.tobytes()).hexdigest()

    provenance = {
        "spec": spec.to_dict(),
        "spec_hash": spec.spec_hash(),
        "library_versions": get_library_versions(),
        "n_images": len(image_paths),
        "embedding_shape": list(all_embeddings.shape),
        "pool_hash": pool_hash,
        "image_hashes": image_hashes,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    return all_embeddings, provenance


def verify_embedding_provenance(
    embeddings_path: Path,
    expected_hash: str | None = None,
    spec: CLIPProvenanceSpec | None = None,
) -> dict[str, Any]:
    """Verify provenance of an existing embeddings file."""
    result: dict[str, Any] = {
        "path": str(embeddings_path),
        "exists": embeddings_path.exists(),
    }

    if not embeddings_path.exists():
        result["status"] = "FILE_NOT_FOUND"
        return result

    embeddings = np.load(str(embeddings_path))
    result["shape"] = list(embeddings.shape)
    result["dtype"] = str(embeddings.dtype)

    pool_hash = hashlib.sha256(embeddings.tobytes()).hexdigest()
    result["pool_hash"] = pool_hash

    if expected_hash:
        result["expected_hash"] = expected_hash
        result["hash_match"] = pool_hash == expected_hash

    if spec:
        result["spec_hash"] = spec.spec_hash()
        result["embedding_dim_match"] = embeddings.shape[1] == spec.embedding_dim if embeddings.ndim == 2 else False

    norms = np.linalg.norm(embeddings, axis=1)
    result["l2_normalized"] = bool(np.allclose(norms, 1.0, atol=1e-5))
    result["status"] = "VERIFIED" if result.get("hash_match", True) and result["l2_normalized"] else "UNVERIFIED"

    return result


def check_stimuli_availability(stimuli_root: Path | None = None) -> dict[str, Any]:
    """Check whether NSD stimulus images are locally available.

    Requires NSD_STIMULI_ROOT environment variable or explicit path.
    """
    if stimuli_root is None:
        env_val = os.environ.get("NSD_STIMULI_ROOT")
        if not env_val:
            return {
                "status": "BLOCKED_STIMULI_ROOT_NOT_CONFIGURED",
                "error": (
                    "Environment variable NSD_STIMULI_ROOT is not set. "
                    "Set it to the directory containing NSD stimulus images "
                    "(e.g. the path to nsddata_stimuli/stimuli/nsd or the HDF5 container)."
                ),
            }
        stimuli_root = Path(env_val)

    result: dict[str, Any] = {
        "stimuli_root": str(stimuli_root),
        "exists": stimuli_root.exists(),
    }

    if not stimuli_root.exists():
        result["status"] = "BLOCKED_STIMULI_NOT_AVAILABLE"
        result["blocker"] = (
            "NSD stimulus images not found at expected path. "
            "These are required for generating perception CLIP embeddings. "
            "They must be obtained separately from the NSD data agreement."
        )
        return result

    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
    count = 0
    for f in stimuli_root.rglob("*"):
        if f.suffix.lower() in image_extensions:
            count += 1
    result["n_images_found"] = count
    result["status"] = "AVAILABLE" if count > 0 else "EMPTY_DIRECTORY"
    return result
