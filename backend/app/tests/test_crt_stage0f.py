from dataclasses import replace

import pytest

from app.research.crt.design import DesignPowerConfig, simulate_design_power
from app.research.crt.distortion import DistortionConfig, run_distortion_assay
from app.research.crt.hierarchical import HierarchicalScreenConfig, run_hierarchical_screen
from app.research.crt.protocol import (
    EXPECTED_PRIMARY_CONTRAST,
    audit_spec,
    load_spec,
    run_protocol_audit,
)


def test_protocol_audit_passes_for_canonical_yaml() -> None:
    audit = run_protocol_audit()
    assert audit.passed, audit.errors
    assert audit.spec.total_trials == 240
    assert audit.spec.expected_trials_per_occasion == 120
    assert audit.spec.primary_contrast == EXPECTED_PRIMARY_CONTRAST


def test_protocol_audit_records_stage0g_design_fields() -> None:
    audit = run_protocol_audit()
    assert audit.passed, audit.errors
    assert audit.spec.main_n == 480
    assert audit.spec.sesoi_d == 0.20
    assert audit.spec.calibration_n == 80
    assert audit.spec.primary_endpoint == "model_based_source_sensitivity"


def test_protocol_audit_rejects_underpowered_main_design() -> None:
    spec = load_spec()
    broken = replace(spec, main_n=240)
    audit = audit_spec(broken)
    assert not audit.passed
    assert any("main_n" in error for error in audit.errors)


def test_protocol_audit_catches_trial_arithmetic_mismatch() -> None:
    spec = load_spec()
    broken = replace(spec, trials_per_cell_per_occasion=30)
    audit = audit_spec(broken)
    assert not audit.passed
    assert any("trial arithmetic mismatch" in error for error in audit.errors)


def test_protocol_audit_requires_yoked_primary_contrast() -> None:
    spec = load_spec()
    broken = replace(spec, primary_contrast="active_predict_minus_active_intervene")
    audit = audit_spec(broken)
    assert not audit.passed
    assert any("primary_contrast" in error for error in audit.errors)


def test_design_power_is_deterministic_and_bounded() -> None:
    config = DesignPowerConfig(n_participants=120, n_simulations=40, seed=7)
    first = simulate_design_power(config)
    second = simulate_design_power(config)
    assert first == second
    assert 0.0 <= first["primary_contrast"]["power"] <= 1.0
    assert 0.0 <= first["false_seen_assay"]["power"] <= 1.0


def test_design_power_rejects_invalid_correlation() -> None:
    with pytest.raises(ValueError):
        DesignPowerConfig(within_correlation=1.0)


def test_distortion_assay_is_sensitive_to_injected_effect() -> None:
    report = run_distortion_assay(
        DistortionConfig(n_simulations=60, readout_n=6, readout_trials=30)
    )
    assert report["injected_assay"]["power_to_detect_positive_shift"] >= 0.80
    assert report["readout_only_model"]["null_as_expected"] is True
    assert report["decision"] == "CRT_STAGE0F_DISTORTION_PASS"


def test_hierarchical_screen_is_labeled_screening_only() -> None:
    report = run_hierarchical_screen(
        HierarchicalScreenConfig(n_participants=6, n_trials=20, n_replicates=3)
    )
    assert report["status"] == "screening_only_not_full_sbc"
    assert report["decision"].startswith("CRT_STAGE0F_HIERARCHICAL_SCREENING_")
