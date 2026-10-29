"""Deterministic Stage 0 simulator for the Source and Imagination Monitor."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from statistics import mean

from app.research.prm.design import (
    Item,
    allowed_conditions,
    fixed_schedule,
    likelihood_table,
    posterior_mean,
    posterior_update,
    select_next_item,
    uniform_posterior,
)
from app.research.prm.metrics import TrialRecord, summarize
from app.research.prm.model import SOURCES, PersonParams, entropy, simulate_trial

CONDITION_INDEX = {name: index for index, name in enumerate(SOURCES)}


@dataclass(frozen=True)
class SimulationConfig:
    n_participants: int = 120
    n_trials: int = 120
    n_items: int = 60
    seed: int = 20261029
    design: str = "adaptive"
    true_d_mean: float = 1.5
    true_d_sd: float = 0.35
    true_bias_sd: float = 0.20
    confidence_noise: float = 0.05

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.n_items < 4 or self.n_items % 4 != 0:
            raise ValueError("n_items must be a positive multiple of four")
        if self.design not in {"adaptive", "fixed"}:
            raise ValueError("design must be 'adaptive' or 'fixed'")


@dataclass
class ParticipantResult:
    true_params: PersonParams
    trials: list[TrialRecord]
    posterior: list[float]
    entropy_trace: list[float]
    estimated_d: float
    estimated_bias: float
    final_entropy: float
    item_sequence: list[str] = field(default_factory=list)


def build_items(n_items: int, seed: int) -> list[Item]:
    if n_items < 4 or n_items % 4 != 0:
        raise ValueError("n_items must be a positive multiple of four")
    rng = random.Random(seed)
    difficulties = (0.6, 1.0, 1.5, 2.0)
    items: list[Item] = []
    for index in range(n_items):
        condition = index % 4
        items.append(
            Item(
                item_id=f"item-{index:03d}",
                condition=condition,
                discriminability=rng.choice(difficulties),
                family="object" if condition in (0, 1) else "spatial",
            )
        )
    return items


def _scaled_params(params: PersonParams, item: Item) -> PersonParams:
    return PersonParams(
        d=params.d * item.discriminability,
        bias=params.bias,
        described_gap=params.described_gap,
        new_gap=params.new_gap,
        lapse=params.lapse,
        confidence_noise=params.confidence_noise,
    )


def _simulate_participant(
    config: SimulationConfig,
    items: list[Item],
    table: list[list[tuple[float, float, float, float]]],
    true_params: PersonParams,
    rng: random.Random,
) -> ParticipantResult:
    posterior = uniform_posterior()
    trials: list[TrialRecord] = []
    entropy_trace = [entropy(posterior)]
    item_sequence: list[str] = []
    condition_counts = [0, 0, 0, 0]

    if config.design == "adaptive":
        for trial_index in range(config.n_trials):
            allowed = allowed_conditions(trial_index, condition_counts, config.n_trials)
            item_index = select_next_item(items, posterior, table, allowed)
            item = items[item_index]
            result = simulate_trial(_scaled_params(true_params, item), item.condition, rng)
            trials.append(
                TrialRecord(
                    source=result.source,
                    choice=result.choice,
                    confidence=result.confidence,
                    correct=result.correct,
                )
            )
            posterior = posterior_update(posterior, table[item_index], CONDITION_INDEX[result.choice])
            entropy_trace.append(entropy(posterior))
            item_sequence.append(item.item_id)
            condition_counts[item.condition] += 1
    else:
        schedule = fixed_schedule(items, config.n_trials, rng.randrange(2**31))
        for item in schedule:
            result = simulate_trial(_scaled_params(true_params, item), item.condition, rng)
            trials.append(
                TrialRecord(
                    source=result.source,
                    choice=result.choice,
                    confidence=result.confidence,
                    correct=result.correct,
                )
            )
            item_index = items.index(item)
            posterior = posterior_update(posterior, table[item_index], CONDITION_INDEX[result.choice])
            entropy_trace.append(entropy(posterior))
            item_sequence.append(item.item_id)
            condition_counts[item.condition] += 1

    return ParticipantResult(
        true_params=true_params,
        trials=trials,
        posterior=posterior,
        entropy_trace=entropy_trace,
        estimated_d=posterior_mean(posterior, 0),
        estimated_bias=posterior_mean(posterior, 1),
        final_entropy=entropy_trace[-1],
        item_sequence=item_sequence,
    )


def run_simulation(config: SimulationConfig) -> dict[str, object]:
    items = build_items(config.n_items, config.seed)
    table = likelihood_table(items)
    results: list[ParticipantResult] = []
    for participant in range(config.n_participants):
        rng = random.Random(config.seed + participant)
        true_d = min(2.5, max(0.5, rng.gauss(config.true_d_mean, config.true_d_sd)))
        true_bias = rng.gauss(0.0, config.true_bias_sd)
        params = PersonParams(
            d=true_d,
            bias=true_bias,
            confidence_noise=config.confidence_noise,
        )
        results.append(_simulate_participant(config, items, table, params, rng))

    true_values = [result.true_params.d for result in results]
    estimated_values = [result.estimated_d for result in results]
    errors = [estimated - true for estimated, true in zip(estimated_values, true_values)]
    final_entropies = [result.final_entropy for result in results]
    accuracies = [sum(1 for trial in result.trials if trial.correct) / len(result.trials) for result in results]
    condition_counts = {name: 0 for name in SOURCES}
    for result in results:
        for trial in result.trials:
            condition_counts[trial.source] += 1

    recovery_bias = mean(errors)
    recovery_rmse = math.sqrt(mean(error**2 for error in errors))
    decision = (
        "PASS"
        if abs(recovery_bias) <= 0.15 and recovery_rmse <= 0.60
        else "REVIEW"
    )
    return {
        "protocol": "ANIMUS-SIM-v1",
        "design": config.design,
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "n_items": config.n_items,
            "seed": config.seed,
            "true_d_mean": config.true_d_mean,
            "true_d_sd": config.true_d_sd,
        },
        "decision": f"PRM_STAGE0_SIMULATION_{decision}",
        "recovery": {
            "mean_true_d": round(mean(true_values), 6),
            "mean_estimated_d": round(mean(estimated_values), 6),
            "bias": round(recovery_bias, 6),
            "rmse": round(recovery_rmse, 6),
        },
        "measurement": {
            "mean_final_entropy": round(mean(final_entropies), 6),
            "mean_accuracy": round(mean(accuracies), 6),
            "condition_counts": condition_counts,
        },
        "example": summarize(results[0].trials).as_dict(),
    }


def check_simulation() -> dict[str, object]:
    """Small deterministic check used by CI and the CLI ``--check`` mode."""
    report = run_simulation(SimulationConfig(n_participants=24, n_trials=40, n_items=40, seed=7))
    if report["decision"] != "PRM_STAGE0_SIMULATION_PASS":
        raise AssertionError(f"simulation recovery gate failed: {report['recovery']}")
    return report


def compare_designs(config: SimulationConfig) -> dict[str, object]:
    """Compare adaptive EIG with the fixed stratified schedule on the same seeds."""
    adaptive = run_simulation(replace(config, design="adaptive"))
    fixed = run_simulation(replace(config, design="fixed"))
    adaptive_entropy = float(adaptive["measurement"]["mean_final_entropy"])  # type: ignore[index]
    fixed_entropy = float(fixed["measurement"]["mean_final_entropy"])  # type: ignore[index]
    reduction = 0.0 if fixed_entropy <= 0 else (fixed_entropy - adaptive_entropy) / fixed_entropy
    return {
        "adaptive": {
            "mean_final_entropy": adaptive_entropy,
            "recovery_bias": adaptive["recovery"]["bias"],  # type: ignore[index]
            "recovery_rmse": adaptive["recovery"]["rmse"],  # type: ignore[index]
        },
        "fixed": {
            "mean_final_entropy": fixed_entropy,
            "recovery_bias": fixed["recovery"]["bias"],  # type: ignore[index]
            "recovery_rmse": fixed["recovery"]["rmse"],  # type: ignore[index]
        },
        "entropy_reduction_fraction": round(reduction, 6),
        "gate": "PASS" if reduction >= 0.20 else "REVIEW",
        "note": (
            "Stage 0 uses a fixed stratified schedule as a stand-in for the human yoked control; "
            "the human study implements true yoking."
        ),
    }


__all__ = [
    "CONDITION_INDEX",
    "ParticipantResult",
    "SimulationConfig",
    "build_items",
    "check_simulation",
    "compare_designs",
    "run_simulation",
]
