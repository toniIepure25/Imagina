"""Task D — Perceptual negative control.

Target remains visible while the participant matches it. Isolates display
interaction, motor precision, and perceptual matching from imagery ability.
Improvement only in this task should not be interpreted as improved imagery.
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

PERCEPTUAL_PHASES = [
    TrialPhase.FIXATION,
    TrialPhase.TARGET_PRESENTATION,
    TrialPhase.RECONSTRUCTION,
    TrialPhase.CONFIDENCE,
]

FEATURE_RANGES = {
    "orientation_deg": (0.0, 180.0),
    "hue_deg": (0.0, 360.0),
    "spatial_frequency_cpd": (0.5, 8.0),
    "position_x": (100.0, 900.0),
    "position_y": (100.0, 700.0),
    "size": (20.0, 100.0),
}


def generate_perceptual_control_trials(
    n_trials: int,
    seed: int,
    display_diagonal: float = 1000.0,
    id_prefix: str = "percep",
) -> list[TrialSpec]:
    rng = random.Random(seed)
    feature_sets = balanced_feature_values(
        rng, n_trials, FEATURE_RANGES, {"orientation_deg", "hue_deg"},
    )

    trials: list[TrialSpec] = []
    for i, features in enumerate(feature_sets):
        target = StimulusSpec(
            orientation_deg=features["orientation_deg"],
            hue_deg=features["hue_deg"],
            spatial_frequency_cpd=features["spatial_frequency_cpd"],
            position_x=features["position_x"],
            position_y=features["position_y"],
            size=features["size"],
        )
        trials.append(TrialSpec(
            trial_id=f"{id_prefix}-{seed}-{i:04d}",
            trial_index=i,
            task_family=TaskFamily.PERCEPTUAL_CONTROL,
            target=target,
            expected_response=target,
            mask_strength=0.0,
            display_diagonal=display_diagonal,
            phases=list(PERCEPTUAL_PHASES),
        ))
    return trials
