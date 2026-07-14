"""Common types for the psychophysics task battery."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

BATTERY_VERSION = "1.0"


class TaskFamily(Enum):
    FEATURE_RECONSTRUCTION = "feature_reconstruction"
    IMAGERY_MANIPULATION = "imagery_manipulation"
    DELAYED_IMAGERY = "delayed_imagery"
    PERCEPTUAL_CONTROL = "perceptual_control"


class TrialPhase(Enum):
    FIXATION = "fixation"
    TARGET_PRESENTATION = "target_presentation"
    MASK = "mask"
    IMAGERY = "imagery"
    RECONSTRUCTION = "reconstruction"
    CONFIDENCE = "confidence"
    SELF_REPORT = "self_report"


class InvalidityFlag(Enum):
    NONE = "none"
    MISSING_RESPONSE = "missing_response"
    RESPONSE_OUT_OF_RANGE = "response_out_of_range"
    RESPONSE_TOO_FAST = "response_too_fast"
    RESPONSE_TOO_SLOW = "response_too_slow"
    IMPOSSIBLE_TRANSFORMATION = "impossible_transformation"


@dataclass
class StimulusSpec:
    orientation_deg: float
    hue_deg: float
    spatial_frequency_cpd: float
    position_x: float
    position_y: float
    size: float

    def to_dict(self) -> dict[str, float]:
        return {
            "orientation_deg": self.orientation_deg,
            "hue_deg": self.hue_deg,
            "spatial_frequency_cpd": self.spatial_frequency_cpd,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "size": self.size,
        }


@dataclass
class TransformSpec:
    transform_type: str
    parameter: float

    def to_dict(self) -> dict[str, Any]:
        return {"transform_type": self.transform_type, "parameter": self.parameter}


@dataclass
class ResponseSpec:
    orientation_deg: float | None = None
    hue_deg: float | None = None
    spatial_frequency_cpd: float | None = None
    position_x: float | None = None
    position_y: float | None = None
    size: float | None = None
    latency_ms: float | None = None
    confidence: float | None = None
    vividness: float | None = None
    effort: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in {
            "orientation_deg": self.orientation_deg,
            "hue_deg": self.hue_deg,
            "spatial_frequency_cpd": self.spatial_frequency_cpd,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "size": self.size,
            "latency_ms": self.latency_ms,
            "confidence": self.confidence,
            "vividness": self.vividness,
            "effort": self.effort,
        }.items() if v is not None}


@dataclass
class TrialSpec:
    trial_id: str
    trial_index: int
    task_family: TaskFamily
    target: StimulusSpec
    expected_response: StimulusSpec
    transform: TransformSpec | None = None
    delay_s: float = 0.0
    mask_strength: float = 0.5
    display_diagonal: float = 1000.0
    phases: list[TrialPhase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "trial_id": self.trial_id,
            "trial_index": self.trial_index,
            "task_family": self.task_family.value,
            "target": self.target.to_dict(),
            "expected_response": self.expected_response.to_dict(),
            "delay_s": self.delay_s,
            "mask_strength": self.mask_strength,
            "display_diagonal": self.display_diagonal,
            "phases": [p.value for p in self.phases],
        }
        if self.transform:
            d["transform"] = self.transform.to_dict()
        return d


def schedule_hash(trials: list[TrialSpec]) -> str:
    data = [t.to_dict() for t in trials]
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def balanced_feature_values(
    rng: random.Random,
    n: int,
    feature_ranges: dict[str, tuple[float, float]],
    circular_features: set[str] | None = None,
) -> list[dict[str, float]]:
    """Generate n balanced feature-value combinations across feature ranges."""
    circular_features = circular_features or set()
    values: list[dict[str, float]] = []
    for i in range(n):
        row: dict[str, float] = {}
        for feat, (lo, hi) in feature_ranges.items():
            n_bins = max(n, 6)
            bin_idx = i % n_bins
            base = lo + (hi - lo) * (bin_idx + 0.5) / n_bins
            jitter = (hi - lo) / n_bins * 0.3 * (rng.random() - 0.5)
            val = base + jitter
            if feat in circular_features:
                val = val % hi
            else:
                val = max(lo, min(hi, val))
            row[feat] = round(val, 4)
        values.append(row)
    rng.shuffle(values)
    return values
