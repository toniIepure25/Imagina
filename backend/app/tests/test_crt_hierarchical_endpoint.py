import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from analysis.crt.hierarchical_sbc import (  # noqa: E402
    EndpointConfig,
    run_all,
    run_model_recovery,
    run_sbc,
)


def test_endpoint_sbc_smoke() -> None:
    report = run_sbc(
        EndpointConfig(n_sbc=20, n_posterior_draws=40, n_participants=40, n_recovery=2)
    )
    assert report["n_simulations"] == 20
    assert 0.0 <= report["mean_rank"] <= 1.0
    assert 0.0 <= report["coverage"] <= 1.0
    assert isinstance(report["passed"], bool)


def test_endpoint_model_recovery_smoke() -> None:
    report = run_model_recovery(
        EndpointConfig(n_sbc=2, n_posterior_draws=20, n_participants=30, n_recovery=1)
    )
    assert set(report["models"]) == {"M0", "M2", "M3", "M4"}
    assert 0.0 <= report["balanced_accuracy"] <= 1.0
    assert sum(sum(row.values()) for row in report["confusion"].values()) == 4


def test_endpoint_report_scope_is_explicit() -> None:
    report = run_all(
        EndpointConfig(n_sbc=2, n_posterior_draws=20, n_participants=30, n_recovery=1)
    )
    assert report["scope"] == "stage1d_paired_false_seen_endpoint_not_trial_level_crt"
    assert report["decision"].startswith("CRT_STAGE0F_HIERARCHICAL_ENDPOINT_")
