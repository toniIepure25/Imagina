"""Stage 0 tests for the Source and Imagination Monitor simulation core."""
from __future__ import annotations

import random

import pytest

from app.research.prm.design import (
    THETA_GRID,
    Item,
    allowed_conditions,
    expected_information_gain,
    fixed_schedule,
    likelihood_table,
    posterior_update,
    select_next_item,
    uniform_posterior,
)
from app.research.prm.metrics import (
    TrialRecord,
    brier_score,
    expected_calibration_error,
    meta_d_prime_gate,
    summarize,
)
from app.research.prm.model import (
    DESCRIBED,
    IMAGINED,
    NEW,
    SEEN,
    PersonParams,
    dprime_from_counts,
    entropy,
    response_distribution,
    simulate_trial,
)
from app.research.prm.power import PowerConfig, icc_2_1, run_power
from app.research.prm.simulate import (
    SimulationConfig,
    _simulate_participant,
    build_items,
    check_simulation,
    compare_designs,
    run_simulation,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]
CHOICE_INDEX = {"new": NEW, "imagined": IMAGINED, "described": DESCRIBED, "seen": SEEN}


def test_response_distribution_is_a_probability_vector() -> None:
    params = PersonParams(d=1.5, bias=0.1)
    for source in (NEW, IMAGINED, DESCRIBED, SEEN):
        probabilities = response_distribution(params, source)
        assert len(probabilities) == 4
        assert all(probability >= 0.0 for probability in probabilities)
        assert sum(probabilities) == pytest.approx(1.0, abs=1e-9)


def test_dprime_is_positive_when_seen_and_imagined_are_separated() -> None:
    rng = random.Random(11)
    params = PersonParams(d=2.0, bias=0.0)
    counts = {SEEN: [0, 0, 0, 0], IMAGINED: [0, 0, 0, 0]}
    for _ in range(600):
        result = simulate_trial(params, SEEN, rng)
        counts[SEEN][CHOICE_INDEX[result.choice]] += 1
        result = simulate_trial(params, IMAGINED, rng)
        counts[IMAGINED][CHOICE_INDEX[result.choice]] += 1
    hits = counts[SEEN][SEEN]
    misses = sum(counts[SEEN]) - hits
    false_alarms = counts[IMAGINED][SEEN]
    correct_rejections = sum(counts[IMAGINED]) - false_alarms
    assert dprime_from_counts(hits, misses, false_alarms, correct_rejections) > 1.0


def test_dprime_is_near_zero_for_null_model() -> None:
    rng = random.Random(12)
    params = PersonParams(d=0.0, bias=0.0)
    hits = misses = false_alarms = correct_rejections = 0
    for _ in range(2000):
        result = simulate_trial(params, SEEN, rng)
        hits += result.choice == "seen"
        misses += result.choice != "seen"
        result = simulate_trial(params, IMAGINED, rng)
        false_alarms += result.choice == "seen"
        correct_rejections += result.choice != "seen"
    assert abs(dprime_from_counts(hits, misses, false_alarms, correct_rejections)) < 0.25


def test_confidence_metrics_have_expected_bounds() -> None:
    perfect = [
        TrialRecord(source="seen", choice="seen", confidence=1.0, correct=True),
        TrialRecord(source="imagined", choice="imagined", confidence=1.0, correct=True),
    ]
    assert brier_score(perfect) == pytest.approx(0.0)
    assert expected_calibration_error(perfect) == pytest.approx(0.0)
    overconfident = [
        TrialRecord(source="seen", choice="seen", confidence=1.0, correct=False),
        TrialRecord(source="imagined", choice="imagined", confidence=1.0, correct=False),
    ]
    assert brier_score(overconfident) == pytest.approx(1.0)
    assert expected_calibration_error(overconfident) == pytest.approx(1.0)


def test_meta_d_prime_is_gated_at_low_trial_counts() -> None:
    trials = [
        TrialRecord(source="seen", choice="seen", confidence=0.8, correct=True)
        for _ in range(20)
    ]
    assert meta_d_prime_gate(trials) == "insufficient_trials"
    summary = summarize(trials)
    assert summary.meta_d_prime is None
    assert summary.meta_d_prime_status == "insufficient_trials"


