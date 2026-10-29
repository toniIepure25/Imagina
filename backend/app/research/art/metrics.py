"""Metrics and records for the Stage 0 Active Reality Testing simulator."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from app.research.art.model import IMAGINED, SEEN, entropy
from app.research.prm.model import dprime_from_counts


@dataclass(frozen=True)
class QueryRecord:
    card: int
    evidence: bool
    eig: float
    cost: float
    max_eig: float


@dataclass(frozen=True)
class DecisionRecord:
    available: tuple[int, ...]
    eig: tuple[float, ...]
    costs: tuple[float, ...]
    chosen: int


@dataclass(frozen=True)
class TrialRecord:
    true_source: int
    choice: int
    confidence: float
    correct: bool
    queries: tuple[QueryRecord, ...]
    prior_entropy: float
    final_entropy: float
    human_eig: float
    greedy_eig: float
    random_eig: float
    arte: float | None
    arte_raw: float | None
    evidence_resolution: float


@dataclass(frozen=True)
class ArtSummary:
    n_trials: int
    accuracy: float
    brier_score: float
    expected_calibration_error: float
    mean_queries: float
    mean_arte: float | None
    mean_sampling_quality: float | None
    mean_evidence_resolution: float
    d_prime_seen_imagined: float
    insufficient_queries: int

    def as_dict(self) -> dict[str, object]:
        return {
            "n_trials": self.n_trials,
            "accuracy": round(self.accuracy, 6),
            "brier_score": round(self.brier_score, 6),
            "expected_calibration_error": round(self.expected_calibration_error, 6),
            "mean_queries": round(self.mean_queries, 6),
            "mean_arte": None if self.mean_arte is None else round(self.mean_arte, 6),
            "mean_sampling_quality": (
                None if self.mean_sampling_quality is None else round(self.mean_sampling_quality, 6)
            ),
            "mean_evidence_resolution": round(self.mean_evidence_resolution, 6),
            "d_prime_seen_imagined": round(self.d_prime_seen_imagined, 6),
            "insufficient_queries": self.insufficient_queries,
        }


def accuracy(trials: Sequence[TrialRecord]) -> float:
    if not trials:
        return 0.0
    return sum(1 for trial in trials if trial.correct) / len(trials)


def brier_score(trials: Sequence[TrialRecord]) -> float:
    if not trials:
        return 0.0
    return mean((trial.confidence - (1.0 if trial.correct else 0.0)) ** 2 for trial in trials)


def expected_calibration_error(trials: Sequence[TrialRecord], bins: int = 10) -> float:
    if not trials:
        return 0.0
    if bins <= 0:
        raise ValueError("bins must be positive")
    bucket_totals = [0] * bins
    bucket_correct = [0] * bins
    bucket_confidence = [0.0] * bins
    for trial in trials:
        index = min(bins - 1, max(0, int(trial.confidence * bins)))
        bucket_totals[index] += 1
        bucket_correct[index] += int(trial.correct)
        bucket_confidence[index] += trial.confidence
    total = len(trials)
    error = 0.0
    for count, correct, confidence_sum in zip(bucket_totals, bucket_correct, bucket_confidence):
        if count == 0:
            continue
        error += (count / total) * abs(correct / count - confidence_sum / count)
    return error


def mean_queries(trials: Sequence[TrialRecord]) -> float:
    if not trials:
        return 0.0
    return mean(len(trial.queries) for trial in trials)


def mean_arte(trials: Sequence[TrialRecord]) -> float | None:
    values = [trial.arte for trial in trials if trial.arte is not None]
    return mean(values) if values else None


def mean_sampling_quality(trials: Sequence[TrialRecord]) -> float | None:
    values = [
        query.eig / query.max_eig
        for trial in trials
        for query in trial.queries
        if query.max_eig > 1e-12
    ]
    return mean(values) if values else None


def mean_evidence_resolution(trials: Sequence[TrialRecord]) -> float:
    if not trials:
        return 0.0
    return mean(trial.evidence_resolution for trial in trials)


def d_prime_seen_imagined(trials: Sequence[TrialRecord]) -> float:
    hits = sum(1 for trial in trials if trial.true_source == SEEN and trial.choice == SEEN)
    misses = sum(1 for trial in trials if trial.true_source == SEEN and trial.choice != SEEN)
    false_alarms = sum(1 for trial in trials if trial.true_source == IMAGINED and trial.choice == SEEN)
    correct_rejections = sum(
        1 for trial in trials if trial.true_source == IMAGINED and trial.choice != SEEN
    )
    return dprime_from_counts(hits, misses, false_alarms, correct_rejections)


def summarize(trials: Sequence[TrialRecord]) -> ArtSummary:
    return ArtSummary(
        n_trials=len(trials),
        accuracy=accuracy(trials),
        brier_score=brier_score(trials),
        expected_calibration_error=expected_calibration_error(trials),
        mean_queries=mean_queries(trials),
        mean_arte=mean_arte(trials),
        mean_sampling_quality=mean_sampling_quality(trials),
        mean_evidence_resolution=mean_evidence_resolution(trials),
        d_prime_seen_imagined=d_prime_seen_imagined(trials),
        insufficient_queries=sum(1 for trial in trials if trial.arte is None),
    )


def information_resolution(prior: Sequence[float], posterior: Sequence[float]) -> float:
    prior_entropy = entropy(prior)
    if prior_entropy <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - entropy(posterior) / prior_entropy))


__all__ = [
    "ArtSummary",
    "DecisionRecord",
    "QueryRecord",
    "TrialRecord",
    "accuracy",
    "brier_score",
    "d_prime_seen_imagined",
    "expected_calibration_error",
    "information_resolution",
    "mean_arte",
    "mean_evidence_resolution",
    "mean_queries",
    "mean_sampling_quality",
    "summarize",
]
