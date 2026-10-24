"""Task C — Delayed imagery stability.

Uses multiple retention delays to estimate immediate vs. delayed reconstruction
error and within-trial degradation.
"""
from __future__ import annotations

import random

from app.research.psychophysics.common import (
    StimulusSpec,
    TaskFamily,
    TrialPhase,
    TrialSpec,
    balanced_feature_values,
)

DELAYED_PHASES = [
    TrialPhase.FIXATION,
    TrialPhase.TARGET_PRESENTATION,
    TrialPhase.MASK,
    TrialPhase.IMAGERY,
    TrialPhase.RECONSTRUCTION,
    TrialPhase.CONFIDENCE,
    TrialPhase.SELF_REPORT,
]

DEFAULT_DELAYS_S = [0.0, 2.0, 5.0, 10.0]

FEATURE_RANGES = {
    "orientation_deg": (0.0, 180.0),
    "hue_deg": (0.0, 360.0),
    "spatial_frequency_cpd": (1.0, 6.0),
    "position_x": (150.0, 850.0),
    "position_y": (150.0, 650.0),
    "size": (25.0, 90.0),
}


def generate_delayed_trials(
    n_trials_per_delay: int,
    seed: int,
    delays_s: list[float] | None = None,
    display_diagonal: float = 1000.0,
    id_prefix: str = "delay",
) -> list[TrialSpec]:
    if delays_s is None:
        delays_s = list(DEFAULT_DELAYS_S)

    rng = random.Random(seed)
    total = n_trials_per_delay * len(delays_s)
    feature_sets = balanced_feature_values(
        rng, total, FEATURE_RANGES, {"orientation_deg", "hue_deg"},
    )

    trials: list[TrialSpec] = []
    idx = 0
    for delay in delays_s:
        for j in range(n_trials_per_delay):
            features = feature_sets[idx]
            target = StimulusSpec(
                orientation_deg=features["orientation_deg"],
                hue_deg=features["hue_deg"],
                spatial_frequency_cpd=features["spatial_frequency_cpd"],
                position_x=features["position_x"],
                position_y=features["position_y"],
                size=features["size"],
            )
            trials.append(TrialSpec(
                trial_id=f"{id_prefix}-{seed}-d{delay:.0f}-{j:04d}",
                trial_index=idx,
                task_family=TaskFamily.DELAYED_IMAGERY,
                target=target,
                expected_response=target,
                delay_s=delay,
                display_diagonal=display_diagonal,
                phases=list(DELAYED_PHASES),
            ))
            idx += 1

    rng.shuffle(trials)
    for i, t in enumerate(trials):
        t.trial_index = i
    return trials
