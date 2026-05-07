from datetime import datetime, timezone

from app.schemas.metrics import IQIEstimate, PIDEstimate, StateEstimate
from app.services.curriculum_manager import CurriculumManager


def _ts():
    return datetime.now(timezone.utc)


def _state(**kw) -> StateEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        attention_stability=0.7, relaxation=0.6, imagery_engagement=0.7,
        behavioral_consistency=0.7, fatigue=0.2, uncertainty=0.2, confidence=0.8,
    )
    d.update(kw)
    return StateEstimate(**d)


def _pid(**kw) -> PIDEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        pid=0.30, neural_proxy_distance=0.30, behavioral_distance=0.30,
        uncertainty_component=0.20, interpretation="good",
    )
    d.update(kw)
    return PIDEstimate(**d)


def _iqi(**kw) -> IQIEstimate:
    d = dict(
        session_id="s1", timestamp=_ts(), window_index=0,
        iqi=0.65, stability_component=0.7, engagement_component=0.7,
        relaxation_component=0.6, confidence=0.8,
    )
    d.update(kw)
    return IQIEstimate(**d)


def test_advance_after_3_successes():
    cm = CurriculumManager(starting_level=1)
    state = _state(attention_stability=0.70, fatigue=0.2)
    pid = _pid(pid=0.30)
    iqi = _iqi(iqi=0.65)

    for _ in range(3):
        cs = cm.update("s1", state, pid, iqi)

    assert cs.current_level == 2
    assert cs.reason == "advance"


def test_regress_on_major_failure():
    cm = CurriculumManager(starting_level=3)
    state = _state(fatigue=0.90)
    pid = _pid(pid=0.80)
    iqi = _iqi(iqi=0.20)
    cs = cm.update("s1", state, pid, iqi)
    assert cs.current_level == 2


def test_fatigue_cooldown():
    cm = CurriculumManager(starting_level=4)
    state = _state(fatigue=0.85)
    pid = _pid(pid=0.30)
    iqi = _iqi(iqi=0.70)
    cs = cm.update("s1", state, pid, iqi)
    assert cs.current_level == 3
    assert cs.reason == "fatigue_cooldown"


def test_stays_at_level_1():
    cm = CurriculumManager(starting_level=1)
    state = _state(fatigue=0.90)
    pid = _pid(pid=0.80)
    iqi = _iqi(iqi=0.20)
    cs = cm.update("s1", state, pid, iqi)
    assert cs.current_level == 1
