"""Fixed-sample sensitivity analysis for the C2 primary estimand (H1),
reusing C1's `sensitivity.py` machinery unchanged (it is fully generic over
any per-participant "delta" quantity, participant count, and observed
standard deviation -- not specific to C1's own estimand).

The per-participant "delta" here is (chance_log_loss - observed_log_loss)
for the classical-feature-decoder content baseline (Commit 3,
results/c2_content_decoding.json): a POSITIVE delta means a participant's
held-out content decoding was better than chance, matching the sign
convention `sensitivity.py` already assumes (positive = the direction of
interest). This is the closest thing to a primary confirmatory effect
size established anywhere in C2's real-data results.

Not a CI-run script in the sense of requiring real data download, but it
IS cheap (a Monte Carlo simulation, no EEG data needed) -- run manually:

    python -m app.research.neural.run_c2_sensitivity
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.research.neural.sensitivity import MINIMUM_EFFECT_OF_INTEREST, run_sensitivity_analysis

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def main() -> None:
    content_decoding = json.loads((RESULTS_DIR / "c2_content_decoding.json").read_text())
    per_participant_log_loss = (
        content_decoding["baselines"]["classical_feature_decoder"]["class_weighted_log_loss"]["per_participant"]
    )
    chance_log_loss = float(np.log(3))
    deltas = {p: chance_log_loss - ll for p, ll in per_participant_log_loss.items()}
    delta_values = np.array(list(deltas.values()))
    n_participants = len(delta_values)
    observed_std = float(delta_values.std())
    observed_mean = float(delta_values.mean())

    print(
        f"n_participants={n_participants} observed_mean_delta={observed_mean:.4f} "
        f"observed_std_delta={observed_std:.4f}", file=sys.stderr,
    )

    result = run_sensitivity_analysis(
        n_participants=n_participants, observed_std_delta_oos=observed_std, n_simulations=2000,
    )

    payload = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": _code_sha(),
        "created_at": datetime.now(timezone.utc).isoformat(), "confirmatory_or_exploratory": "confirmatory",
        "estimand_id": "C2_H1_CONTENT_DECODING_SENSITIVITY",
        "basis": "classical_feature_decoder content baseline (results/c2_content_decoding.json, Commit 3)",
        "n_participants": n_participants,
        "observed_mean_delta_log_loss_vs_chance": observed_mean,
        "observed_std_delta_log_loss_vs_chance": observed_std,
        "per_participant_delta": deltas,
        **result.to_dict(),
        "note": (
            "Positive delta = better-than-chance content decoding for that participant "
            "(chance_log_loss - observed_log_loss); the observed mean delta is negative "
            "(worse than chance), consistent with Commits 3-6's null findings. This "
            "sensitivity analysis establishes whether the fixed 14-participant sample "
            f"had adequate power (>= 0.80) to detect a real effect of the prespecified "
            f"minimum size ({MINIMUM_EFFECT_OF_INTEREST}) if one existed -- it does not "
            "retroactively change the observed null result, only characterizes its "
            "statistical power."
        ),
    }
    with open(RESULTS_DIR / "c2_sensitivity.json", "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"power_at_minimum_effect_of_interest={result.power_at_minimum_effect_of_interest:.4f} "
          f"adequately_powered={result.adequately_powered}", file=sys.stderr)
    print("Wrote c2_sensitivity.json", file=sys.stderr)


if __name__ == "__main__":
    main()
