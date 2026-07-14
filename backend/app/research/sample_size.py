"""Robust sample-size optimization and Pareto analysis.

Searches a grid across participants, sessions, trials, and scenarios to find
designs that satisfy prespecified requirements for Type-I error, coverage,
power, convergence, and negative-control FP.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_DROPOUT,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_SMALL_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    AgentScenario,
)
from app.research.design_simulation import run_simulation

SAMPLE_SIZE_VERSION = "1.0"

DEFAULT_N_GRID = [12, 18, 24, 30]
DEFAULT_SESSION_GRID = [3]
DEFAULT_TRIAL_GRID = [5, 8]


@dataclass
class DesignPoint:
    n_participants: int
    sessions: int
    trials_per_task: int
    total_trials: int
    power_small: float
    power_medium: float
    type_i: float
    coverage: float
    convergence: float
    nc_fp: float
    valid_inference: float
    robustness_dropout: float
    robustness_carryover: float
    meets_requirements: bool

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ParetoTable:
    points: list[DesignPoint] = field(default_factory=list)
    requirements: dict[str, float] = field(default_factory=dict)
    version: str = SAMPLE_SIZE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "requirements": self.requirements,
            "version": self.version,
        }


DEFAULT_REQUIREMENTS = {
    "max_type_i": 0.10,
    "min_coverage": 0.85,
    "min_power_small": 0.50,
    "min_power_medium": 0.70,
    "min_convergence": 0.70,
    "max_nc_fp": 0.15,
    "min_valid_inference": 0.60,
}


def search_design_grid(
    n_grid: list[int] | None = None,
    session_grid: list[int] | None = None,
    trial_grid: list[int] | None = None,
    requirements: dict[str, float] | None = None,
    base_seed: int = 42,
    n_iterations: int = 15,
) -> ParetoTable:
    """Search over design parameters to find satisfactory configurations."""
    if n_grid is None:
        n_grid = DEFAULT_N_GRID
    if session_grid is None:
        session_grid = DEFAULT_SESSION_GRID
    if trial_grid is None:
        trial_grid = DEFAULT_TRIAL_GRID
    if requirements is None:
        requirements = dict(DEFAULT_REQUIREMENTS)

    scenarios_to_test = {
        "strict_null": SCENARIO_STRICT_NULL,
        "small_adaptive": SCENARIO_SMALL_ADAPTIVE,
        "medium_adaptive": SCENARIO_MEDIUM_ADAPTIVE,
        "dropout": SCENARIO_DROPOUT,
        "carryover": SCENARIO_CARRYOVER,
    }

    table = ParetoTable(requirements=requirements)

    for n in n_grid:
        for s in session_grid:
            for t in trial_grid:
                results = {}
                for sid, scenario in scenarios_to_test.items():
                    results[sid] = run_simulation(
                        scenario, n_iterations=n_iterations,
                        n_participants=n, sessions_per_participant=s,
                        trials_per_task=t, base_seed=base_seed, mode="unit",
                    )

                null_r = results["strict_null"]
                small_r = results["small_adaptive"]
                medium_r = results["medium_adaptive"]
                dropout_r = results["dropout"]
                carry_r = results["carryover"]

                point = DesignPoint(
                    n_participants=n,
                    sessions=s,
                    trials_per_task=t,
                    total_trials=n * s * t * 4,
                    power_small=small_r.power,
                    power_medium=medium_r.power,
                    type_i=null_r.type_i_error,
                    coverage=null_r.coverage,
                    convergence=null_r.convergence_rate,
                    nc_fp=null_r.negative_control_fp_rate,
                    valid_inference=null_r.valid_inference_rate,
                    robustness_dropout=dropout_r.valid_inference_rate,
                    robustness_carryover=carry_r.valid_inference_rate,
                    meets_requirements=False,
                )

                point.meets_requirements = (
                    point.type_i <= requirements["max_type_i"]
                    and point.coverage >= requirements["min_coverage"]
                    and point.power_medium >= requirements["min_power_medium"]
                    and point.convergence >= requirements["min_convergence"]
                    and point.nc_fp <= requirements["max_nc_fp"]
                    and point.valid_inference >= requirements["min_valid_inference"]
                )

                table.points.append(point)

    return table


def sample_size_hash(table: ParetoTable) -> str:
    data = json.dumps(table.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()
