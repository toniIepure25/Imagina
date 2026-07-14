"""Counterfactual causal oracle for observed-scale estimand truth.

Computes E[Y(adaptive) - Y(yoked)] using common random numbers where Y is
the production-scored composite_reconstruction_error. This replaces the
latent-parameter approximation.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any

from app.research.cognitive_agent import (
    AgentScenario,
    generate_population,
    generate_trial_response,
)
from app.research.psychophysics.common import StimulusSpec
from app.research.rng_registry import derive_seed

ORACLE_VERSION = "1.0"

WILLIAMS_SEQUENCES = [
    ["adaptive", "fixed", "yoked"],
    ["fixed", "yoked", "adaptive"],
    ["yoked", "adaptive", "fixed"],
    ["yoked", "fixed", "adaptive"],
    ["adaptive", "yoked", "fixed"],
    ["fixed", "adaptive", "yoked"],
]

DEFAULT_TARGETS = [
    StimulusSpec(45, 120, 3.0, 500, 400, 50),
    StimulusSpec(90, 200, 5.0, 300, 600, 30),
    StimulusSpec(135, 60, 1.5, 700, 200, 70),
    StimulusSpec(20, 300, 8.0, 400, 500, 40),
    StimulusSpec(170, 350, 2.0, 600, 300, 60),
]


@dataclass
class OracleResult:
    """Observed-scale counterfactual truth for a specific contrast."""
    contrast_id: str
    effect: float
    effect_se: float
    n_agents: int
    n_trials_per_agent: int
    n_sessions: int
    endpoint_id: str
    scenario_id: str
    oracle_seed: int
    oracle_version: str = ORACLE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class OracleSpecification:
    """Full oracle specification for provenance."""
    contrasts: dict[str, OracleResult] = field(default_factory=dict)
    scenario_hash: str = ""
    schedule_hash: str = ""
    endpoint_version: str = ""
    oracle_version: str = ORACLE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "contrasts": {k: v.to_dict() for k, v in self.contrasts.items()},
            "scenario_hash": self.scenario_hash,
            "schedule_hash": self.schedule_hash,
            "endpoint_version": self.endpoint_version,
            "oracle_version": self.oracle_version,
        }


def compute_oracle_effect(
    scenario: AgentScenario,
    condition_a: str = "adaptive",
    condition_b: str = "yoked",
    n_agents: int = 200,
    n_sessions: int = 3,
    n_trials: int = 10,
    seed: int = 99999,
    targets: list[StimulusSpec] | None = None,
) -> OracleResult:
    """Compute observed-scale counterfactual ATE using common random numbers.

    For each agent, session, and trial:
      1. Generate the frozen latent traits
      2. Use common random stimulus
      3. Produce potential outcome under condition_a
      4. Produce potential outcome under condition_b
      5. Score both with production scoring
      6. Within-unit difference = Y(a) - Y(b)
    Average over agents to get E[Y(a) - Y(b)].
    """
    if targets is None:
        targets = DEFAULT_TARGETS

    pop = generate_population(n_agents, seed=derive_seed(seed, "oracle"), scenario=scenario)
    sequences = WILLIAMS_SEQUENCES

    diffs: list[float] = []
    for ai, agent in enumerate(pop):
        seq = sequences[ai % len(sequences)]
        for si in range(n_sessions):
            prev_a = seq[si - 1] if si > 0 else None
            prev_b = prev_a
            for ti in range(n_trials):
                target = targets[ti % len(targets)]
                trial_seed = derive_seed(seed, "oracle",
                                         participant_id=agent.participant_id,
                                         session_index=si, trial_index=ti)

                y_a = generate_trial_response(
                    agent, target, target, condition_a, si, ti,
                    scenario, False, trial_seed,
                    prev_condition=prev_a,
                )
                y_b = generate_trial_response(
                    agent, target, target, condition_b, si, ti,
                    scenario, False, trial_seed,
                    prev_condition=prev_b,
                )
                diffs.append(y_a["composite_error"] - y_b["composite_error"])

    n = len(diffs)
    mean_diff = sum(diffs) / n if n > 0 else 0.0
    if n > 1:
        variance = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
        se = math.sqrt(variance / n)
    else:
        se = 0.0

    return OracleResult(
        contrast_id=f"{condition_a}_vs_{condition_b}",
        effect=round(mean_diff, 6),
        effect_se=round(se, 6),
        n_agents=n_agents,
        n_trials_per_agent=n_trials,
        n_sessions=n_sessions,
        endpoint_id="composite_reconstruction_error",
        scenario_id=scenario.scenario_id,
        oracle_seed=seed,
    )


def compute_full_oracle(
    scenario: AgentScenario,
    n_agents: int = 200,
    seed: int = 99999,
) -> OracleSpecification:
    """Compute oracle for all prespecified contrasts."""
    contrasts = {}

    for ca, cb in [("adaptive", "yoked"), ("adaptive", "fixed"), ("fixed", "yoked")]:
        contrasts[f"{ca}_vs_{cb}"] = compute_oracle_effect(
            scenario, ca, cb, n_agents=n_agents, seed=seed,
        )

    scenario_data = json.dumps(scenario.to_dict(), sort_keys=True, separators=(",", ":"))
    return OracleSpecification(
        contrasts=contrasts,
        scenario_hash=hashlib.sha256(scenario_data.encode()).hexdigest()[:16],
        endpoint_version="1.0",
    )


def oracle_spec_hash(spec: OracleSpecification) -> str:
    data = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()
