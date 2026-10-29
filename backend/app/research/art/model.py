"""Formal Stage 0 model for Active Reality Testing (ART).

ART treats source attribution as a sequential evidence-selection problem. A person may sample
source-diagnostic cards before judging whether an experience was seen, imagined, described, or new.
The model is a Bayesian ideal observer for the card evidence plus a softmax policy for query choice
and stopping. It is a design and simulation model, not a fit to human data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from app.research.prm.model import entropy

SOURCES: tuple[str, str, str, str] = ("seen", "imagined", "described", "new")
SEEN, IMAGINED, DESCRIBED, NEW = range(4)

CARD_IDS: tuple[str, str, str, str] = ("perceptual", "generation", "context", "novelty")
PERCEPTUAL, GENERATION, CONTEXT, NOVELTY = range(4)

# Probability of a positive card signal conditional on the true source.
# Rows are cards; columns follow SOURCES (seen, imagined, described, new).
CARD_LIKELIHOODS: tuple[tuple[float, float, float, float], ...] = (
    (0.80, 0.35, 0.25, 0.20),
    (0.30, 0.75, 0.55, 0.20),
    (0.70, 0.65, 0.60, 0.20),
    (0.20, 0.25, 0.30, 0.80),
)

DEFAULT_PRIOR: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)
_EPS = 1e-9


@dataclass(frozen=True)
class AgentParams:
    """Person-level parameters for the active evidence-selection model."""

    beta: float = 2.0
    lam: float = 0.25
    tau: float = -0.2
    d: float = 1.0
    lapse: float = 0.02
    confidence_noise: float = 0.05

    def __post_init__(self) -> None:
        if self.beta < 0:
            raise ValueError("beta must be non-negative")
        if self.lam < 0:
            raise ValueError("lam must be non-negative")
        if self.d <= 0:
            raise ValueError("d must be positive")
        if not 0.0 <= self.lapse <= 1.0:
            raise ValueError("lapse must be in [0, 1]")


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


def effective_likelihoods(d: float = 1.0) -> tuple[tuple[float, float, float, float], ...]:
    """Sharpen or flatten the card likelihoods by person-level evidence gain ``d``."""
    if d <= 0:
        raise ValueError("d must be positive")
    return tuple(
        tuple(_sigmoid(d * _logit(probability)) for probability in row)
        for row in CARD_LIKELIHOODS
    )


def card_likelihood(
    card: int,
    source: int,
    likelihoods: Sequence[Sequence[float]] = CARD_LIKELIHOODS,
) -> float:
    if card not in range(len(CARD_IDS)):
        raise ValueError(f"unknown card index: {card}")
    if source not in (SEEN, IMAGINED, DESCRIBED, NEW):
        raise ValueError(f"unknown source index: {source}")
    return float(likelihoods[card][source])


def posterior_from_evidence(
    prior: Sequence[float],
    evidence: Sequence[tuple[int, bool]],
    likelihoods: Sequence[Sequence[float]] = CARD_LIKELIHOODS,
) -> tuple[float, float, float, float]:
    if len(prior) != len(SOURCES):
        raise ValueError("prior must have one probability per source")
    posterior = [max(0.0, value) for value in prior]
    for card, positive in evidence:
        for source in range(len(SOURCES)):
            probability = card_likelihood(card, source, likelihoods)
            posterior[source] *= probability if positive else 1.0 - probability
    return normalize(posterior)


def expected_information_gain(
    prior: Sequence[float],
    card: int,
    likelihoods: Sequence[Sequence[float]] = CARD_LIKELIHOODS,
) -> float:
    """Expected entropy reduction about the source from one binary card."""
    prior = normalize(prior)
    prior_entropy = entropy(prior)
    positive_probability = sum(
        prior[source] * card_likelihood(card, source, likelihoods) for source in range(len(SOURCES))
    )
    positive_probability = min(1.0 - _EPS, max(_EPS, positive_probability))
    positive_posterior = posterior_from_evidence(prior, ((card, True),), likelihoods)
    negative_posterior = posterior_from_evidence(prior, ((card, False),), likelihoods)
    expected_posterior_entropy = (
        positive_probability * entropy(positive_posterior)
        + (1.0 - positive_probability) * entropy(negative_posterior)
    )
    return max(0.0, prior_entropy - expected_posterior_entropy)


def _best_card(
    prior: Sequence[float],
    cards: Sequence[int],
    likelihoods: Sequence[Sequence[float]],
) -> tuple[int, float]:
    scored = [(expected_information_gain(prior, card, likelihoods), card) for card in cards]
    gain, card = max(scored, key=lambda item: (item[0], -item[1]))
    return card, gain


def greedy_eig(
    prior: Sequence[float],
    max_queries: int,
    cards: Sequence[int] = (PERCEPTUAL, GENERATION, CONTEXT),
    likelihoods: Sequence[Sequence[float]] = CARD_LIKELIHOODS,
) -> float:
    """Cumulative EIG of a one-step-greedy policy without replacement.

    This is a strong computable baseline, not a claim of global optimality over the finite horizon.
    """
    if max_queries <= 0 or not cards:
        return 0.0
    prior = normalize(prior)
    card, gain = _best_card(prior, cards, likelihoods)
    remaining = tuple(candidate for candidate in cards if candidate != card)
    positive_probability = sum(
        prior[source] * card_likelihood(card, source, likelihoods) for source in range(len(SOURCES))
    )
    positive_posterior = posterior_from_evidence(prior, ((card, True),), likelihoods)
    negative_posterior = posterior_from_evidence(prior, ((card, False),), likelihoods)
    future = (
        positive_probability * greedy_eig(positive_posterior, max_queries - 1, remaining, likelihoods)
        + (1.0 - positive_probability)
        * greedy_eig(negative_posterior, max_queries - 1, remaining, likelihoods)
    )
    return gain + future


def expected_random_eig(
    prior: Sequence[float],
    max_queries: int,
    cards: Sequence[int] = (PERCEPTUAL, GENERATION, CONTEXT),
    likelihoods: Sequence[Sequence[float]] = CARD_LIKELIHOODS,
) -> float:
    """Expected cumulative EIG when cards are sampled uniformly without replacement."""
    if max_queries <= 0 or not cards:
        return 0.0
    prior = normalize(prior)
    total = 0.0
    for card in cards:
        remaining = tuple(candidate for candidate in cards if candidate != card)
        gain = expected_information_gain(prior, card, likelihoods)
        positive_probability = sum(
            prior[source] * card_likelihood(card, source, likelihoods)
            for source in range(len(SOURCES))
        )
        positive_posterior = posterior_from_evidence(prior, ((card, True),), likelihoods)
        negative_posterior = posterior_from_evidence(prior, ((card, False),), likelihoods)
        future = (
            positive_probability
            * expected_random_eig(positive_posterior, max_queries - 1, remaining, likelihoods)
            + (1.0 - positive_probability)
            * expected_random_eig(negative_posterior, max_queries - 1, remaining, likelihoods)
        )
        total += gain + future
    return total / len(cards)


def softmax(utilities: Sequence[float]) -> tuple[float, ...]:
    if not utilities:
        return ()
    maximum = max(utilities)
    exponentials = [math.exp(value - maximum) for value in utilities]
    total = sum(exponentials)
    return tuple(value / total for value in exponentials)


__all__ = [
    "CARD_IDS",
    "CARD_LIKELIHOODS",
    "CONTEXT",
    "DEFAULT_PRIOR",
    "DESCRIBED",
    "GENERATION",
    "IMAGINED",
    "NEW",
    "NOVELTY",
    "PERCEPTUAL",
    "SEEN",
    "SOURCES",
    "AgentParams",
    "card_likelihood",
    "effective_likelihoods",
    "entropy",
    "expected_information_gain",
    "expected_random_eig",
    "greedy_eig",
    "normalize",
    "posterior_from_evidence",
    "softmax",
]
