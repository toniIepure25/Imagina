from __future__ import annotations

import random
from itertools import permutations

from app.schemas.research import FeedbackCondition


def generate_condition_sequence(
    conditions: list[FeedbackCondition],
    seed: int,
) -> list[FeedbackCondition]:
    rng = random.Random(seed)
    all_orders = list(permutations(conditions))
    chosen = rng.choice(all_orders)
    return list(chosen)


def generate_block_randomization(
    conditions: list[FeedbackCondition],
    n_participants: int,
    base_seed: int = 42,
) -> list[list[FeedbackCondition]]:
    all_orders = list(permutations(conditions))
    rng = random.Random(base_seed)

    assignments: list[list[FeedbackCondition]] = []
    block: list[list[FeedbackCondition]] = []

    for _ in range(n_participants):
        if not block:
            block = [list(o) for o in all_orders]
            rng.shuffle(block)
        assignments.append(block.pop())

    return assignments


def verify_counterbalance(
    assignments: list[list[FeedbackCondition]],
    conditions: list[FeedbackCondition],
) -> dict:
    all_orders = list(permutations(conditions))
    order_counts: dict[tuple, int] = {order: 0 for order in all_orders}
    for seq in assignments:
        key = tuple(seq)
        if key in order_counts:
            order_counts[key] += 1

    counts = list(order_counts.values())
    return {
        "total_participants": len(assignments),
        "n_conditions": len(conditions),
        "n_possible_orders": len(all_orders),
        "order_counts": {str(k): v for k, v in order_counts.items()},
        "min_per_order": min(counts) if counts else 0,
        "max_per_order": max(counts) if counts else 0,
        "balanced": max(counts) - min(counts) <= 1 if counts else True,
    }
