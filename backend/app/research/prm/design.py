"""Adaptive design utilities for the Source and Imagination Monitor.

Stage 0 uses a discrete grid over person parameters. The expected-information-gain calculation is
therefore exact for the grid and deterministic for a fixed posterior, which makes the simulator
auditable without numpy or scipy.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.research.prm.model import PersonParams, entropy, response_distribution

D_GRID: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 2.5)
BIAS_GRID: tuple[float, ...] = (-0.5, 0.0, 0.5)
THETA_GRID: tuple[tuple[float, float], ...] = tuple(
    (d, bias) for d in D_GRID for bias in BIAS_GRID
)
COVERAGE_FRACTION = 0.15
MAX_FAMILY_FRACTION = 0.40


@dataclass(frozen=True)
class Item:
    item_id: str
    condition: int
    discriminability: float = 1.0
    family: str = "object"


def theta_params(theta: tuple[float, float], **overrides: float) -> PersonParams:
    d, bias = theta
    return PersonParams(d=d, bias=bias, **overrides)


def uniform_posterior() -> list[float]:
    weight = 1.0 / len(THETA_GRID)
    return [weight for _ in THETA_GRID]


def normalize(weights: Sequence[float]) -> list[float]:
    total = sum(weights)
    if total <= 0:
        return uniform_posterior()
    return [max(0.0, weight) / total for weight in weights]


def posterior_update(
    posterior: Sequence[float], likelihoods: Sequence[float], observed_choice: int
) -> list[float]:
    if len(posterior) != len(THETA_GRID):
        raise ValueError("posterior length does not match theta grid")
    if not 0 <= observed_choice < 4:
        raise ValueError("observed_choice must be in [0, 3]")
    updated = [
        posterior[index] * likelihoods[index][observed_choice]
        for index in range(len(THETA_GRID))
    ]
    return normalize(updated)


def likelihood_table(items: Sequence[Item]) -> list[list[tuple[float, float, float, float]]]:
    """Return ``table[item_index][theta_index]`` response probabilities."""
    table = []
    for item in items:
        row = []
        for theta in THETA_GRID:
            params = theta_params(theta)
            scaled = PersonParams(
                d=params.d * item.discriminability,
                bias=params.bias,
                described_gap=params.described_gap,
                new_gap=params.new_gap,
            )
            row.append(response_distribution(scaled, item.condition))
        table.append(row)
    return table


def expected_information_gain(
    posterior: Sequence[float],
    likelihoods: Sequence[tuple[float, float, float, float]],
) -> float:
    """Expected entropy reduction about theta from observing one item response."""
    prior_entropy = entropy(list(posterior))
    predictive = [0.0, 0.0, 0.0, 0.0]
    for index, weight in enumerate(posterior):
        for choice in range(4):
            predictive[choice] += weight * likelihoods[index][choice]
    expected_posterior_entropy = 0.0
    for choice in range(4):
        probability = predictive[choice]
        if probability <= 0:
            continue
        posterior_given_choice = normalize(
            [posterior[index] * likelihoods[index][choice] for index in range(len(posterior))]
        )
        expected_posterior_entropy += probability * entropy(posterior_given_choice)
    return max(0.0, prior_entropy - expected_posterior_entropy)


def select_next_item(
    items: Sequence[Item],
    posterior: Sequence[float],
    table: Sequence[Sequence[tuple[float, float, float, float]]],
    allowed_conditions: set[int] | None = None,
) -> int:
    """Select the item with the highest EIG; ties break on item_id for determinism."""
    best_index = -1
    best_gain = -1.0
    for index, item in enumerate(items):
        if allowed_conditions is not None and item.condition not in allowed_conditions:
            continue
        gain = expected_information_gain(posterior, table[index])
        if gain > best_gain + 1e-12 or (
            abs(gain - best_gain) <= 1e-12 and (best_index < 0 or item.item_id < items[best_index].item_id)
        ):
            best_index = index
            best_gain = gain
    if best_index < 0:
        raise ValueError("no item satisfies the allowed conditions")
    return best_index


def allowed_conditions(
    trial_index: int, counts: Sequence[int], n_trials: int
) -> set[int] | None:
    """Return the conditions allowed at this trial under the coverage and cap rules.

    The floor reserves enough remaining trials to bring every source to at least 15% of the
    session. The cap prevents one source from exceeding 40% of the session. A ``None`` return means
    all conditions are allowed.
    """
    if trial_index < 0 or trial_index >= n_trials:
        raise ValueError("trial_index must be inside the session")
    if len(counts) != 4:
        raise ValueError("counts must contain four source counts")
    remaining = n_trials - trial_index
    target = max(1, int(COVERAGE_FRACTION * n_trials))
    deficits = [max(0, target - count) for count in counts]
    if remaining <= sum(deficits):
        largest = max(range(4), key=lambda condition: (deficits[condition], -condition))
        return {largest}
    cap = max(1, int(MAX_FAMILY_FRACTION * n_trials))
    allowed = {condition for condition, count in enumerate(counts) if count < cap}
    return allowed or None


def fixed_schedule(items: Sequence[Item], n_trials: int, seed: int) -> list[Item]:
    """Build a stratified fixed schedule with balanced source counts.

    The human study uses a true yoked schedule. Stage 0 uses this fixed schedule as the comparison
    condition because it isolates selection from condition balance without requiring a driver
    participant.
    """
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")
    for condition in range(4):
        if not any(item.condition == condition for item in items):
            raise ValueError(f"no items for condition {condition}")
    rng = random.Random(seed)
    pools: dict[int, list[Item]] = {condition: [] for condition in range(4)}
    for item in items:
        pools[item.condition].append(item)
    for pool in pools.values():
        rng.shuffle(pool)

    schedule: list[Item] = []
    while len(schedule) < n_trials:
        for condition in range(4):
            pool = pools[condition]
            if not pool:
                pool.extend(item for item in items if item.condition == condition)
                rng.shuffle(pool)
            schedule.append(pool.pop())
            if len(schedule) >= n_trials:
                break
    return schedule


def posterior_mean(posterior: Sequence[float], dimension: int = 0) -> float:
    if dimension == 0:
        return sum(weight * theta[0] for weight, theta in zip(posterior, THETA_GRID))
    if dimension == 1:
        return sum(weight * theta[1] for weight, theta in zip(posterior, THETA_GRID))
    raise ValueError("dimension must be 0 (d) or 1 (bias)")


def posterior_sd(posterior: Sequence[float], dimension: int = 0) -> float:
    mean = posterior_mean(posterior, dimension)
    variance = sum(
        weight * (theta[dimension] - mean) ** 2 for weight, theta in zip(posterior, THETA_GRID)
    )
    return variance**0.5
