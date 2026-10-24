"""ANIMUS-P2 content-generalization splits (grouped by stimulus identity).

The primary test is on UNSEEN stimulus identities: an identity used in training may NEVER appear in the
primary test, and ALL repetitions of an identity fall in exactly one partition. Splits are frozen (with
identity hashes) before outcomes. A perceptual-hash audit flags near-duplicate images so image-family
leakage is caught, not just exact-id leakage.
"""
from __future__ import annotations

import hashlib

import numpy as np

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
TEST_FRAC = 0.15


def _identity_hash(stimulus_id: str) -> str:
    return hashlib.sha256(str(stimulus_id).encode()).hexdigest()[:16]


def freeze_identity_split(identities: list[str], seed: int = 20260909,
                          train_frac: float = TRAIN_FRAC, val_frac: float = VAL_FRAC) -> dict:
    """Deterministically partition unique identities into train/val/test groups (grouped, no leakage)."""
    uniq = sorted(set(str(i) for i in identities))
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(uniq))
    n = len(uniq)
    n_tr = int(round(train_frac * n))
    n_va = int(round(val_frac * n))
    tr = sorted(uniq[i] for i in perm[:n_tr])
    va = sorted(uniq[i] for i in perm[n_tr:n_tr + n_va])
    te = sorted(uniq[i] for i in perm[n_tr + n_va:])
    assert not (set(tr) & set(va)) and not (set(tr) & set(te)) and not (set(va) & set(te))
    return {"train": tr, "val": va, "test": te,
            "train_hash": _group_hash(tr), "val_hash": _group_hash(va), "test_hash": _group_hash(te),
            "n_train": len(tr), "n_val": len(va), "n_test": len(te), "seed": seed}


def _group_hash(ids: list[str]) -> str:
    return hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()


def trial_partition(stimulus_ids: list[str], split: dict) -> np.ndarray:
    """Map each trial to 'train'/'val'/'test' by its identity's group. All reps follow the identity."""
    tr, va, te = set(split["train"]), set(split["val"]), set(split["test"])
    out = []
    for s in stimulus_ids:
        s = str(s)
        out.append("train" if s in tr else "val" if s in va else "test" if s in te else "unassigned")
    return np.array(out)


def assert_no_identity_leakage(stimulus_ids: list[str], split: dict) -> dict:
    """Verify no identity spans partitions and every trial's identity is assigned to exactly one group."""
    part = trial_partition(stimulus_ids, split)
    # each identity -> the set of partitions its trials landed in (must be size 1)
    by_id: dict[str, set] = {}
    for s, p in zip((str(x) for x in stimulus_ids), part):
        by_id.setdefault(s, set()).add(p)
    spanning = [s for s, ps in by_id.items() if len(ps) > 1]
    unassigned = int(np.sum(part == "unassigned"))
    return {"no_identity_spans_partitions": len(spanning) == 0, "spanning_identities": spanning[:10],
            "unassigned_trials": unassigned, "leakage_free": len(spanning) == 0 and unassigned == 0}


def perceptual_hash_audit(embeddings: np.ndarray, identities: list[str], split: dict,
                          near_dup_cos: float = 0.98) -> dict:
    """Flag near-duplicate identities (cosine over the frozen stimulus representation) that straddle
    train/test, which would leak an image family across the boundary."""
    ids = [str(i) for i in identities]
    # one representative embedding per identity
    uniq = sorted(set(ids))
    idx = {u: [k for k, s in enumerate(ids) if s == u] for u in uniq}
    reps = np.stack([np.asarray(embeddings)[idx[u]].mean(0) for u in uniq])
    reps = reps / np.clip(np.linalg.norm(reps, axis=1, keepdims=True), 1e-9, None)
    tr, te = set(split["train"]), set(split["test"])
    leaks = 0
    sim = reps @ reps.T
    for a in range(len(uniq)):
        for b in range(a + 1, len(uniq)):
            if sim[a, b] >= near_dup_cos:
                ua, ub = uniq[a], uniq[b]
                if (ua in tr and ub in te) or (ua in te and ub in tr):
                    leaks += 1
    return {"near_dup_cos_threshold": near_dup_cos, "cross_split_near_duplicates": leaks,
            "family_leakage_free": leaks == 0}
