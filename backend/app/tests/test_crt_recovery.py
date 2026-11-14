"""Tests for the Stage 0E conditional SBC and model-recovery audit."""
from __future__ import annotations

import pytest

from app.research.crt.recovery import PI_GRID, RecoveryConfig, run_recovery

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_pi_grid_covers_the_declared_prior_range() -> None:
    assert PI_GRID[0] == 0.40
    assert PI_GRID[-1] == 2.00
    assert all(left < right for left, right in zip(PI_GRID, PI_GRID[1:]))


def test_recovery_report_has_the_registered_sections() -> None:
    report = run_recovery(
        RecoveryConfig(n_participants=2, n_sbc=8, n_model_participants=2, n_trials=60)
    )
    assert report["decision"] in {
        "CRT_STAGE0E_RECOVERY_PASS",
        "CRT_STAGE0E_RECOVERY_REVIEW",
    }
    assert sum(report["sbc"]["histogram"]) == 8
    assert "relative_rmse" in report["parameter_recovery"]
    assert sum(report["model_recovery"]["confusion"]["M0"].values()) == 2
    assert sum(report["model_recovery"]["confusion"]["M2"].values()) == 2


def test_recovery_config_rejects_invalid_sizes() -> None:
    with pytest.raises(ValueError):
        RecoveryConfig(n_sbc=0)
