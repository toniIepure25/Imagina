"""CLI for the Stage 0 Source and Imagination Monitor simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.prm.simulate import SimulationConfig, check_simulation, compare_designs, run_simulation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Stage 0 SIM simulation.",
    )
    parser.add_argument("--check", action="store_true", help="run the small CI gate and exit")
    parser.add_argument("--compare", action="store_true", help="compare adaptive and fixed designs")
    parser.add_argument("--participants", type=int, default=120)
    parser.add_argument("--trials", type=int, default=120)
    parser.add_argument("--items", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--design", choices=("adaptive", "fixed"), default="adaptive")
    parser.add_argument("--out", type=Path, default=None, help="optional JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        report = check_simulation()
    else:
        config = SimulationConfig(
            n_participants=args.participants,
            n_trials=args.trials,
            n_items=args.items,
            seed=args.seed,
            design=args.design,
        )
        report = run_simulation(config)
        if args.compare:
            report["comparison"] = compare_designs(config)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
