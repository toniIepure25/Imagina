"""NSD image-identity split manifest for perception decoder training.

Constructs the final perception split from official NSD image identities
(not from downloaded beta availability). The split must be frozen before
any perception model results are inspected.

Invariants:
- No repeated image crosses folds
- shared1000 handling is explicit
- Validation images are disjoint from final held-out images
- All hyperparameter selection uses only training/validation identities
- Imagery targets do not influence perception split construction
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import numpy as np
from numpy.typing import NDArray

NSD_SHARED1000_COUNT = 1000
IMAGERY_TARGET_IMAGE_IDS: list[int] = []  # populated at certification time


def build_perception_split(
    subjectim: NDArray[np.int64],
    subject_idx: int,
    sharedix: NDArray[np.int64],
    masterordering: NDArray[np.int64] | None = None,
    n_total_sessions: int = 40,
    trials_per_session: int = 750,
    test_fraction: float = 0.1,
    val_fraction: float = 0.1,
    seed: int = 42,
    imagery_target_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Build a frozen train/val/test split based on image identities.

    Split logic:
    1. Identify all unique image IDs seen by the subject
    2. Reserve shared1000 as the test set (standard NSD benchmark)
    3. From remaining images, split into train and validation
    4. Ensure no image crosses partitions
    5. Exclude imagery targets from split influence
    """
    total_trials = n_total_sessions * trials_per_session
    n_unique_images = subjectim.shape[1]

    unique_images = np.unique(subjectim[subject_idx, :n_unique_images])
    unique_images = unique_images[unique_images > 0]

    shared_set = set(sharedix.tolist())
    excluded_imagery = set(imagery_target_ids) if imagery_target_ids else set()

    test_images = sorted([int(i) for i in unique_images if i in shared_set])
    remaining = sorted([int(i) for i in unique_images if i not in shared_set and i not in excluded_imagery])

    rng = np.random.default_rng(seed)
    remaining_shuffled = rng.permutation(remaining).tolist()

    n_val = max(1, int(len(remaining_shuffled) * val_fraction / (1 - test_fraction)))
    val_images = sorted(remaining_shuffled[:n_val])
    train_images = sorted(remaining_shuffled[n_val:])

    train_set = set(train_images)
    val_set = set(val_images)
    test_set = set(test_images)
    assert len(train_set & val_set) == 0, "Train/val overlap"
    assert len(train_set & test_set) == 0, "Train/test overlap"
    assert len(val_set & test_set) == 0, "Val/test overlap"

    split_counts = {"train": 0, "val": 0, "test": 0, "excluded": 0}

    if masterordering is not None:
        for trial_idx in range(min(total_trials, len(masterordering))):
            image_slot = int(masterordering[trial_idx]) - 1
            if image_slot < 0 or image_slot >= n_unique_images:
                split_counts["excluded"] += 1
                continue
            img_id = int(subjectim[subject_idx, image_slot])
            if img_id in train_set:
                split_counts["train"] += 1
            elif img_id in val_set:
                split_counts["val"] += 1
            elif img_id in test_set:
                split_counts["test"] += 1
            else:
                split_counts["excluded"] += 1
    else:
        for img_id in unique_images:
            img_id = int(img_id)
            repeats = 3
            if img_id in train_set:
                split_counts["train"] += repeats
            elif img_id in val_set:
                split_counts["val"] += repeats
            elif img_id in test_set:
                split_counts["test"] += repeats
            else:
                split_counts["excluded"] += repeats

    manifest_content = json.dumps({
        "train_images": train_images,
        "val_images": val_images,
        "test_images": test_images,
        "seed": seed,
    }, sort_keys=True).encode()
    manifest_hash = hashlib.sha256(manifest_content).hexdigest()

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "subject_idx": subject_idx,
        "n_total_sessions": n_total_sessions,
        "trials_per_session": trials_per_session,
        "n_unique_images": len(unique_images),
        "n_train_images": len(train_images),
        "n_val_images": len(val_images),
        "n_test_images": len(test_images),
        "n_excluded_imagery_targets": len(excluded_imagery),
        "trial_split_counts": split_counts,
        "shared1000_as_test": True,
        "shared1000_count": len(test_images),
        "seed": seed,
        "manifest_hash": manifest_hash,
        "invariants": {
            "no_repeated_image_crosses_folds": True,
            "shared1000_handling": "explicit_test_set",
            "val_disjoint_from_test": len(val_set & test_set) == 0,
            "imagery_targets_excluded": len(excluded_imagery) > 0 if imagery_target_ids else False,
        },
        "train_image_ids": train_images,
        "val_image_ids": val_images,
        "test_image_ids": test_images,
    }


def verify_split_integrity(split_manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify that a split manifest satisfies all invariants."""
    checks: dict[str, Any] = {}

    train = set(split_manifest["train_image_ids"])
    val = set(split_manifest["val_image_ids"])
    test = set(split_manifest["test_image_ids"])

    checks["train_val_disjoint"] = len(train & val) == 0
    checks["train_test_disjoint"] = len(train & test) == 0
    checks["val_test_disjoint"] = len(val & test) == 0
    checks["no_empty_partitions"] = all([len(train) > 0, len(val) > 0, len(test) > 0])
    checks["all_valid"] = all(checks.values())

    content = json.dumps({
        "train_images": sorted(train),
        "val_images": sorted(val),
        "test_images": sorted(test),
        "seed": split_manifest["seed"],
    }, sort_keys=True).encode()
    checks["hash_reproduces"] = hashlib.sha256(content).hexdigest() == split_manifest["manifest_hash"]

    return checks
