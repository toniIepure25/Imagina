"""Versioned objective endpoint registry for imagery measurement.

Each endpoint defines a scientifically meaningful outcome variable with frozen
scoring semantics, valid ranges, aggregation rules, and role classification.

The registry is immutable after protocol freeze — endpoint definitions must not
change without a version bump that invalidates prior manifests.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

REGISTRY_VERSION = "1.0"


class EndpointDomain(Enum):
    IMAGERY_PRECISION = "imagery_precision"
    IMAGERY_CONTROL = "imagery_control"
    IMAGERY_STABILITY = "imagery_stability"
    METACOGNITIVE_CALIBRATION = "metacognitive_calibration"
    SUBJECTIVE_VIVIDNESS = "subjective_vividness"
    PERCEPTUAL_MOTOR_CONTROL = "perceptual_motor_control"
    SAFETY = "safety"


class EndpointRole(Enum):
    PRIMARY = "primary"
    KEY_SECONDARY = "key_secondary"
    EXPLORATORY = "exploratory"
    MANIPULATION_CHECK = "manipulation_check"
    NEGATIVE_CONTROL = "negative_control"
    SAFETY = "safety"
    SUBJECTIVE_SECONDARY = "subjective_secondary"


class ScoreDirection(Enum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"


class Unit(Enum):
    STANDARDIZED_ERROR = "standardized_error"
    DEGREES = "degrees"
    LOG_RATIO = "log_ratio"
    PROPORTION = "proportion"
    PIXELS = "pixels"
    MILLISECONDS = "milliseconds"
    LIKERT_1_7 = "likert_1_7"
    SLOPE = "slope"
    CORRELATION = "correlation"
    UNITLESS = "unitless"


class AggregationRule(Enum):
    TRIAL_LEVEL = "trial_level"
    SESSION_MEAN = "session_mean"
    PARTICIPANT_MEAN = "participant_mean"
    BLOCK_MEAN = "block_mean"


class MissingnessRule(Enum):
    EXCLUDE_TRIAL = "exclude_trial"
    MAXIMUM_ERROR = "maximum_error"
    IMPUTE_MEDIAN = "impute_median"


class OutlierRule(Enum):
    NONE = "none"
    WINSORIZE_3SD = "winsorize_3sd"
    EXCLUDE_3SD = "exclude_3sd"


@dataclass(frozen=True)
class ReliabilityRequirement:
    minimum_split_half: float = 0.60
    minimum_trials_for_estimate: int = 10


@dataclass(frozen=True)
class ObjectiveEndpointDefinition:
    endpoint_id: str
    version: str
    display_name: str
    construct: EndpointDomain
    is_objective: bool
    role: EndpointRole
    unit: Unit
    score_direction: ScoreDirection
    valid_range: tuple[float, float]
    aggregation: AggregationRule
    missingness: MissingnessRule
    outlier_rule: OutlierRule
    reliability: ReliabilityRequirement
    description: str
    interpretation_boundary: str
    feature_weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "version": self.version,
            "display_name": self.display_name,
            "construct": self.construct.value,
            "is_objective": self.is_objective,
            "role": self.role.value,
            "unit": self.unit.value,
            "score_direction": self.score_direction.value,
            "valid_range": list(self.valid_range),
            "aggregation": self.aggregation.value,
            "missingness": self.missingness.value,
            "outlier_rule": self.outlier_rule.value,
            "reliability": {
                "minimum_split_half": self.reliability.minimum_split_half,
                "minimum_trials_for_estimate": self.reliability.minimum_trials_for_estimate,
            },
            "description": self.description,
            "interpretation_boundary": self.interpretation_boundary,
            "feature_weights": dict(self.feature_weights),
        }


# ---------------------------------------------------------------------------
# Scoring functions — used by both endpoint definitions and task scoring
# ---------------------------------------------------------------------------

def circular_distance(a: float, b: float, period: float) -> float:
    """Unsigned circular distance between two angles in [0, period)."""
    d = abs(a - b) % period
    return min(d, period - d)


def orientation_error(response_deg: float, target_deg: float) -> float:
    """Normalized orientation error in [0, 1]. Period = 180 degrees."""
    return circular_distance(response_deg, target_deg, 180.0) / 90.0


def hue_error(response_deg: float, target_deg: float) -> float:
    """Normalized hue error in [0, 1]. Period = 360 degrees."""
    return circular_distance(response_deg, target_deg, 360.0) / 180.0


def position_error(
    response_x: float, response_y: float,
    target_x: float, target_y: float,
    display_diagonal: float,
) -> float:
    """Normalized position error in [0, 1]."""
    d = math.sqrt((response_x - target_x) ** 2 + (response_y - target_y) ** 2)
    return min(d / display_diagonal, 1.0)


def spatial_frequency_error(response_cpd: float, target_cpd: float) -> float:
    """Normalized spatial frequency error as absolute log-ratio in [0, inf)."""
    if response_cpd <= 0 or target_cpd <= 0:
        return 1.0
    return abs(math.log(response_cpd / target_cpd))


def size_error(response_size: float, target_size: float) -> float:
    """Normalized size error as absolute log-ratio."""
    if response_size <= 0 or target_size <= 0:
        return 1.0
    return abs(math.log(response_size / target_size))


def composite_reconstruction_error(
    component_errors: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    """Weighted composite reconstruction error from normalized component errors."""
    if weights is None:
        weights = PRIMARY_ENDPOINT_WEIGHTS
    total_weight = sum(weights.get(k, 0.0) for k in component_errors)
    if total_weight == 0:
        return 0.0
    return sum(
        component_errors[k] * weights.get(k, 0.0)
        for k in component_errors if k in weights
    ) / total_weight


PRIMARY_ENDPOINT_WEIGHTS: dict[str, float] = {
    "orientation": 0.25,
    "hue": 0.25,
    "spatial_frequency": 0.20,
    "position": 0.15,
    "size": 0.15,
}


def confidence_resolution_slope(
    confidences: list[float], accuracies: list[float],
) -> float:
    """Slope of confidence-accuracy relationship (metacognitive sensitivity)."""
    n = len(confidences)
    if n < 3:
        return 0.0
    mc = sum(confidences) / n
    ma = sum(accuracies) / n
    num = sum((c - mc) * (a - ma) for c, a in zip(confidences, accuracies))
    den = sum((c - mc) ** 2 for c in confidences)
    if den == 0:
        return 0.0
    return num / den


def stability_degradation(immediate_error: float, delayed_error: float) -> float:
    """Within-trial degradation: how much error increases from immediate to delayed."""
    return max(0.0, delayed_error - immediate_error)


# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------

_ENDPOINTS: dict[str, ObjectiveEndpointDefinition] = {}


def _register(ep: ObjectiveEndpointDefinition) -> ObjectiveEndpointDefinition:
    _ENDPOINTS[ep.endpoint_id] = ep
    return ep


PRIMARY_ENDPOINT = _register(ObjectiveEndpointDefinition(
    endpoint_id="composite_reconstruction_error",
    version="1.0",
    display_name="Standardized Multi-Feature Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.PRIMARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(minimum_split_half=0.60, minimum_trials_for_estimate=20),
    description=(
        "Weighted combination of normalized feature-specific reconstruction errors: "
        "orientation (circular/90°), hue (circular/180°), spatial frequency (|log-ratio|), "
        "position (Euclidean/diagonal), size (|log-ratio|). Lower is better."
    ),
    interpretation_boundary=(
        "This score reflects imagery reconstruction precision in a synthetic task. "
        "It does not measure neural imagery quality or clinical status."
    ),
    feature_weights=dict(PRIMARY_ENDPOINT_WEIGHTS),
))


_register(ObjectiveEndpointDefinition(
    endpoint_id="orientation_reconstruction_error",
    version="1.0",
    display_name="Orientation Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Circular distance between response and target orientation, normalized by 90°.",
    interpretation_boundary="Synthetic precision metric only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="hue_reconstruction_error",
    version="1.0",
    display_name="Hue Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Circular distance between response and target hue, normalized by 180°.",
    interpretation_boundary="Synthetic precision metric only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="spatial_frequency_reconstruction_error",
    version="1.0",
    display_name="Spatial Frequency Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.LOG_RATIO,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 5.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Absolute log-ratio between response and target spatial frequency.",
    interpretation_boundary="Synthetic precision metric only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="position_reconstruction_error",
    version="1.0",
    display_name="Position Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Euclidean distance normalized by display diagonal.",
    interpretation_boundary="Synthetic precision metric only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="size_reconstruction_error",
    version="1.0",
    display_name="Size Reconstruction Error",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.LOG_RATIO,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 5.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Absolute log-ratio between response and target size.",
    interpretation_boundary="Synthetic precision metric only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="imagery_manipulation_accuracy",
    version="1.0",
    display_name="Imagery Manipulation Accuracy",
    construct=EndpointDomain.IMAGERY_CONTROL,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Distance between response and mathematically expected transformed target.",
    interpretation_boundary="Measures voluntary imagery control, not recall alone.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="delayed_stability_degradation",
    version="1.0",
    display_name="Delayed Stability Degradation",
    construct=EndpointDomain.IMAGERY_STABILITY,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Increase in reconstruction error from immediate to delayed recall.",
    interpretation_boundary="Does not imply neural decay without convergent evidence.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="stability_slope",
    version="1.0",
    display_name="Stability Slope Across Delays",
    construct=EndpointDomain.IMAGERY_STABILITY,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.SLOPE,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(-1.0, 1.0),
    aggregation=AggregationRule.PARTICIPANT_MEAN,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(minimum_trials_for_estimate=30),
    description="Slope of reconstruction error as a function of retention delay.",
    interpretation_boundary="Synthetic measurement only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="metacognitive_calibration",
    version="1.0",
    display_name="Metacognitive Calibration",
    construct=EndpointDomain.METACOGNITIVE_CALIBRATION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.CORRELATION,
    score_direction=ScoreDirection.HIGHER_IS_BETTER,
    valid_range=(-1.0, 1.0),
    aggregation=AggregationRule.PARTICIPANT_MEAN,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.NONE,
    reliability=ReliabilityRequirement(minimum_trials_for_estimate=20),
    description="Confidence-resolution slope: how well confidence predicts objective accuracy.",
    interpretation_boundary="Synthetic metacognitive proxy only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="confidence_resolution_slope",
    version="1.0",
    display_name="Confidence-Resolution Slope",
    construct=EndpointDomain.METACOGNITIVE_CALIBRATION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.SLOPE,
    score_direction=ScoreDirection.HIGHER_IS_BETTER,
    valid_range=(-1.0, 1.0),
    aggregation=AggregationRule.PARTICIPANT_MEAN,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.NONE,
    reliability=ReliabilityRequirement(minimum_trials_for_estimate=20),
    description="Linear slope of accuracy as a function of reported confidence.",
    interpretation_boundary="Synthetic metacognitive proxy only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="response_latency",
    version="1.0",
    display_name="Response Latency",
    construct=EndpointDomain.IMAGERY_PRECISION,
    is_objective=True,
    role=EndpointRole.KEY_SECONDARY,
    unit=Unit.MILLISECONDS,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 30000.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.EXCLUDE_3SD,
    reliability=ReliabilityRequirement(),
    description="Time from response prompt to response submission.",
    interpretation_boundary="May reflect decision speed, motor speed, or task engagement.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="subjective_vividness",
    version="1.0",
    display_name="Subjective Vividness",
    construct=EndpointDomain.SUBJECTIVE_VIVIDNESS,
    is_objective=False,
    role=EndpointRole.SUBJECTIVE_SECONDARY,
    unit=Unit.LIKERT_1_7,
    score_direction=ScoreDirection.HIGHER_IS_BETTER,
    valid_range=(1.0, 7.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.NONE,
    reliability=ReliabilityRequirement(),
    description="Self-reported vividness rating (1=no image, 7=perfectly vivid).",
    interpretation_boundary=(
        "Subjective measure only. Must not be treated as objective imagery precision. "
        "Expected to be related but not identical to objective reconstruction error."
    ),
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="subjective_effort",
    version="1.0",
    display_name="Subjective Effort",
    construct=EndpointDomain.SUBJECTIVE_VIVIDNESS,
    is_objective=False,
    role=EndpointRole.SUBJECTIVE_SECONDARY,
    unit=Unit.LIKERT_1_7,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(1.0, 7.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.NONE,
    reliability=ReliabilityRequirement(),
    description="Self-reported effort rating.",
    interpretation_boundary="Subjective measure only.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="simple_motor_latency",
    version="1.0",
    display_name="Simple Motor Response Latency",
    construct=EndpointDomain.PERCEPTUAL_MOTOR_CONTROL,
    is_objective=True,
    role=EndpointRole.NEGATIVE_CONTROL,
    unit=Unit.MILLISECONDS,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 5000.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.EXCLUDE_3SD,
    reliability=ReliabilityRequirement(),
    description="Latency for simple motor response with no imagery component.",
    interpretation_boundary="Improvement here suggests general practice/speed effects, not imagery.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="perceptual_matching_error",
    version="1.0",
    display_name="Perceptual Matching Accuracy",
    construct=EndpointDomain.PERCEPTUAL_MOTOR_CONTROL,
    is_objective=True,
    role=EndpointRole.NEGATIVE_CONTROL,
    unit=Unit.STANDARDIZED_ERROR,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(0.0, 1.0),
    aggregation=AggregationRule.TRIAL_LEVEL,
    missingness=MissingnessRule.MAXIMUM_ERROR,
    outlier_rule=OutlierRule.WINSORIZE_3SD,
    reliability=ReliabilityRequirement(),
    description="Reconstruction error with target visible (perceptual control).",
    interpretation_boundary="Improvement only here should not be interpreted as imagery improvement.",
))

_register(ObjectiveEndpointDefinition(
    endpoint_id="fatigue_rating",
    version="1.0",
    display_name="Post-Session Fatigue",
    construct=EndpointDomain.SAFETY,
    is_objective=False,
    role=EndpointRole.SAFETY,
    unit=Unit.LIKERT_1_7,
    score_direction=ScoreDirection.LOWER_IS_BETTER,
    valid_range=(1.0, 7.0),
    aggregation=AggregationRule.SESSION_MEAN,
    missingness=MissingnessRule.EXCLUDE_TRIAL,
    outlier_rule=OutlierRule.NONE,
    reliability=ReliabilityRequirement(),
    description="Post-session fatigue rating for safety monitoring.",
    interpretation_boundary="Safety signal only.",
))


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

def get_endpoint(endpoint_id: str) -> ObjectiveEndpointDefinition | None:
    return _ENDPOINTS.get(endpoint_id)


def list_endpoints() -> list[ObjectiveEndpointDefinition]:
    return list(_ENDPOINTS.values())


def get_primary_endpoint() -> ObjectiveEndpointDefinition:
    return PRIMARY_ENDPOINT


def get_endpoints_by_role(role: EndpointRole) -> list[ObjectiveEndpointDefinition]:
    return [ep for ep in _ENDPOINTS.values() if ep.role == role]


def get_endpoints_by_domain(domain: EndpointDomain) -> list[ObjectiveEndpointDefinition]:
    return [ep for ep in _ENDPOINTS.values() if ep.construct == domain]


def get_objective_endpoints() -> list[ObjectiveEndpointDefinition]:
    return [ep for ep in _ENDPOINTS.values() if ep.is_objective]


def get_subjective_endpoints() -> list[ObjectiveEndpointDefinition]:
    return [ep for ep in _ENDPOINTS.values() if not ep.is_objective]


def get_registry() -> dict[str, "ObjectiveEndpointDefinition"]:
    return dict(_ENDPOINTS)


def registry_hash() -> str:
    """Compute a deterministic hash of the entire endpoint registry."""
    data = {eid: ep.to_dict() for eid, ep in sorted(_ENDPOINTS.items())}
    canon = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def validate_registry() -> list[str]:
    """Return a list of integrity violations, empty if valid."""
    errors: list[str] = []

    primary_count = sum(1 for ep in _ENDPOINTS.values() if ep.role == EndpointRole.PRIMARY)
    if primary_count != 1:
        errors.append(f"Expected exactly 1 primary endpoint, found {primary_count}")

    for eid, ep in _ENDPOINTS.items():
        if ep.score_direction is None:
            errors.append(f"{eid}: missing score direction")
        if ep.valid_range[0] >= ep.valid_range[1]:
            errors.append(f"{eid}: invalid range {ep.valid_range}")
        if not ep.is_objective and ep.role == EndpointRole.PRIMARY:
            errors.append(f"{eid}: primary endpoint must be objective")
        if ep.role in (EndpointRole.PRIMARY, EndpointRole.KEY_SECONDARY) and not ep.is_objective:
            if ep.role == EndpointRole.PRIMARY:
                errors.append(f"{eid}: primary endpoint cannot be subjective")
        if not ep.is_objective and ep.role == EndpointRole.NEGATIVE_CONTROL:
            errors.append(f"{eid}: negative control should be objective")

    return errors
