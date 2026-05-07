from datetime import datetime, timezone

from app.schemas.features import FeatureVector
from app.schemas.metrics import StateEstimate
from app.services.pid_iqi_engine import PIDIQIEngine


def _make_state(**overrides) -> StateEstimate:
    defaults = dict(
        session_id="s1",
        timestamp=datetime.now(timezone.utc),
        window_index=0,
        attention_stability=0.6,
        relaxation=0.5,
        imagery_engagement=0.6,
        behavioral_consistency=0.6,
        fatigue=0.2,
        uncertainty=0.3,
        confidence=0.7,
    )
    defaults.update(overrides)
    return StateEstimate(**defaults)


def _make_fv(**overrides) -> FeatureVector:
    defaults = dict(
        session_id="s1",
        timestamp=datetime.now(timezone.utc),
        window_index=0,
        theta_power=0.3,
        alpha_power=0.5,
        beta_power=0.3,
        theta_beta_ratio=1.0,
        alpha_stability=0.6,
        signal_quality=0.7,
        simulated_imagery_strength=0.6,
        behavioral_stability=0.6,
        reaction_time_ms=400.0,
    )
    defaults.update(overrides)
    return FeatureVector(**defaults)


def test_pid_iqi_in_range():
    engine = PIDIQIEngine()
    pid, iqi = engine.compute("s1", _make_state(), _make_fv(), 0)
    assert 0 <= pid.pid <= 1
    assert 0 <= iqi.iqi <= 1


def test_higher_engagement_improves_iqi():
    engine = PIDIQIEngine()
    _, iqi_low = engine.compute("s1", _make_state(imagery_engagement=0.2), _make_fv(), 0)
    _, iqi_high = engine.compute("s1", _make_state(imagery_engagement=0.9), _make_fv(), 1)
    assert iqi_high.iqi > iqi_low.iqi


def test_high_fatigue_gives_fatigue_risk():
    engine = PIDIQIEngine()
    state = _make_state(fatigue=0.85, confidence=0.7)
    pid, _ = engine.compute("s1", state, _make_fv(), 0)
    assert pid.interpretation == "fatigue_risk"


def test_excellent_interpretation():
    engine = PIDIQIEngine()
    state = _make_state(
        attention_stability=0.95,
        imagery_engagement=0.95,
        behavioral_consistency=0.95,
        relaxation=0.90,
        fatigue=0.05,
        uncertainty=0.05,
        confidence=0.95,
    )
    fv = _make_fv(simulated_imagery_strength=0.95, alpha_stability=0.95)
    pid, iqi = engine.compute("s1", state, fv, 0)
    assert pid.interpretation == "excellent"
    assert iqi.iqi > 0.75
    assert pid.pid < 0.25
