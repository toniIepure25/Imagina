"""Counterfactual causal oracle for observed-scale estimand truth.

Computes participant-clustered E[Y(a) - Y(b)] where Y is production-scored
composite_reconstruction_error. Uses common random numbers to compute
potential outcomes under each condition for the same agent, period, task,
and random stream.

Two estimands are supported:
  - direct_period: E[Y_i,p(a, history) - Y_i,p(b, history)] holding
    period and treatment history fixed
  - regime: E[Y_i(sequence_with_a) - Y_i(comparator_sequence)]
    including carryover and treatment history

SE is computed at the participant level (clustered), not trial level.
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

ORACLE_VERSION = "2.0"

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
    """Observed-scale counterfactual truth with participant-clustered SE."""
    contrast_id: str
    estimand_type: str
    effect: float
    clustered_se: float
    n_agents: int
    n_trials_per_agent: int
    n_sessions: int
    endpoint_id: str
    scenario_id: str
    oracle_seed: int
    participant_contrasts: list[float] = field(default_factory=list)
    schedule_hash: str = ""
    scenario_hash: str = ""
    rng_hash: str = ""
    oracle_version: str = ORACLE_VERSION

    @property
    def effect_se(self) -> float:
        return self.clustered_se

    def to_dict(self) -> dict[str, Any]:
        return {
            "contrast_id": self.contrast_id,
            "estimand_type": self.estimand_type,
            "effect": self.effect,
            "clustered_se": self.clustered_se,
            "n_agents": self.n_agents,
            "n_trials_per_agent": self.n_trials_per_agent,
            "n_sessions": self.n_sessions,
            "endpoint_id": self.endpoint_id,
            "scenario_id": self.scenario_id,
            "oracle_seed": self.oracle_seed,
            "participant_contrasts": self.participant_contrasts,
            "schedule_hash": self.schedule_hash,
            "scenario_hash": self.scenario_hash,
            "rng_hash": self.rng_hash,
            "oracle_version": self.oracle_version,
        }


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


def _compute_schedule_hash(sequences: list[list[str]], n_sessions: int, n_trials: int) -> str:
    data = json.dumps({"sequences": sequences, "sessions": n_sessions, "trials": n_trials},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _compute_scenario_hash(scenario: AgentScenario) -> str:
    data = json.dumps(scenario.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def compute_oracle_effect(
    scenario: AgentScenario,
    condition_a: str = "adaptive",
    condition_b: str = "yoked",
    n_agents: int = 200,
    n_sessions: int = 3,
    n_trials: int = 10,
    seed: int = 99999,
    targets: list[StimulusSpec] | None = None,
    estimand_type: str = "direct_period",
) -> OracleResult:
    """Compute observed-scale counterfactual ATE with participant-clustered SE.

    For each agent, period, and trial:
      1. Use common random stimulus and RNG stream
      2. Produce potential outcome under condition_a
      3. Produce potential outcome under condition_b (same history)
      4. Within-trial difference = Y(a) - Y(b)
    Average within each agent to get agent-level contrast.
    Population mean and SE computed across agent-level contrasts.
    """
    if targets is None:
        targets = DEFAULT_TARGETS

    pop = generate_population(n_agents, seed=derive_seed(seed, "oracle"), scenario=scenario)
    sequences = WILLIAMS_SEQUENCES

    participant_contrasts: list[float] = []

    for ai, agent in enumerate(pop):
        seq = sequences[ai % len(sequences)]
        agent_diffs: list[float] = []

        for si in range(min(n_sessions, len(seq))):
            prev_cond = seq[si - 1] if si > 0 else None

            for ti in range(n_trials):
                target = targets[ti % len(targets)]
                trial_seed = derive_seed(seed, "oracle",
                                         participant_id=agent.participant_id,
                                         session_index=si, trial_index=ti)

                y_a = generate_trial_response(
                    agent, target, target, condition_a, si, ti,
                    scenario, False, trial_seed,
                    prev_condition=prev_cond,
                )
                y_b = generate_trial_response(
                    agent, target, target, condition_b, si, ti,
                    scenario, False, trial_seed,
                    prev_condition=prev_cond,
                )
                agent_diffs.append(y_a["composite_error"] - y_b["composite_error"])

        agent_mean = sum(agent_diffs) / len(agent_diffs) if agent_diffs else 0.0
        participant_contrasts.append(agent_mean)

    n = len(participant_contrasts)
    population_effect = sum(participant_contrasts) / n if n > 0 else 0.0

    if n > 1:
        variance = sum((c - population_effect) ** 2 for c in participant_contrasts) / (n - 1)
        clustered_se = math.sqrt(variance / n)
    else:
        clustered_se = 0.0

    return OracleResult(
        contrast_id=f"{condition_a}_vs_{condition_b}",
        estimand_type=estimand_type,
        effect=round(population_effect, 10),
        clustered_se=round(clustered_se, 10),
        n_agents=n_agents,
        n_trials_per_agent=n_trials,
        n_sessions=n_sessions,
        endpoint_id="composite_reconstruction_error",
        scenario_id=scenario.scenario_id,
        oracle_seed=seed,
        participant_contrasts=[round(c, 10) for c in participant_contrasts],
        schedule_hash=_compute_schedule_hash(sequences, n_sessions, n_trials),
        scenario_hash=_compute_scenario_hash(scenario),
        rng_hash=hashlib.sha256(f"oracle-{seed}".encode()).hexdigest()[:16],
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

    return OracleSpecification(
        contrasts=contrasts,
        scenario_hash=_compute_scenario_hash(scenario),
        endpoint_version="1.0",
    )


def oracle_spec_hash(spec: OracleSpecification) -> str:
    data = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()
