"""Scoring for the objective imagery precision battery.

Uses production scoring functions from objective_endpoints to ensure
consistency between task scoring and endpoint definitions.
"""
from __future__ import annotations

from app.research.objective_endpoints import (
    composite_reconstruction_error,
    hue_error,
    orientation_error,
    position_error,
    size_error,
    spatial_frequency_error,
)
from app.research.psychophysics.common import (
    InvalidityFlag,
    ResponseSpec,
    StimulusSpec,
)

SCORING_VERSION = "1.0"


def score_reconstruction(
    target: StimulusSpec,
    response: ResponseSpec,
    display_diagonal: float = 1000.0,
) -> dict[str, float | str]:
    """Score a single reconstruction trial against the expected target."""
    invalidity = _check_invalidity(response)
    if invalidity != InvalidityFlag.NONE:
        return _invalid_result(invalidity)

    components = {}

    if response.orientation_deg is not None:
        components["orientation"] = orientation_error(response.orientation_deg, target.orientation_deg)
    if response.hue_deg is not None:
        components["hue"] = hue_error(response.hue_deg, target.hue_deg)
    if response.spatial_frequency_cpd is not None:
        components["spatial_frequency"] = spatial_frequency_error(
            response.spatial_frequency_cpd, target.spatial_frequency_cpd,
        )
    if response.position_x is not None and response.position_y is not None:
        components["position"] = position_error(
            response.position_x, response.position_y,
            target.position_x, target.position_y,
            display_diagonal,
        )
    if response.size is not None:
        components["size"] = size_error(response.size, target.size)

    composite = composite_reconstruction_error(components)

    result: dict[str, float | str] = {
        "composite_error": round(composite, 6),
        "invalidity": InvalidityFlag.NONE.value,
        "scoring_version": SCORING_VERSION,
    }
    for k, v in components.items():
        result[f"{k}_error"] = round(v, 6)
    return result


def _check_invalidity(response: ResponseSpec) -> InvalidityFlag:
    all_none = (
        response.orientation_deg is None
        and response.hue_deg is None
        and response.spatial_frequency_cpd is None
        and response.position_x is None
        and response.size is None
    )
    if all_none:
        return InvalidityFlag.MISSING_RESPONSE

    if response.latency_ms is not None and response.latency_ms < 200:
        return InvalidityFlag.RESPONSE_TOO_FAST

    if response.latency_ms is not None and response.latency_ms > 30000:
        return InvalidityFlag.RESPONSE_TOO_SLOW

    if response.spatial_frequency_cpd is not None and response.spatial_frequency_cpd <= 0:
        return InvalidityFlag.RESPONSE_OUT_OF_RANGE
    if response.size is not None and response.size <= 0:
        return InvalidityFlag.RESPONSE_OUT_OF_RANGE

    return InvalidityFlag.NONE


def _invalid_result(flag: InvalidityFlag) -> dict[str, float | str]:
    return {
        "composite_error": 1.0,
        "invalidity": flag.value,
        "scoring_version": SCORING_VERSION,
    }
