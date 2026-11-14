import pytest

from analysis.crt.m7_diagnostic import (
    DIAGNOSTIC_CANDIDATES,
    M7DiagnosticConfig,
    run_m7_diagnostic,
)


def test_m7_diagnostic_compares_trial_compositions() -> None:
    config = M7DiagnosticConfig(
        screen_n=24,
        screen_trials=40,
        target_n=24,
        target_trials=40,
        n_replicates=1,
        candidates=DIAGNOSTIC_CANDIDATES[:2],
        target_candidate_id="balanced",
        run_target=False,
    )
    payload = run_m7_diagnostic(config)
    assert payload["analysis"] == "stage0i_m7_diagnostic"
    assert payload["scope"] == "m7_design_diagnostic_synthetic_not_human_evidence"
    assert len(payload["screen"]) == 2
    assert payload["target_check"] is None
    assert payload["decision"] in {
        "CRT_STAGE0I_M7_DIAGNOSTIC_DESIGN_SENSITIVE",
        "CRT_STAGE0I_M7_DIAGNOSTIC_REVIEW",
        "CRT_STAGE0I_M7_DIAGNOSTIC_PERSISTENT",
    }
    assert set(payload["best_screen_design"]["per_model_accuracy"]) == {"M4", "M6", "M7"}


def test_m7_diagnostic_rejects_smaller_target() -> None:
    with pytest.raises(ValueError, match="target must not be smaller"):
        M7DiagnosticConfig(screen_n=100, target_n=50)
