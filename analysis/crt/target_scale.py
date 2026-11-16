"""Target-scale readiness orchestration for the CRT confirmatory model space.

This module does not analyse human data and does not upgrade any claim. It packages three
simulation-only checks into one auditable artifact:

1. NUTS simulation-based calibration for every confirmatory model;
2. BIC-based recovery among the pre-specified full joint models;
3. a readiness decision that refuses to pass below the declared SBC count.

The full target run is deliberately not executed by CI. ``--smoke`` is a fast wiring check; the
default profile is a planning profile that stays below the decision minimum and therefore cannot
produce a PASS by accident.
"""
from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from .full_model import FULL_MODELS, FullModelConfig, run_full_recovery
from .numpyro_model import (
    RANK_TOLERANCE,
    NutsSbcConfig,
    numpyro_available,
    run_nuts_sbc,
)

SCOPE = "simulation_only_target_scale_readiness_not_human_evidence"
CONFIRMATORY = ("M0", "M2", "M4", "M6", "M7")


@dataclass(frozen=True)
class TargetScaleConfig:
    n_participants: int = 432
    n_trials: int = 240
    n_sbc: int = 20
    chains: int = 1
    warmup: int = 500
    draws: int = 500
    n_recovery: int = 2
    seed: int = 20261117
    min_sbc_for_decision: int = 50
    coverage_low: float = 0.93
    coverage_high: float = 0.97
    recovery_threshold: float = 0.85
    models: tuple[str, ...] = CONFIRMATORY

    def __post_init__(self) -> None:
        if self.n_participants < 6 or self.n_trials < 20:
            raise ValueError("target-scale simulation requires at least 6 participants and 20 trials")
        if self.n_sbc <= 0 or self.n_recovery <= 0 or self.chains < 1 or self.warmup < 1:
            raise ValueError("simulation counts must be positive")
        if self.draws < 20:
            raise ValueError("draws must be at least 20")
        if not 0 < self.coverage_low < self.coverage_high < 1:
            raise ValueError("coverage bounds must be ordered in (0, 1)")
        if not 0 < self.recovery_threshold <= 1:
            raise ValueError("recovery_threshold must be in (0, 1]")
        if not self.models or any(model not in FULL_MODELS for model in self.models):
            raise ValueError("models must be a non-empty subset of FULL_MODELS")

    @classmethod
    def smoke(cls) -> TargetScaleConfig:
        return cls(
            n_participants=6,
            n_trials=20,
            n_sbc=2,
            chains=1,
            warmup=20,
            draws=20,
            n_recovery=1,
            min_sbc_for_decision=1,
        )

    @classmethod
    def target(cls) -> TargetScaleConfig:
        return cls(
            n_sbc=50,
            chains=1,
            warmup=1000,
            draws=1000,
            n_recovery=20,
            min_sbc_for_decision=50,
        )

    def as_nuts_sbc(self) -> NutsSbcConfig:
        return NutsSbcConfig(
            n_participants=self.n_participants,
            n_trials=self.n_trials,
            n_sbc=self.n_sbc,
            chains=self.chains,
            warmup=self.warmup,
            draws=self.draws,
            seed=self.seed,
            coverage_low=self.coverage_low,
            coverage_high=self.coverage_high,
            min_sbc_for_decision=self.min_sbc_for_decision,
        )

    def as_recovery(self) -> FullModelConfig:
        return FullModelConfig(
            n_participants=self.n_participants,
            n_trials=self.n_trials,
            n_sbc=self.n_sbc,
            n_posterior_draws=20,
            n_recovery=self.n_recovery,
            seed=self.seed + 101,
            recovery_threshold=self.recovery_threshold,
            laplace=False,
        )


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2], text=True
        ).strip()
    except Exception:
        return "unknown"


def _version(module: str) -> str | None:
    try:
        imported = __import__(module)
    except Exception:
        return None
    return str(getattr(imported, "__version__", "unknown"))


