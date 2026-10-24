#!/usr/bin/env python3
"""Generate a synthetic research dataset for analysis pipeline development.

Usage:
    python scripts/generate_synthetic_dataset.py [--n-participants 24] [--seed 42] [--output data/synthetic/]

Produces:
    participants.csv  — one row per participant with VVIQ-2 scores
    trials.csv        — one row per trial with all DV/IV columns
    metadata.json     — generation parameters and version info
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.research.synthetic_data import export_to_csv_rows, generate_synthetic_dataset


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic IMAGINA dataset")
    parser.add_argument("--n-participants", type=int, default=24)
    parser.add_argument("--n-sessions", type=int, default=3)
    parser.add_argument("--trials-per-session", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="data/synthetic/")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    dataset = generate_synthetic_dataset(
        n_participants=args.n_participants,
        n_sessions_per_condition=args.n_sessions,
        trials_per_session=args.trials_per_session,
        seed=args.seed,
    )

    participants, trials = export_to_csv_rows(dataset)

    p_path = os.path.join(args.output, "participants.csv")
    with open(p_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=participants[0].keys())
        writer.writeheader()
        writer.writerows(participants)

    t_path = os.path.join(args.output, "trials.csv")
    with open(t_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=trials[0].keys())
        writer.writeheader()
        writer.writerows(trials)

    m_path = os.path.join(args.output, "metadata.json")
    with open(m_path, "w") as f:
        json.dump(dataset["metadata"], f, indent=2)

    print(f"Generated {len(participants)} participants, {len(trials)} trials")
    print(f"Output: {args.output}")
    print(f"  {p_path}")
    print(f"  {t_path}")
    print(f"  {m_path}")


if __name__ == "__main__":
    main()
