"""
Computes PID (Perception-Imagination Distance) and IQI (Imagery Quality Index).

Both are experimental proxy metrics — see docs/metrics.md.
"""

from typing import Literal

from app.core.time import utcnow
from app.schemas.features import FeatureVector
from app.schemas.metrics import IQIEstimate, PIDEstimate, StateEstimate


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


class PIDIQIEngine:
    def compute(
        self,
        session_id: str,
        state: StateEstimate,
        fv: FeatureVector,
        window_index: int,
    ) -> tuple[PIDEstimate, IQIEstimate]:
        # ---------- IQI ----------
        raw_iqi = (
            0.35 * state.attention_stability
            + 0.30 * state.imagery_engagement
            + 0.20 * state.behavioral_consistency
            + 0.15 * state.relaxation
        )
        iqi = _clamp(raw_iqi * state.confidence)

        iqi_est = IQIEstimate(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            iqi=round(iqi, 4),
            stability_component=round(state.attention_stability, 4),
            engagement_component=round(state.imagery_engagement, 4),
            relaxation_component=round(state.relaxation, 4),
            confidence=round(state.confidence, 4),
        )

        # ---------- PID ----------
        # Neural proxy distance: lower is better imagery
        neural_proxy_distance = _clamp(
            1.0
            - fv.simulated_imagery_strength * 0.5
            - fv.alpha_stability * 0.3
            - state.imagery_engagement * 0.2
        )
        # Behavioral distance
        behavioral_distance = _clamp(
            1.0 - state.behavioral_consistency * 0.6 - (1.0 - state.fatigue) * 0.4
        )

        pid = _clamp(
            0.45 * neural_proxy_distance
            + 0.35 * behavioral_distance
            + 0.20 * state.uncertainty
        )

        interpretation = self._interpret(pid, iqi, state.fatigue, state.confidence)

        pid_est = PIDEstimate(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            pid=round(pid, 4),
            neural_proxy_distance=round(neural_proxy_distance, 4),
            behavioral_distance=round(behavioral_distance, 4),
            uncertainty_component=round(state.uncertainty, 4),
            interpretation=interpretation,
        )

        return pid_est, iqi_est

    @staticmethod
    def _interpret(
        pid: float, iqi: float, fatigue: float, confidence: float
    ) -> Literal["excellent", "good", "unstable", "fatigue_risk", "unknown"]:
        if confidence < 0.30:
            return "unknown"
        if fatigue > 0.75:
            return "fatigue_risk"
        if pid < 0.25 and iqi > 0.75:
            return "excellent"
        if pid < 0.40 and iqi > 0.60:
            return "good"
        if pid > 0.65:
            return "unstable"
        return "good"
