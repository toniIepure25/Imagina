"""CLI for the Stage 0 ART reliability power check."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.art.power import PowerConfig, check_power, run_power


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Stage 0 ART reliability power check.")
    parser.add_argument("--check", action="store_true", help="run the small CI gate and exit")
    parser.add_argument("--participants", type=int, default=180)
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.check:
        report = check_power()
    else:
        report = run_power(
            PowerConfig(
                n_participants=args.participants,
                n_simulations=args.simulations,
                seed=args.seed,
            )
        )
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
