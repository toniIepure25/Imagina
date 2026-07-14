"""Hierarchical cognitive agent model for scientific simulation.

Generates synthetic participants from population distributions, then trials
conditionally on participant-level latent traits. Observed outcomes are
generated from latent state + stimulus + noise, then scored using production
scoring code.

This replaces simplistic random response generation with a model that
separates imagery precision, control, stability, metacognition, motor skill,
confidence bias, learning, fatigue, expectancy, and condition effects.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any

from app.research.objective_endpoints import (
    composite_reconstruction_error,
    hue_error,
    orientation_error,
    position_error,
    size_error,
    spatial_frequency_error,
)
from app.research.psychophysics.common import ResponseSpec, StimulusSpec

MODEL_VERSION = "3.0"


@dataclass
class AgentTraits:
    """Latent trait profile for a synthetic cognitive agent."""
    participant_id: str
    baseline_imagery_precision: float
    imagery_control: float
    imagery_stability: float
    perceptual_matching_skill: float
    motor_precision: float
    metacognitive_sensitivity: float
    confidence_bias: float
    subjective_vividness_bias: float
    learning_rate: float
    fatigue_susceptibility: float
    expectancy_response: float
    condition_treatment_response: float
    period_effect: float
    carryover_effect: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "baseline_imagery_precision": self.baseline_imagery_precision,
            "imagery_control": self.imagery_control,
            "imagery_stability": self.imagery_stability,
            "perceptual_matching_skill": self.perceptual_matching_skill,
            "motor_precision": self.motor_precision,
            "metacognitive_sensitivity": self.metacognitive_sensitivity,
            "confidence_bias": self.confidence_bias,
            "subjective_vividness_bias": self.subjective_vividness_bias,
            "learning_rate": self.learning_rate,
            "fatigue_susceptibility": self.fatigue_susceptibility,
            "expectancy_response": self.expectancy_response,
            "condition_treatment_response": self.condition_treatment_response,
            "period_effect": self.period_effect,
            "carryover_effect": self.carryover_effect,
        }


@dataclass
class AgentScenario:
    """Configurable scenario for simulation experiments."""
    scenario_id: str
    version: str = MODEL_VERSION
    adaptive_precision_effect: float = 0.0
    adaptive_control_effect: float = 0.0
    adaptive_stability_effect: float = 0.0
    adaptive_learning_boost: float = 0.0
    adaptive_fatigue_regulation: float = 0.0
    fixed_practice_effect: float = 0.0
    yoked_practice_effect: float = 0.0
    placebo_effect: float = 0.0
    objective_expectancy_effect: float = 0.0
    expectancy_vividness_effect: float = 0.0
    period_effect_strength: float = 0.0
    carryover_strength: float = 0.0
    dropout_rate: float = 0.0
    dropout_bias: str = "none"
    perceptual_control_improvement: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


# --- Predefined scenarios ---

SCENARIO_STRICT_NULL = AgentScenario(
    scenario_id="strict_null",
    description="All conditions identical — for Type-I error validation",
)

SCENARIO_SMALL_ADAPTIVE = AgentScenario(
    scenario_id="small_adaptive",
    adaptive_precision_effect=0.08,
    adaptive_control_effect=0.05,
    adaptive_learning_boost=0.03,
    description="Small genuine adaptive benefit on precision and control",
)

SCENARIO_MEDIUM_ADAPTIVE = AgentScenario(
    scenario_id="medium_adaptive",
    adaptive_precision_effect=0.15,
    adaptive_control_effect=0.10,
    adaptive_stability_effect=0.05,
    adaptive_learning_boost=0.05,
    adaptive_fatigue_regulation=0.02,
    description="Medium genuine adaptive benefit across constructs",
)

SCENARIO_SUBJECTIVE_ONLY = AgentScenario(
    scenario_id="subjective_only",
    placebo_effect=0.10,
    expectancy_vividness_effect=0.3,
    description="Vividness improves but objective precision does not",
)

SCENARIO_PRACTICE_ONLY = AgentScenario(
    scenario_id="practice_only",
    fixed_practice_effect=0.08,
    yoked_practice_effect=0.08,
    adaptive_precision_effect=0.0,
    adaptive_learning_boost=0.08,
    description="All conditions improve equally from practice",
)

SCENARIO_PLACEBO_EXPECTANCY = AgentScenario(
    scenario_id="placebo_expectancy",
    placebo_effect=0.05,
    expectancy_vividness_effect=0.4,
    description="Adaptive labeling affects self-report only",
)

SCENARIO_CARRYOVER = AgentScenario(
    scenario_id="carryover",
    adaptive_precision_effect=0.12,
    carryover_strength=0.5,
    description="Adaptive effects persist into later conditions",
)

SCENARIO_DROPOUT = AgentScenario(
    scenario_id="differential_dropout",
    adaptive_precision_effect=0.12,
    dropout_rate=0.20,
    dropout_bias="low_performer",
    description="Low performers drop out differentially",
)

SCENARIO_PERCEPTUAL_ONLY = AgentScenario(
    scenario_id="perceptual_control_only",
    perceptual_control_improvement=0.10,
    description="Motor/perceptual matching improves but not imagery",
)

SCENARIOS: dict[str, AgentScenario] = {
    s.scenario_id: s for s in [
        SCENARIO_STRICT_NULL, SCENARIO_SMALL_ADAPTIVE, SCENARIO_MEDIUM_ADAPTIVE,
        SCENARIO_SUBJECTIVE_ONLY, SCENARIO_PRACTICE_ONLY, SCENARIO_PLACEBO_EXPECTANCY,
        SCENARIO_CARRYOVER, SCENARIO_DROPOUT, SCENARIO_PERCEPTUAL_ONLY,
    ]
}


def generate_population(
    n_participants: int,
    seed: int,
    scenario: AgentScenario | None = None,
) -> list[AgentTraits]:
    """Generate a population of synthetic cognitive agents from hierarchical distributions."""
    if scenario is None:
        scenario = SCENARIO_STRICT_NULL
    rng = random.Random(seed)

    agents: list[AgentTraits] = []
    for i in range(n_participants):
        precision = _clamp01(rng.gauss(0.55, 0.15))
        control = _clamp01(precision * 0.7 + rng.gauss(0.0, 0.12))
        stability = _clamp01(precision * 0.5 + rng.gauss(0.2, 0.10))
        perceptual = _clamp01(precision * 0.4 + rng.gauss(0.4, 0.10))
        motor = _clamp01(rng.gauss(0.70, 0.10))
        metacog = _clamp01(rng.gauss(0.50, 0.15))
        conf_bias = rng.gauss(0.0, 0.3)
        vivid_bias = rng.gauss(0.0, 0.4)
        learn = max(0.0, rng.gauss(0.05, 0.03))
        fatigue = max(0.0, rng.gauss(0.03, 0.02))
        expectancy = _clamp01(rng.gauss(0.5, 0.15))
        treatment = rng.gauss(1.0, 0.2)
        period = rng.gauss(0.0, scenario.period_effect_strength)
        carryover = rng.gauss(0.0, scenario.carryover_strength * 0.1)

        agents.append(AgentTraits(
            participant_id=f"agent-{seed}-{i:04d}",
            baseline_imagery_precision=precision,
            imagery_control=control,
            imagery_stability=stability,
            perceptual_matching_skill=perceptual,
            motor_precision=motor,
            metacognitive_sensitivity=metacog,
            confidence_bias=conf_bias,
            subjective_vividness_bias=vivid_bias,
            learning_rate=learn,
            fatigue_susceptibility=fatigue,
            expectancy_response=expectancy,
            condition_treatment_response=treatment,
            period_effect=period,
            carryover_effect=carryover,
        ))
    return agents


def generate_trial_response(
    agent: AgentTraits,
    target: StimulusSpec,
    expected: StimulusSpec,
    condition: str,
    session_index: int,
    trial_index: int,
    scenario: AgentScenario,
    is_perceptual_control: bool,
    seed: int,
    delay_s: float = 0.0,
    prev_condition: str | None = None,
) -> dict[str, Any]:
    """Generate a noisy response for one trial from the cognitive agent model.

    Returns both the response and all computed scores using production scoring.
    """
    from app.research.rng_registry import derive_seed
    rng = random.Random(derive_seed(seed, "imagery_noise",
                                    participant_id=agent.participant_id,
                                    session_index=session_index,
                                    trial_index=trial_index))

    # --- Compute effective precision for this trial ---
    base_precision = agent.baseline_imagery_precision

    if is_perceptual_control:
        effective = agent.perceptual_matching_skill + session_index * scenario.perceptual_control_improvement
    else:
        effective = base_precision
        practice = session_index * agent.learning_rate

        if condition == "adaptive":
            precision_eff = scenario.adaptive_precision_effect * agent.condition_treatment_response
            control_eff = scenario.adaptive_control_effect * agent.imagery_control
            stability_eff = scenario.adaptive_stability_effect * agent.imagery_stability
            learning_eff = scenario.adaptive_learning_boost
            fatigue_reg = scenario.adaptive_fatigue_regulation
            effect = (precision_eff + control_eff + stability_eff + learning_eff) * session_index
            effective += effect + practice
            effective -= agent.fatigue_susceptibility * trial_index * 0.01 * (1.0 - fatigue_reg)
        elif condition == "fixed":
            effective += scenario.fixed_practice_effect * session_index + practice
            effective -= agent.fatigue_susceptibility * trial_index * 0.01
        elif condition == "yoked":
            effective += scenario.yoked_practice_effect * session_index + practice
            effective -= agent.fatigue_susceptibility * trial_index * 0.01

        effective += agent.period_effect * session_index * scenario.period_effect_strength
        if condition == "adaptive" and scenario.objective_expectancy_effect != 0.0:
            effective += agent.expectancy_response * scenario.objective_expectancy_effect

        if prev_condition == "adaptive" and condition != "adaptive":
            effective += agent.carryover_effect * scenario.carryover_strength

        if delay_s > 0:
            stability_loss = delay_s * 0.01 * (1.0 - agent.imagery_stability)
            effective -= stability_loss

    effective = _clamp01(effective)

    noise_sd = 0.08 * (1.0 - agent.motor_precision)

    response = ResponseSpec(
        orientation_deg=(expected.orientation_deg + rng.gauss(0, (1.0 - effective) * 30 + noise_sd * 10)) % 180,
        hue_deg=(expected.hue_deg + rng.gauss(0, (1.0 - effective) * 60 + noise_sd * 20)) % 360,
        spatial_frequency_cpd=max(0.1, expected.spatial_frequency_cpd * math.exp(
            rng.gauss(0, (1.0 - effective) * 0.3 + noise_sd)
        )),
        position_x=expected.position_x + rng.gauss(0, (1.0 - effective) * 50 + noise_sd * 20),
        position_y=expected.position_y + rng.gauss(0, (1.0 - effective) * 50 + noise_sd * 20),
        size=max(1.0, expected.size * math.exp(rng.gauss(0, (1.0 - effective) * 0.2 + noise_sd))),
        latency_ms=max(300, rng.gauss(2000, 500) + (1.0 - agent.motor_precision) * 500),
    )

    # --- Compute objective score using production scoring ---
    components: dict[str, float] = {}
    components["orientation"] = orientation_error(response.orientation_deg, expected.orientation_deg)
    components["hue"] = hue_error(response.hue_deg, expected.hue_deg)
    components["spatial_frequency"] = spatial_frequency_error(
        response.spatial_frequency_cpd, expected.spatial_frequency_cpd,
    )
    components["position"] = position_error(
        response.position_x, response.position_y,
        expected.position_x, expected.position_y,
        1000.0,
    )
    components["size"] = size_error(response.size, expected.size)
    composite = composite_reconstruction_error(components)

    # --- Generate subjective ratings from latent state + bias ---
    accuracy_signal = 1.0 - min(1.0, composite)
    confidence_raw = (
        agent.metacognitive_sensitivity * accuracy_signal
        + (1.0 - agent.metacognitive_sensitivity) * 0.5
        + agent.confidence_bias * 0.3
        + rng.gauss(0, 0.15)
    )
    confidence = max(1.0, min(7.0, round(confidence_raw * 6 + 1)))

    vividness_raw = (
        accuracy_signal * 0.4
        + agent.subjective_vividness_bias * 0.2
        + (scenario.expectancy_vividness_effect if condition == "adaptive" else 0) * 0.3
        + rng.gauss(0.5, 0.15)
    )
    vividness = max(1.0, min(7.0, round(vividness_raw * 6 + 1)))
    effort = max(1.0, min(7.0, round(4.0 + rng.gauss(0, 0.8))))

    return {
        "participant_id": agent.participant_id,
        "condition": condition,
        "session_index": session_index,
        "trial_index": trial_index,
        "is_perceptual_control": is_perceptual_control,
        "delay_s": delay_s,
        "response": response.to_dict(),
        "target": expected.to_dict(),
        "component_errors": {k: round(v, 6) for k, v in components.items()},
        "composite_error": round(composite, 6),
        "confidence": confidence,
        "vividness": vividness,
        "effort": effort,
        "latency_ms": round(response.latency_ms, 1),
        "effective_precision": round(effective, 4),
    }


def should_dropout(
    agent: AgentTraits,
    session_index: int,
    scenario: AgentScenario,
    rng: random.Random,
) -> bool:
    """Determine if agent drops out at this session."""
    if scenario.dropout_rate <= 0:
        return False
    base_rate = scenario.dropout_rate * session_index / 6
    if scenario.dropout_bias == "low_performer":
        base_rate *= (1.5 - agent.baseline_imagery_precision)
    return rng.random() < base_rate


def model_hash(scenario: AgentScenario, seed: int) -> str:
    data = json.dumps({"scenario": scenario.to_dict(), "seed": seed, "version": MODEL_VERSION},
                      sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(data.encode()).hexdigest()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
