"""CLI for the Stage 0 Counterfactual Reality Testing simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.crt.simulate import (
    SimulationConfig,
    check_prediction_ablation,
    check_recovery,
    check_simulation,
    compare_conditions,
    run_recovery,
    run_simulation,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic Stage 0 CRT simulation.")
    parser.add_argument("--check", action="store_true", help="run the small CI gates and exit")
    parser.add_argument("--recovery", action="store_true", help="run parameter recovery")
    parser.add_argument("--compare", action="store_true", help="run the condition comparison")
    parser.add_argument("--participants", type=int, default=60)
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--max-tests", type=int, default=2)
    parser.add_argument("--out", type=Path, default=None, help="optional JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        report = {
            "simulation": check_simulation(),
            "recovery": check_recovery(),
            "prediction_ablation": check_prediction_ablation(),
        }
    else:
        config = SimulationConfig(
            n_participants=args.participants,
            n_trials=args.trials,
            seed=args.seed,
            max_tests=args.max_tests,
        )
        report = run_simulation(config)
        if args.recovery:
            report["recovery"] = run_recovery(
                SimulationConfig(
                    n_participants=args.participants,
                    n_trials=args.trials,
                    seed=args.seed,
                    max_tests=args.max_tests,
                )
            )
        if args.compare:
            report["comparison"] = compare_conditions(config)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
