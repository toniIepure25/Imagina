from dataclasses import replace

import numpy as np
import pytest
from analysis.crt.design_optimization import (
    DEFAULT_CANDIDATES,
    DesignCandidate,
    DesignOptimizationConfig,
    run_design_optimization,
)
from analysis.crt.full_model import (
    FULL_MODELS,
    FullModelConfig,
    fit_full_model,
    run_full_recovery,
    run_full_sbc,
    simulate_full_data,
)

from app.research.crt.protocol import audit_spec, load_spec, run_protocol_audit


def test_stage0h_protocol_declares_model_space_and_gate() -> None:
    audit = run_protocol_audit()
    assert audit.passed, audit.errors
    assert audit.spec.version == "0.7.0"
    assert audit.spec.stage == "0I"
    assert audit.spec.model_space == ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7")
    assert audit.spec.confirmatory_models == ("M0", "M2", "M4", "M6", "M7")
    assert audit.spec.exploratory_models == ("M1", "M3", "M5")
    assert audit.spec.stage0h_status.startswith("historical_computational_only")
    assert audit.spec.stage0i_status == "computational_only_human_data_gated"


def test_protocol_audit_rejects_missing_m6_m7() -> None:
    spec = load_spec()
    broken = replace(spec, model_space=("M0", "M2", "M4"), confirmatory_models=("M0", "M2", "M4"))
    audit = audit_spec(broken)
    assert not audit.passed
    assert any("model_space" in error for error in audit.errors)


def test_full_model_simulation_has_latent_source_and_report() -> None:
    data, truth = simulate_full_data("M6", n_participants=6, n_trials=20, seed=7)
    assert data.source is not None and data.source_report is not None
    assert np.all((data.source >= 0) & (data.source <= 3))
    assert np.all((data.source_report >= 0) & (data.source_report <= 3))
    assert np.allclose(data.source_correct, (data.source == data.source_report).astype(float))
    assert abs(truth["gamma_v"]) >= 0.25


def test_full_model_fit_is_deterministic_for_same_seed() -> None:
    data, _ = simulate_full_data("M2", n_participants=6, n_trials=20, seed=8)
    config = FullModelConfig(
        n_participants=6,
        n_trials=20,
        n_sbc=1,
        n_recovery=1,
        n_posterior_draws=20,
        max_iter=30,
        seed=8,
    )
    first = fit_full_model(data, "M2", config)
    second = fit_full_model(data, "M2", config)
    assert first.model == "M2"
    assert first.bic == pytest.approx(second.bic, rel=1e-8, abs=1e-8)


def test_full_model_sbc_and_recovery_are_labeled_screening() -> None:
    config = FullModelConfig(
        n_participants=6,
        n_trials=20,
        n_sbc=1,
        n_recovery=1,
        n_posterior_draws=20,
        max_iter=20,
        seed=9,
    )
    sbc = run_full_sbc(config, model="M6")
    assert sbc["scope"] == "full_joint_source_monitoring_latent_state_not_policy_pomdp"
    assert sbc["decision"].startswith("CRT_STAGE0H_FULL_MODEL_SBC_")
    recovery = run_full_recovery(config, model_set=("M0", "M6"))
    assert recovery["selection_status"] == "pre_specified"
    assert recovery["decision"].startswith("CRT_STAGE0H_FULL_MODEL_RECOVERY_")


def test_design_optimization_is_a_design_gate_not_a_test() -> None:
    candidates = (
        DesignCandidate("combined", 0.5, 0.5, 0.0, 1.0, vividness_spread=0.35, confidence_spread=0.35),
        DesignCandidate("balanced", 0.5, 0.5, 0.0, 1.0),
    )
    config = DesignOptimizationConfig(
        n_participants=8,
        n_trials=30,
        n_replicates=1,
        n_power_simulations=20,
        candidates=candidates,
        seed=10,
    )
    payload = run_design_optimization(config)
    assert payload["scope"] == "offline_model_discrimination_design_screening_not_human_evidence"
    assert payload["decision"] in {
        "CRT_STAGE0H_DESIGN_OPTIMIZATION_PASS",
        "CRT_STAGE0H_DESIGN_OPTIMIZATION_REVIEW",
    }
    assert payload["selected_design"]["design_id"] in {"combined", "balanced"}


def test_stage0h_full_model_list_is_explicit() -> None:
    assert FULL_MODELS == ("M0", "M2", "M4", "M6", "M7")
    assert all(candidate.design_id for candidate in DEFAULT_CANDIDATES)
