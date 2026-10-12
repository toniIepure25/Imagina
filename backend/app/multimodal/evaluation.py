"""Validation utilities: subject-grouped splits, leakage checks, permutation/bootstrap inference, effect sizes,
calibration. Every result records the source kinds of the data it was computed on so synthetic results cannot be
reported as human findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold

from app.multimodal.schemas import SourceKind
from app.research.neural.nested_validation import bootstrap_ci
from app.research.statistics.multiplicity import holm_correction

SYNTHETIC_DISCLAIMER = ("SYNTHETIC/REPLAY infrastructure result. Demonstrates that the pipeline runs and behaves "
                        "as designed on generated data; it is not a human neuroscience finding.")


class LeakageError(RuntimeError):
    pass


@dataclass
class EvalResult:
    name: str
    scheme: str
    fold_scores: list[float]
    mean: float
    ci95: tuple[float, float]
    chance: float
    permutation_p: float | None
    n_samples: int
    n_groups: int
    source_kinds: list[str]
    extra: dict = field(default_factory=dict)

    @property
    def interpretation_scope(self) -> str:
        if set(self.source_kinds) <= {SourceKind.SYNTHETIC.value, SourceKind.REPLAY.value} and \
                SourceKind.REAL_SENSOR.value not in self.source_kinds:
            return SYNTHETIC_DISCLAIMER
        return "Real-sensor data; requires preregistered confirmatory analysis before any claim."

    def to_dict(self) -> dict:
        return {**self.__dict__, "interpretation_scope": self.interpretation_scope}


def check_group_leakage(train_groups: np.ndarray, test_groups: np.ndarray) -> None:
    overlap = set(np.unique(train_groups)) & set(np.unique(test_groups))
    if overlap:
        raise LeakageError(f"subjects present in both train and test: {sorted(overlap)[:5]}")


def check_duplicate_rows(x_train: np.ndarray, x_test: np.ndarray) -> int:
    def keys(a):
        return {np.round(r, 9).tobytes() for r in a.reshape(a.shape[0], -1)}
    return len(keys(x_train) & keys(x_test))


def splits(y: np.ndarray, groups: np.ndarray | None, scheme: str, n_splits: int = 5, seed: int = 0):
    if scheme == "loso":
        if groups is None:
            raise ValueError("LOSO requires groups")
        yield from LeaveOneGroupOut().split(np.zeros(len(y)), y, groups)
    elif scheme == "within_subject":
        if groups is None:
            groups = np.zeros(len(y))
        for g in np.unique(groups):
            idx = np.where(groups == g)[0]
            k = min(n_splits, int(np.min(np.bincount(np.unique(y[idx], return_inverse=True)[1]))))
            if k < 2:
                continue
            for tr, te in StratifiedKFold(k, shuffle=True, random_state=seed).split(idx, y[idx]):
                yield idx[tr], idx[te]
    else:
        raise ValueError(f"unknown scheme {scheme}")


def cross_validate(make_model: Callable, x: np.ndarray, y: np.ndarray, groups: np.ndarray | None, scheme: str,
                   source_kinds: list[str], name: str = "model", n_permutations: int = 0, seed: int = 0,
                   score: Callable | None = None) -> EvalResult:
    score = score or (lambda yt, yp: float(np.mean(yt == yp)))
    fold_scores, dup = [], 0
    folds = list(splits(y, groups, scheme, seed=seed))
    if not folds:
        raise ValueError("no valid folds")
    for tr, te in folds:
        if scheme == "loso":
            check_group_leakage(groups[tr], groups[te])
        dup += check_duplicate_rows(x[tr], x[te])
        m = make_model()
        m.fit(x[tr], y[tr])
        fold_scores.append(score(y[te], m.predict(x[te])))
    if dup:
        raise LeakageError(f"{dup} identical feature rows appear in both train and test")
    observed = float(np.mean(fold_scores))
    p = None
    if n_permutations:
        rng = np.random.default_rng(seed)
        null = []
        for _ in range(n_permutations):
            yp = permute_within_groups(y, groups, rng)
            s = []
            for tr, te in folds:
                m = make_model()
                m.fit(x[tr], yp[tr])
                s.append(score(yp[te], m.predict(x[te])))
            null.append(np.mean(s))
        p = (1 + int(np.sum(np.array(null) >= observed))) / (n_permutations + 1)
    classes, counts = np.unique(y, return_counts=True)
    lo, hi = bootstrap_ci(np.array(fold_scores), n_boot=2000, seed=seed)
    return EvalResult(name, scheme, [float(s) for s in fold_scores], observed, (lo, hi),
                      float(counts.max() / counts.sum()), p, int(len(y)),
                      int(len(np.unique(groups))) if groups is not None else 1, sorted(set(source_kinds)))


def permute_within_groups(y: np.ndarray, groups: np.ndarray | None, rng: np.random.Generator) -> np.ndarray:
    yp = y.copy()
    if groups is None:
        return rng.permutation(yp)
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        yp[idx] = rng.permutation(yp[idx])
    return yp


def hedges_g(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    d = (a.mean() - b.mean()) / sp if sp > 0 else 0.0
    return float(d * (1 - 3 / (4 * (na + nb) - 9)))


def paired_dz(a: np.ndarray, b: np.ndarray) -> float:
    d = np.asarray(a, float) - np.asarray(b, float)
    return float(d.mean() / d.std(ddof=1)) if d.std(ddof=1) > 0 else 0.0


def expected_calibration_error(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10) -> float:
    probs = np.asarray(probs, float)
    conf = probs.max(axis=1) if probs.ndim == 2 else np.where(probs >= 0.5, probs, 1 - probs)
    pred = probs.argmax(axis=1) if probs.ndim == 2 else (probs >= 0.5).astype(int)
    correct = (pred == np.asarray(y_true)).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def holm(results: dict[str, float], alpha: float = 0.05) -> list[dict]:
    return holm_correction(list(results.items()), alpha)
