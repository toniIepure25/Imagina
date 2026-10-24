from __future__ import annotations

import pytest

from app.evaluation.animus_instrument_sim import POLICIES, simulate

pytestmark = pytest.mark.core


def test_simulation_is_deterministic_for_each_policy():
    for policy in POLICIES:
        first = simulate(policy, trials=40, seed=11)
        second = simulate(policy, trials=40, seed=11)
        assert first == second
        assert first["metrics"]["coverage"] == 1.0
        assert first["metrics"]["brier"] is not None


def test_simulation_requires_every_dimension():
    with pytest.raises(ValueError):
        simulate(latent={"stability": 0.7}, trials=20)


def test_simulation_rejects_short_runs_and_unknown_policies():
    with pytest.raises(ValueError):
        simulate(trials=3)
    with pytest.raises(ValueError):
        simulate(policy="unknown")
