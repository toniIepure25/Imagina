from datetime import datetime, timezone

from app.schemas.metrics import StateEstimate
from app.services.safety_monitor import SafetyMonitor


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


def test_fatigue_high_triggers_after_2():
    sm = SafetyMonitor()
    sm.check("s1", _state(fatigue=0.85))
    events = sm.check("s1", _state(fatigue=0.85))
    types = [e.event_type for e in events]
    assert "fatigue_high" in types


def test_overeffort():
    sm = SafetyMonitor()
    events = sm.check("s1", _state(), self_report={"effort": 9, "fatigue": 7})
    types = [e.event_type for e in events]
    assert "overeffort" in types


def test_session_too_long():
    sm = SafetyMonitor(max_duration_s=1200)
    events = sm.check("s1", _state(), session_elapsed_s=1300)
    types = [e.event_type for e in events]
    assert "session_too_long" in types


def test_dissociation_keyword():
    sm = SafetyMonitor()
    events = sm.check("s1", _state(), self_report={"notes": "I feel dizzy and detached"})
    types = [e.event_type for e in events]
    assert "dissociation_warning" in types


def test_no_events_normal():
    sm = SafetyMonitor()
    events = sm.check("s1", _state())
    assert len(events) == 0
