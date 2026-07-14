"""Task B — Imagery manipulation.

Participant sees a base stimulus, is instructed to mentally transform it,
then reconstructs the transformed version. Scores distance between response
and the mathematically expected transformed target.
"""
from __future__ import annotations

import math
import random

from app.research.psychophysics.common import (
    StimulusSpec,
    TaskFamily,
    TransformSpec,
    TrialPhase,
    TrialSpec,
    balanced_feature_values,
)

MANIPULATION_PHASES = [
    TrialPhase.FIXATION,
    TrialPhase.TARGET_PRESENTATION,
    TrialPhase.MASK,
    TrialPhase.IMAGERY,
    TrialPhase.RECONSTRUCTION,
    TrialPhase.CONFIDENCE,
    TrialPhase.SELF_REPORT,
]

TRANSFORM_TYPES = [
    "rotate",
    "shift_position",
    "change_frequency",
    "change_hue",
    "resize",
]


def apply_transform(stimulus: StimulusSpec, transform: TransformSpec) -> StimulusSpec:
    """Apply a mental transformation to produce the expected target."""
    s = StimulusSpec(
        orientation_deg=stimulus.orientation_deg,
        hue_deg=stimulus.hue_deg,
        spatial_frequency_cpd=stimulus.spatial_frequency_cpd,
        position_x=stimulus.position_x,
        position_y=stimulus.position_y,
        size=stimulus.size,
    )
    if transform.transform_type == "rotate":
        s.orientation_deg = (s.orientation_deg + transform.parameter) % 180.0
    elif transform.transform_type == "shift_position":
        s.position_x = max(0.0, min(1000.0, s.position_x + transform.parameter))
    elif transform.transform_type == "change_frequency":
        s.spatial_frequency_cpd = max(0.1, s.spatial_frequency_cpd * math.exp(transform.parameter))
    elif transform.transform_type == "change_hue":
        s.hue_deg = (s.hue_deg + transform.parameter) % 360.0
    elif transform.transform_type == "resize":
        s.size = max(5.0, s.size * math.exp(transform.parameter))
    return s


def generate_manipulation_trials(
    n_trials: int,
    seed: int,
    display_diagonal: float = 1000.0,
    id_prefix: str = "manip",
) -> list[TrialSpec]:
    rng = random.Random(seed)

    feature_ranges = {
        "orientation_deg": (0.0, 180.0),
        "hue_deg": (0.0, 360.0),
        "spatial_frequency_cpd": (1.0, 6.0),
        "position_x": (200.0, 800.0),
        "position_y": (200.0, 600.0),
        "size": (30.0, 80.0),
    }
    feature_sets = balanced_feature_values(
        rng, n_trials, feature_ranges, {"orientation_deg", "hue_deg"},
    )

    transform_params = {
        "rotate": (-45.0, 45.0),
        "shift_position": (-100.0, 100.0),
        "change_frequency": (-0.5, 0.5),
        "change_hue": (-60.0, 60.0),
        "resize": (-0.3, 0.3),
    }

    trials: list[TrialSpec] = []
    for i, features in enumerate(feature_sets):
        t_type = TRANSFORM_TYPES[i % len(TRANSFORM_TYPES)]
        lo, hi = transform_params[t_type]
        param = rng.uniform(lo, hi)
        if abs(param) < (hi - lo) * 0.1:
            param = (hi - lo) * 0.15 * (1 if param >= 0 else -1)

        base = StimulusSpec(
            orientation_deg=features["orientation_deg"],
            hue_deg=features["hue_deg"],
            spatial_frequency_cpd=features["spatial_frequency_cpd"],
            position_x=features["position_x"],
            position_y=features["position_y"],
            size=features["size"],
        )
        transform = TransformSpec(transform_type=t_type, parameter=round(param, 4))
        expected = apply_transform(base, transform)

        trials.append(TrialSpec(
            trial_id=f"{id_prefix}-{seed}-{i:04d}",
            trial_index=i,
            task_family=TaskFamily.IMAGERY_MANIPULATION,
            target=base,
            expected_response=expected,
            transform=transform,
            display_diagonal=display_diagonal,
            phases=list(MANIPULATION_PHASES),
        ))
    return trials
