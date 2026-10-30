"""CLI for the Stage 0D CRT theory and design controls."""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from app.research.crt.calibration import CalibrationConfig, run_calibration
from app.research.crt.gtheory import GTheoryConfig, run_gtheory
from app.research.crt.power import PowerConfig, simulate_power
from app.research.crt.simulate import (
    SimulationConfig,
    run_selection_simulation,
    run_specificity_simulation,
)
from app.research.crt.theory import TheoryConfig, run_theory_tournament

DEFAULT_OUT = Path("results/crt")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic Stage 0D CRT design checks.")
    parser.add_argument("--check", action="store_true", help="run the small CI checks and exit")
    parser.add_argument("--write", action="store_true", help="write the registered JSON artifacts")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--participants", type=int, default=60)
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--max-tests", type=int, default=2)
    return parser


def _control_report(config: SimulationConfig) -> dict[str, object]:
    legacy = replace(config, prediction_source="oracle", source_update="legacy")
    specificity = run_specificity_simulation(legacy)
    selection = run_selection_simulation(legacy)
    passed = (
        specificity["decision"] == "CRT_STAGE0D_SPECIFICITY_PASS"
        and selection["decision"] == "CRT_STAGE0D_SELECTION_PASS"
    )
    return {
        "protocol": "ANIMUS-CRT-v1",
        "analysis": "stage0d_specificity_and_active_selection",
        "config": {
            "n_participants": config.n_participants,
            "n_trials": config.n_trials,
            "seed": config.seed,
            "max_tests": config.max_tests,
        },
        "specificity": specificity,
        "selection": selection,
        "decision": "CRT_STAGE0D_SPECIFICITY_PASS" if passed else "CRT_STAGE0D_SPECIFICITY_REVIEW",
        "note": (
            "Simulation-only design checks under the historical oracle prediction path. The diagnostic-"
            "versus-nondiagnostic contrast tests prediction specificity; active, algorithm-adaptive, and "
            "random-passive arms decompose active selection. This artifact is retained for provenance; "
            "Stage 0E shows that the diagnostic-specificity result does not survive belief-based "
            "prediction. Neither check is human evidence."
        ),
    }


def _write_reports(out_dir: Path, reports: dict[str, dict[str, object]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, report in reports.items():
        (out_dir / filename).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        report = {
            "theory": run_theory_tournament(TheoryConfig(n_observations=20, noise_sd=0.02, seed=7)),
            "controls": _control_report(
                SimulationConfig(n_participants=8, n_trials=30, seed=7, max_tests=args.max_tests)
            ),
            "gtheory": run_gtheory(GTheoryConfig(n_participants=30, n_occasions=2, seed=7)),
            "calibration": run_calibration(
                CalibrationConfig(n_participants=20, trials_per_cell=20, seed=7, noise_sd=0.01)
            ),
        }
        failed = [
            name
            for name, item in report.items()
            if str(item.get("decision", "")).endswith("_REVIEW")
        ]
        if failed:
            raise AssertionError(f"Stage 0D checks failed: {failed}")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    config = SimulationConfig(
        n_participants=args.participants,
        n_trials=args.trials,
        seed=args.seed,
        max_tests=args.max_tests,
    )
    gtheory = run_gtheory(GTheoryConfig(n_participants=60, n_occasions=2, seed=args.seed))
    gtheory["power_n240"] = simulate_power(
        0.80,
        PowerConfig(
            n_participants=240,
            n_simulations=2000,
            seed=args.seed,
            lower_bound_target=0.70,
        ),
    )
    reports = {
        "CRT_STAGE0D_MODEL_TOURNAMENT.json": run_theory_tournament(
            TheoryConfig(n_observations=40, noise_sd=0.03, seed=args.seed)
        ),
        "CRT_STAGE0D_SPECIFICITY_POWER.json": _control_report(config),
        "CRT_STAGE0D_GTHEORY.json": gtheory,
        "CRT_STAGE0D_CALIBRATION.json": run_calibration(
            CalibrationConfig(n_participants=40, trials_per_cell=20, seed=args.seed)
        ),
    }
    if args.write:
        _write_reports(args.out_dir, reports)
    print(json.dumps(reports, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
