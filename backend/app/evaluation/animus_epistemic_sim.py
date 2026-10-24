"""Deterministic simulation of epistemic-interview probe policies.

This is a design check, not a validation study. It asks whether adaptive selection can reduce the number
of probes needed to recover a known synthetic belief state under a stated response model. The response
model is deliberately simple and is not a model of any person.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from app.core.animus.studio.epistemic import (
    DEFAULT_SENSITIVITY,
    EpistemicBelief,
    EpistemicProbe,
    information_gain,
    init_belief,
    select_probe,
    update_belief,
)

POLICIES = ("random", "fixed", "info_gain")


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 20261023
    interviews: int = 120
    max_probes: int = 12
    n_objects: int = 10
    n_relations: int = 10
    true_positive_rate: float = 0.62
    sensitivity: float = DEFAULT_SENSITIVITY
    abstention_rate: float = 0.08
    threshold: float = 0.65


def _probe_id(*parts: Any) -> str:
    return "pr_" + hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:14]


def _task_id(*parts: Any) -> str:
    return "eri_" + hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:18]


def synthetic_probes(config: SimulationConfig) -> tuple[EpistemicProbe, ...]:
    probes: list[EpistemicProbe] = []
    for index in range(config.n_objects):
        variable = f"obj:{index}"
        probes.append(EpistemicProbe(
            probe_id=_probe_id("sim", "object", index),
            task_id=_task_id("sim", "object", index),
            probe_type="object_presence",
            prompt=f"Was object {index} present?",
            options=({"id": "present", "label": "Present"}, {"id": "absent", "label": "Absent"}),
            dimension="stability",
            difficulty=0.45,
            preview_seconds=4,
            variable_id=variable,
            answer={"choice": "present" if index % 2 == 0 else "absent"},
            metadata={"label": f"Object {index}", "kind": "simulated", "variable_kind": "object"},
        ))
    for index in range(config.n_relations):
        variable = f"rel:{index}"
        probes.append(EpistemicProbe(
            probe_id=_probe_id("sim", "relation", index),
            task_id=_task_id("sim", "relation", index),
            probe_type="spatial_relation",
            prompt=f"Is relation {index} left or right?",
            options=({"id": "left", "label": "Left"}, {"id": "right", "label": "Right"}),
            dimension="spatial",
            difficulty=0.45,
            preview_seconds=4,
            variable_id=variable,
            answer={"choice": "left" if index % 2 == 0 else "right"},
            metadata={
                "subject_label": f"Object {index}",
                "object_label": f"Object {index + 1}",
                "relation": "left_of" if index % 2 == 0 else "right_of",
                "variable_kind": "relation",
            },
        ))
    return tuple(probes)


def _choose(policy: str, probes: tuple[EpistemicProbe, ...], belief: EpistemicBelief,
            asked: set[str], rng: random.Random) -> EpistemicProbe | None:
    available = [probe for probe in probes if probe.probe_id not in asked]
    if not available:
        return None
    if policy == "random":
        return available[rng.randrange(len(available))]
    if policy == "fixed":
        asked_types = {probe.probe_type for probe in probes if probe.probe_id in asked}
        for probe_type in ("object_presence", "spatial_relation"):
            if probe_type not in asked_types:
                for probe in available:
                    if probe.probe_type == probe_type:
                        return probe
        return available[0]
    return select_probe(probes, belief)


def _response(probe: EpistemicProbe, config: SimulationConfig, rng: random.Random) -> tuple[str, float, bool]:
    abstained = rng.random() < config.abstention_rate
    if abstained:
        return "", 0.5, True
    correct = rng.random() < config.sensitivity
    truth = str(probe.answer.get("choice"))
    other = next(option["id"] for option in probe.options if option["id"] != truth)
    choice = truth if correct else other
    if correct and rng.random() < config.true_positive_rate:
        confidence = rng.uniform(0.75, 0.98)
    elif correct:
        confidence = rng.uniform(0.55, 0.75)
    else:
        confidence = rng.uniform(0.5, 0.85)
    return choice, round(confidence, 4), False


def run_policy(policy: str, config: SimulationConfig) -> dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    probes = synthetic_probes(config)
    rng = random.Random(f"{config.seed}:{policy}")
    correct_object = 0
    object_total = 0
    brier_values: list[float] = []
    gains: list[float] = []
    answered = 0
    asked_total = 0
    true_objects = {probe.variable_id: probe.answer["choice"] == "present"
                    for probe in probes if probe.probe_type == "object_presence"}
    for _ in range(config.interviews):
        belief = init_belief(probes)
        asked: set[str] = set()
        for _ in range(config.max_probes):
            probe = _choose(policy, probes, belief, asked, rng)
            if probe is None:
                break
            before = belief.probability(probe.variable_id)
            choice, confidence, abstained = _response(probe, config, rng)
            asked.add(probe.probe_id)
            asked_total += 1
            if not abstained:
                answered += 1
                correct = choice == probe.answer.get("choice")
                brier_values.append((confidence - (1.0 if correct else 0.0)) ** 2)
            belief = update_belief(
                belief, probe, choice=choice, confidence=confidence, abstained=abstained)
            gains.append(information_gain(before, belief.probability(probe.variable_id)))
        for variable, truth in true_objects.items():
            probability = belief.probability(variable)
            predicted = probability >= config.threshold
            correct_object += int(predicted == truth)
            object_total += 1
    return {
        "policy": policy,
        "object_recovery_accuracy": round(correct_object / object_total, 6) if object_total else None,
        "mean_brier": round(sum(brier_values) / len(brier_values), 6) if brier_values else None,
        "coverage": round(answered / asked_total, 6) if asked_total else 0.0,
        "mean_information_gain": round(sum(gains) / len(gains), 6) if gains else None,
        "mean_probes": round(asked_total / config.interviews, 3) if config.interviews else 0.0,
    }


def run_simulation(config: SimulationConfig | None = None) -> dict[str, Any]:
    active = config or SimulationConfig()
    results = [run_policy(policy, active) for policy in POLICIES]
    return {
        "simulation_only": True,
        "protocol_version": "eri-sim-v1",
        "config": {
            "seed": active.seed,
            "interviews": active.interviews,
            "max_probes": active.max_probes,
            "n_objects": active.n_objects,
            "n_relations": active.n_relations,
            "true_positive_rate": active.true_positive_rate,
            "sensitivity": active.sensitivity,
            "abstention_rate": active.abstention_rate,
            "threshold": active.threshold,
        },
        "results": results,
        "limitations": [
            "The response model is synthetic; these values are not human data.",
            "Object recovery uses a fixed posterior threshold and is not a validated scoring rule.",
            "No result here supports a neural, clinical, or diagnostic claim.",
        ],
    }


__all__ = [
    "POLICIES",
    "SimulationConfig",
    "synthetic_probes",
    "run_policy",
    "run_simulation",
]
