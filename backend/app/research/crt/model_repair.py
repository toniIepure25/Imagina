"""Stage 0E model-repair audit: oracle versus belief-based prediction.

The Stage 0C/0D simulator gave the simulated participant the true source when forming a prediction.
That is an oracle benchmark. This module recomputes the same design under a belief-based readout and
quantifies how much of the earlier prediction and specificity result depended on oracle access.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from app.research.crt.simulate import SimulationConfig, run_simulation, run_specificity_simulation


@dataclass(frozen=True)
class ModelRepairConfig:
    n_participants: int = 24
    n_trials: int = 60
    seed: int = 20261030

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")


def _simulation_config(config: ModelRepairConfig) -> SimulationConfig:
    return SimulationConfig(
        n_participants=config.n_participants,
        n_trials=config.n_trials,
        seed=config.seed,
        prediction_source="belief",
        source_update="outcome",
    )


def _prediction_accuracy(summary: Mapping[str, object]) -> float | None:
    value = summary.get("prediction_accuracy")
    return None if value is None else float(value)


def run_model_repair(config: ModelRepairConfig | None = None) -> dict[str, object]:
    """Compare oracle and belief-based prediction under the same design and participants."""

    config = config or ModelRepairConfig()
    base = _simulation_config(config)
    oracle_config = replace(base, prediction_source="oracle", source_update="legacy")
    belief_config = replace(base, prediction_source="belief", source_update="outcome")

    oracle = run_simulation(oracle_config)
    belief = run_simulation(belief_config)
    oracle_specificity = run_specificity_simulation(oracle_config)
    belief_specificity = run_specificity_simulation(belief_config)

    oracle_comparison = oracle["condition_comparison"]
    belief_comparison = belief["condition_comparison"]
    oracle_advantage = float(oracle_comparison["prediction_advantage"])
    belief_advantage = float(belief_comparison["prediction_advantage"])
    oracle_prediction_accuracy = _prediction_accuracy(
        oracle["condition_summaries"]["active_predict"]  # type: ignore[index]
    )
    belief_prediction_accuracy = _prediction_accuracy(
        belief["condition_summaries"]["active_predict"]  # type: ignore[index]
    )
    oracle_inflation = oracle_advantage - belief_advantage

    passed = (
        oracle_prediction_accuracy is not None
        and belief_prediction_accuracy is not None
        and oracle_prediction_accuracy >= belief_prediction_accuracy + 0.05
        and oracle_inflation >= 0.02
    )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_model_repair_oracle_audit",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "prediction_sources": ["oracle", "belief"],
        },
        "oracle": {
            "prediction_source": "oracle",
            "source_update": "legacy",
            "prediction_advantage": round(oracle_advantage, 6),
            "prediction_accuracy": (
                None if oracle_prediction_accuracy is None else round(oracle_prediction_accuracy, 6)
            ),
            "specificity_decision": oracle_specificity["decision"],
            "specificity_contrasts": oracle_specificity["contrasts"],
        },
        "belief": {
            "prediction_source": "belief",
            "source_update": "outcome",
            "prediction_advantage": round(belief_advantage, 6),
            "prediction_accuracy": (
                None if belief_prediction_accuracy is None else round(belief_prediction_accuracy, 6)
            ),
            "specificity_decision": belief_specificity["decision"],
            "specificity_contrasts": belief_specificity["contrasts"],
        },
        "audit": {
            "oracle_inflation": round(oracle_inflation, 6),
            "oracle_prediction_accuracy_gap": (
                None
                if oracle_prediction_accuracy is None or belief_prediction_accuracy is None
                else round(oracle_prediction_accuracy - belief_prediction_accuracy, 6)
            ),
            "stage0d_specificity_reproduced_under_belief": (
                belief_specificity["decision"] == "CRT_STAGE0D_SPECIFICITY_PASS"
            ),
            "double_counting_removed": True,
        },
        "decision": "CRT_STAGE0E_MODEL_PASS" if passed else "CRT_STAGE0E_MODEL_REVIEW",
        "note": (
            "The oracle arm is a historical benchmark, not a human model. The belief arm predicts from "
            "the current source posterior and updates the source from the outcome only. A positive "
            "oracle inflation means the Stage 0C/0D prediction result cannot be interpreted as human "
            "prediction evidence. A PASS means the repair was quantified; it is not human validation."
        ),
    }


def check_model_repair() -> dict[str, object]:
    report = run_model_repair(ModelRepairConfig(n_participants=12, n_trials=30, seed=7))
    if report["decision"] != "CRT_STAGE0E_MODEL_PASS":
        raise AssertionError(f"CRT model-repair gate failed: {report['audit']}")
    return report


__all__ = ["ModelRepairConfig", "check_model_repair", "run_model_repair"]
