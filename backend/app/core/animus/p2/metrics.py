"""ANIMUS-P2 content-decoding metrics (held-out identities only).

Primary content margin M, 2AFC identification, retrieval (Top-k / MRR / rank), plus the mandatory controls:
label-permutation (effect must collapse), category-matched decoys, and a low-level-only baseline. Inference
is by within-test stimulus-label permutation and identity bootstrap under sealed seeds. All operate on the
frozen TEST partition only.
"""
from __future__ import annotations

import numpy as np

from app.core.animus.p2.target_representation import unit_l2

SEEDS = (20260909, 20260909 + 100, 20260909 + 200)


def _cos_matrix(pred: np.ndarray, true: np.ndarray) -> np.ndarray:
    return unit_l2(pred) @ unit_l2(true).T


def content_margin(pred: np.ndarray, true: np.ndarray) -> float:
    """M = mean_i ( cos(p_i,t_i) - mean_{j!=i} cos(p_i,t_j) ) over held-out test trials."""
    s = _cos_matrix(pred, true)
    n = s.shape[0]
    diag = np.diag(s)
    off = (s.sum(1) - diag) / (n - 1)
    return float(np.mean(diag - off))


def permutation_p(pred: np.ndarray, true: np.ndarray, n_perm: int = 1000, seed: int = SEEDS[0]) -> float:
    obs = content_margin(pred, true)
    rng = np.random.default_rng(seed + 1)
    ge = 0
    for _ in range(n_perm):
        perm = rng.permutation(len(true))
        if content_margin(pred, true[perm]) >= obs:
            ge += 1
    return float((ge + 1) / (n_perm + 1))


def identity_bootstrap_ci(pred: np.ndarray, true: np.ndarray, n_boot: int = 1000,
                          seed: int = SEEDS[0]) -> list[float]:
    rng = np.random.default_rng(seed + 2)
    n = len(true)
    vals = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        vals.append(content_margin(pred[idx], true[idx]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def two_afc(pred: np.ndarray, true: np.ndarray, n_decoy: int = 50, seed: int = SEEDS[0]) -> dict:
    rng = np.random.default_rng(seed + 3)
    n = len(true)
    p = unit_l2(pred)
    t = unit_l2(true)
    correct = 0
    total = 0
    for i in range(n):
        true_sim = float(p[i] @ t[i])
        decoys = rng.integers(0, n, n_decoy)
        for j in decoys:
            if j == i:
                continue
            total += 1
            if true_sim > float(p[i] @ t[j]):
                correct += 1
    acc = correct / max(total, 1)
    # binomial-ish CI
    se = np.sqrt(acc * (1 - acc) / max(total, 1))
    return {"accuracy": round(acc, 5), "ci95": [round(acc - 1.96 * se, 5), round(acc + 1.96 * se, 5)],
            "n_comparisons": total, "chance": 0.5}


def retrieval(pred: np.ndarray, true_gallery: np.ndarray) -> dict:
    """Rank each prediction's true identity within the held-out gallery (unique test identities)."""
    s = _cos_matrix(pred, true_gallery)          # (n_query, n_gallery), aligned index = correct
    n = s.shape[0]
    ranks = []
    for i in range(n):
        order = np.argsort(-s[i])
        ranks.append(int(np.where(order == i)[0][0]) + 1)
    ranks = np.array(ranks)
    g = true_gallery.shape[0]
    return {"top1": float(np.mean(ranks <= 1)), "top5": float(np.mean(ranks <= 5)),
            "top10": float(np.mean(ranks <= 10)), "mrr": float(np.mean(1.0 / ranks)),
            "median_rank": float(np.median(ranks)), "normalized_rank": float(np.mean(ranks) / g),
            "gallery_size": int(g), "chance_top1": round(1.0 / g, 6)}


def category_matched_2afc(pred, true, categories, seed: int = SEEDS[0]) -> dict:
    """2AFC where decoys are drawn from the SAME category (identity-sensitive, not category-sensitive)."""
    cats = np.asarray(categories)
    p = unit_l2(pred)
    t = unit_l2(true)
    rng = np.random.default_rng(seed + 4)
    correct = 0
    total = 0
    for i in range(len(t)):
        same = np.where((cats == cats[i]))[0]
        same = same[same != i]
        if len(same) == 0:
            continue
        for j in rng.choice(same, size=min(len(same), 20), replace=False):
            total += 1
            if float(p[i] @ t[i]) > float(p[i] @ t[j]):
                correct += 1
    if total == 0:
        return {"accuracy": None, "n_comparisons": 0, "chance": 0.5, "note": "no within-category decoys"}
    return {"accuracy": round(correct / total, 5), "n_comparisons": total, "chance": 0.5}


def low_level_baseline_margin(low_level_features_test: np.ndarray, true: np.ndarray,
                              low_level_features_train: np.ndarray, y_train: np.ndarray,
                              alpha: float = 100.0) -> float:
    """Fit a decoder on TRIVIAL image features (luminance/color/contrast/SF) and report its content margin.
    The neural decoder must beat this to claim more than low-level structure."""
    from app.core.animus.p2.decoder import RidgeDecoder
    dec = RidgeDecoder(alpha=alpha).fit(low_level_features_train, y_train)
    pred = dec.predict(low_level_features_test)
    return content_margin(pred, true)


def multi_seed_margin(pred, true) -> dict:
    ms = {str(s): content_margin(pred, true) for s in SEEDS}  # margin itself is seed-independent
    # the seed-dependence enters permutation/bootstrap; here report the point margin under each sealed seed
    return {"per_seed_margin": {k: round(v, 6) for k, v in ms.items()},
            "min_margin": round(min(ms.values()), 6), "all_positive": all(v > 0 for v in ms.values())}
