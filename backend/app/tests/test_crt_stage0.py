"""Stage 0 tests for the Counterfactual Reality Testing simulation core."""
from __future__ import annotations

import math

import pytest

from app.research.crt.design import (
    CONDITIONS,
    DEFAULT_TESTS,
    default_blocks,
    source_schedule,
    yoked_test_sequence,
)
from app.research.crt.design import (
    test_agency_values as agency_vector,
)
from app.research.crt.design import (
    test_complexities as complexity_vector,
)
from app.research.crt.design import (
    test_costs as cost_vector,
)
from app.research.crt.metrics import (
    TestRecord,
    TrialRecord,
    brier_score,
    confounded_test_rate,
    expected_calibration_error,
    imagination_inflation_rate,
    information_resolution,
    summarize,
)
from app.research.crt.model import (
    ALL_TESTS,
    DEFAULT_PRIOR,
    DESCRIBED,
    FLUENCY,
    IMAGINED,
    INTEND,
    NEW,
    SEEN,
    SOURCES,
    TEST_IDS,
    TEST_LIKELIHOODS,
    VIEWPOINT,
    AgentParams,
    apply_prediction_bias,
    choose_source_probabilities,
    counterfactual_discrimination,
    effective_likelihoods,
    eig,
    entropy,
    expected_random_eig,
    expected_random_meta_eig,
    greedy_eig,
    greedy_meta_eig,
    meta_eig,
    posterior_from_outcome,
    posterior_from_prediction_outcome,
    prediction_likelihood,
    softmax,
)
from app.research.crt.power import PowerConfig, run_power
from app.research.crt.simulate import (
    SimulationConfig,
    check_prediction_ablation,
    check_recovery,
    check_simulation,
    fit_precision,
    run_recovery,
    simulate_participant,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def _agent(**overrides: float) -> AgentParams:
    values: dict[str, float] = {
        "beta": 2.0,
        "lam": 0.25,
        "gamma": 0.2,
        "tau": -0.2,
        "d": 1.0,
        "pi": 1.2,
        "b_pi": 0.3,
        "guess": 0.0,
        "bias": 0.2,
        "lapse": 0.0,
        "confidence_noise": 0.0,
        "mix": 1.0,
        "alpha": 0.5,
    }
    values.update(overrides)
    return AgentParams(**values)


def _test_record(**overrides: object) -> TestRecord:
    values: dict[str, object] = {
        "test": VIEWPOINT,
        "outcome": True,
        "eig": 0.1,
        "meta_eig": 0.2,
        "counterfactual_discrimination": 0.1,
        "cost": 1.5,
        "complexity": 2.0,
        "max_eig": 0.1,
        "max_meta_eig": 0.2,
        "predicted": True,
        "prediction_confidence": 0.8,
        "prediction_correct": True,
    }
    values.update(overrides)
    return TestRecord(**values)  # type: ignore[arg-type]


def _trial(source: int = SEEN, choice: int = SEEN, **overrides: object) -> TrialRecord:
    tests = tuple(overrides.pop("tests", (_test_record(),)))  # type: ignore[arg-type]
    values: dict[str, object] = {
        "condition": "active_predict",
        "true_source": source,
        "choice": choice,
        "confidence": 0.8,
        "correct": source == choice,
        "tests": tests,
        "prior_entropy": entropy(DEFAULT_PRIOR),
        "final_entropy": 0.5,
        "human_meta_eig": sum(test.meta_eig for test in tests),
        "greedy_meta_eig": 0.4,
        "random_meta_eig": 0.1,
        "crte_meta": 0.8,
        "crte_eig": 0.7,
        "base_posterior": DEFAULT_PRIOR,
        "evidence_resolution": 0.5,
    }
    values.update(overrides)
    return TrialRecord(**values)  # type: ignore[arg-type]


def test_sources_and_tests_are_well_formed() -> None:
    assert len(SOURCES) == 4
    assert len(TEST_IDS) == len(TEST_LIKELIHOODS) == len(DEFAULT_TESTS) == 6
    assert ALL_TESTS == tuple(range(6))
    assert TEST_IDS[VIEWPOINT] == "viewpoint"
    assert TEST_IDS[FLUENCY] == "fluency"


def test_likelihoods_are_valid_probabilities() -> None:
    for row in TEST_LIKELIHOODS:
        assert len(row) == len(SOURCES)
        for value in row:
            assert 0.0 < value < 1.0


def test_effective_likelihoods_sharpen_with_d() -> None:
    flat = effective_likelihoods(0.5)
    sharp = effective_likelihoods(1.5)
    assert sharp[VIEWPOINT][SEEN] > flat[VIEWPOINT][SEEN]
    assert sharp[VIEWPOINT][NEW] < flat[VIEWPOINT][NEW]


def test_zero_precision_makes_prediction_neutral() -> None:
    for test in ALL_TESTS:
        for source in range(4):
            assert prediction_likelihood(test, source, 0.0) == pytest.approx(0.5)


def test_outcome_posterior_is_normalized_and_directional() -> None:
    positive = posterior_from_outcome(DEFAULT_PRIOR, VIEWPOINT, True, 1.0)
    negative = posterior_from_outcome(DEFAULT_PRIOR, VIEWPOINT, False, 1.0)
    assert sum(positive) == pytest.approx(1.0)
    assert sum(negative) == pytest.approx(1.0)
    assert positive[SEEN] > 0.25
    assert negative[SEEN] < 0.25


def test_prediction_and_outcome_posterior_uses_both_signals() -> None:
    outcome_only = posterior_from_outcome(DEFAULT_PRIOR, VIEWPOINT, True, 1.0)
    both_consistent = posterior_from_prediction_outcome(
        DEFAULT_PRIOR, VIEWPOINT, True, True, 1.0, 1.0
    )
    contradiction = posterior_from_prediction_outcome(
        DEFAULT_PRIOR, VIEWPOINT, False, True, 1.0, 1.0
    )
    assert sum(both_consistent) == pytest.approx(1.0)
    assert both_consistent[SEEN] > outcome_only[SEEN]
    assert contradiction[SEEN] < both_consistent[SEEN]


def test_eig_is_bounded_by_prior_entropy() -> None:
    for test in ALL_TESTS:
        gain = eig(DEFAULT_PRIOR, test, 1.0)
        assert 0.0 <= gain <= entropy(DEFAULT_PRIOR) + 1e-12


def test_meta_eig_reduces_to_eig_when_prediction_is_uninformative() -> None:
    for test in ALL_TESTS:
        assert meta_eig(DEFAULT_PRIOR, test, 0.0, 1.0) == pytest.approx(
            eig(DEFAULT_PRIOR, test, 1.0), abs=1e-12
        )


def test_meta_eig_exceeds_eig_for_informative_prediction() -> None:
    for test in ALL_TESTS[:-1]:
        assert meta_eig(DEFAULT_PRIOR, test, 1.2, 1.0) >= eig(DEFAULT_PRIOR, test, 1.0) - 1e-12


def test_fluency_is_a_zero_diagnosticity_trap() -> None:
    assert counterfactual_discrimination(DEFAULT_PRIOR, FLUENCY, 1.2) == pytest.approx(0.0)
    assert counterfactual_discrimination(DEFAULT_PRIOR, VIEWPOINT, 1.2) > 0.0


def test_greedy_eig_beats_random_and_is_monotone() -> None:
    assert greedy_eig(DEFAULT_PRIOR, 1) >= expected_random_eig(DEFAULT_PRIOR, 1)
    assert greedy_eig(DEFAULT_PRIOR, 2) >= greedy_eig(DEFAULT_PRIOR, 1)
    assert greedy_eig(DEFAULT_PRIOR, 0) == 0.0


def test_greedy_meta_eig_beats_random_and_reduces_to_outcome_greedy() -> None:
    assert greedy_meta_eig(DEFAULT_PRIOR, 2, ALL_TESTS, 1.2, 1.0) >= expected_random_meta_eig(
        DEFAULT_PRIOR, 2, ALL_TESTS, 1.2, 1.0
    )
    assert greedy_meta_eig(DEFAULT_PRIOR, 2, ALL_TESTS, 0.0, 1.0) == pytest.approx(
        greedy_eig(DEFAULT_PRIOR, 2, ALL_TESTS, 1.0), abs=1e-12
    )


def test_softmax_is_a_distribution() -> None:
    probabilities = softmax([1.0, 2.0, 3.0])
    assert sum(probabilities) == pytest.approx(1.0)
    assert probabilities[2] > probabilities[1] > probabilities[0]
    assert softmax([0.0, 0.0]) == pytest.approx((0.5, 0.5))


def test_prediction_bias_inflates_seen_attribution() -> None:
    biased = apply_prediction_bias(DEFAULT_PRIOR, ((True, 0.9),), 0.5)
    assert biased[SEEN] > 0.25
    assert sum(biased) == pytest.approx(1.0)
    assert apply_prediction_bias(DEFAULT_PRIOR, (), 0.5) == DEFAULT_PRIOR


def test_source_guessing_probabilities_are_normalized_and_biased() -> None:
    neutral = choose_source_probabilities(DEFAULT_PRIOR, guess=0.2, bias=0.0)
    biased = choose_source_probabilities(DEFAULT_PRIOR, guess=0.2, bias=0.5)
    assert sum(neutral) == pytest.approx(1.0)
    assert sum(biased) == pytest.approx(1.0)
    assert biased[SEEN] > neutral[SEEN]


def test_invalid_agent_parameters_are_rejected() -> None:
    with pytest.raises(ValueError):
        AgentParams(d=0.0)
    with pytest.raises(ValueError):
        AgentParams(pi=-1.0)
    with pytest.raises(ValueError):
        AgentParams(guess=1.5)
    with pytest.raises(ValueError):
        AgentParams(mix=2.0)


def test_source_schedule_is_balanced_and_deterministic() -> None:
    first = source_schedule(120, seed=11)
    second = source_schedule(120, seed=11)
    assert first == second
    counts = [sum(1 for source in first if source == index) for index in range(4)]
    assert counts == [30, 30, 30, 30]


def test_design_helpers_return_expected_vectors() -> None:
    assert len(cost_vector(DEFAULT_TESTS)) == 6
    assert cost_vector(DEFAULT_TESTS, multiplier=2.0)[0] == pytest.approx(3.0)
    assert len(complexity_vector(DEFAULT_TESTS)) == 6
    assert len(agency_vector(DEFAULT_TESTS)) == 6
    with pytest.raises(ValueError):
        cost_vector(DEFAULT_TESTS, multiplier=-1.0)


def test_default_blocks_cover_the_registered_conditions() -> None:
    blocks = default_blocks()
    assert {block.condition for block in blocks} == set(CONDITIONS)
    assert sum(block.n_trials for block in blocks) == 140


def test_yoked_sequence_keeps_only_test_identity() -> None:
    assert yoked_test_sequence(((VIEWPOINT, True), (INTEND, False))) == (VIEWPOINT, INTEND)


def test_summary_metrics_are_finite_and_bounded() -> None:
    trials = [_trial(), _trial(source=IMAGINED, choice=SEEN, correct=False)]
    summary = summarize(trials)
    assert 0.0 <= summary.accuracy <= 1.0
    assert 0.0 <= summary.brier_score <= 1.0
    assert 0.0 <= summary.expected_calibration_error <= 1.0
    assert summary.n_trials == 2
    assert math.isfinite(summary.d_prime_seen_imagined)


def test_information_resolution_is_bounded() -> None:
    posterior = posterior_from_outcome(DEFAULT_PRIOR, VIEWPOINT, True, 1.0)
    resolution = information_resolution(DEFAULT_PRIOR, posterior)
    assert 0.0 <= resolution <= 1.0


def test_imagination_inflation_rate_uses_high_confidence_predictions() -> None:
    eligible = _trial(source=IMAGINED, choice=SEEN, correct=False)
    low_confidence = _trial(
        source=IMAGINED,
        choice=SEEN,
        correct=False,
        tests=(_test_record(prediction_confidence=0.55),),
    )
    assert imagination_inflation_rate([eligible, low_confidence]) == pytest.approx(1.0)


def test_confounded_test_rate_counts_fluency() -> None:
    trials = [
        _trial(tests=(_test_record(test=FLUENCY),)),
        _trial(tests=(_test_record(test=VIEWPOINT), _test_record(test=FLUENCY))),
    ]
    assert confounded_test_rate(trials) == pytest.approx(2.0 / 3.0)


def test_expected_calibration_error_is_zero_for_perfect_calibration() -> None:
    trial = _trial(confidence=1.0, correct=True)
    assert expected_calibration_error([trial]) < 0.05
    assert brier_score([trial]) == pytest.approx(0.0)


def test_simulated_participant_is_deterministic() -> None:
    config = SimulationConfig(n_participants=1, n_trials=12, seed=3)
    first = simulate_participant(config, _agent(), seed=99, condition="active_predict")
    second = simulate_participant(config, _agent(), seed=99, condition="active_predict")
    assert [trial.choice for trial in first.trials] == [trial.choice for trial in second.trials]
    assert first.scripts == second.scripts


def test_active_prediction_produces_predictions_and_crte() -> None:
    config = SimulationConfig(n_participants=3, n_trials=20, seed=5)
    result = simulate_participant(config, _agent(), seed=101, condition="active_predict")
    assert result.trials
    assert any(test.predicted is not None for trial in result.trials for test in trial.tests)
    assert all(
        trial.crte_meta is None or 0.0 <= trial.crte_meta <= 1.0 for trial in result.trials
    )


def test_yoked_conditions_require_scripts() -> None:
    config = SimulationConfig(n_participants=1, n_trials=5, seed=3)
    with pytest.raises(ValueError):
        simulate_participant(config, _agent(), seed=99, condition="yoked_predict")


def test_simulation_gate_passes() -> None:
    report = check_simulation()
    assert report["decision"] == "CRT_STAGE0_SIMULATION_PASS"
    comparison = report["condition_comparison"]
    assert comparison["prediction_advantage"] >= 0.03
    assert comparison["active_calibration_advantage"] >= 0.03


def test_prediction_ablation_is_positive() -> None:
    report = check_prediction_ablation()
    assert report["prediction_ablation"]["prediction_advantage"] > 0.0


def test_precision_recovery_is_close() -> None:
    predictions = [
        (VIEWPOINT, SEEN, True),
        (VIEWPOINT, NEW, False),
        (INTEND, IMAGINED, True),
        (DESCRIBED, DESCRIBED, True),
    ]
    estimate = fit_precision(predictions)
    assert 0.0 <= estimate <= 2.0


def test_recovery_reports_a_registered_decision() -> None:
    report = check_recovery()
    assert report["decision"] in {
        "CRT_STAGE0_RECOVERY_PASS",
        "CRT_STAGE0_RECOVERY_REVIEW",
    }
    assert set(report["recovery"]["estimated"]) == {"beta", "lam", "gamma", "tau", "mix", "pi", "b_pi"}


def test_recovery_artifact_contains_all_parameters() -> None:
    report = run_recovery(SimulationConfig(n_participants=8, n_trials=40, seed=13))
    assert set(report["recovery"]["true"]) == {"beta", "lam", "gamma", "tau", "mix", "pi", "b_pi"}


def test_power_gate_passes() -> None:
    report = run_power(PowerConfig(n_participants=180, n_simulations=200, seed=7))
    assert report["decision"] == "CRT_STAGE0_POWER_PASS"


def test_invalid_simulation_config_is_rejected() -> None:
    with pytest.raises(ValueError):
        SimulationConfig(n_participants=0)
    with pytest.raises(ValueError):
        SimulationConfig(n_trials=0)
    with pytest.raises(ValueError):
        SimulationConfig(max_tests=0)
    with pytest.raises(ValueError):
        SimulationConfig(cost_levels=())
