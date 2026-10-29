"""Stage 0 tests for the Active Reality Testing simulation core."""
from __future__ import annotations

import math

import pytest

from app.research.art.design import card_costs, source_schedule, yoked_card_sequence
from app.research.art.metrics import (
    QueryRecord,
    TrialRecord,
    brier_score,
    expected_calibration_error,
    information_resolution,
    summarize,
)
from app.research.art.model import (
    CARD_IDS,
    CARD_LIKELIHOODS,
    CONTEXT,
    DEFAULT_PRIOR,
    DESCRIBED,
    IMAGINED,
    NEW,
    PERCEPTUAL,
    SEEN,
    AgentParams,
    card_likelihood,
    effective_likelihoods,
    entropy,
    expected_information_gain,
    expected_random_eig,
    greedy_eig,
    posterior_from_evidence,
    softmax,
)
from app.research.art.power import PowerConfig, run_power
from app.research.art.simulate import (
    SimulationConfig,
    check_policy_comparison,
    check_recovery,
    check_simulation,
    compare_policies,
    fit_policy,
    run_recovery,
    run_simulation,
    simulate_participant,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def _agent(**overrides: float) -> AgentParams:
    values: dict[str, float] = {
        "beta": 2.0,
        "lam": 0.25,
        "tau": -0.2,
        "d": 1.0,
        "lapse": 0.0,
        "confidence_noise": 0.0,
    }
    values.update(overrides)
    return AgentParams(**values)


def test_card_likelihoods_are_probabilities() -> None:
    for card in range(len(CARD_IDS)):
        for source in (SEEN, IMAGINED, DESCRIBED, NEW):
            assert 0.0 < card_likelihood(card, source) < 1.0


def test_effective_likelihoods_sharpen_with_evidence_gain() -> None:
    flat = effective_likelihoods(0.5)
    sharp = effective_likelihoods(1.5)
    assert sharp[PERCEPTUAL][SEEN] > flat[PERCEPTUAL][SEEN]
    assert sharp[PERCEPTUAL][NEW] < flat[PERCEPTUAL][NEW]
    assert sharp[PERCEPTUAL][SEEN] > CARD_LIKELIHOODS[PERCEPTUAL][SEEN]


def test_posterior_is_normalized_and_directional() -> None:
    positive = posterior_from_evidence(DEFAULT_PRIOR, ((PERCEPTUAL, True),))
    negative = posterior_from_evidence(DEFAULT_PRIOR, ((PERCEPTUAL, False),))
    assert sum(positive) == pytest.approx(1.0)
    assert sum(negative) == pytest.approx(1.0)
    assert positive[SEEN] > 0.25
    assert negative[SEEN] < 0.25


def test_expected_information_gain_is_bounded() -> None:
    for card in range(len(CARD_IDS)):
        gain = expected_information_gain(DEFAULT_PRIOR, card)
        assert gain >= 0.0
        assert gain <= entropy(DEFAULT_PRIOR) + 1e-12


def test_expected_information_gain_orders_the_uniform_prior() -> None:
    gains = [expected_information_gain(DEFAULT_PRIOR, card) for card in range(len(CARD_IDS))]
    assert gains[PERCEPTUAL] > gains[CONTEXT]
    assert gains[PERCEPTUAL] > 0.0


def test_greedy_eig_beats_random_sampling() -> None:
    greedy = greedy_eig(DEFAULT_PRIOR, 3)
    random_gain = expected_random_eig(DEFAULT_PRIOR, 3)
    assert greedy > random_gain
    assert greedy_eig(DEFAULT_PRIOR, 0) == 0.0


def test_softmax_is_a_distribution() -> None:
    probabilities = softmax([1.0, 2.0, 3.0])
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[2] > probabilities[1] > probabilities[0]
    assert softmax([0.0, 0.0]) == pytest.approx((0.5, 0.5))


def test_source_schedule_is_balanced() -> None:
    schedule = source_schedule(80, seed=11)
    counts = [sum(1 for source in schedule if source == index) for index in range(4)]
    assert counts == [20, 20, 20, 20]


def test_yoked_sequence_keeps_only_card_identity() -> None:
    assert yoked_card_sequence(((PERCEPTUAL, True), (CONTEXT, False))) == (PERCEPTUAL, CONTEXT)


def test_participant_simulation_is_deterministic() -> None:
    config = SimulationConfig(n_participants=1, n_trials=20, seed=13)
    first = simulate_participant(config, _agent(), seed=13)
    second = simulate_participant(config, _agent(), seed=13)
    assert first.trials == second.trials
    assert first.decisions == second.decisions


def test_participant_respects_query_limit() -> None:
    config = SimulationConfig(n_participants=1, n_trials=20, seed=14, max_queries=2)
    result = simulate_participant(config, _agent(), seed=14)
    assert all(len(trial.queries) <= 2 for trial in result.trials)


def test_participant_queries_are_distinct_cards() -> None:
    config = SimulationConfig(n_participants=1, n_trials=20, seed=14, max_queries=2)
    result = simulate_participant(config, _agent(), seed=14)
    for trial in result.trials:
        cards = [query.card for query in trial.queries]
        assert len(cards) == len(set(cards))


def test_participant_records_query_costs() -> None:
    config = SimulationConfig(
        n_participants=1,
        n_trials=20,
        seed=15,
        cost_levels=(0.5, 1.0, 2.0),
    )
    result = simulate_participant(config, _agent(), seed=15)
    costs = {query.cost for trial in result.trials for query in trial.queries}
    assert costs.issubset({0.5, 1.0, 2.0})


def test_arte_is_bounded_and_insufficient_queries_are_marked() -> None:
    config = SimulationConfig(n_participants=1, n_trials=20, seed=16)
    result = simulate_participant(config, _agent(), seed=16)
    for trial in result.trials:
        if trial.arte is None:
            assert not trial.queries
        else:
            assert 0.0 <= trial.arte <= 1.0


def test_metrics_have_expected_bounds() -> None:
    perfect = [
        TrialRecord(SEEN, SEEN, 1.0, True, (), 2.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0),
        TrialRecord(IMAGINED, IMAGINED, 1.0, True, (), 2.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0),
    ]
    assert brier_score(perfect) == pytest.approx(0.0)
    assert expected_calibration_error(perfect) == pytest.approx(0.0)
    overconfident = [
        TrialRecord(SEEN, IMAGINED, 1.0, False, (), 2.0, 1.0, 0.0, 0.0, 0.0, None, None, 0.5),
    ]
    assert brier_score(overconfident) == pytest.approx(1.0)
    assert summarize([]).mean_arte is None


def test_information_resolution_is_bounded() -> None:
    assert information_resolution(DEFAULT_PRIOR, DEFAULT_PRIOR) == pytest.approx(0.0)
    peaked = (1.0, 0.0, 0.0, 0.0)
    assert information_resolution(DEFAULT_PRIOR, peaked) == pytest.approx(1.0)


def test_simulation_gate_passes() -> None:
    report = check_simulation()
    assert report["decision"] == "ART_STAGE0_SIMULATION_PASS"
    assert report["measurement"]["mean_accuracy"] > 0.25


def test_simulation_is_deterministic() -> None:
    config = SimulationConfig(n_participants=6, n_trials=20, seed=17)
    assert run_simulation(config) == run_simulation(config)


def test_policy_recovery_gate_passes() -> None:
    report = check_recovery()
    assert report["decision"] == "ART_STAGE0_RECOVERY_PASS"
    assert abs(report["recovery"]["beta"]["bias"]) <= 0.30


def test_recovery_is_deterministic() -> None:
    config = SimulationConfig(
        n_participants=4,
        n_trials=30,
        seed=19,
        cost_levels=(0.5, 1.0, 2.0),
    )
    assert run_recovery(config) == run_recovery(config)


def test_fit_policy_handles_empty_decisions() -> None:
    recovered = fit_policy(())
    assert recovered.beta == 0.0


def test_policy_comparison_gate_passes() -> None:
    report = check_policy_comparison()
    assert report["decision"] == "ART_STAGE0_POLICY_PASS"
    assert report["policies"]["eig"]["mean_arte"] > report["policies"]["random"]["mean_arte"]


def test_compare_policies_has_all_baselines() -> None:
    report = compare_policies(SimulationConfig(n_participants=4, n_trials=20, seed=21))
    assert set(report["policies"]) == {"eig", "fixed", "heuristic", "random"}


def test_power_gate_passes() -> None:
    report = run_power(PowerConfig(n_participants=180, n_simulations=300, seed=7))
    assert report["decision"] == "ART_STAGE0_POWER_PASS"
    target = next(item for item in report["scenarios"] if item["true_icc"] == 0.75)
    assert target["power"] >= 0.80


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        SimulationConfig(n_participants=0)
    with pytest.raises(ValueError):
        SimulationConfig(n_trials=10, max_queries=0)
    with pytest.raises(ValueError):
        card_costs(multiplier=-1.0)
    with pytest.raises(ValueError):
        card_likelihood(99, SEEN)


def test_query_record_fields_are_finite() -> None:
    config = SimulationConfig(n_participants=1, n_trials=10, seed=23)
    result = simulate_participant(config, _agent(), seed=23)
    for trial in result.trials:
        for query in trial.queries:
            assert isinstance(query, QueryRecord)
            assert math.isfinite(query.eig)
            assert math.isfinite(query.max_eig)
