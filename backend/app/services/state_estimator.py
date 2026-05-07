"""Rule-based state estimator.

Maps FeatureVector + self-report + baseline into a StateEstimate.
All components normalised to 0-1.  These are proxy estimates only.
"""

from app.core.time import utcnow
from app.schemas.features import FeatureVector
from app.schemas.metrics import StateEstimate


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


class StateEstimator:
    def __init__(self):
        self.prev: StateEstimate | None = None
        self.window_count = 0

    def estimate(
        self,
        session_id: str,
        fv: FeatureVector,
        self_report: dict | None = None,
        baseline: dict | None = None,
        window_index: int = 0,
    ) -> StateEstimate:
        self.window_count += 1
        sr = self_report or {}
        bl = baseline or {}
        alpha = 0.3

        sr_focus = sr.get("focus", 5) / 10.0
        sr_relaxation = sr.get("relaxation", 5) / 10.0
        sr_vividness = sr.get("vividness", 5) / 10.0
        sr_stability = sr.get("stability", 5) / 10.0
        sr_effort = sr.get("effort", 5) / 10.0
        sr_fatigue = sr.get("fatigue", 3) / 10.0
        sr_distraction = sr.get("distraction", 3) / 10.0

        bl_relaxation = bl.get("relaxation", bl.get("baseline_relaxation", 0.5))
        bl_alpha = bl_relaxation / 10.0 if bl_relaxation > 1 else bl_relaxation

        raw_attention = (
            0.30 * (1.0 - _clamp(fv.theta_beta_ratio / 3.0))
            + 0.30 * sr_focus
            + 0.20 * (1.0 - sr_distraction)
            + 0.20 * fv.signal_quality
        )
        attention_stability = _clamp(raw_attention)

        alpha_ratio = fv.alpha_power / max(bl_alpha, 0.1)
        raw_relaxation = (
            0.40 * _clamp(alpha_ratio / 2.0)
            + 0.40 * sr_relaxation
            + 0.20 * (1.0 - sr_effort * 0.5)
        )
        relaxation = _clamp(raw_relaxation)

        raw_engagement = (
            0.30 * sr_vividness
            + 0.25 * sr_stability
            + 0.25 * fv.alpha_stability
            + 0.20 * fv.simulated_imagery_strength
        )
        imagery_engagement = _clamp(raw_engagement)

        rt_norm = _clamp(1.0 - (fv.reaction_time_ms or 500) / 1500.0)
        raw_behavioral = (
            0.35 * fv.behavioral_stability
            + 0.25 * rt_norm
            + 0.20 * sr_stability
            + 0.20 * sr_focus
        )
        behavioral_consistency = _clamp(raw_behavioral)

        raw_fatigue = (
            0.35 * sr_fatigue
            + 0.20 * _clamp(fv.theta_beta_ratio / 3.0)
            + 0.15 * sr_effort
            + 0.15 * (1.0 - sr_focus)
            + 0.15 * _clamp(self.window_count / 60.0)
        )
        fatigue = _clamp(raw_fatigue)

        contradictions = abs(sr_vividness - fv.simulated_imagery_strength)
        data_sparse = _clamp(1.0 - self.window_count / 5.0)
        raw_uncertainty = (
            0.30 * (1.0 - fv.signal_quality)
            + 0.25 * contradictions
            + 0.20 * sr_fatigue
            + 0.25 * data_sparse
        )
        uncertainty = _clamp(raw_uncertainty)
        confidence = _clamp(1.0 - uncertainty)

        if self.prev is not None:
            p = self.prev
            attention_stability = alpha * attention_stability + (1 - alpha) * p.attention_stability
            relaxation = alpha * relaxation + (1 - alpha) * p.relaxation
            imagery_engagement = alpha * imagery_engagement + (1 - alpha) * p.imagery_engagement
            behavioral_consistency = (
                alpha * behavioral_consistency + (1 - alpha) * p.behavioral_consistency
            )
            fatigue = alpha * fatigue + (1 - alpha) * p.fatigue
            uncertainty = alpha * uncertainty + (1 - alpha) * p.uncertainty
            confidence = alpha * confidence + (1 - alpha) * p.confidence

        est = StateEstimate(
            session_id=session_id,
            timestamp=utcnow(),
            window_index=window_index,
            attention_stability=round(attention_stability, 4),
            relaxation=round(relaxation, 4),
            imagery_engagement=round(imagery_engagement, 4),
            behavioral_consistency=round(behavioral_consistency, 4),
            fatigue=round(fatigue, 4),
            uncertainty=round(uncertainty, 4),
            confidence=round(confidence, 4),
        )
        self.prev = est
        return est
