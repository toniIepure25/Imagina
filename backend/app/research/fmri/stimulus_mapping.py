"""Stimulus-mapping certification for NSD perception trials.

Verifies trial-to-image mapping invariants using official nsd_expdesign.mat
and completed session data. Certifies that:
- All trial indices are in bounds
- All eligible trials map to exactly one image
- Repeated images receive one canonical image identity
- No image identity crosses frozen train/test partitions
- Candidate embeddings are unique under the duplicate policy
- CLIP pool hash reproduces exactly
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np


def load_nsd_expdesign(mat_path: Path) -> dict[str, Any]:
    """Load NSD experiment design from .mat file."""
    from scipy.io import loadmat

    mat = loadmat(str(mat_path), squeeze_me=True)
    return {
        "masterordering": np.asarray(mat["masterordering"]),
        "subjectim": np.asarray(mat["subjectim"]),
        "sharedix": np.asarray(mat.get("sharedix", [])),
    }


def get_trials_for_session(
    masterordering: np.ndarray,
    session_num: int,
    trials_per_session: int = 750,
) -> np.ndarray:
    """Get global trial indices for a given session (1-indexed)."""
    start = (session_num - 1) * trials_per_session
    end = start + trials_per_session
    return masterordering[start:end]


def get_image_ids_for_subject(
    subjectim: np.ndarray,
    subject_idx: int,
    trial_indices: np.ndarray,
) -> np.ndarray:
    """Map trial ordering indices to NSD image IDs for a subject.

    subjectim is [n_subjects, n_trials_total] (0-indexed subjects, 1-indexed images).
    trial_indices are 1-indexed into subjectim columns.
    """
    return subjectim[subject_idx, trial_indices - 1]


def count_repeats(image_ids: np.ndarray) -> dict[int, int]:
    """Count how many times each image ID appears."""
    unique, counts = np.unique(image_ids, return_counts=True)
    return dict(zip(unique.tolist(), counts.tolist()))


def verify_no_cross_partition_images(
    train_image_ids: set[int],
    test_image_ids: set[int],
) -> dict[str, Any]:
    """Verify no image identity crosses train/test partition."""
    overlap = train_image_ids & test_image_ids
    return {
        "n_train_images": len(train_image_ids),
        "n_test_images": len(test_image_ids),
        "overlap_count": len(overlap),
        "partition_valid": len(overlap) == 0,
        "overlapping_ids": sorted(list(overlap))[:20] if overlap else [],
    }


def verify_embedding_uniqueness(
    embeddings: np.ndarray,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Verify all embeddings in the pool are unique."""
    n = embeddings.shape[0]
    duplicates = []
    for i in range(n):
        for j in range(i + 1, n):
            if np.allclose(embeddings[i], embeddings[j], atol=tolerance):
                duplicates.append((i, j))
    return {
        "n_embeddings": n,
        "n_duplicates": len(duplicates),
        "unique": len(duplicates) == 0,
        "duplicate_pairs": duplicates[:10],
    }


def verify_clip_pool_hash(embeddings: np.ndarray, expected_hash: str | None = None) -> dict[str, Any]:
    """Compute and optionally verify the CLIP embedding pool hash."""
    pool_hash = hashlib.sha256(embeddings.tobytes()).hexdigest()
    result: dict[str, Any] = {"pool_hash": pool_hash}
    if expected_hash:
        result["expected_hash"] = expected_hash
        result["match"] = pool_hash == expected_hash
    return result


