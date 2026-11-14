import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import check_grad

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analysis.crt.trial_model import (  # noqa: E402
    ACTIVE_DELTAS,
    CONFIRMATORY_MODELS,
    GROUP_NAMES,
    MODELS,
    SCOPE,
    MissingModelInputError,
    TrialModelConfig,
    _objective_and_grad,
    run_trial_recovery,
    run_trial_sbc,
    simulate_trial_data,
)


def test_trial_model_gradient_matches_finite_difference() -> None:
    for model in ("M2", "M6", "M7"):
        data, _ = simulate_trial_data(model, n_participants=6, n_trials=20, seed=11)
        x0 = np.concatenate([np.zeros(len(GROUP_NAMES)), np.full(4, math.log(0.5)), np.zeros(24)])
        error = check_grad(
            lambda x: _objective_and_grad(model, data, x, 6)[0],
            lambda x: _objective_and_grad(model, data, x, 6)[1],
            x0,
        )
        assert error < 1e-3


def test_trial_model_scope_and_mapping_are_explicit() -> None:
    assert SCOPE == "trial_level_hierarchical_readout_not_full_crt_pomdp"
    assert ACTIVE_DELTAS["M0"] == ()
    assert "delta_d" in ACTIVE_DELTAS["M2"]
    assert "delta_dual_b" in ACTIVE_DELTAS["M4"]
    assert set(MODELS) == {"M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"}
    assert set(CONFIRMATORY_MODELS) == {"M0", "M2", "M4", "M6", "M7"}


def test_m6_m7_require_their_trial_covariates() -> None:
    data, _ = simulate_trial_data("M2", n_participants=6, n_trials=20, seed=12)
    stripped = type(data)(
        participant=data.participant,
        predict=data.predict,
        dual=data.dual,
        diagnosticity=data.diagnosticity,
        imagined=data.imagined,
        prediction=data.prediction,
        outcome=data.outcome,
        source_correct=data.source_correct,
    )
    with np.testing.assert_raises(MissingModelInputError):
        _objective_and_grad("M6", stripped, np.zeros(len(GROUP_NAMES) + 4 + 24), 6)
    with np.testing.assert_raises(MissingModelInputError):
        _objective_and_grad("M7", stripped, np.zeros(len(GROUP_NAMES) + 4 + 24), 6)


def test_trial_sbc_smoke_runs_and_records_scope() -> None:
    config = TrialModelConfig(
        n_participants=8,
        n_trials=20,
        n_sbc=4,
        n_posterior_draws=20,
        n_recovery=1,
        max_iter=200,
        seed=5,
    )
    report = run_trial_sbc(config, model="M2")
    assert report["scope"] == SCOPE
    assert report["decision"].startswith("CRT_STAGE0G_TRIAL_SBC_")
    assert "delta_d" in report["metrics"]
    assert 0.0 <= report["convergence_rate"] <= 1.0


def test_trial_model_recovery_smoke_runs() -> None:
    config = TrialModelConfig(
        n_participants=6,
        n_trials=20,
        n_sbc=2,
        n_posterior_draws=20,
        n_recovery=1,
        max_iter=200,
        seed=6,
    )
    report = run_trial_recovery(config)
    assert report["scope"] == SCOPE
    assert len(report["confusion"]) == len(MODELS)
    assert 0.0 <= report["balanced_accuracy"] <= 1.0
    assert report["decision"].startswith("CRT_STAGE0G_TRIAL_RECOVERY_")
