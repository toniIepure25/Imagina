"""Deterministic calibration procedures for psychophysics task difficulty.

Estimates an individual difficulty range that avoids ceiling/floor effects.
Calibration is independent of experimental condition and frozen before
the first experimental session.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field

CALIBRATION_VERSION = "1.0"


@dataclass
class StaircaseState:
    current_level: float
    step_size: float
    n_reversals: int = 0
    n_trials: int = 0
    n_correct: int = 0
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0
    reversal_levels: list[float] = field(default_factory=list)
    direction: int = 0  # 1=going up, -1=going down, 0=initial
    history: list[dict] = field(default_factory=list)


@dataclass
class StaircaseTransition:
    trial_index: int
    stimulus_level: float
    response_correct: bool
    new_level: float
    reversal: bool
    step_size: float


@dataclass
class PsychometricEstimate:
    threshold: float
    uncertainty: float
    converged: bool
    n_trials: int
    n_reversals: int
    method: str


@dataclass
class CalibrationResult:
    protocol_version: str
    participant_id: str
    task_family: str
    threshold_estimate: float
    uncertainty: float
    converged: bool
    n_trials: int
    n_reversals: int
    frozen_difficulty: dict[str, float]
    calibration_hash: str
    convergence_diagnostics: dict
    trials: list[dict]
    seed: int


def transformed_up_down_staircase(
    responses: list[bool],
    start_level: float = 0.5,
    step_size: float = 0.1,
    min_step: float = 0.02,
    step_factor: float = 0.7071,
    up_count: int = 1,
    down_count: int = 3,
    max_reversals: int = 12,
    min_level: float = 0.05,
    max_level: float = 0.95,
) -> tuple[StaircaseState, list[StaircaseTransition]]:
    """Run a transformed up-down staircase on a sequence of responses.

    3-down/1-up targets approximately the 79.4% correct performance point.
    """
    state = StaircaseState(current_level=start_level, step_size=step_size)
    transitions: list[StaircaseTransition] = []

    for i, correct in enumerate(responses):
        old_level = state.current_level
        state.n_trials += 1

        if correct:
            state.n_correct += 1
            state.consecutive_correct += 1
            state.consecutive_incorrect = 0
        else:
            state.consecutive_correct = 0
            state.consecutive_incorrect += 1

        reversal = False
        new_direction = state.direction

        if state.consecutive_correct >= down_count:
            new_direction = -1
            if state.direction == 1:
                reversal = True
            state.current_level = max(min_level, state.current_level - state.step_size)
            state.consecutive_correct = 0

        elif state.consecutive_incorrect >= up_count:
            new_direction = 1
            if state.direction == -1:
                reversal = True
            state.current_level = min(max_level, state.current_level + state.step_size)
            state.consecutive_incorrect = 0

        if reversal:
            state.n_reversals += 1
            state.reversal_levels.append(old_level)
            if state.step_size * step_factor >= min_step:
                state.step_size *= step_factor

        state.direction = new_direction

        transitions.append(StaircaseTransition(
            trial_index=i,
            stimulus_level=old_level,
            response_correct=correct,
            new_level=state.current_level,
            reversal=reversal,
            step_size=state.step_size,
        ))

        state.history.append({
            "trial": i, "level": old_level,
            "correct": correct, "reversal": reversal,
        })

        if state.n_reversals >= max_reversals:
            break

    return state, transitions


def estimate_threshold(state: StaircaseState, discard_initial: int = 4) -> PsychometricEstimate:
    """Estimate psychometric threshold from reversal levels."""
    usable = state.reversal_levels[discard_initial:]
    if len(usable) < 2:
        usable = state.reversal_levels

    converged = len(usable) >= 4

    if not usable:
        return PsychometricEstimate(
            threshold=state.current_level,
            uncertainty=1.0,
            converged=False,
            n_trials=state.n_trials,
            n_reversals=state.n_reversals,
            method="transformed_up_down",
        )

    threshold = sum(usable) / len(usable)
    if len(usable) >= 2:
        mean = threshold
        variance = sum((x - mean) ** 2 for x in usable) / (len(usable) - 1)
        uncertainty = math.sqrt(variance) / math.sqrt(len(usable))
    else:
        uncertainty = 0.5

    return PsychometricEstimate(
        threshold=round(threshold, 4),
        uncertainty=round(uncertainty, 4),
        converged=converged,
        n_trials=state.n_trials,
        n_reversals=state.n_reversals,
        method="transformed_up_down",
    )


def run_calibration(
    participant_id: str,
    task_family: str,
    response_function: callable,
    seed: int,
    n_trials: int = 60,
    start_level: float = 0.5,
) -> CalibrationResult:
    """Run a complete calibration procedure and return frozen results.

    response_function(level, trial_index, rng) -> bool
    """
    rng = random.Random(seed)
    responses: list[bool] = []
    for i in range(n_trials):
        level = start_level if i == 0 else state.current_level  # noqa: F821
        correct = response_function(level, i, rng)
        responses.append(correct)
        if i == 0:
            state, transitions = transformed_up_down_staircase(
                responses[:1], start_level=start_level,
            )
        else:
            state, transitions = transformed_up_down_staircase(
                responses, start_level=start_level,
            )

    estimate = estimate_threshold(state)

    frozen_difficulty = {
        "mask_strength": round(estimate.threshold, 4),
        "retention_delay_s": round(estimate.threshold * 10, 2),
        "distractor_similarity": round(estimate.threshold, 4),
        "transform_magnitude": round(estimate.threshold * 45, 2),
    }

    trial_records = [
        {"trial": t.trial_index, "level": round(t.stimulus_level, 4),
         "correct": t.response_correct, "reversal": t.reversal}
        for t in transitions
    ]

    cal_data = json.dumps({
        "participant_id": participant_id,
        "task_family": task_family,
        "threshold": estimate.threshold,
        "frozen_difficulty": frozen_difficulty,
        "seed": seed,
        "version": CALIBRATION_VERSION,
    }, sort_keys=True, separators=(",", ":"))
    cal_hash = hashlib.sha256(cal_data.encode()).hexdigest()

    return CalibrationResult(
        protocol_version=CALIBRATION_VERSION,
        participant_id=participant_id,
        task_family=task_family,
        threshold_estimate=estimate.threshold,
        uncertainty=estimate.uncertainty,
        converged=estimate.converged,
        n_trials=state.n_trials,
        n_reversals=state.n_reversals,
        frozen_difficulty=frozen_difficulty,
        calibration_hash=cal_hash,
        convergence_diagnostics={
            "final_step_size": round(state.step_size, 4),
            "reversal_levels": [round(r, 4) for r in state.reversal_levels],
            "accuracy": round(state.n_correct / max(1, state.n_trials), 4),
        },
        trials=trial_records,
        seed=seed,
    )