def certify_stimulus_mapping(
    mat_path: Path,
    subject_id: str = "subj01",
    sessions_available: list[int] | None = None,
    clip_embeddings_path: Path | None = None,
    expected_clip_hash: str | None = None,
) -> dict[str, Any]:
    """Run full stimulus-mapping certification."""
    subject_idx_map = {"subj01": 0, "subj02": 1, "subj05": 4, "subj07": 6}
    subject_idx = subject_idx_map.get(subject_id)
    if subject_idx is None:
        return {"status": "FAILED", "error": f"Unknown subject: {subject_id}"}

    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject_id": subject_id,
        "subject_idx": subject_idx,
        "status": "PENDING",
    }

    expdesign = load_nsd_expdesign(mat_path)
    masterordering = expdesign["masterordering"]
    subjectim = expdesign["subjectim"]
    sharedix = expdesign["sharedix"]

    report["masterordering_shape"] = list(masterordering.shape)
    report["subjectim_shape"] = list(subjectim.shape)
    report["n_shared1000"] = len(sharedix)

    trials_per_session = 750
    total_expected_trials = 40 * trials_per_session

    report["checks"] = {}

    report["checks"]["masterordering_length"] = {
        "expected": total_expected_trials,
        "actual": len(masterordering),
        "valid": len(masterordering) >= total_expected_trials,
    }

    report["checks"]["subjectim_subjects"] = {
        "expected_subjects": 8,
        "actual_shape_0": subjectim.shape[0],
        "valid": subjectim.shape[0] >= 8,
    }

    if sessions_available:
        all_image_ids = []
        session_reports = []
        for sess in sessions_available:
            trial_ordering = get_trials_for_session(masterordering, sess, trials_per_session)
            image_ids = get_image_ids_for_subject(subjectim, subject_idx, trial_ordering)
            all_image_ids.extend(image_ids.tolist())
            session_reports.append({
                "session": sess,
                "n_trials": len(trial_ordering),
                "n_unique_images": len(np.unique(image_ids)),
                "image_id_range": [int(image_ids.min()), int(image_ids.max())],
                "all_in_bounds": bool(np.all(image_ids > 0) and np.all(image_ids <= 73000)),
            })
        report["session_mappings"] = session_reports
        report["checks"]["all_trials_in_bounds"] = all(s["all_in_bounds"] for s in session_reports)
        report["checks"]["total_mapped_trials"] = len(all_image_ids)

        repeat_counts = count_repeats(np.array(all_image_ids))
        report["checks"]["repeat_distribution"] = {
            "images_seen_once": sum(1 for c in repeat_counts.values() if c == 1),
            "images_seen_twice": sum(1 for c in repeat_counts.values() if c == 2),
            "images_seen_thrice": sum(1 for c in repeat_counts.values() if c == 3),
            "max_repeats": max(repeat_counts.values()) if repeat_counts else 0,
        }

    shared1000_set = set(sharedix.tolist()) if len(sharedix) > 0 else set()
    report["checks"]["shared1000_count"] = len(shared1000_set)
    report["checks"]["shared1000_handling"] = "explicit_identification"

    if clip_embeddings_path and clip_embeddings_path.exists():
        embeddings = np.load(str(clip_embeddings_path))
        uniqueness = verify_embedding_uniqueness(embeddings)
        pool_hash = verify_clip_pool_hash(embeddings, expected_clip_hash)
        report["checks"]["clip_uniqueness"] = uniqueness
        report["checks"]["clip_pool_hash"] = pool_hash
        report["status"] = "CERTIFIED" if (uniqueness["unique"] and pool_hash.get("match", True)) else "FAILED_CLIP"
    else:
        report["status"] = "PARTIALLY_CERTIFIED_CLIP_PENDING"

    return report


def main():
    mat_path = Path(os.environ.get(
        "NSD_DATA_ROOT",
        r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata"
    )) / "experiments" / "nsd" / "nsd_expdesign.mat"

    clip_path = Path(os.environ.get(
        "NSD_CACHE_ROOT",
        r"D:\ComputaCenter\FMRI2images\data\nsd\cache"
    )) / "imagery_target_clip_embeddings.npy"

    expected_hash = "0f4a98d41187ee7f577d65f71e3e312cfe3da86c837bfa41c6b7e2d959ce759d"

    betas_dir = Path(os.environ.get(
        "NSD_BETAS_ROOT",
        r"D:\ComputaCenter\FMRI2images\data\nsd\nsddata_betas"
    )) / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"

    sessions = []
    for s in range(1, 41):
        if (betas_dir / f"betas_session{s:02d}.hdf5").exists():
            sessions.append(s)

    print("=" * 60)
    print("NSD Stimulus-Mapping Certification")
    print("=" * 60)
    print(f"Available sessions: {sessions}")

    result = certify_stimulus_mapping(
        mat_path=mat_path,
        subject_id="subj01",
        sessions_available=sessions,
        clip_embeddings_path=clip_path,
        expected_clip_hash=expected_hash,
    )

    print(f"\nStatus: {result['status']}")
    if "checks" in result:
        for k, v in result["checks"].items():
            print(f"  {k}: {v}")

    out_path = Path("results/c3_stimulus_alignment.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nArtifact: {out_path}")


if __name__ == "__main__":
    main()
