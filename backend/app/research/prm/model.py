"""Dependency-free generative model for the Source and Imagination Monitor.

The module is deliberately small: it defines the four-source signal-detection model, the
ideal-observer confidence baseline, and the summary statistics used by the Stage 0 simulator. It
does not fit human data and it does not make a claim about imagery.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import NormalDist

SOURCES: tuple[str, str, str, str] = ("new", "imagined", "described", "seen")
NEW, IMAGINED, DESCRIBED, SEEN = range(4)

_STANDARD_NORMAL = NormalDist()
_EPS = 1e-6


def normal_cdf(value: float) -> float:
    """Standard normal CDF with a stable tail clamp."""
    return min(1.0 - _EPS, max(_EPS, _STANDARD_NORMAL.cdf(value)))


def normal_ppf(value: float) -> float:
    """Standard normal quantile with a stable tail clamp."""
    return _STANDARD_NORMAL.inv_cdf(min(1.0 - _EPS, max(_EPS, value)))


def entropy(probabilities: list[float] | tuple[float, ...]) -> float:
    """Shannon entropy in bits for a discrete distribution."""
    total = sum(probabilities)
    if total <= 0:
        return 0.0
    result = 0.0
    for probability in probabilities:
        if probability <= 0:
            continue
        normalized = probability / total
        result -= normalized * math.log2(normalized)
    return result


@dataclass(frozen=True)
class PersonParams:
    """Person-level parameters on the evidence axis."""

    d: float = 0.0
    bias: float = 0.0
    described_gap: float = 0.75
    new_gap: float = 0.75
    lapse: float = 0.0
    confidence_noise: float = 0.0

    def means(self) -> tuple[float, float, float, float]:
        seen = self.d / 2.0
        imagined = -self.d / 2.0
        described = imagined - self.described_gap
        new = described - self.new_gap
        return new, imagined, described, seen

    def criteria(self) -> tuple[float, float, float]:
        new, imagined, described, seen = self.means()
        first = (new + imagined) / 2.0 + self.bias
        second = (imagined + described) / 2.0 + self.bias
        third = (described + seen) / 2.0 + self.bias
        return first, second, third


def response_distribution(params: PersonParams, source: int) -> tuple[float, float, float, float]:
    """Probability of each source response for a trial with the given true source."""
    if source not in (NEW, IMAGINED, DESCRIBED, SEEN):
        raise ValueError(f"unknown source index: {source}")
    mean = params.means()[source]
    first, second, third = params.criteria()
    cumulative = (
        normal_cdf(first - mean),
        normal_cdf(second - mean),
        normal_cdf(third - mean),
    )
    probabilities = (
        cumulative[0],
        cumulative[1] - cumulative[0],
        cumulative[2] - cumulative[1],
        1.0 - cumulative[2],
    )
    return tuple(max(0.0, probability) for probability in probabilities)  # type: ignore[return-value]


def posterior_source_probabilities(
    params: PersonParams, evidence: float, prior: tuple[float, float, float, float] | None = None
) -> tuple[float, float, float, float]:
    """Posterior probability of each source given scalar evidence and equal priors."""
    if prior is None:
        prior = (0.25, 0.25, 0.25, 0.25)
    likelihoods = []
    for source in range(4):
        mean = params.means()[source]
        density = math.exp(-0.5 * ((evidence - mean) ** 2)) / math.sqrt(2.0 * math.pi)
        likelihoods.append(density * prior[source])
    total = sum(likelihoods)
    if total <= 0:
        return (0.25, 0.25, 0.25, 0.25)
    return tuple(value / total for value in likelihoods)  # type: ignore[return-value]


def ideal_confidence(params: PersonParams, evidence: float, choice: int) -> float:
    """Posterior probability that the chosen source is correct."""
    posterior = posterior_source_probabilities(params, evidence)
    return min(1.0, max(0.5, posterior[choice]))


@dataclass(frozen=True)
class TrialResult:
    source: str
    choice: str
    confidence: float
    correct: bool
    evidence: float


def simulate_trial(params: PersonParams, source: int, rng: random.Random) -> TrialResult:
    """Simulate one source judgment under the generative model."""
    mean = params.means()[source]
    evidence = rng.gauss(mean, 1.0)
    first, second, third = params.criteria()
    if evidence < first:
        choice = NEW
    elif evidence < second:
        choice = IMAGINED
    elif evidence < third:
        choice = DESCRIBED
    else:
        choice = SEEN

    confidence = ideal_confidence(params, evidence, choice)
    if params.confidence_noise > 0:
        confidence = min(1.0, max(0.5, confidence + rng.gauss(0.0, params.confidence_noise)))

    if params.lapse > 0 and rng.random() < params.lapse:
        choice = rng.randrange(4)
        confidence = 0.5

    return TrialResult(
        source=SOURCES[source],
        choice=SOURCES[choice],
        confidence=confidence,
        correct=choice == source,
        evidence=evidence,
    )


def dprime_from_counts(
    hits: int, misses: int, false_alarms: int, correct_rejections: int
) -> float:
    """Log-linear 2-AFC d' for seen (signal) versus imagined (noise)."""
    hit_rate = (hits + 0.5) / (hits + misses + 1.0)
    false_alarm_rate = (false_alarms + 0.5) / (false_alarms + correct_rejections + 1.0)
    return normal_ppf(hit_rate) - normal_ppf(false_alarm_rate)


def criterion_from_counts(
    hits: int, misses: int, false_alarms: int, correct_rejections: int
) -> float:
    """Criterion for seen versus imagined; positive values indicate a conservative bias."""
    hit_rate = (hits + 0.5) / (hits + misses + 1.0)
    false_alarm_rate = (false_alarms + 0.5) / (false_alarms + correct_rejections + 1.0)
    return -0.5 * (normal_ppf(hit_rate) + normal_ppf(false_alarm_rate))
