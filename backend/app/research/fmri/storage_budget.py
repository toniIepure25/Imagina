"""Storage budget calculation and capacity gate for C3 real-data execution.

Computes a conservative storage budget using actual current values and
ensures sufficient disk space exists before and after acquisition.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

EXPECTED_SESSION_SIZE = 1_094_445_528
N_SESSIONS = 40
ROI_CACHE_PER_SESSION_MB = 45.0
CLIP_EMBEDDINGS_MB = 30.0
MODEL_CHECKPOINT_MB = 200.0
TEMPORARY_HEADROOM_MB = 2048.0
MIN_POST_COMPLETION_FREE_GB = 10.0


def compute_storage_budget(betas_dir: Path | None = None) -> dict[str, Any]:
    """Compute storage budget from actual disk state.

    Requires NSD_BETAS_ROOT env var or explicit betas_dir.
    """
    if betas_dir is None:
        root_env = os.environ.get("NSD_BETAS_ROOT")
        if not root_env:
            return {
                "status": "BLOCKED_CONFIGURATION",
                "error": "NSD_BETAS_ROOT not set",
            }
        betas_dir = Path(root_env) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    drive_path = str(betas_dir)
    if os.name == "nt":
        drive_path = betas_dir.anchor or str(betas_dir)[:3]

    usage = shutil.disk_usage(drive_path)
    free_bytes = usage.free

    complete_sessions = []
    for s in range(1, N_SESSIONS + 1):
        f = betas_dir / f"betas_session{s:02d}.hdf5"
        if f.exists() and f.stat().st_size >= EXPECTED_SESSION_SIZE * 0.99:
            complete_sessions.append(s)

    n_complete = len(complete_sessions)
    n_remaining = N_SESSIONS - n_complete
    remaining_download_bytes = n_remaining * EXPECTED_SESSION_SIZE

    roi_cache_bytes = int(N_SESSIONS * ROI_CACHE_PER_SESSION_MB * 1024 * 1024)
    clip_bytes = int(CLIP_EMBEDDINGS_MB * 1024 * 1024)
    model_bytes = int(MODEL_CHECKPOINT_MB * 1024 * 1024)
    temp_bytes = int(TEMPORARY_HEADROOM_MB * 1024 * 1024)

    total_required = remaining_download_bytes + roi_cache_bytes + clip_bytes + model_bytes + temp_bytes
    post_completion_free = free_bytes - total_required
    post_completion_free_gb = post_completion_free / (1024**3)

    sufficient = post_completion_free_gb >= MIN_POST_COMPLETION_FREE_GB

    budget = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "drive": drive_path,
        "current_free_bytes": free_bytes,
        "current_free_gb": round(free_bytes / (1024**3), 2),
        "sessions_complete": n_complete,
        "sessions_remaining": n_remaining,
        "remaining_download_bytes": remaining_download_bytes,
        "remaining_download_gb": round(remaining_download_bytes / (1024**3), 2),
        "largest_single_object_bytes": EXPECTED_SESSION_SIZE,
        "roi_cache_bytes": roi_cache_bytes,
        "roi_cache_gb": round(roi_cache_bytes / (1024**3), 2),
        "clip_embeddings_bytes": clip_bytes,
        "model_checkpoint_bytes": model_bytes,
        "temporary_headroom_bytes": temp_bytes,
        "total_required_bytes": total_required,
        "total_required_gb": round(total_required / (1024**3), 2),
        "post_completion_free_bytes": post_completion_free,
        "post_completion_free_gb": round(post_completion_free_gb, 2),
        "min_required_post_completion_gb": MIN_POST_COMPLETION_FREE_GB,
        "sufficient": sufficient,
        "status": "PASS" if sufficient else "BLOCKED_INSUFFICIENT_DISK",
    }
    return budget


def multi_participant_plan() -> dict[str, Any]:
    """Estimate storage for additional participants (subj02, subj05, subj07)."""
    per_participant_perception_gb = 40.77
    per_participant_imagery_gb = 1.1
    per_participant_roi_cache_gb = 1.8
    per_participant_total_gb = per_participant_perception_gb + per_participant_imagery_gb + per_participant_roi_cache_gb

    return {
        "per_participant_perception_gb": per_participant_perception_gb,
        "per_participant_imagery_gb": per_participant_imagery_gb,
        "per_participant_roi_cache_gb": per_participant_roi_cache_gb,
        "per_participant_total_gb": round(per_participant_total_gb, 1),
        "total_3_additional_gb": round(per_participant_total_gb * 3, 1),
        "recommendation": (
            "Requires separately configured storage root with at least "
            f"{round(per_participant_total_gb * 3, 0):.0f} GB for remaining participants. "
            "Do not begin additional downloads on current data root without verified capacity."
        ),
    }


def main():
    betas_root = os.environ.get("NSD_BETAS_ROOT")
    if not betas_root:
        print("ERROR: NSD_BETAS_ROOT not set")
        return
    betas_dir = Path(betas_root) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    budget = compute_storage_budget(betas_dir)
    print(json.dumps(budget, indent=2))

    out_path = Path("results/c3_storage_preflight.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(budget, f, indent=2)
    print(f"\nArtifact: {out_path}")


if __name__ == "__main__":
    main()
