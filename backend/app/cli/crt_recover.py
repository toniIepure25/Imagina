"""CLI for CRT Stage 0 parameter recovery and condition comparison."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.crt.simulate import SimulationConfig, compare_conditions, run_recovery


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CRT parameter recovery and condition comparison.")
    parser.add_argument("--participants", type=int, default=60)
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = SimulationConfig(
        n_participants=args.participants,
        n_trials=args.trials,
        seed=args.seed,
    )
    report = run_recovery(config)
    report["comparison"] = compare_conditions(config)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
