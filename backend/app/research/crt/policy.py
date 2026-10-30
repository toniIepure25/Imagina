"""Stage 0E policy competition for CRT test selection."""
from __future__ import annotations

from dataclasses import dataclass

from app.research.crt.simulate import SimulationConfig, _aggregate, _participant_params, run_condition

POLICY_IDS: tuple[str, ...] = (
    "meta_eig",
    "eig",
    "cost_only",
    "positive",
    "fixed",
    "heuristic",
    "random",
)


@dataclass(frozen=True)
class PolicyConfig:
    n_participants: int = 24
    n_trials: int = 60
    seed: int = 20261030
    max_tests: int = 2

    def __post_init__(self) -> None:
        if self.n_participants <= 0:
            raise ValueError("n_participants must be positive")
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")
        if self.max_tests <= 0:
            raise ValueError("max_tests must be positive")


def run_policy_tournament(config: PolicyConfig | None = None) -> dict[str, object]:
    config = config or PolicyConfig()
    base = SimulationConfig(
        n_participants=config.n_participants,
        n_trials=config.n_trials,
        seed=config.seed,
        max_tests=config.max_tests,
        prediction_source="belief",
        source_update="outcome",
    )
    params_list = _participant_params(base)
    summaries: dict[str, dict[str, object]] = {}
    for policy in POLICY_IDS:
        participants = run_condition(
            base,
            "active_intervene",
            policy,
            params_list=params_list,
            prediction_mode="none",
        )
        summaries[policy] = _aggregate(participants)  # type: ignore[arg-type]

    accuracy = {policy: float(summary["accuracy"]) for policy, summary in summaries.items()}
    meta_eig = accuracy["meta_eig"]
    best_alternative = max(
        (value for policy, value in accuracy.items() if policy != "meta_eig"),
        default=0.0,
    )
    gain_over_cost_only = meta_eig - accuracy["cost_only"]
    gain_over_best_alternative = meta_eig - best_alternative
    passed = gain_over_cost_only >= 0.01 and gain_over_best_alternative >= 0.01
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_policy_competition",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "max_tests": config.max_tests,
            "policies": list(POLICY_IDS),
        },
        "condition_summaries": summaries,
        "contrasts": {
            "meta_eig_minus_cost_only": round(gain_over_cost_only, 6),
            "meta_eig_minus_best_alternative": round(gain_over_best_alternative, 6),
            "best_alternative_accuracy": round(best_alternative, 6),
        },
        "decision": "CRT_STAGE0E_POLICY_PASS" if passed else "CRT_STAGE0E_POLICY_REVIEW",
        "note": (
            "Policy simulation with belief-based prediction and outcome-only source updating. "
            "A REVIEW means the normative meta-EIG claim is not supported by the current simulation "
            "and should remain descriptive."
        ),
    }


__all__ = ["POLICY_IDS", "PolicyConfig", "run_policy_tournament"]
