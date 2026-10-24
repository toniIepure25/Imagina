"""Task A — Multi-feature imagery reconstruction.

Trial flow:
  fixation -> target presentation -> mask -> imagery -> reconstruction -> confidence -> self-report

Scores objective feature-space error between ground-truth target and reconstruction response.
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

RECONSTRUCTION_PHASES = [
    TrialPhase.FIXATION,
    TrialPhase.TARGET_PRESENTATION,
    TrialPhase.MASK,
    TrialPhase.IMAGERY,
    TrialPhase.RECONSTRUCTION,
    TrialPhase.CONFIDENCE,
    TrialPhase.SELF_REPORT,
]

FEATURE_RANGES = {
    "orientation_deg": (0.0, 180.0),
    "hue_deg": (0.0, 360.0),
    "spatial_frequency_cpd": (0.5, 8.0),
    "position_x": (100.0, 900.0),
    "position_y": (100.0, 700.0),
    "size": (20.0, 100.0),
}

CIRCULAR_FEATURES = {"orientation_deg", "hue_deg"}


def generate_reconstruction_trials(
    n_trials: int,
    seed: int,
    mask_strength: float = 0.5,
    display_diagonal: float = 1000.0,
    id_prefix: str = "recon",
) -> list[TrialSpec]:
    rng = random.Random(seed)
    feature_sets = balanced_feature_values(
        rng, n_trials, FEATURE_RANGES, CIRCULAR_FEATURES,
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
            task_family=TaskFamily.FEATURE_RECONSTRUCTION,
            target=target,
            expected_response=target,
            mask_strength=mask_strength,
            display_diagonal=display_diagonal,
            phases=list(RECONSTRUCTION_PHASES),
        ))
    return trials
