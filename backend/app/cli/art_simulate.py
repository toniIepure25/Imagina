"""CLI for the Stage 0 Active Reality Testing simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.art.simulate import (
    SimulationConfig,
    check_policy_comparison,
    check_recovery,
    check_simulation,
    compare_policies,
    run_recovery,
    run_simulation,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic Stage 0 ART simulation.")
    parser.add_argument("--check", action="store_true", help="run the small CI gates and exit")
    parser.add_argument("--recovery", action="store_true", help="run policy-parameter recovery")
    parser.add_argument("--compare", action="store_true", help="compare EIG and baseline policies")
    parser.add_argument("--participants", type=int, default=60)
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--max-queries", type=int, default=2)
    parser.add_argument("--out", type=Path, default=None, help="optional JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        report = {
            "simulation": check_simulation(),
            "recovery": check_recovery(),
            "policy": check_policy_comparison(),
        }
    else:
        config = SimulationConfig(
            n_participants=args.participants,
            n_trials=args.trials,
            seed=args.seed,
            max_queries=args.max_queries,
        )
        report = run_simulation(config)
        if args.recovery:
            report["recovery"] = run_recovery(
                SimulationConfig(
                    n_participants=args.participants,
                    n_trials=args.trials,
                    seed=args.seed,
                    max_queries=args.max_queries,
                    cost_levels=(0.5, 1.0, 2.0),
                )
            )
        if args.compare:
            report["comparison"] = compare_policies(config)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
