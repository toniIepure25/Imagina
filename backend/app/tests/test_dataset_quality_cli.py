from app.cli.dataset_quality import main as quality_main
from app.services.signal_quality import evaluate_signal_quality


def test_quality_fixture_returns_zero():
    rc = quality_main(["--dataset", "fixture", "--max-windows", "5"])
    assert rc == 0


def test_quality_report_has_expected_keys():
    import json
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base, "..", "..", "data", "exports", "dataset_quality_fixture.json")
    assert os.path.exists(output_path)
    with open(output_path) as f:
        r = json.load(f)
    assert "quality_score" in r
    assert "warnings" in r
    assert "summary" in r


def test_quality_empty_triggers_warning():
    r = evaluate_signal_quality([])
    assert r["warnings"] == ["insufficient_windows"]
    assert r["quality_score"] == 0.0


def test_quality_bad_data_triggers_warnings():
    from datetime import datetime, timezone

    from app.schemas.features import FeatureVector
    t = datetime.now(timezone.utc)
    fvs = [
        FeatureVector(
            session_id="t", timestamp=t, window_index=i,
            theta_power=0.4, alpha_power=0.4, beta_power=0.3,
            theta_beta_ratio=1.0, alpha_stability=0.3, signal_quality=0.1,
            simulated_imagery_strength=0.3, behavioral_stability=0.3,
            missing_data_ratio=0.3, clipping_score=0.3, muscle_score=0.7,
        )
        for i in range(10)
    ]
    r = evaluate_signal_quality(fvs)
    assert r["quality_score"] < 0.4
    assert len(r["warnings"]) >= 1
