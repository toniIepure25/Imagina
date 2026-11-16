from __future__ import annotations

import json
from pathlib import Path

import pytest
from analysis.crt import target_scale


def _sbc(model: str, decision: str = "CRT_NUTS_SBC_PASS") -> dict:
    return {
        "model": model,
        "decision": decision,
        "metrics": {"alpha_d": {"coverage": 0.95, "mean_rank": 0.5}},
    }


def _recovery(decision: str = "CRT_STAGE0J_FULL_MODEL_RECOVERY_PASS") -> dict:
    return {"decision": decision, "balanced_accuracy": 0.9}


def test_smoke_and_target_profiles_are_explicit():
    smoke = target_scale.TargetScaleConfig.smoke()
    target = target_scale.TargetScaleConfig.target()

    assert smoke.min_sbc_for_decision == 1
    assert target.min_sbc_for_decision == 50
    assert target.n_sbc == 50
    assert target.draws == 1000
    assert set(target.models) == {"M0", "M2", "M4", "M6", "M7"}


def test_config_rejects_unknown_or_tiny_designs():
    with pytest.raises(ValueError):
        target_scale.TargetScaleConfig(n_participants=5)
    with pytest.raises(ValueError):
        target_scale.TargetScaleConfig(n_trials=19)
    with pytest.raises(ValueError):
        target_scale.TargetScaleConfig(models=("M0", "M9"))
    with pytest.raises(ValueError):
        target_scale.TargetScaleConfig(coverage_low=0.99, coverage_high=0.95)


def test_missing_numpyro_is_blocked_not_silently_reviewed(monkeypatch):
    monkeypatch.setattr(target_scale, "numpyro_available", lambda: False)

    payload = target_scale.run_target_scale(target_scale.TargetScaleConfig.smoke())

    assert payload["decision"] == "CRT_STAGE0J_BLOCKED"
    assert payload["status"] == "blocked"
    assert payload["sbc"] == []
    assert "NumPyro" in payload["reason"]


def test_review_is_not_promoted_to_pass(monkeypatch):
    monkeypatch.setattr(target_scale, "numpyro_available", lambda: True)
    monkeypatch.setattr(target_scale, "run_nuts_sbc", lambda model, config: _sbc(model, "CRT_NUTS_SBC_REVIEW"))
    monkeypatch.setattr(
        target_scale,
        "run_full_recovery",
        lambda **kwargs: _recovery("CRT_STAGE0J_FULL_MODEL_RECOVERY_REVIEW"),
    )

    payload = target_scale.run_target_scale(target_scale.TargetScaleConfig.smoke())

    assert payload["decision"] == "CRT_STAGE0J_REVIEW"
    assert payload["failures"]


def test_all_checks_pass_only_with_both_sbc_and_recovery(monkeypatch):
    monkeypatch.setattr(target_scale, "numpyro_available", lambda: True)
    monkeypatch.setattr(target_scale, "run_nuts_sbc", lambda model, config: _sbc(model))
    monkeypatch.setattr(target_scale, "run_full_recovery", lambda **kwargs: _recovery())

    payload = target_scale.run_target_scale(target_scale.TargetScaleConfig.smoke())

    assert payload["decision"] == "CRT_STAGE0J_PASS"
    assert payload["failures"] == []


def test_mean_rank_outside_tolerance_is_not_a_pass(monkeypatch):
    monkeypatch.setattr(target_scale, "numpyro_available", lambda: True)
    bad = _sbc("M0")
    bad["metrics"]["alpha_d"]["mean_rank"] = 0.8
    monkeypatch.setattr(target_scale, "run_nuts_sbc", lambda model, config: bad)
    monkeypatch.setattr(target_scale, "run_full_recovery", lambda **kwargs: _recovery())

    payload = target_scale.run_target_scale(target_scale.TargetScaleConfig.smoke())

    assert payload["decision"] == "CRT_STAGE0J_REVIEW"
    assert any("mean rank" in failure for failure in payload["failures"])


def test_artifact_is_json_serializable_and_keeps_limitations(monkeypatch):
    monkeypatch.setattr(target_scale, "numpyro_available", lambda: False)
    payload = target_scale.run_target_scale(target_scale.TargetScaleConfig.smoke())
    path = Path.cwd() / "target_scale_test_artifact.json"
    try:
        target_scale.write_artifact(payload, path)
        loaded = json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)

    assert loaded["schema"] == "IMAGINA-CRT-TARGET-SCALE-v1"
    assert loaded["scope"] == target_scale.SCOPE
    assert loaded["limitations"]
    assert "no human participants" in loaded["limitations"][0].lower()


def test_target_cli_requires_compute_confirmation(capsys):
    with pytest.raises(SystemExit) as error:
        target_scale.main(["--target"])
    assert error.value.code == 2
    assert "confirm-compute" in capsys.readouterr().err
