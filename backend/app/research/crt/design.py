"""Design helpers for the Stage 0 Counterfactual Reality Testing simulator."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.research.crt.model import (
    ALL_TESTS,
    DEFAULT_PRIOR,
    SOURCES,
    TEST_AGENCY,
    TEST_COMPLEXITY,
    TEST_COSTS,
    TEST_IDS,
)


@dataclass(frozen=True)
class TestSpec:
    test: int
    name: str
    cost: float
    complexity: float
    agency_value: float


@dataclass(frozen=True)
class BlockSpec:
    name: str
    n_trials: int
    condition: str
    cost_multiplier: float = 1.0
    source_prior: tuple[float, float, float, float] = DEFAULT_PRIOR


DEFAULT_TESTS: tuple[TestSpec, ...] = tuple(
    TestSpec(
        test=index,
        name=TEST_IDS[index],
        cost=TEST_COSTS[index],
        complexity=TEST_COMPLEXITY[index],
        agency_value=TEST_AGENCY[index],
    )
    for index in ALL_TESTS
)

CONDITIONS: tuple[str, ...] = (
    "observe",
    "active_intervene",
    "active_predict",
    "yoked_intervene",
    "yoked_predict",
)


def test_costs(tests: Sequence[TestSpec] = DEFAULT_TESTS, multiplier: float = 1.0) -> tuple[float, ...]:
    if multiplier < 0:
        raise ValueError("cost multiplier must be non-negative")
    return tuple(test.cost * multiplier for test in tests)


def test_complexities(tests: Sequence[TestSpec] = DEFAULT_TESTS) -> tuple[float, ...]:
    return tuple(test.complexity for test in tests)


def test_agency_values(tests: Sequence[TestSpec] = DEFAULT_TESTS) -> tuple[float, ...]:
    return tuple(test.agency_value for test in tests)


def source_schedule(
    n_trials: int,
    seed: int,
    prior: Sequence[float] = DEFAULT_PRIOR,
) -> list[int]:
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


def default_blocks() -> tuple[BlockSpec, ...]:
    return (
        BlockSpec("observe", 20, "observe"),
        BlockSpec("active_intervene", 30, "active_intervene"),
        BlockSpec("active_predict", 30, "active_predict"),
        BlockSpec("yoked_intervene", 30, "yoked_intervene"),
        BlockSpec("yoked_predict", 30, "yoked_predict"),
    )


def yoked_test_sequence(tests: Sequence[tuple[int, bool]]) -> tuple[int, ...]:
    return tuple(test for test, _ in tests)


__all__ = [
    "CONDITIONS",
    "DEFAULT_TESTS",
    "BlockSpec",
    "TestSpec",
    "default_blocks",
    "source_schedule",
    "test_agency_values",
    "test_complexities",
    "test_costs",
    "yoked_test_sequence",
]
