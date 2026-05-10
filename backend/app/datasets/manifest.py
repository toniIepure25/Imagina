import json
import os
from datetime import datetime, timezone

MANIFEST_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external"))


def write_manifest(dataset_id: str, metadata: dict) -> str:
    ds_dir = os.path.join(MANIFEST_DIR, dataset_id)
    os.makedirs(ds_dir, exist_ok=True)
    manifest = {
        "dataset_id": dataset_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_fallback": metadata.get("is_fallback", False),
        "fallback_reason": metadata.get("fallback_reason"),
        "acquisition_method": metadata.get("acquisition_method", "fixture"),
        **metadata,
    }
    path = os.path.join(ds_dir, "manifest.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    return path


def read_manifest(dataset_id: str) -> dict | None:
    path = os.path.join(MANIFEST_DIR, dataset_id, "manifest.json")
    if not os.path.exists(path):
        path = os.path.join(MANIFEST_DIR, f"{dataset_id}_manifest.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

