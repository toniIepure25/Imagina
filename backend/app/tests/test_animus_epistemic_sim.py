"""Deterministic checks for the synthetic ERI policy simulation."""
from __future__ import annotations

import pytest

from app.evaluation.animus_epistemic_sim import POLICIES, SimulationConfig, run_policy, run_simulation

pytestmark = pytest.mark.core


def test_simulation_is_deterministic_and_labelled_as_simulation():
    first = run_simulation(SimulationConfig(seed=7, interviews=8))
    second = run_simulation(SimulationConfig(seed=7, interviews=8))
    assert first == second
    assert first["simulation_only"] is True
    assert first["protocol_version"] == "eri-sim-v1"
    assert [item["policy"] for item in first["results"]] == list(POLICIES)
    assert first["limitations"]


def test_info_gain_policy_uses_no_more_than_the_probe_budget():
    config = SimulationConfig(seed=11, interviews=4, max_probes=6)
    for policy in POLICIES:
        result = run_policy(policy, config)
        assert result["mean_probes"] <= config.max_probes
        assert 0.0 <= result["coverage"] <= 1.0
        assert result["object_recovery_accuracy"] is not None
        assert 0.0 <= result["object_recovery_accuracy"] <= 1.0
