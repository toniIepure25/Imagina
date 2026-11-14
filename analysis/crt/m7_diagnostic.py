"""M7 diagnostic for the CRT Stage 0I design.

The target readout screen failed to recover M7 under the balanced trial composition. This module
isolates the cause: it compares balanced, vividness-manipulated, confidence-manipulated, and combined
compositions on the M4/M6/M7 subset, then optionally checks the best composition at target size with
all confirmatory models. It is a synthetic design diagnostic, not human evidence.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .design_optimization import (
    DEFAULT_CANDIDATES,
    DesignCandidate,
    DesignOptimizationConfig,
    _confusion_for_candidate,
)
from .full_model import FULL_MODELS

SCOPE = "m7_design_diagnostic_synthetic_not_human_evidence"
DIAGNOSTIC_MODELS: tuple[str, ...] = ("M4", "M6", "M7")
DIAGNOSTIC_CANDIDATES: tuple[DesignCandidate, ...] = tuple(
    candidate
    for candidate in DEFAULT_CANDIDATES
    if candidate.design_id
    in {"balanced", "vividness_manipulated", "confidence_manipulated", "combined_manipulation"}
)


@dataclass(frozen=True)
class M7DiagnosticConfig:
    screen_n: int = 144
    screen_trials: int = 120
    target_n: int = 432
    target_trials: int = 240
    n_replicates: int = 1
    models: tuple[str, ...] = DIAGNOSTIC_MODELS
    target_models: tuple[str, ...] = FULL_MODELS
    candidates: tuple[DesignCandidate, ...] = DIAGNOSTIC_CANDIDATES
    target_candidate_id: str = "combined_manipulation"
    effect_scale: float = 0.8
    min_abs_effect: float = 0.25
    recovery_threshold: float = 0.85
    run_target: bool = True
    seed: int = 20261104

    def __post_init__(self) -> None:
        if self.screen_n < 6 or self.screen_trials < 20:
            raise ValueError("screen requires at least 6 participants and 20 trials")
        if self.target_n < self.screen_n or self.target_trials < self.screen_trials:
            raise ValueError("target must not be smaller than the screen")
        if self.n_replicates <= 0:
            raise ValueError("n_replicates must be positive")
        if not self.models or any(model not in FULL_MODELS for model in self.models):
            raise ValueError("models must be a non-empty subset of FULL_MODELS")
        if not self.target_models or any(model not in FULL_MODELS for model in self.target_models):
            raise ValueError("target_models must be a non-empty subset of FULL_MODELS")
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        candidate_ids = {candidate.design_id for candidate in self.candidates}
        if self.target_candidate_id not in candidate_ids:
            raise ValueError("target_candidate_id must be one of the diagnostic candidates")
        if not 0 < self.recovery_threshold <= 1:
            raise ValueError("recovery_threshold must be in (0, 1]")


def _screen_candidate(
    candidate: DesignCandidate,
    config: M7DiagnosticConfig,
    rng: np.random.Generator,
) -> dict[str, Any]:
    screen_config = DesignOptimizationConfig(
        n_participants=config.screen_n,
        n_trials=config.screen_trials,
        n_replicates=config.n_replicates,
        n_power_simulations=1,
        models=tuple(config.models),
        candidates=(candidate,),
        effect_scale=config.effect_scale,
        min_abs_effect=config.min_abs_effect,
        seed=config.seed,
        laplace=False,
    )
    confusion, per_model = _confusion_for_candidate(candidate, screen_config, rng)
    rows = confusion.sum(axis=1)
    pairwise = {}
    for left in range(len(config.models)):
        for right in range(left + 1, len(config.models)):
            correct = confusion[left, left] + confusion[right, right]
            total = max(rows[left] + rows[right], 1)
            pairwise[f"{config.models[left]}_vs_{config.models[right]}"] = float(correct / total)
    return {
        "design_id": candidate.design_id,
        "candidate": asdict(candidate),
        "confusion": confusion.tolist(),
        "per_model_accuracy": per_model,
        "pairwise_accuracy": pairwise,
        "min_pairwise_accuracy": float(min(pairwise.values())),
    }


def _target_check(
    candidate: DesignCandidate,
    config: M7DiagnosticConfig,
    rng: np.random.Generator,
) -> dict[str, Any]:
    target_config = DesignOptimizationConfig(
        n_participants=config.target_n,
        n_trials=config.target_trials,
        n_replicates=config.n_replicates,
        n_power_simulations=1,
        models=tuple(config.target_models),
        candidates=(candidate,),
        effect_scale=config.effect_scale,
        min_abs_effect=config.min_abs_effect,
        seed=config.seed,
        laplace=False,
    )
    confusion, per_model = _confusion_for_candidate(candidate, target_config, rng)
    rows = confusion.sum(axis=1)
    pairwise = {}
    for left in range(len(config.target_models)):
        for right in range(left + 1, len(config.target_models)):
            correct = confusion[left, left] + confusion[right, right]
            total = max(rows[left] + rows[right], 1)
            pairwise[f"{config.target_models[left]}_vs_{config.target_models[right]}"] = float(
                correct / total
            )
    return {
        "design_id": candidate.design_id,
        "n_participants": config.target_n,
        "n_trials": config.target_trials,
        "confusion": confusion.tolist(),
        "per_model_accuracy": per_model,
        "pairwise_accuracy": pairwise,
        "min_pairwise_accuracy": float(min(pairwise.values())),
    }


def run_m7_diagnostic(config: M7DiagnosticConfig | None = None) -> dict[str, Any]:
    cfg = config or M7DiagnosticConfig()
    rng = np.random.default_rng(cfg.seed)
    screen = [_screen_candidate(candidate, cfg, rng) for candidate in cfg.candidates]
    best = max(screen, key=lambda row: (row["per_model_accuracy"]["M7"], row["min_pairwise_accuracy"]))
    target = None
    if cfg.run_target:
        target_candidate = next(
            candidate for candidate in cfg.candidates if candidate.design_id == cfg.target_candidate_id
        )
        target = _target_check(target_candidate, cfg, rng)

    m7_screen = best["per_model_accuracy"]["M7"]
    m7_target = target["per_model_accuracy"]["M7"] if target else None
    if m7_screen >= cfg.recovery_threshold and (m7_target is None or m7_target >= cfg.recovery_threshold):
        decision = "CRT_STAGE0I_M7_DIAGNOSTIC_DESIGN_SENSITIVE"
        conclusion = (
            "M7 recovery depends on the trial composition; a vividness/confidence manipulation "
            "recovers it in this synthetic screen."
        )
    elif m7_screen < 0.5 and (m7_target is None or m7_target < 0.5):
        decision = "CRT_STAGE0I_M7_DIAGNOSTIC_PERSISTENT"
        conclusion = "M7 is not recovered under any tested composition; treat it as exploratory."
    else:
        decision = "CRT_STAGE0I_M7_DIAGNOSTIC_REVIEW"
        conclusion = "M7 recovery is composition- or scale-dependent; further design work is required."

    return {
        "analysis": "stage0i_m7_diagnostic",
        "scope": SCOPE,
        "models": list(cfg.models),
        "target_models": list(cfg.target_models),
        "config": asdict(cfg),
        "screen": screen,
        "best_screen_design": best,
        "target_check": target,
        "decision": decision,
        "conclusion": conclusion,
        "note": (
            "Synthetic design diagnostic only. It does not establish that humans use M7, does not "
            "replace the full joint model, and does not authorize recruitment."
        ),
    }


def write_artifact(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run a small diagnostic")
    parser.add_argument("--write", action="store_true", help="write the M7 diagnostic artifact")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/crt/CRT_STAGE0I_M7_DIAGNOSTIC.json"),
    )
    args = parser.parse_args(argv)
    if not args.check and not args.write:
        parser.print_help()
        return 0
    if args.write:
        config = M7DiagnosticConfig()
    else:
        config = M7DiagnosticConfig(
            screen_n=24,
            screen_trials=40,
            target_n=24,
            target_trials=40,
            run_target=False,
            candidates=DIAGNOSTIC_CANDIDATES[:2],
        )
    payload = run_m7_diagnostic(config)
    if args.write:
        write_artifact(payload, args.out)
    print(json.dumps({"decision": payload["decision"], "best": payload["best_screen_design"]["design_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
