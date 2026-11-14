"""Stage 0F counterfactual-distortion assay.

The current CRT generative model treats prediction as a belief readout, not as source evidence, so
it predicts no direct prediction-induced shift in source choice. The human question is whether that
restriction is false: dual counterfactual prediction may increase false "seen" attributions for
imagined items. This module validates the *assay* against an injected effect and documents the
readout-only model's null, rather than assuming the effect exists.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean, stdev

from app.research.crt.metrics import TrialRecord
from app.research.crt.model import IMAGINED, SEEN
from app.research.crt.simulate import SimulationConfig, _participant_params, run_condition

_Z_975 = 1.959963984540054


@dataclass(frozen=True)
class DistortionConfig:
    n_participants: int = 160
    n_imagined_per_arm: int = 40
    n_simulations: int = 1000
    seed: int = 20261030
    baseline_false_seen: float = 0.20
    injected_effect: float = 0.05
    between_sd: float = 0.12
    equivalence_margin: float = 0.03
    alpha: float = 0.05
    readout_n: int = 12
    readout_trials: int = 60

    def __post_init__(self) -> None:
        if self.n_participants < 4:
            raise ValueError("n_participants must be at least 4")
        if self.n_imagined_per_arm <= 0:
            raise ValueError("n_imagined_per_arm must be positive")
        if self.n_simulations <= 0:
            raise ValueError("n_simulations must be positive")
        if not 0.0 < self.baseline_false_seen < 1.0:
            raise ValueError("baseline_false_seen must be between 0 and 1")
        if self.injected_effect <= 0:
            raise ValueError("injected_effect must be positive")
        if self.between_sd <= 0:
            raise ValueError("between_sd must be positive")
        if self.equivalence_margin <= 0:
            raise ValueError("equivalence_margin must be positive")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1")
        if self.readout_n < 2 or self.readout_trials < 4:
            raise ValueError("readout simulation is too small")


def _false_seen_rate(trials: list[TrialRecord]) -> float | None:
    imagined = [trial for trial in trials if trial.true_source == IMAGINED]
    if not imagined:
        return None
    return sum(1 for trial in imagined if trial.choice == SEEN) / len(imagined)


def _normal_two_sided_p(t_value: float) -> float:
    return math.erfc(abs(t_value) / math.sqrt(2.0))


def _paired_effect(differences: list[float]) -> dict[str, float]:
    if len(differences) < 2:
        return {"mean": 0.0, "sd": 0.0, "t": 0.0, "p": 1.0, "ci_low": 0.0, "ci_high": 0.0}
    average = mean(differences)
    spread = stdev(differences)
    if spread <= 0.0:
        return {
            "mean": round(average, 6),
            "sd": 0.0,
            "t": 0.0,
            "p": 1.0,
            "ci_low": round(average, 6),
            "ci_high": round(average, 6),
        }
    standard_error = spread / math.sqrt(len(differences))
    t_value = average / standard_error
    return {
        "mean": round(average, 6),
        "sd": round(spread, 6),
        "t": round(t_value, 6),
        "p": round(_normal_two_sided_p(t_value), 6),
        "ci_low": round(average - _Z_975 * standard_error, 6),
        "ci_high": round(average + _Z_975 * standard_error, 6),
    }


def _injected_assay(config: DistortionConfig, rng: random.Random) -> dict[str, object]:
    differences: list[float] = []
    detectable = 0
    for _ in range(config.n_simulations):
        participant_differences: list[float] = []
        for _ in range(config.n_participants):
            baseline = min(
                0.95,
                max(0.05, config.baseline_false_seen + rng.gauss(0.0, config.between_sd)),
            )
            dual = min(0.98, baseline + config.injected_effect)
            single_count = sum(rng.random() < baseline for _ in range(config.n_imagined_per_arm))
            dual_count = sum(rng.random() < dual for _ in range(config.n_imagined_per_arm))
            participant_differences.append(
                (dual_count - single_count) / config.n_imagined_per_arm
            )
        effect = _paired_effect(participant_differences)
        differences.append(float(effect["mean"]))
        if effect["ci_low"] > 0.0:
            detectable += 1
    summary = _paired_effect(differences)
    return {
        "injected_effect": config.injected_effect,
        "n_simulations": config.n_simulations,
        "mean_recovered_effect": summary["mean"],
        "power_to_detect_positive_shift": round(detectable / config.n_simulations, 6),
        "note": (
            "Assay sensitivity is evaluated against an injected +5pp effect. This is not evidence "
            "that dual prediction causes the effect in humans."
        ),
    }


def _format_contrast(
    config: DistortionConfig,
    *,
    b_pi: float,
) -> tuple[dict[str, object], dict[str, object]]:
    base = SimulationConfig(
        n_participants=config.readout_n,
        n_trials=config.readout_trials,
        seed=config.seed,
        max_tests=2,
        prediction_mode="diagnostic",
        prediction_source="belief",
        source_update="outcome",
        selection_mode="algorithm",
        b_pi_mean=b_pi,
        b_pi_sd=0.0,
    )
    params = _participant_params(base)
    single = run_condition(
        base,
        "active_predict",
        params_list=params,
        prediction_format="single",
    )
    dual = run_condition(
        base,
        "active_predict",
        params_list=params,
        prediction_format="dual",
    )
    single_rates = [_false_seen_rate(result.trials) for result in single]
    dual_rates = [_false_seen_rate(result.trials) for result in dual]
    paired = [
        dual_rate - single_rate
        for single_rate, dual_rate in zip(single_rates, dual_rates)
        if single_rate is not None and dual_rate is not None
    ]
    effect = _paired_effect(paired)
    summary = {
        "n_participants": config.readout_n,
        "n_trials": config.readout_trials,
        "b_pi": b_pi,
        "single_false_seen_rate": round(mean([r for r in single_rates if r is not None]), 6)
        if any(r is not None for r in single_rates)
        else None,
        "dual_false_seen_rate": round(mean([r for r in dual_rates if r is not None]), 6)
        if any(r is not None for r in dual_rates)
        else None,
        "paired_effect": effect,
    }
    return summary, effect


def _readout_only_check(config: DistortionConfig) -> dict[str, object]:
    summary, effect = _format_contrast(config, b_pi=0.0)
    summary["null_as_expected"] = abs(float(effect["mean"])) <= config.equivalence_margin
    summary["note"] = (
        "Readout-only check with b_pi fixed at zero. A near-zero effect is expected because "
        "prediction does not enter the source likelihood; a non-zero effect would indicate a "
        "simulator bug or another format-dependent channel."
    )
    return summary


def _bias_channel_check(config: DistortionConfig) -> dict[str, object]:
    summary, effect = _format_contrast(config, b_pi=0.4)
    summary["model_predicted_shift"] = float(effect["mean"]) > 0.0
    summary["note"] = (
        "Prediction-consistency bias channel with b_pi fixed at 0.4. A positive shift is a model "
        "prediction (M5-like), not human evidence; the human study tests whether this channel exists."
    )
    return summary


def run_distortion_assay(config: DistortionConfig | None = None) -> dict[str, object]:
    config = config or DistortionConfig()
    rng = random.Random(config.seed)
    injected = _injected_assay(config, rng)
    readout = _readout_only_check(config)
    bias_channel = _bias_channel_check(config)
    power = float(injected["power_to_detect_positive_shift"])
    passed = power >= 0.80 and bool(readout["null_as_expected"])
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0f_counterfactual_distortion_assay",
        "config": {
            "n_participants": config.n_participants,
            "n_imagined_per_arm": config.n_imagined_per_arm,
            "n_simulations": config.n_simulations,
            "seed": config.seed,
            "baseline_false_seen": config.baseline_false_seen,
            "injected_effect": config.injected_effect,
            "between_sd": config.between_sd,
            "equivalence_margin": config.equivalence_margin,
            "alpha": config.alpha,
        },
        "injected_assay": injected,
        "readout_only_model": readout,
        "bias_channel_model": bias_channel,
        "decision": (
            "CRT_STAGE0F_DISTORTION_PASS"
            if passed
            else "CRT_STAGE0F_DISTORTION_REVIEW"
        ),
        "note": (
            "The assay is sensitive to a synthetic +5pp shift. With b_pi=0 the readout-only model is "
            "null; with b_pi>0 a prediction-consistency bias can produce a shift. The human study "
            "tests whether that channel exists; it cannot borrow a distortion claim from simulation."
        ),
    }


__all__ = ["DistortionConfig", "run_distortion_assay"]
