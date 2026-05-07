from datetime import datetime, timezone

from app.schemas.curriculum import CurriculumState
from app.schemas.metrics import IQIEstimate, PIDEstimate, StateEstimate
from app.services.feedback_policy_engine import FeedbackPolicyEngine


def _ts():
    return datetime.now(timezone.utc)


def _state(**kw) -> StateEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        attention_stability=0.6, relaxation=0.5, imagery_engagement=0.6,
        behavioral_consistency=0.6, fatigue=0.2, uncertainty=0.3, confidence=0.7,
    )
    d.update(kw)
    return StateEstimate(**d)


def _pid(**kw) -> PIDEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        pid=0.35, neural_proxy_distance=0.35, behavioral_distance=0.35,
        uncertainty_component=0.20, interpretation="good",
    )
    d.update(kw)
    return PIDEstimate(**d)


def _iqi(**kw) -> IQIEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        iqi=0.60, stability_component=0.6, engagement_component=0.6,
        relaxation_component=0.5, confidence=0.7,
    )
    d.update(kw)
    return IQIEstimate(**d)


def _curr(**kw) -> CurriculumState:
    d = dict(
        session_id="s1", timestamp=_ts(), current_level=3, level_name="Stable Walls",
        consecutive_successes=0, consecutive_failures=0, difficulty=0.375, reason="",
    )
    d.update(kw)
    return CurriculumState(**d)


def test_clarity_increases_with_iqi():
    engine = FeedbackPolicyEngine()
    low = engine.compute("s1", _state(), _pid(), _iqi(iqi=0.30), _curr(), 0)
    high = engine.compute("s1", _state(), _pid(), _iqi(iqi=0.90), _curr(), 1)
    assert high.scene_clarity > low.scene_clarity


def test_blur_increases_with_pid():
    engine = FeedbackPolicyEngine()
    low = engine.compute("s1", _state(), _pid(pid=0.10), _iqi(), _curr(), 0)
    high = engine.compute("s1", _state(), _pid(pid=0.90), _iqi(), _curr(), 1)
    assert high.blur > low.blur


def test_fatigue_prompt():
    engine = FeedbackPolicyEngine()
    fa = engine.compute(
        "s1", _state(fatigue=0.80), _pid(), _iqi(), _curr(), 0
    )
    assert "fatigue" in fa.prompt_text.lower()
