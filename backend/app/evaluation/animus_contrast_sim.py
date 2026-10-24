"""Deterministic simulation harness for the Scene Threshold task.

This module is evaluation-only. It exercises the same public pair generation and SDT scoring code
path as the product, but it does not touch the database, the API, or any participant data. Simulated
respondents are convenient for checking recovery of a known threshold and for spotting staircase or
scoring regressions. They are not a validation study.

The simulation deliberately does not model imagery, neural signals, or clinical status. It models a
2-AFC observer with a logistic psychometric function, an optional side bias, and a lapse rate.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.core.animus.scene.model import SceneGraph
from app.core.animus.studio.contrast import (
    CONTRAST_PROTOCOL_VERSION,
    DEFAULT_LAPSE,
    DEFAULT_MAX_TRIALS,
    TARGET_CRITERION,
    ContrastPair,
    next_trial,
    score_trial,
    summarize_contrast,
)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class SimulatedRespondent:
    """A synthetic 2-AFC observer.

    ``threshold`` and ``slope`` are in the same normalized change units as the task. ``side_bias`` is
    the probability of choosing A on an otherwise unbiased trial. ``policy`` may be ``"sensitivity"``,
    ``"guesser"``, ``"side_bias"``, or ``"abstainer"``.
    """

    threshold: float = 0.35
    slope: float = 0.12
    lapse: float = DEFAULT_LAPSE
    side_bias: float = 0.0
    confidence_base: float = 0.62
    confidence_slope: float = 0.3
    confidence_noise: float = 0.06
    policy: str = "sensitivity"
    seed: int = 7
    _rng: random.Random = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_rng", random.Random(self.seed))

    def probability_correct(self, delta: float | None) -> float:
        if delta is None:
            return 0.5
        if self.policy == "guesser":
            return 0.5
        if self.policy == "abstainer":
            return 0.5
        if self.policy == "side_bias":
            return _clamp(0.5 + self.side_bias * 0.5, 0.0, 1.0)
        chance = _sigmoid((float(delta) - self.threshold) / max(0.01, self.slope))
        return _clamp(0.5 + 0.5 * (1.0 - self.lapse) * chance, 0.0, 1.0)

    def confidence(self, delta: float | None) -> float:
        strength = 0.0 if delta is None else abs(self.probability_correct(delta) - 0.5) * 2.0
        value = self.confidence_base + self.confidence_slope * strength
        value += self._rng.uniform(-self.confidence_noise, self.confidence_noise)
        return round(_clamp(value, 0.5, 1.0), 6)

    def respond(self, pair: ContrastPair) -> dict[str, Any]:
        if self.policy == "abstainer":
            return {"choice": "", "confidence": 0.5, "abstained": True}
        probability = self.probability_correct(pair.delta)
        if self.policy == "side_bias":
            choice = "a" if self._rng.random() < _clamp(0.5 + self.side_bias, 0.0, 1.0) else "b"
        elif self._rng.random() < probability:
            choice = pair.target_side
        else:
            choice = "b" if pair.target_side == "a" else "a"
        return {
            "choice": choice,
            "confidence": self.confidence(pair.delta),
            "abstained": False,
        }


@dataclass
class ContrastSimulation:
    session: dict[str, Any]
    trials: list[dict[str, Any]]
    summary: dict[str, Any]
    respondent: SimulatedRespondent


def simulate_contrast(
    scene: SceneGraph,
    *,
    respondent: SimulatedRespondent,
    max_trials: int = DEFAULT_MAX_TRIALS,
    form_id: str = "A",
    difficulty: float = 0.45,
    seed: int = 7,
) -> ContrastSimulation:
    session = {
        "contrast_id": "ct_simulation",
        "session_id": "simulation",
        "source_version_id": "ver_simulation",
        "scene_hash": scene.content_hash(),
        "protocol_version": CONTRAST_PROTOCOL_VERSION,
        "form_id": form_id,
        "seed": seed,
        "max_trials": max(1, int(max_trials)),
        "difficulty": float(difficulty),
        "occasion": "baseline",
        "status": "active",
    }
    trials: list[dict[str, Any]] = []
    while True:
        pair = next_trial(scene, session, trials)
        if pair is None:
            break
        response = respondent.respond(pair)
        outcome = score_trial(
            pair,
            choice=str(response["choice"]),
            confidence=float(response["confidence"]),
            abstained=bool(response["abstained"]),
        )
        trials.append({
            "trial_id": pair.trial_id,
            "trial_index": pair.trial_index,
            "feature_type": pair.feature_type,
            "feature_key": pair.feature_key,
            "delta": pair.delta,
            "choice": outcome["choice"],
            "correct": outcome["correct"],
            "confidence": outcome["confidence"],
            "abstained": bool(response["abstained"]),
        })
        if len(trials) >= int(session["max_trials"]):
            break
    summary = summarize_contrast(
        {**session, "status": "completed"},
        trials,
        bootstrap=0,
    )
    return ContrastSimulation(session=session, trials=trials, summary=summary, respondent=respondent)


def recovery_check(
    scenes: Sequence[SceneGraph],
    *,
    thresholds: Sequence[float] = (0.2, 0.35, 0.5),
    max_trials: int = DEFAULT_MAX_TRIALS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scene in scenes:
        for threshold in thresholds:
            simulation = simulate_contrast(
                scene,
                respondent=SimulatedRespondent(
                    threshold=float(threshold), slope=0.1, seed=17, policy="sensitivity"),
                max_trials=max_trials,
            )
            spatial = simulation.summary["thresholds"].get("spatial_position", {})
            rows.append({
                "scene_hash": scene.content_hash(),
                "true_threshold": float(threshold),
                "estimated_threshold": spatial.get("threshold"),
                "dprime": simulation.summary["dprime"],
                "n_answered": simulation.summary["n_answered"],
                "coverage": simulation.summary["coverage"],
            })
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Scene Threshold simulation")
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--max-trials", type=int, default=DEFAULT_MAX_TRIALS)
    args = parser.parse_args(argv)
    from app.core.animus.scene.compose import compose_from_intention

    scene = compose_from_intention(
        "a white castle above a dark ocean with a moon and three lanterns at dusk", seed=31).scene
    result = simulate_contrast(
        scene,
        respondent=SimulatedRespondent(threshold=args.threshold),
        max_trials=args.max_trials,
    )
    print(json.dumps({
        "target_criterion": TARGET_CRITERION,
        "true_threshold": args.threshold,
        "summary": result.summary,
        "trials": len(result.trials),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["ContrastSimulation", "SimulatedRespondent", "main", "recovery_check", "simulate_contrast"]