def test_expected_information_gain_prefers_discriminable_items() -> None:
    sharp = Item(item_id="sharp", condition=IMAGINED, discriminability=2.0)
    flat = Item(item_id="flat", condition=IMAGINED, discriminability=0.5)
    table = likelihood_table([sharp, flat])
    posterior = uniform_posterior()
    sharp_gain = expected_information_gain(posterior, table[0])
    flat_gain = expected_information_gain(posterior, table[1])
    assert sharp_gain > flat_gain
    assert sharp_gain > 0.0


def test_posterior_update_reduces_entropy() -> None:
    rng = random.Random(13)
    items = build_items(40, seed=3)
    table = likelihood_table(items)
    posterior = uniform_posterior()
    true_params = PersonParams(d=1.5, bias=0.0)
    initial_entropy = entropy(posterior)
    for _ in range(30):
        index = select_next_item(items, posterior, table)
        result = simulate_trial(true_params, items[index].condition, rng)
        posterior = posterior_update(
            posterior,
            table[index],
            {"new": NEW, "imagined": IMAGINED, "described": DESCRIBED, "seen": SEEN}[result.choice],
        )
    assert entropy(posterior) < initial_entropy


def test_fixed_schedule_is_balanced() -> None:
    items = build_items(40, seed=5)
    schedule = fixed_schedule(items, 40, seed=9)
    counts = [sum(1 for item in schedule if item.condition == condition) for condition in range(4)]
    assert counts == [10, 10, 10, 10]


def test_allowed_conditions_reserves_the_coverage_floor() -> None:
    counts = [0, 0, 0, 0]
    assert allowed_conditions(0, counts, 20) == {0, 1, 2, 3}
    assert allowed_conditions(8, counts, 20) == {0}


def test_adaptive_simulation_is_deterministic() -> None:
    config = SimulationConfig(n_participants=8, n_trials=20, n_items=20, seed=17)
    first = run_simulation(config)
    second = run_simulation(config)
    assert first == second


def test_adaptive_simulation_respects_coverage() -> None:
    items = build_items(40, seed=4)
    table = likelihood_table(items)
    params = PersonParams(d=1.5, bias=0.0)
    result = _simulate_participant(
        SimulationConfig(n_participants=1, n_trials=20, n_items=40, seed=21),
        items,
        table,
        params,
        random.Random(21),
    )
    counts = {
        source: sum(1 for trial in result.trials if trial.source == source)
        for source in ("new", "imagined", "described", "seen")
    }
    assert all(count >= 3 for count in counts.values())


def test_check_simulation_passes_its_gate() -> None:
    report = check_simulation()
    assert report["decision"] == "PRM_STAGE0_SIMULATION_PASS"
    assert abs(report["recovery"]["bias"]) <= 0.15
    assert len(THETA_GRID) == 15


def test_compare_designs_reports_both_arms() -> None:
    comparison = compare_designs(
        SimulationConfig(n_participants=12, n_trials=30, n_items=20, seed=5)
    )
    assert comparison["adaptive"]["mean_final_entropy"] > 0.0
    assert comparison["fixed"]["mean_final_entropy"] > 0.0
    assert comparison["gate"] in {"PASS", "REVIEW"}
    assert "yoked" in comparison["note"]


def test_icc_is_one_for_identical_occasions() -> None:
    values = [0.1, -0.4, 0.7, 1.2, -1.0, 0.3, 0.9, -0.2]
    assert icc_2_1(values, values) == pytest.approx(1.0)


def test_power_gate_passes_at_the_planned_n() -> None:
    report = run_power(PowerConfig(n_participants=180, n_simulations=300, seed=7))
    assert report["decision"] == "PRM_STAGE0_POWER_PASS"
    target = next(item for item in report["scenarios"] if item["true_icc"] == 0.75)
    assert target["power"] >= 0.80
