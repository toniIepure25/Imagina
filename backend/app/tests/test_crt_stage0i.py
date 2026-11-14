import math
from dataclasses import replace

import numpy as np
from analysis.crt.design_optimization import (
    DEFAULT_CANDIDATES,
    HierarchicalDesignConfig,
    run_hierarchical_design_optimization,
)
from analysis.crt.full_model import FULL_MODELS
from analysis.crt.identifiability import IdentifiabilityConfig, run_identifiability
from analysis.crt.inference import backend_status
from analysis.crt.policy_model import (
    POLICIES,
    PolicyConfig,
    fit_policy_choice,
    fit_policy_parameters,
    run_policy_parameter_sbc,
    run_policy_recovery,
    run_policy_sbc,
    simulate_policy_data,
)
from analysis.crt.target_design import TargetProjectionConfig, _projected_pairwise
from analysis.crt.trial_model import TrialModelConfig, fit_trial_model, simulate_trial_data

from app.cli.crt_stage0i import package_payload, source_audit_payload
from app.research.crt.protocol import audit_spec, load_spec, run_protocol_audit


def test_stage0i_protocol_fields() -> None:
    audit = run_protocol_audit()
    assert audit.passed, audit.errors
    assert audit.spec.version == "0.7.0"
    assert audit.spec.stage == "0I"
    assert audit.spec.stage0i_status == "computational_only_human_data_gated"
    assert audit.spec.policy_model_status == "required_before_registration"
    assert audit.spec.identifiability_status == "required_before_registration"


def test_protocol_rejects_missing_stage0i_status() -> None:
    spec = load_spec()
    broken = replace(spec, stage0i_status="")
    audit = audit_spec(broken)
    assert "stage0i_status must be computational_only_human_data_gated" in audit.errors


def test_source_audit_records_corcoran_correction() -> None:
    payload = source_audit_payload()
    assert payload["decision"] == "CRT_STAGE0I_SOURCE_INTEGRITY_PASS"
    corcoran = next(item for item in payload["sources"] if item["id"] == "corcoran_2023")
    assert "Bayesian adversarial collaboration" in corcoran["title"]
    assert corcoran["used_for"] == "Bayesian adversarial collaboration method"
    assert payload["corrections"]


def test_policy_choice_probabilities_and_recovery_are_explicit() -> None:
    config = PolicyConfig(n_participants=3, n_trials=8, n_simulations=1, seed=7)
    data, _ = simulate_policy_data("meta_eig", config)
    fit = fit_policy_choice(data, config)
    assert fit["selected_by_bic"] in POLICIES
    assert set(fit["scores"]) == set(POLICIES)
    sbc = run_policy_sbc(config)
    assert sbc["sbc_type"] == "discrete_policy_model_rank_not_continuous_parameter_sbc"
    assert sbc["decision"] in {
        "CRT_STAGE0I_POLICY_SBC_PASS",
        "CRT_STAGE0I_POLICY_SBC_REVIEW",
    }
    recovery = run_policy_recovery(config)
    assert recovery["confusion"]
    assert recovery["decision"] in {
        "CRT_STAGE0I_POLICY_RECOVERY_PASS",
        "CRT_STAGE0I_POLICY_RECOVERY_REVIEW",
    }


def test_policy_parameter_sbc_is_labelled_laplace() -> None:
    config = PolicyConfig(
        n_participants=3,
        n_trials=8,
        n_simulations=1,
        n_parameter_sbc=1,
        n_parameter_draws=20,
        seed=11,
    )
    data, _ = simulate_policy_data("meta_eig", config)
    fit = fit_policy_parameters(data, "meta_eig", config)
    assert 0 < fit["temperature"] <= 20
    assert 0 < fit["cost_weight"] < 1
    sbc = run_policy_parameter_sbc(config)
    assert sbc["sbc_type"] == "laplace_approximate_continuous_parameter_sbc"
    assert sbc["decision"] in {
        "CRT_STAGE0I_POLICY_PARAMETER_SBC_PASS",
        "CRT_STAGE0I_POLICY_PARAMETER_SBC_REVIEW",
    }


def test_target_scale_config_is_declared_without_running() -> None:
    config = HierarchicalDesignConfig(
        n_participants=432,
        n_trials=240,
        n_replicates=1,
        models=FULL_MODELS,
        candidates=DEFAULT_CANDIDATES[:1],
        max_iter=200,
    )
    assert config.n_participants == 432
    assert config.n_trials == 240
    assert config.models == FULL_MODELS
    assert config.recovery_threshold == 0.85
    projection = TargetProjectionConfig(
        pilot_n=6,
        pilot_trials=20,
        target_n=432,
        target_trials=240,
        n_replicates=2,
        candidates=DEFAULT_CANDIDATES[:1],
    )
    assert projection.scale_factor > 1


def test_readout_fit_can_skip_laplace_for_design_screen() -> None:
    data, _ = simulate_trial_data("M0", n_participants=6, n_trials=20, seed=3)
    fit = fit_trial_model(
        data,
        "M0",
        TrialModelConfig(
            n_participants=6,
            n_trials=20,
            n_sbc=1,
            n_posterior_draws=20,
            n_recovery=1,
            max_iter=60,
            laplace=False,
        ),
    )
    assert fit.posterior_draws.shape == (0, fit.map_params.size)
    assert math.isfinite(fit.bic)


def test_projected_pairwise_rewards_consistent_bic_separation() -> None:
    deltas = {
        "M0": np.array([[0.0, 20.0], [0.0, 22.0]]),
        "M6": np.array([[20.0, 0.0], [22.0, 0.0]]),
    }
    pairwise = _projected_pairwise(deltas, ("M0", "M6"), scale=4.0)
    assert pairwise["M0_vs_M6"] > 0.99


def test_subset_design_and_identifiability_cannot_pass() -> None:
    design = run_hierarchical_design_optimization(
        HierarchicalDesignConfig(
            n_participants=6,
            n_trials=20,
            n_replicates=1,
            models=("M0", "M6"),
            candidates=DEFAULT_CANDIDATES[:1],
            max_iter=40,
        )
    )
    assert design["decision"] == "CRT_STAGE0I_DESIGN_ADO_REVIEW"
    ident = run_identifiability(
        IdentifiabilityConfig(
            n_participants=6,
            n_trials=20,
            n_simulations=1,
            n_posterior_draws=20,
            max_iter=40,
        )
    )
    assert ident["decision"] in {
        "CRT_STAGE0I_IDENTIFIABILITY_PASS",
        "CRT_STAGE0I_IDENTIFIABILITY_REVIEW",
    }


def test_inference_backend_is_not_silently_confirmatory() -> None:
    status = backend_status()
    assert status["decision"] in {
        "CRT_STAGE0I_INFERENCE_BACKEND_READY",
        "CRT_STAGE0I_INFERENCE_BACKEND_BLOCKED",
    }
    assert status["laplace_role"] == "screening_only_not_confirmatory"


def test_package_blocks_without_review(tmp_path) -> None:
    payload = package_payload(tmp_path)
    assert payload["status"] == "BLOCKED"
    assert any("missing" in blocker for blocker in payload["blockers"])
