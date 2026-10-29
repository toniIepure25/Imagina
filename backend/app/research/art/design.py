"""Design helpers for the Stage 0 Active Reality Testing simulator."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.research.art.model import (
    CONTEXT,
    DEFAULT_PRIOR,
    GENERATION,
    NOVELTY,
    PERCEPTUAL,
    SOURCES,
)


@dataclass(frozen=True)
class CardSpec:
    card: int
    name: str
    cost: float = 1.0


@dataclass(frozen=True)
class BlockSpec:
    name: str
    n_trials: int
    cost_multiplier: float = 1.0
    source_prior: tuple[float, float, float, float] = DEFAULT_PRIOR


DEFAULT_CARDS: tuple[CardSpec, ...] = (
    CardSpec(PERCEPTUAL, "perceptual", 1.0),
    CardSpec(GENERATION, "generation", 1.0),
    CardSpec(CONTEXT, "context", 1.0),
    CardSpec(NOVELTY, "novelty", 1.0),
)


def card_costs(cards: Sequence[CardSpec] = DEFAULT_CARDS, multiplier: float = 1.0) -> tuple[float, ...]:
    if multiplier < 0:
        raise ValueError("cost multiplier must be non-negative")
    return tuple(card.cost * multiplier for card in cards)


def source_schedule(
    n_trials: int,
    seed: int,
    prior: Sequence[float] = DEFAULT_PRIOR,
) -> list[int]:
    """Return a deterministic source schedule with balanced counts when the prior is uniform."""
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    if len(prior) != len(SOURCES):
        raise ValueError("prior must have one probability per source")
    rng = random.Random(seed)
    if all(abs(value - 0.25) < 1e-12 for value in prior):
        schedule = [index % len(SOURCES) for index in range(n_trials)]
    else:
        total = sum(prior)
        if total <= 0:
            raise ValueError("prior must have positive mass")
        probabilities = [value / total for value in prior]
        schedule = rng.choices(range(len(SOURCES)), weights=probabilities, k=n_trials)
    rng.shuffle(schedule)
    return schedule


def default_blocks(n_trials: int = 80) -> tuple[BlockSpec, ...]:
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    return (BlockSpec("active", n_trials),)


def yoked_card_sequence(queries: Sequence[tuple[int, bool]]) -> tuple[int, ...]:
    """Replay only the card identities from a recorded active sequence."""
    return tuple(card for card, _ in queries)


__all__ = [
    "DEFAULT_CARDS",
    "CardSpec",
    "BlockSpec",
    "card_costs",
    "default_blocks",
    "source_schedule",
    "yoked_card_sequence",
]
