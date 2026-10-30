"""Formal Stage 0 model for Counterfactual Reality Testing (CRT).

CRT extends source monitoring with a prospective forward model: before observing a test outcome,
the person predicts it. Source attribution then uses both the prediction and the outcome, and the
person can be more or less calibrated about the precision of their own prediction. The model is a
design and simulation model, not a fit to human data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from app.research.prm.model import entropy

SOURCES: tuple[str, str, str, str] = ("seen", "imagined", "described", "new")
SEEN, IMAGINED, DESCRIBED, NEW = range(4)

TEST_IDS: tuple[str, str, str, str, str, str] = (
    "viewpoint",
    "generation",
    "context",
    "intend",
    "description",
    "fluency",
)
VIEWPOINT, GENERATION, CONTEXT, INTEND, DESCRIPTION, FLUENCY = range(6)
ALL_TESTS: tuple[int, ...] = tuple(range(len(TEST_IDS)))

TEST_LIKELIHOODS: tuple[tuple[float, float, float, float], ...] = (
    (0.80, 0.40, 0.25, 0.20),
    (0.30, 0.75, 0.55, 0.20),
    (0.70, 0.65, 0.60, 0.20),
    (0.20, 0.70, 0.25, 0.20),
    (0.25, 0.50, 0.80, 0.20),
    (0.55, 0.55, 0.55, 0.55),
)

TEST_COSTS: tuple[float, ...] = (1.5, 1.0, 1.0, 2.0, 1.0, 0.5)
TEST_COMPLEXITY: tuple[float, ...] = (2.0, 1.0, 1.0, 3.0, 1.0, 1.0)
TEST_AGENCY: tuple[float, ...] = (0.30, 0.40, 0.30, 0.70, 0.30, 0.30)

DEFAULT_PRIOR: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)
_EPS = 1e-9


@dataclass(frozen=True)
class AgentParams:
    beta: float = 2.0
    lam: float = 0.25
    gamma: float = 0.2
    tau: float = -0.2
    d: float = 1.0
    pi: float = 1.0
    b_pi: float = 0.0
    guess: float = 0.05
    bias: float = 0.2
    lapse: float = 0.0
    confidence_noise: float = 0.05
    mix: float = 0.8
    alpha: float = 0.5

    def __post_init__(self) -> None:
        if self.beta < 0:
            raise ValueError("beta must be non-negative")
        if self.lam < 0:
            raise ValueError("lam must be non-negative")
        if self.gamma < 0:
            raise ValueError("gamma must be non-negative")
        if self.d <= 0:
            raise ValueError("d must be positive")
        if self.pi < 0:
            raise ValueError("pi must be non-negative")
        if self.b_pi < 0:
            raise ValueError("b_pi must be non-negative")
        if not 0.0 <= self.guess <= 1.0:
            raise ValueError("guess must be in [0, 1]")
        if not 0.0 <= self.bias <= 1.0:
            raise ValueError("bias must be in [0, 1]")
        if not 0.0 <= self.lapse <= 1.0:
            raise ValueError("lapse must be in [0, 1]")
        if not 0.0 <= self.mix <= 1.0:
            raise ValueError("mix must be in [0, 1]")
        if not 0.0 <= self.alpha <= 2.0:
            raise ValueError("alpha must be in [0, 2]")


def normalize(values: Sequence[float]) -> tuple[float, float, float, float]:
    total = sum(values)
    if total <= 0:
        return DEFAULT_PRIOR
    return tuple(max(0.0, value) / total for value in values)  # type: ignore[return-value]


def _logit(probability: float) -> float:
    clipped = min(1.0 - _EPS, max(_EPS, probability))
    return math.log(clipped / (1.0 - clipped))


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def _validate_test(test: int) -> None:
    if test not in range(len(TEST_IDS)):
        raise ValueError(f"unknown test index: {test}")


def _validate_source(source: int) -> None:
    if source not in (SEEN, IMAGINED, DESCRIBED, NEW):
        raise ValueError(f"unknown source index: {source}")


def effective_likelihoods(d: float = 1.0) -> tuple[tuple[float, float, float, float], ...]:
    if d <= 0:
        raise ValueError("d must be positive")
    return tuple(
        tuple(_sigmoid(d * _logit(probability)) for probability in row)
        for row in TEST_LIKELIHOODS
    )


def prediction_likelihood(
    test: int,
    source: int,
    pi: float = 1.0,
    likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> float:
    if pi < 0:
        raise ValueError("pi must be non-negative")
    _validate_test(test)
    _validate_source(source)
    if pi == 0.0:
        return 0.5
    return _sigmoid(pi * _logit(float(likelihoods[test][source])))


def posterior_predictive(
    prior: Sequence[float],
    test: int,
    pi: float = 1.0,
    likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> float:
    """Belief-based probability of a positive test outcome.

    A person who does not know the true source predicts from the current source posterior, not
    from the simulator's oracle source. ``pi`` is a metacognitive distortion of that readout:
    ``pi = 1`` uses the posterior predictive exactly; ``pi = 0`` is source-neutral.
    """

    if pi < 0:
        raise ValueError("pi must be non-negative")
    _validate_test(test)
    if len(prior) != len(SOURCES):
        raise ValueError("prior must have one probability per source")
    belief = normalize(prior)
    if pi == 0.0:
        return 0.5
    base = sum(belief[source] * float(likelihoods[test][source]) for source in range(len(SOURCES)))
    return _sigmoid(pi * _logit(base))



def outcome_likelihood(
    test: int,
    source: int,
    d: float = 1.0,
    likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> float:
    if d <= 0:
        raise ValueError("d must be positive")
    _validate_test(test)
    _validate_source(source)
    return _sigmoid(d * _logit(float(likelihoods[test][source])))


def _posterior(
    prior: Sequence[float],
    test: int,
    prediction: bool | None,
    outcome: bool,
    pi: float,
    d: float,
    prediction_likelihoods: Sequence[Sequence[float]],
    outcome_likelihoods: Sequence[Sequence[float]],
) -> tuple[float, float, float, float]:
    if len(prior) != len(SOURCES):
        raise ValueError("prior must have one probability per source")
    posterior = [max(0.0, value) for value in prior]
    for source in range(len(SOURCES)):
        if prediction is not None:
            probability = prediction_likelihoods[test][source]
            posterior[source] *= probability if prediction else 1.0 - probability
        probability = outcome_likelihoods[test][source]
        posterior[source] *= probability if outcome else 1.0 - probability
    return normalize(posterior)


def posterior_from_outcome(
    prior: Sequence[float],
    test: int,
    outcome: bool,
    d: float = 1.0,
    likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> tuple[float, float, float, float]:
    outcome_likelihoods = tuple(
        tuple(outcome_likelihood(test, source, d, likelihoods) for source in range(len(SOURCES)))
        for test in range(len(TEST_IDS))
    )
    neutral = tuple((0.5, 0.5, 0.5, 0.5) for _ in TEST_IDS)
    return _posterior(prior, test, None, outcome, 0.0, d, neutral, outcome_likelihoods)


def posterior_from_prediction_outcome(
    prior: Sequence[float],
    test: int,
    prediction: bool,
    outcome: bool,
    pi: float = 1.0,
    d: float = 1.0,
    prediction_likelihoods: Sequence[Sequence[float]] | None = None,
    outcome_likelihoods: Sequence[Sequence[float]] | None = None,
) -> tuple[float, float, float, float]:
    if prediction_likelihoods is None:
        prediction_likelihoods = tuple(
            tuple(prediction_likelihood(test, source, pi) for source in range(len(SOURCES)))
            for test in range(len(TEST_IDS))
        )
    if outcome_likelihoods is None:
        outcome_likelihoods = tuple(
            tuple(outcome_likelihood(test, source, d) for source in range(len(SOURCES)))
            for test in range(len(TEST_IDS))
        )
    return _posterior(prior, test, prediction, outcome, pi, d, prediction_likelihoods, outcome_likelihoods)


def _joint_prediction_outcome(
    prior: Sequence[float],
    test: int,
    prediction: bool,
    outcome: bool,
    pi: float,
    d: float,
) -> float:
    total = 0.0
    for source in range(len(SOURCES)):
        p_prediction = prediction_likelihood(test, source, pi)
        p_outcome = outcome_likelihood(test, source, d)
        total += (
            prior[source]
            * (p_prediction if prediction else 1.0 - p_prediction)
            * (p_outcome if outcome else 1.0 - p_outcome)
        )
    return total


def eig(
    prior: Sequence[float],
    test: int,
    d: float = 1.0,
    likelihoods: Sequence[Sequence[float]] = TEST_LIKELIHOODS,
) -> float:
    prior = normalize(prior)
    prior_entropy = entropy(prior)
    outcome_likelihoods = tuple(
        tuple(outcome_likelihood(test_index, source, d, likelihoods) for source in range(len(SOURCES)))
        for test_index in range(len(TEST_IDS))
    )
    expected_entropy = 0.0
    for outcome in (True, False):
        probability = sum(
            prior[source]
            * (outcome_likelihoods[test][source] if outcome else 1.0 - outcome_likelihoods[test][source])
            for source in range(len(SOURCES))
        )
        if probability <= _EPS:
            continue
        posterior = _posterior(
            prior,
            test,
            None,
            outcome,
            0.0,
            d,
            tuple((0.5, 0.5, 0.5, 0.5) for _ in TEST_IDS),
            outcome_likelihoods,
        )
        expected_entropy += probability * entropy(posterior)
    return max(0.0, prior_entropy - expected_entropy)


def meta_eig(
    prior: Sequence[float],
    test: int,
    pi: float = 1.0,
    d: float = 1.0,
    prediction_likelihoods: Sequence[Sequence[float]] | None = None,
    outcome_likelihoods: Sequence[Sequence[float]] | None = None,
) -> float:
    prior = normalize(prior)
    prior_entropy = entropy(prior)
    if prediction_likelihoods is None:
        prediction_likelihoods = tuple(
            tuple(prediction_likelihood(test_index, source, pi) for source in range(len(SOURCES)))
            for test_index in range(len(TEST_IDS))
        )
    if outcome_likelihoods is None:
        outcome_likelihoods = tuple(
            tuple(outcome_likelihood(test_index, source, d) for source in range(len(SOURCES)))
            for test_index in range(len(TEST_IDS))
        )
    expected_entropy = 0.0
    for prediction in (True, False):
        for outcome in (True, False):
            probability = 0.0
            for source in range(len(SOURCES)):
                p_prediction = prediction_likelihoods[test][source]
                p_outcome = outcome_likelihoods[test][source]
                probability += (
                    prior[source]
                    * (p_prediction if prediction else 1.0 - p_prediction)
                    * (p_outcome if outcome else 1.0 - p_outcome)
                )
            if probability <= _EPS:
                continue
            posterior = _posterior(
                prior,
                test,
                prediction,
                outcome,
                pi,
                d,
                prediction_likelihoods,
                outcome_likelihoods,
            )
            expected_entropy += probability * entropy(posterior)
    return max(0.0, prior_entropy - expected_entropy)


def counterfactual_discrimination(prior: Sequence[float], test: int, pi: float = 1.0) -> float:
    prior = normalize(prior)
    p_positive = sum(
        prior[source] * prediction_likelihood(test, source, pi) for source in range(len(SOURCES))
    )
    p_positive = min(1.0 - _EPS, max(_EPS, p_positive))
    marginal_entropy = entropy((p_positive, 1.0 - p_positive))
    conditional_entropy = sum(
        prior[source]
        * entropy(
            (
                max(_EPS, prediction_likelihood(test, source, pi)),
                max(_EPS, 1.0 - prediction_likelihood(test, source, pi)),
            )
        )
        for source in range(len(SOURCES))
    )
    return max(0.0, marginal_entropy - conditional_entropy)


def _best_test(prior: Sequence[float], tests: Sequence[int], scorer) -> tuple[int, float]:
    scored = [(scorer(prior, test), test) for test in tests]
    gain, test = max(scored, key=lambda item: (item[0], -item[1]))
    return test, gain


@lru_cache(maxsize=4096)
def _greedy_eig_cached(
    prior: tuple[float, float, float, float],
    max_tests: int,
    tests: tuple[int, ...],
    d: float,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    test, gain = _best_test(prior, tests, lambda current, candidate: eig(current, candidate, d))
    remaining = tuple(candidate for candidate in tests if candidate != test)
    expected_future = 0.0
    p_positive = sum(
        prior[source] * outcome_likelihood(test, source, d) for source in range(len(SOURCES))
    )
    for outcome in (True, False):
        probability = p_positive if outcome else 1.0 - p_positive
        if probability <= _EPS:
            continue
        posterior = posterior_from_outcome(prior, test, outcome, d)
        expected_future += probability * _greedy_eig_cached(posterior, max_tests - 1, remaining, d)
    return gain + expected_future


def greedy_eig(
    prior: Sequence[float],
    max_tests: int,
    tests: Sequence[int] = ALL_TESTS,
    d: float = 1.0,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    return _greedy_eig_cached(tuple(normalize(prior)), max_tests, tuple(tests), d)


@lru_cache(maxsize=4096)
def _random_eig_cached(
    prior: tuple[float, float, float, float],
    max_tests: int,
    tests: tuple[int, ...],
    d: float,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    total = 0.0
    for test in tests:
        remaining = tuple(candidate for candidate in tests if candidate != test)
        gain = eig(prior, test, d)
        expected_future = 0.0
        p_positive = sum(
            prior[source] * outcome_likelihood(test, source, d) for source in range(len(SOURCES))
        )
        for outcome in (True, False):
            probability = p_positive if outcome else 1.0 - p_positive
            if probability <= _EPS:
                continue
            posterior = posterior_from_outcome(prior, test, outcome, d)
            expected_future += probability * _random_eig_cached(posterior, max_tests - 1, remaining, d)
        total += gain + expected_future
    return total / len(tests)


def expected_random_eig(
    prior: Sequence[float],
    max_tests: int,
    tests: Sequence[int] = ALL_TESTS,
    d: float = 1.0,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    return _random_eig_cached(tuple(normalize(prior)), max_tests, tuple(tests), d)


@lru_cache(maxsize=4096)
def _greedy_meta_eig_cached(
    prior: tuple[float, float, float, float],
    max_tests: int,
    tests: tuple[int, ...],
    pi: float,
    d: float,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    test, gain = _best_test(prior, tests, lambda current, candidate: meta_eig(current, candidate, pi, d))
    remaining = tuple(candidate for candidate in tests if candidate != test)
    expected_future = 0.0
    for prediction in (True, False):
        for outcome in (True, False):
            probability = _joint_prediction_outcome(prior, test, prediction, outcome, pi, d)
            if probability <= _EPS:
                continue
            posterior = posterior_from_prediction_outcome(
                prior, test, prediction, outcome, pi, d
            )
            expected_future += probability * _greedy_meta_eig_cached(
                posterior, max_tests - 1, remaining, pi, d
            )
    return gain + expected_future


def greedy_meta_eig(
    prior: Sequence[float],
    max_tests: int,
    tests: Sequence[int] = ALL_TESTS,
    pi: float = 1.0,
    d: float = 1.0,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    return _greedy_meta_eig_cached(tuple(normalize(prior)), max_tests, tuple(tests), pi, d)


@lru_cache(maxsize=4096)
def _random_meta_eig_cached(
    prior: tuple[float, float, float, float],
    max_tests: int,
    tests: tuple[int, ...],
    pi: float,
    d: float,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    total = 0.0
    for test in tests:
        remaining = tuple(candidate for candidate in tests if candidate != test)
        gain = meta_eig(prior, test, pi, d)
        expected_future = 0.0
        for prediction in (True, False):
            for outcome in (True, False):
                probability = _joint_prediction_outcome(prior, test, prediction, outcome, pi, d)
                if probability <= _EPS:
                    continue
                posterior = posterior_from_prediction_outcome(
                    prior, test, prediction, outcome, pi, d
                )
                expected_future += probability * _random_meta_eig_cached(
                    posterior, max_tests - 1, remaining, pi, d
                )
        total += gain + expected_future
    return total / len(tests)


def expected_random_meta_eig(
    prior: Sequence[float],
    max_tests: int,
    tests: Sequence[int] = ALL_TESTS,
    pi: float = 1.0,
    d: float = 1.0,
) -> float:
    if max_tests <= 0 or not tests:
        return 0.0
    return _random_meta_eig_cached(tuple(normalize(prior)), max_tests, tuple(tests), pi, d)


def softmax(utilities: Sequence[float]) -> tuple[float, ...]:
    if not utilities:
        return ()
    maximum = max(utilities)
    exponentials = [math.exp(value - maximum) for value in utilities]
    total = sum(exponentials)
    return tuple(value / total for value in exponentials)


def choose_source_probabilities(
    posterior: Sequence[float],
    guess: float = 0.0,
    bias: float = 0.0,
) -> tuple[float, float, float, float]:
    if not 0.0 <= guess <= 1.0:
        raise ValueError("guess must be in [0, 1]")
    if not 0.0 <= bias <= 1.0:
        raise ValueError("bias must be in [0, 1]")
    posterior = normalize(posterior)
    guessing = [(1.0 - bias) / len(SOURCES) for _ in SOURCES]
    guessing[SEEN] += bias
    return tuple((1.0 - guess) * posterior[source] + guess * guessing[source] for source in range(len(SOURCES)))


def apply_prediction_bias(
    posterior: Sequence[float],
    predictions: Sequence[tuple[bool, float]],
    b_pi: float,
) -> tuple[float, float, float, float]:
    if b_pi <= 0 or not predictions:
        return normalize(posterior)
    consistent = [confidence for correct, confidence in predictions if correct]
    if not consistent:
        return normalize(posterior)
    weight = b_pi * sum(max(0.0, confidence - 0.5) * 2.0 for confidence in consistent) / len(consistent)
    logits = [_logit(value) for value in normalize(posterior)]
    logits[SEEN] += weight
    maximum = max(logits)
    exponentials = [math.exp(value - maximum) for value in logits]
    total = sum(exponentials)
    return tuple(value / total for value in exponentials)


__all__ = [
    "ALL_TESTS",
    "CONTEXT",
    "DEFAULT_PRIOR",
    "DESCRIBED",
    "FLUENCY",
    "GENERATION",
    "IMAGINED",
    "INTEND",
    "NEW",
    "SEEN",
    "SOURCES",
    "TEST_AGENCY",
    "TEST_COMPLEXITY",
    "TEST_COSTS",
    "TEST_IDS",
    "TEST_LIKELIHOODS",
    "VIEWPOINT",
    "AgentParams",
    "apply_prediction_bias",
    "choose_source_probabilities",
    "counterfactual_discrimination",
    "effective_likelihoods",
    "eig",
    "entropy",
    "expected_random_eig",
    "expected_random_meta_eig",
    "greedy_eig",
    "greedy_meta_eig",
    "meta_eig",
    "normalize",
    "outcome_likelihood",
    "posterior_from_outcome",
    "posterior_from_prediction_outcome",
    "posterior_predictive",
    "prediction_likelihood",
    "softmax",
]
