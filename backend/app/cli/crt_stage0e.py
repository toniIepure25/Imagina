"""CLI for the Stage 0E CRT model-repair, counterfactual, policy, and psychometric checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.crt.counterfactual import CounterfactualConfig, run_counterfactual_simulation
from app.research.crt.model_repair import ModelRepairConfig, run_model_repair
from app.research.crt.pit import PitConfig, run_pit_calibration
from app.research.crt.policy import PolicyConfig, run_policy_tournament
from app.research.crt.psychometrics import PsychometricConfig, run_psychometrics
from app.research.crt.recovery import RecoveryConfig, run_recovery
from app.research.crt.simulate import SimulationConfig, run_specificity_simulation

DEFAULT_OUT = Path("results/crt")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic Stage 0E CRT checks.")
    parser.add_argument("--check", action="store_true", help="run the small CI checks and exit")
    parser.add_argument("--write", action="store_true", help="write the registered JSON artifacts")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--participants", type=int, default=24)
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20261030)
    parser.add_argument("--max-tests", type=int, default=2)
    parser.add_argument(
        "--recovery",
        action="store_true",
        help="also run the slow conditional SBC and model-recovery audit",
    )
    return parser


def _model_report(participants: int, trials: int, seed: int, max_tests: int) -> dict[str, object]:
    model = run_model_repair(ModelRepairConfig(n_participants=participants, n_trials=trials, seed=seed))
    pit = run_pit_calibration(PitConfig(n_simulations=1000, n_tests=max_tests, seed=seed))
    passed = model["decision"] == "CRT_STAGE0E_MODEL_PASS" and pit["decision"] == "CRT_STAGE0E_PIT_PASS"
    model["pit_calibration"] = pit
    model["decision"] = "CRT_STAGE0E_MODEL_PASS" if passed else "CRT_STAGE0E_MODEL_REVIEW"
    model["note"] = (
        "Stage 0E model repair. Oracle prediction is retained only as a benchmark; the belief arm "
        "predicts from the current source posterior and updates the source from the outcome only. "
        "The nested PIT check is a posterior calibration screening for the assumed generative model, "
        "not full hierarchical SBC. A PASS is design evidence, not human validation."
    )
    return model


def _specificity_audit(args: argparse.Namespace) -> dict[str, object]:
    specificity = run_specificity_simulation(
        SimulationConfig(
            n_participants=args.participants,
            n_trials=args.trials,
            seed=args.seed,
            max_tests=args.max_tests,
            prediction_source="belief",
            source_update="outcome",
        )
    )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0e_belief_specificity_audit",
        "config": {
            "n_participants": args.participants,
            "n_trials": args.trials,
            "seed": args.seed,
            "max_tests": args.max_tests,
            "prediction_source": "belief",
            "source_update": "outcome",
        },
        "specificity": specificity,
        "decision": "CRT_STAGE0D_SPECIFICITY_PASS"
        if specificity["decision"] == "CRT_STAGE0D_SPECIFICITY_PASS"
        else "CRT_STAGE0D_SPECIFICITY_REVIEW",
        "note": (
            "Superseding belief-based audit of the Stage 0D diagnostic-specificity control. The "
            "historical oracle artifact is preserved. A REVIEW means the diagnostic-specificity claim "
            "is downgraded and cannot be used as human prediction evidence."
        ),
    }


def _reports(args: argparse.Namespace) -> dict[str, dict[str, object]]:
    reports = {
        "CRT_STAGE0E_MODEL_REPAIR.json": _model_report(
            args.participants, args.trials, args.seed, args.max_tests
        ),
        "CRT_STAGE0E_SPECIFICITY_AUDIT.json": _specificity_audit(args),
        "CRT_STAGE0E_COUNTERFACTUAL.json": run_counterfactual_simulation(
            CounterfactualConfig(
                n_participants=args.participants,
                n_trials=args.trials,
                seed=args.seed,
                max_tests=args.max_tests,
            )
        ),
        "CRT_STAGE0E_POLICY.json": run_policy_tournament(
            PolicyConfig(
                n_participants=args.participants,
                n_trials=args.trials,
                seed=args.seed,
                max_tests=args.max_tests,
            )
        ),
        "CRT_STAGE0E_PSYCHOMETRIC.json": run_psychometrics(
            PsychometricConfig(n_participants=60, n_tests=6, seed=args.seed)
        ),
    }
    if getattr(args, "recovery", False):
        reports["CRT_STAGE0E_RECOVERY.json"] = run_recovery(RecoveryConfig(seed=args.seed))
    return reports


def _write_reports(out_dir: Path, reports: dict[str, dict[str, object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, report in reports.items():
        (out_dir / filename).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        reports = _reports(argparse.Namespace(**{**vars(args), "participants": 8, "trials": 30, "seed": 7}))
        model = reports["CRT_STAGE0E_MODEL_REPAIR.json"]
        psychometric = reports["CRT_STAGE0E_PSYCHOMETRIC.json"]
        failed = []
        if model["decision"] != "CRT_STAGE0E_MODEL_PASS":
            failed.append("model")
        if psychometric["decision"] != "CRT_STAGE0E_PSYCHOMETRIC_PASS":
            failed.append("psychometric")
        if failed:
            raise AssertionError(f"Stage 0E checks failed: {failed}")
        print(json.dumps(reports, indent=2, sort_keys=True))
        return 0

    reports = _reports(args)
    if args.write:
        _write_reports(args.out_dir, reports)
    print(json.dumps(reports, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
