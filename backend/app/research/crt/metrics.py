"""Metrics and records for the Stage 0 Counterfactual Reality Testing simulator."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import ClassVar, Sequence

from app.research.crt.model import FLUENCY, IMAGINED, SEEN, entropy
from app.research.prm.model import dprime_from_counts


@dataclass(frozen=True)
class TestRecord:
    __test__: ClassVar[bool] = False
    test: int
    outcome: bool
    eig: float
    meta_eig: float
    counterfactual_discrimination: float
    cost: float
    complexity: float
    max_eig: float
    max_meta_eig: float
    predicted: bool | None = None
    prediction_confidence: float | None = None
    prediction_correct: bool | None = None


@dataclass(frozen=True)
class DecisionRecord:
    available: tuple[int, ...]
    meta_eig: tuple[float, ...]
    eig: tuple[float, ...]
    costs: tuple[float, ...]
    complexities: tuple[float, ...]
    positive_values: tuple[float, ...]
    agency_values: tuple[float, ...]
    counterfactual_discrimination: tuple[float, ...]
    chosen: int


@dataclass(frozen=True)
class TrialRecord:
    condition: str
    true_source: int
    choice: int
    confidence: float
    correct: bool
    tests: tuple[TestRecord, ...]
    prior_entropy: float
    final_entropy: float
    human_meta_eig: float
    greedy_meta_eig: float
    random_meta_eig: float
    crte_meta: float | None
    crte_eig: float | None
    base_posterior: tuple[float, float, float, float]
    evidence_resolution: float


@dataclass(frozen=True)
class CrtSummary:
    n_trials: int
    accuracy: float
    brier_score: float
    expected_calibration_error: float
    mean_tests: float
    mean_crte_meta: float | None
    mean_crte_eig: float | None
    prediction_accuracy: float | None
    prediction_ece: float | None
    imagination_inflation_rate: float | None
    confounded_test_rate: float
    mean_evidence_resolution: float
    d_prime_seen_imagined: float
    insufficient_tests: int

    def as_dict(self) -> dict[str, object]:
        return {
            "n_trials": self.n_trials,
            "accuracy": round(self.accuracy, 6),
            "brier_score": round(self.brier_score, 6),
            "expected_calibration_error": round(self.expected_calibration_error, 6),
            "mean_tests": round(self.mean_tests, 6),
            "mean_crte_meta": None if self.mean_crte_meta is None else round(self.mean_crte_meta, 6),
            "mean_crte_eig": None if self.mean_crte_eig is None else round(self.mean_crte_eig, 6),
            "prediction_accuracy": (
                None if self.prediction_accuracy is None else round(self.prediction_accuracy, 6)
            ),
            "prediction_ece": None if self.prediction_ece is None else round(self.prediction_ece, 6),
            "imagination_inflation_rate": (
                None if self.imagination_inflation_rate is None else round(self.imagination_inflation_rate, 6)
            ),
            "confounded_test_rate": round(self.confounded_test_rate, 6),
            "mean_evidence_resolution": round(self.mean_evidence_resolution, 6),
            "d_prime_seen_imagined": round(self.d_prime_seen_imagined, 6),
            "insufficient_tests": self.insufficient_tests,
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
    totals = [0] * bins
    correct = [0] * bins
    confidence = [0.0] * bins
    for trial in trials:
        index = min(bins - 1, max(0, int(trial.confidence * bins)))
        totals[index] += 1
        correct[index] += int(trial.correct)
        confidence[index] += trial.confidence
    total = len(trials)
    error = 0.0
    for count, hits, confidence_sum in zip(totals, correct, confidence):
        if count == 0:
            continue
        error += (count / total) * abs(hits / count - confidence_sum / count)
    return error


def mean_tests(trials: Sequence[TrialRecord]) -> float:
    if not trials:
        return 0.0
    return mean(len(trial.tests) for trial in trials)


def mean_crte_meta(trials: Sequence[TrialRecord]) -> float | None:
    values = [trial.crte_meta for trial in trials if trial.crte_meta is not None]
    return mean(values) if values else None


def mean_crte_eig(trials: Sequence[TrialRecord]) -> float | None:
    values = [trial.crte_eig for trial in trials if trial.crte_eig is not None]
    return mean(values) if values else None


def prediction_accuracy(trials: Sequence[TrialRecord]) -> float | None:
    values = [
        int(test.prediction_correct)
        for trial in trials
        for test in trial.tests
        if test.prediction_correct is not None
    ]
    return mean(values) if values else None


def prediction_ece(trials: Sequence[TrialRecord], bins: int = 10) -> float | None:
    predictions = [
        (test.prediction_confidence, test.prediction_correct)
        for trial in trials
        for test in trial.tests
        if test.prediction_confidence is not None and test.prediction_correct is not None
    ]
    if not predictions:
        return None
    if bins <= 0:
        raise ValueError("bins must be positive")
    totals = [0] * bins
    correct = [0] * bins
    confidence = [0.0] * bins
    for value, hit in predictions:
        assert value is not None
        index = min(bins - 1, max(0, int(value * bins)))
        totals[index] += 1
        correct[index] += int(bool(hit))
        confidence[index] += value
    total = len(predictions)
    error = 0.0
    for count, hits, confidence_sum in zip(totals, correct, confidence):
        if count == 0:
            continue
        error += (count / total) * abs(hits / count - confidence_sum / count)
    return error


def imagination_inflation_rate(trials: Sequence[TrialRecord]) -> float | None:
    eligible = [
        trial
        for trial in trials
        if trial.true_source == IMAGINED
        and any(
            test.prediction_correct is True and (test.prediction_confidence or 0.0) >= 0.60
            for test in trial.tests
        )
    ]
    if not eligible:
        return None
    return sum(1 for trial in eligible if trial.choice == SEEN) / len(eligible)


def confounded_test_rate(trials: Sequence[TrialRecord]) -> float:
    tests = [test for trial in trials for test in trial.tests]
    if not tests:
        return 0.0
    return sum(1 for test in tests if test.test == FLUENCY) / len(tests)


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


def summarize(trials: Sequence[TrialRecord]) -> CrtSummary:
    return CrtSummary(
        n_trials=len(trials),
        accuracy=accuracy(trials),
        brier_score=brier_score(trials),
        expected_calibration_error=expected_calibration_error(trials),
        mean_tests=mean_tests(trials),
        mean_crte_meta=mean_crte_meta(trials),
        mean_crte_eig=mean_crte_eig(trials),
        prediction_accuracy=prediction_accuracy(trials),
        prediction_ece=prediction_ece(trials),
        imagination_inflation_rate=imagination_inflation_rate(trials),
        confounded_test_rate=confounded_test_rate(trials),
        mean_evidence_resolution=mean_evidence_resolution(trials),
        d_prime_seen_imagined=d_prime_seen_imagined(trials),
        insufficient_tests=sum(1 for trial in trials if trial.crte_meta is None),
    )


def information_resolution(prior: Sequence[float], posterior: Sequence[float]) -> float:
    prior_entropy = entropy(prior)
    if prior_entropy <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - entropy(posterior) / prior_entropy))


__all__ = [
    "CrtSummary",
    "DecisionRecord",
    "TestRecord",
    "TrialRecord",
    "accuracy",
    "brier_score",
    "confounded_test_rate",
    "d_prime_seen_imagined",
    "expected_calibration_error",
    "imagination_inflation_rate",
    "information_resolution",
    "mean_crte_eig",
    "mean_crte_meta",
    "mean_evidence_resolution",
    "mean_tests",
    "prediction_accuracy",
    "prediction_ece",
    "summarize",
]
