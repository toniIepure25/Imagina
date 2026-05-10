"""Dataset signal quality evaluation CLI."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from app.datasets.loaders import load_windows
from app.services.feature_engine import FeatureEngine
from app.services.signal_quality import evaluate_signal_quality


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m app.cli.dataset_quality",
        description="Evaluate signal quality on dataset/fixture windows.",
    )
    p.add_argument("--dataset", default="fixture")
    p.add_argument("--max-windows", type=int, default=50)
    p.add_argument("--output", default=None)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    windows = load_windows(args.dataset, max_windows=args.max_windows)
    engine = FeatureEngine()
    fvs = [engine.process_eeg_window(w) for w in windows]
    result = evaluate_signal_quality(fvs)

    report = {
        "tool": "imagina_dataset_quality",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": args.dataset,
        "windows_evaluated": len(fvs),
        **result,
        "disclaimer": "Experimental proxy features. Not clinical-grade EEG analysis.",
    }

    output_path = args.output or os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "exports",
        f"dataset_quality_{args.dataset}.json",
    )
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Quality report written to {output_path}", file=sys.stderr)
    print(f"  Quality: {result['quality_score']:.3f} | Warnings: {result['warnings']}", file=sys.stderr)
    return 1 if result["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