def _finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _sbc_failures(sbc: Iterable[Mapping[str, Any]]) -> list[str]:
    failures: list[str] = []
    for result in sbc:
        if result.get("decision") != "CRT_NUTS_SBC_PASS":
            failures.append(f"{result.get('model')}: {result.get('decision')}")
            continue
        for name, metrics in (result.get("metrics") or {}).items():
            if not _finite(metrics.get("coverage")):
                failures.append(f"{result.get('model')}:{name}: non-finite coverage")
            elif not 0.0 <= float(metrics["coverage"]) <= 1.0:
                failures.append(f"{result.get('model')}:{name}: coverage outside [0,1]")
            if not _finite(metrics.get("mean_rank")):
                failures.append(f"{result.get('model')}:{name}: non-finite mean rank")
            elif abs(float(metrics["mean_rank"]) - 0.5) > RANK_TOLERANCE:
                failures.append(f"{result.get('model')}:{name}: mean rank outside tolerance")
    return failures


def _artifact(
    cfg: TargetScaleConfig,
    *,
    status: str,
    sbc: list[dict[str, Any]] | None = None,
    recovery: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    failures = _sbc_failures(sbc or [])
    recovery_decision = str((recovery or {}).get("decision", "CRT_STAGE0J_FULL_MODEL_RECOVERY_REVIEW"))
    if status == "blocked":
        decision = "CRT_STAGE0J_BLOCKED"
    elif status == "pass" and not failures and recovery_decision.endswith("_PASS"):
        decision = "CRT_STAGE0J_PASS"
    else:
        decision = "CRT_STAGE0J_REVIEW"
    return {
        "schema": "IMAGINA-CRT-TARGET-SCALE-v1",
        "analysis": "crt_stage0j_target_scale_readiness",
        "protocol": "ANIMUS-CRT-v1",
        "scope": SCOPE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_sha": _git_sha(),
        "decision": decision,
        "status": status,
        "reason": reason,
        "config": asdict(cfg),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "jax": _version("jax"),
            "numpyro": _version("numpyro"),
        },
        "sbc": sbc or [],
        "recovery": recovery or {},
        "failures": failures,
        "limitations": [
            "Simulation-only; no human participants and no human evidence.",
            "SBC coverage and mean-rank checks are necessary but not sufficient for a valid study design.",
            "Rhat/ESS are not yet enforced in the SBC loop; only divergent transitions count as unclean chains.",
            "Recovery is BIC-based among pre-specified models; it is not a NUTS marginal-likelihood comparison.",
            "A PASS does not authorize a measurement, clinical, decoding, or consciousness claim.",
        ],
    }


def run_target_scale(config: TargetScaleConfig | None = None) -> dict[str, Any]:
    cfg = config or TargetScaleConfig()
    if not numpyro_available():
        return _artifact(
            cfg,
            status="blocked",
            reason="NumPyro/JAX is not installed; target-scale SBC cannot run.",
        )

    sbc: list[dict[str, Any]] = []
    for model in cfg.models:
        sbc.append(run_nuts_sbc(model=model, config=cfg.as_nuts_sbc()))

    recovery = run_full_recovery(
        config=cfg.as_recovery(),
        model_set=cfg.models,
        analysis_prefix="stage0j",
    )
    status = "pass" if not _sbc_failures(sbc) and recovery.get("decision", "").endswith("_PASS") else "review"
    return _artifact(cfg, status=status, sbc=sbc, recovery=recovery)


def write_artifact(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="tiny wiring check, never a PASS")
    parser.add_argument("--target", action="store_true", help="target-scale profile; requires --confirm-compute")
    parser.add_argument("--confirm-compute", action="store_true", help="acknowledge the GPU/time cost")
    parser.add_argument("--check", action="store_true", help="print a JSON summary without writing")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("results/crt/CRT_STAGE0J_TARGET_SCALE.json"))
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.target and not args.confirm_compute:
        parser.error("--target requires --confirm-compute; benchmark one model before scaling")
    if args.smoke and args.target:
        parser.error("choose --smoke or --target, not both")
    cfg = TargetScaleConfig.smoke() if args.smoke else (TargetScaleConfig.target() if args.target else TargetScaleConfig())
    payload = run_target_scale(cfg)
    if args.write:
        write_artifact(payload, args.out)
    print(json.dumps({"decision": payload["decision"], "status": payload["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
