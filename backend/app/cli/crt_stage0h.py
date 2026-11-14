"""Stage 0H model-space, design-optimization, and full-model audit.

Examples:
    python -m app.cli.crt_stage0h --check
    python -m app.cli.crt_stage0h --model-space --design --write
    python -m app.cli.crt_stage0h --full-sbc --recovery --write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.crt.design_optimization import (  # noqa: E402
    DEFAULT_CANDIDATES,
    DesignOptimizationConfig,
    run_design_optimization,
)
from analysis.crt.full_model import (  # noqa: E402
    FULL_ACTIVE,
    FULL_MODELS,
    FullModelConfig,
    run_full_recovery,
    run_full_sbc,
)
from analysis.crt.full_model import (  # noqa: E402
    SCOPE as FULL_SCOPE,
)
from analysis.crt.trial_model import (  # noqa: E402
    CONFIRMATORY_MODELS,
    EXPLORATORY_MODELS,
    MODELS,
    active_parameters,
)
from analysis.crt.trial_model import (  # noqa: E402
    SCOPE as READOUT_SCOPE,
)

DEFAULT_OUT = Path("results/crt")
ARTIFACTS = {
    "model_space": "CRT_STAGE0H_MODEL_SPACE.json",
    "design": "CRT_STAGE0H_DESIGN_OPTIMIZATION.json",
    "full_sbc": "CRT_STAGE0H_FULL_MODEL_SBC.json",
    "full_recovery": "CRT_STAGE0H_FULL_MODEL_RECOVERY.json",
    "package": "CRT_STAGE0H_PACKAGE.json",
}

MODEL_ACCOUNTS = {
    "M0": "baseline source SDT",
    "M1": "prediction precision only (exploratory)",
    "M2": "active prospective single prediction",
    "M3": "dual counterfactual plus direct effect (exploratory)",
    "M4": "dual counterfactual plus consistency bias",
    "M5": "prediction-induced bias (exploratory)",
    "M6": "signal strength / vividness",
    "M7": "higher-order precision / confidence",
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def model_space_payload() -> dict[str, Any]:
    models = []
    for model in MODELS:
        models.append(
            {
                "model_id": model,
                "account": MODEL_ACCOUNTS[model],
                "status": "confirmatory" if model in CONFIRMATORY_MODELS else "exploratory",
                "active_parameters": list(active_parameters(model)),
                "readout_scope": READOUT_SCOPE,
                "full_model_scope": FULL_SCOPE if model in FULL_MODELS else None,
                "prediction": {
                    "M6": (
                        "source judgment is mediated by trial vividness; a direct prediction effect "
                        "after controlling vividness rejects M6"
                    ),
                    "M7": (
                        "source judgment and confidence are joint functions of precision; a direct "
                        "prediction effect beyond precision rejects M7"
                    ),
                }.get(model, "see CRT theory adjudication"),
            }
        )
    return {
        "analysis": "stage0h_model_space",
        "protocol": "ANIMUS-CRT-v1",
        "models": models,
        "confirmatory_models": list(CONFIRMATORY_MODELS),
        "exploratory_models": list(EXPLORATORY_MODELS),
        "full_models": list(FULL_MODELS),
        "full_active": {model: list(values) for model, values in FULL_ACTIVE.items()},
        "decision": "CRT_STAGE0H_MODEL_SPACE_PASS",
        "note": (
            "Model-space declaration only. M1/M3/M5 remain exploratory. No model is evidence for a "
            "human mechanism until the pre-specified recovery and SBC gates pass."
        ),
    }


def _read_artifact(out_dir: Path, name: str) -> dict[str, Any] | None:
    path = out_dir / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def package_payload(out_dir: Path) -> dict[str, Any]:
    model_space = _read_artifact(out_dir, ARTIFACTS["model_space"])
    design = _read_artifact(out_dir, ARTIFACTS["design"])
    sbc = _read_artifact(out_dir, ARTIFACTS["full_sbc"])
    recovery = _read_artifact(out_dir, ARTIFACTS["full_recovery"])
    blockers: list[str] = []
    if not model_space or model_space.get("decision") != "CRT_STAGE0H_MODEL_SPACE_PASS":
        blockers.append("model space")
    if not design or design.get("decision") != "CRT_STAGE0H_DESIGN_OPTIMIZATION_PASS":
        blockers.append("design optimization")
    if not sbc or sbc.get("decision") != "CRT_STAGE0H_FULL_MODEL_SBC_PASS":
        blockers.append("full-model SBC")
    if not recovery or recovery.get("decision") != "CRT_STAGE0H_FULL_MODEL_RECOVERY_PASS":
        blockers.append("full-model recovery")
    blockers.extend(["independent PI/statistician review", "adversarial review", "ethics approval"])
    return {
        "analysis": "stage0h_registration_package",
        "protocol": "ANIMUS-CRT-v1",
        "status": "BLOCKED" if blockers else "READY_FOR_INDEPENDENT_REVIEW",
        "blockers": blockers,
        "decisions": {
            "model_space": None if not model_space else model_space.get("decision"),
            "design_optimization": None if not design else design.get("decision"),
            "full_model_sbc": None if not sbc else sbc.get("decision"),
            "full_model_recovery": None if not recovery else recovery.get("decision"),
        },
        "note": (
            "Stage 0H is computational and documentation-only. A READY status would still require "
            "independent review, calibration, registration, and ethics approval before human data."
        ),
    }


def build_reports(*, quick: bool, full: bool = False) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {"model_space": model_space_payload()}
    if quick:
        design_cfg = DesignOptimizationConfig(
            n_participants=8,
            n_trials=30,
            n_replicates=1,
            n_power_simulations=20,
            candidates=DEFAULT_CANDIDATES[:2],
            seed=20261031,
        )
        reports["design"] = run_design_optimization(design_cfg)
        sbc_cfg = FullModelConfig(
            n_sbc=2,
            n_recovery=1,
            n_participants=8,
            n_trials=30,
            n_posterior_draws=20,
            max_iter=60,
            seed=20261031,
        )
        reports["full_sbc"] = run_full_sbc(sbc_cfg, model="M6")
        reports["full_recovery"] = run_full_recovery(sbc_cfg, model_set=("M0", "M6"))
    else:
        design_cfg = DesignOptimizationConfig(
            n_participants=16,
            n_trials=80,
            n_replicates=2,
            n_power_simulations=200,
            candidates=DEFAULT_CANDIDATES,
            seed=20261031,
        )
        reports["design"] = run_design_optimization(design_cfg)
        sbc_cfg = FullModelConfig(
            n_sbc=20,
            n_recovery=1,
            n_participants=12,
            n_trials=60,
            n_posterior_draws=100,
            max_iter=150,
            seed=20261031,
        )
        reports["full_sbc"] = run_full_sbc(sbc_cfg, model="M6")
        reports["full_recovery"] = run_full_recovery(sbc_cfg)
    reports["package"] = package_payload_from_reports(reports)
    return reports


def package_payload_from_reports(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if reports["model_space"].get("decision") != "CRT_STAGE0H_MODEL_SPACE_PASS":
        blockers.append("model space")
    if reports["design"].get("decision") != "CRT_STAGE0H_DESIGN_OPTIMIZATION_PASS":
        blockers.append("design optimization")
    if reports["full_sbc"].get("decision") != "CRT_STAGE0H_FULL_MODEL_SBC_PASS":
        blockers.append("full-model SBC")
    if reports["full_recovery"].get("decision") != "CRT_STAGE0H_FULL_MODEL_RECOVERY_PASS":
        blockers.append("full-model recovery")
    blockers.extend(["independent PI/statistician review", "adversarial review", "ethics approval"])
    return {
        "analysis": "stage0h_registration_package",
        "protocol": "ANIMUS-CRT-v1",
        "status": "BLOCKED" if blockers else "READY_FOR_INDEPENDENT_REVIEW",
        "blockers": blockers,
        "decisions": {
            name: reports[name].get("decision")
            for name in ("model_space", "design", "full_sbc", "full_recovery")
        },
        "note": (
            "Stage 0H is computational and documentation-only. A READY status would still require "
            "independent review, calibration, registration, and ethics approval before human data."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--full-sbc", action="store_true")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--model-space", action="store_true")
    parser.add_argument("--design", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    if args.full_sbc or args.recovery:
        cfg = FullModelConfig(
            n_sbc=20 if args.full_sbc else 1,
            n_recovery=1,
            n_participants=12,
            n_trials=60,
            n_posterior_draws=100,
            max_iter=150,
        )
        if args.full_sbc:
            payload = run_full_sbc(cfg, model="M6")
            _write_json(args.out_dir / ARTIFACTS["full_sbc"], payload)
        if args.recovery:
            payload = run_full_recovery(cfg)
            _write_json(args.out_dir / ARTIFACTS["full_recovery"], payload)
        print(
            json.dumps(
                {
                    "full_sbc": (args.out_dir / ARTIFACTS["full_sbc"]).exists(),
                    "recovery": (args.out_dir / ARTIFACTS["full_recovery"]).exists(),
                }
            )
        )
        return 0

    reports = build_reports(quick=args.check or not args.write)
    if args.write:
        for key, payload in reports.items():
            _write_json(args.out_dir / ARTIFACTS[key], payload)
        package = package_payload(args.out_dir)
        _write_json(args.out_dir / ARTIFACTS["package"], package)
    for key, payload in reports.items():
        print(f"{ARTIFACTS[key]}: {payload.get('decision', payload.get('status', 'UNKNOWN'))}")
    if args.strict and any(
        payload.get("decision", "").endswith("_REVIEW") or payload.get("status") == "BLOCKED"
        for payload in reports.values()
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
