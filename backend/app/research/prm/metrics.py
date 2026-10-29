"""Scoring for the Source and Imagination Monitor.

The primary statistics are ordinary signal-detection summaries with a log-linear correction for
extreme rates. ``meta_d_prime`` is deliberately gated: Stage 0 does not estimate it, and Stage 1 may
report it only when the trial-count gate is met.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.research.prm.model import (
    DESCRIBED,
    IMAGINED,
    NEW,
    SEEN,
    SOURCES,
    criterion_from_counts,
    dprime_from_counts,
)

_CONFIDENCE_FLOOR = 0.5
_CONFIDENCE_CEILING = 1.0
_META_D_PRIME_MIN_TRIALS = 200
_META_D_PRIME_MIN_PER_SOURCE = 100


@dataclass(frozen=True)
class TrialRecord:
    source: str
    choice: str
    confidence: float
    correct: bool
    latency_ms: int | None = None
    abstained: bool = False

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"unknown source: {self.source!r}")
        if self.choice not in SOURCES:
            raise ValueError(f"unknown choice: {self.choice!r}")
        if not _CONFIDENCE_FLOOR <= self.confidence <= _CONFIDENCE_CEILING:
            raise ValueError("confidence must be in [0.5, 1.0]")


@dataclass
class SourceSummary:
    n_trials: int
    n_seen: int
    n_imagined: int
    accuracy: float
    d_prime: float
    criterion: float
    brier: float
    ece: float
    overconfidence: float
    meta_d_prime: float | None
    meta_d_prime_status: str
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "n_trials": self.n_trials,
            "n_seen": self.n_seen,
            "n_imagined": self.n_imagined,
            "accuracy": round(self.accuracy, 6),
            "d_prime": round(self.d_prime, 6),
            "criterion": round(self.criterion, 6),
            "brier": round(self.brier, 6),
            "ece": round(self.ece, 6),
            "overconfidence": round(self.overconfidence, 6),
            "meta_d_prime": None if self.meta_d_prime is None else round(self.meta_d_prime, 6),
            "meta_d_prime_status": self.meta_d_prime_status,
            "confusion": self.confusion,
        }


def confusion_matrix(trials: list[TrialRecord]) -> dict[str, dict[str, int]]:
    matrix = {source: {choice: 0 for choice in SOURCES} for source in SOURCES}
    for trial in trials:
        matrix[trial.source][trial.choice] += 1
    return matrix


def seen_imagined_counts(trials: list[TrialRecord]) -> tuple[int, int, int, int]:
    """Return hits, misses, false alarms, and correct rejections for seen versus imagined."""
    hits = sum(1 for trial in trials if trial.source == "seen" and trial.choice == "seen")
    misses = sum(1 for trial in trials if trial.source == "seen" and trial.choice != "seen")
    false_alarms = sum(1 for trial in trials if trial.source == "imagined" and trial.choice == "seen")
    correct_rejections = sum(
        1 for trial in trials if trial.source == "imagined" and trial.choice != "seen"
    )
    return hits, misses, false_alarms, correct_rejections


def brier_score(trials: list[TrialRecord]) -> float:
    scored = [trial for trial in trials if not trial.abstained]
    if not scored:
        return 0.0
    return sum((trial.confidence - float(trial.correct)) ** 2 for trial in scored) / len(scored)


def expected_calibration_error(trials: list[TrialRecord], bins: int = 10) -> float:
    scored = [trial for trial in trials if not trial.abstained]
    if not scored:
        return 0.0
    buckets: list[list[TrialRecord]] = [[] for _ in range(bins)]
    for trial in scored:
        index = min(bins - 1, int((trial.confidence - _CONFIDENCE_FLOOR) * bins))
        buckets[index].append(trial)
    total = len(scored)
    error = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        mean_confidence = sum(trial.confidence for trial in bucket) / len(bucket)
        accuracy = sum(1.0 if trial.correct else 0.0 for trial in bucket) / len(bucket)
        error += (len(bucket) / total) * abs(mean_confidence - accuracy)
    return error


def overconfidence(trials: list[TrialRecord]) -> float:
    scored = [trial for trial in trials if not trial.abstained]
    if not scored:
        return 0.0
    return sum(trial.confidence for trial in scored) / len(scored) - sum(
        1.0 if trial.correct else 0.0 for trial in scored
    ) / len(scored)


def meta_d_prime_gate(trials: list[TrialRecord]) -> str:
    if len(trials) < _META_D_PRIME_MIN_TRIALS:
        return "insufficient_trials"
    for source in ("seen", "imagined"):
        if sum(1 for trial in trials if trial.source == source) < _META_D_PRIME_MIN_PER_SOURCE:
            return "insufficient_source_trials"
    return "eligible_not_estimated_stage0"


def summarize(trials: list[TrialRecord]) -> SourceSummary:
    if not trials:
        raise ValueError("cannot summarize an empty trial list")
    hits, misses, false_alarms, correct_rejections = seen_imagined_counts(trials)
    n_seen = sum(1 for trial in trials if trial.source == "seen")
    n_imagined = sum(1 for trial in trials if trial.source == "imagined")
    accuracy = sum(1 for trial in trials if trial.correct) / len(trials)
    status = meta_d_prime_gate(trials)
    return SourceSummary(
        n_trials=len(trials),
        n_seen=n_seen,
        n_imagined=n_imagined,
        accuracy=accuracy,
        d_prime=dprime_from_counts(hits, misses, false_alarms, correct_rejections),
        criterion=criterion_from_counts(hits, misses, false_alarms, correct_rejections),
        brier=brier_score(trials),
        ece=expected_calibration_error(trials),
        overconfidence=overconfidence(trials),
        meta_d_prime=None,
        meta_d_prime_status=status,
        confusion=confusion_matrix(trials),
    )


__all__ = [
    "DESCRIBED",
    "IMAGINED",
    "NEW",
    "SEEN",
    "SourceSummary",
    "TrialRecord",
    "brier_score",
    "confusion_matrix",
    "expected_calibration_error",
    "meta_d_prime_gate",
    "overconfidence",
    "seen_imagined_counts",
    "summarize",
]
