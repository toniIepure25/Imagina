"""Tests for Stage 0E policy competition."""
from __future__ import annotations

import pytest

from app.research.crt.policy import PolicyConfig, run_policy_tournament

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_policy_tournament_is_deterministic() -> None:
    config = PolicyConfig(n_participants=8, n_trials=30, seed=7)
    assert run_policy_tournament(config) == run_policy_tournament(config)


def test_policy_tournament_includes_cost_only_baseline() -> None:
    report = run_policy_tournament(PolicyConfig(n_participants=8, n_trials=30, seed=7))
    assert "cost_only" in report["condition_summaries"]
    assert "meta_eig_minus_cost_only" in report["contrasts"]


def test_normative_policy_claim_is_not_yet_supported() -> None:
    report = run_policy_tournament(PolicyConfig(n_participants=24, n_trials=60, seed=20261030))
    assert report["decision"] == "CRT_STAGE0E_POLICY_REVIEW"
    assert report["contrasts"]["meta_eig_minus_cost_only"] > 0.0
    assert report["contrasts"]["meta_eig_minus_best_alternative"] < 0.01
