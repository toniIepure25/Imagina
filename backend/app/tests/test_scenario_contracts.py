"""Scenario contract tests — verify the data-generating process
before running any statistical analysis.

Each test verifies that the causal mechanism behaves as documented.
Under strict null, adaptive/fixed/yoked potential outcomes must be
EXACTLY equal (same RNG stream, same code path except condition label).
"""
import random

from app.research.causal_oracle import compute_oracle_effect
from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_DROPOUT,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PLACEBO_EXPECTANCY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_SMALL_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
    generate_population,
    generate_trial_response,
    should_dropout,
)
from app.research.design_simulation import _generate_study_data
from app.research.psychophysics.common import StimulusSpec
from app.research.rng_registry import derive_seed

FP_TOLERANCE = 1e-12
ORACLE_NUMERICAL_TOLERANCE = 1e-10
TARGET = StimulusSpec(45, 120, 3.0, 500, 400, 50)
N_AGENTS = 30
SEED = 42


def _individual_potential_outcomes(scenario, agent, session_index, trial_index):
    """Generate potential outcomes for all three conditions using CRN."""
    trial_seed = derive_seed(SEED, "contract_test",
                             participant_id=agent.participant_id,
                             session_index=session_index,
                             trial_index=trial_index)
    outcomes = {}
    for cond in ["adaptive", "fixed", "yoked"]:
        outcomes[cond] = generate_trial_response(
            agent, TARGET, TARGET, cond, session_index, trial_index,
            scenario, False, trial_seed, prev_condition=None,
        )
    return outcomes


class TestStrictNullContract:
    """Under strict null, all conditions must produce identical potential outcomes."""

    def test_individual_potential_outcomes_identical(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_STRICT_NULL)
        for agent in pop:
            for si in range(3):
                for ti in range(5):
                    pos = _individual_potential_outcomes(SCENARIO_STRICT_NULL, agent, si, ti)
                    for field in ["composite_error", "effective_precision"]:
                        a_val = pos["adaptive"][field]
                        f_val = pos["fixed"][field]
                        y_val = pos["yoked"][field]
                        assert a_val == f_val, (
                            f"Strict null violated: adaptive {field}={a_val} != fixed {field}={f_val} "
                            f"for {agent.participant_id} s={si} t={ti}"
                        )
                        assert a_val == y_val, (
                            f"Strict null violated: adaptive {field}={a_val} != yoked {field}={y_val} "
                            f"for {agent.participant_id} s={si} t={ti}"
                        )

    def test_oracle_effect_numerically_zero(self):
        for ca, cb in [("adaptive", "yoked"), ("adaptive", "fixed"), ("fixed", "yoked")]:
            r = compute_oracle_effect(SCENARIO_STRICT_NULL, ca, cb, n_agents=200, seed=SEED)
            assert abs(r.effect) <= ORACLE_NUMERICAL_TOLERANCE, (
                f"Strict null oracle {ca} vs {cb} = {r.effect}, expected 0"
            )

    def test_oracle_se_zero_under_exact_null(self):
        r = compute_oracle_effect(SCENARIO_STRICT_NULL, n_agents=200, seed=SEED)
        assert abs(r.effect_se) <= ORACLE_NUMERICAL_TOLERANCE, (
            f"Strict null SE = {r.effect_se}, expected 0 with exact PO equality"
        )

    def test_no_scenario_parameters_active(self):
        s = SCENARIO_STRICT_NULL
        assert s.adaptive_precision_effect == 0.0
        assert s.adaptive_control_effect == 0.0
        assert s.adaptive_stability_effect == 0.0
        assert s.adaptive_learning_boost == 0.0
        assert s.adaptive_fatigue_regulation == 0.0
        assert s.fixed_practice_effect == 0.0
        assert s.yoked_practice_effect == 0.0
        assert s.placebo_effect == 0.0
        assert s.objective_expectancy_effect == 0.0
        assert s.expectancy_vividness_effect == 0.0
        assert s.period_effect_strength == 0.0
        assert s.carryover_strength == 0.0
        assert s.dropout_rate == 0.0
        assert s.perceptual_control_improvement == 0.0


class TestSubjectiveOnlyContract:
    """Subjective-only: vividness differs, objective POs are identical."""

    def test_objective_potential_outcomes_identical(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_SUBJECTIVE_ONLY)
        for agent in pop[:10]:
            for si in range(3):
                pos = _individual_potential_outcomes(SCENARIO_SUBJECTIVE_ONLY, agent, si, 0)
                a_err = pos["adaptive"]["composite_error"]
                y_err = pos["yoked"]["composite_error"]
                assert a_err == y_err, (
                    f"Subjective-only objective leak: adaptive={a_err} != yoked={y_err}"
                )

    def test_oracle_objective_zero(self):
        r = compute_oracle_effect(SCENARIO_SUBJECTIVE_ONLY, n_agents=200, seed=SEED)
        assert abs(r.effect) <= ORACLE_NUMERICAL_TOLERANCE, (
            f"Subjective-only oracle effect = {r.effect}, expected ~0"
        )

    def test_vividness_differs_by_condition(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_SUBJECTIVE_ONLY)
        a_vivid = []
        y_vivid = []
        for agent in pop:
            trial_seed = derive_seed(SEED, "vividness_test", participant_id=agent.participant_id)
            ra = generate_trial_response(agent, TARGET, TARGET, "adaptive", 1, 0,
                                         SCENARIO_SUBJECTIVE_ONLY, False, trial_seed)
            ry = generate_trial_response(agent, TARGET, TARGET, "yoked", 1, 0,
                                         SCENARIO_SUBJECTIVE_ONLY, False, trial_seed)
            a_vivid.append(ra["vividness"])
            y_vivid.append(ry["vividness"])
        assert sum(a_vivid) / len(a_vivid) > sum(y_vivid) / len(y_vivid), (
            "Subjective-only: adaptive vividness should exceed yoked"
        )


class TestPlaceboOnlyContract:
    """Placebo-only: self-report affected, objective POs identical."""

    def test_objective_potential_outcomes_identical(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_PLACEBO_EXPECTANCY)
        for agent in pop[:10]:
            pos = _individual_potential_outcomes(SCENARIO_PLACEBO_EXPECTANCY, agent, 1, 0)
            a_err = pos["adaptive"]["composite_error"]
            y_err = pos["yoked"]["composite_error"]
            assert a_err == y_err, (
                f"Placebo objective leak: adaptive={a_err} != yoked={y_err}"
            )

    def test_oracle_objective_zero(self):
        r = compute_oracle_effect(SCENARIO_PLACEBO_EXPECTANCY, n_agents=200, seed=SEED)
        assert abs(r.effect) <= ORACLE_NUMERICAL_TOLERANCE


class TestPracticeOnlyContract:
    """Practice-only: session effect present, no adaptive-yoked causal effect."""

    def test_all_conditions_improve_with_session(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_PRACTICE_ONLY)
        for cond in ["adaptive", "fixed", "yoked"]:
            early = []
            late = []
            for agent in pop:
                seed_e = derive_seed(SEED, "practice_test", participant_id=agent.participant_id, session_index=0)
                seed_l = derive_seed(SEED, "practice_test", participant_id=agent.participant_id, session_index=2)
                e0 = generate_trial_response(agent, TARGET, TARGET, cond, 0, 0,
                                             SCENARIO_PRACTICE_ONLY, False, seed_e)
                e2 = generate_trial_response(agent, TARGET, TARGET, cond, 2, 0,
                                             SCENARIO_PRACTICE_ONLY, False, seed_l)
                early.append(e0["composite_error"])
                late.append(e2["composite_error"])
            assert sum(late) / len(late) < sum(early) / len(early), (
                f"{cond}: later sessions should have lower error"
            )

    def test_adaptive_yoked_potential_outcomes_identical(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_PRACTICE_ONLY)
        for agent in pop[:10]:
            pos = _individual_potential_outcomes(SCENARIO_PRACTICE_ONLY, agent, 1, 0)
            a_err = pos["adaptive"]["composite_error"]
            y_err = pos["yoked"]["composite_error"]
            assert a_err == y_err, (
                f"Practice-only: adaptive={a_err} != yoked={y_err}"
            )

    def test_oracle_treatment_zero(self):
        r = compute_oracle_effect(SCENARIO_PRACTICE_ONLY, n_agents=200, seed=SEED)
        assert abs(r.effect) <= ORACLE_NUMERICAL_TOLERANCE


class TestPerceptualOnlyContract:
    """Perceptual-only: imagery unchanged, motor/perceptual improves."""

    def test_imagery_oracle_zero(self):
        r = compute_oracle_effect(SCENARIO_PERCEPTUAL_ONLY, n_agents=200, seed=SEED)
        assert abs(r.effect) <= ORACLE_NUMERICAL_TOLERANCE

    def test_imagery_potential_outcomes_identical(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_PERCEPTUAL_ONLY)
        for agent in pop[:10]:
            pos = _individual_potential_outcomes(SCENARIO_PERCEPTUAL_ONLY, agent, 1, 0)
            assert pos["adaptive"]["composite_error"] == pos["yoked"]["composite_error"]

    def test_perceptual_data_generated(self):
        _, nc = _generate_study_data(SCENARIO_PERCEPTUAL_ONLY, 12, 3, 3, SEED)
        assert len(nc) > 0


class TestCarryoverContract:
    """Carryover: adaptive effects persist into later conditions."""

    def test_carryover_produces_treatment_effect(self):
        r = compute_oracle_effect(SCENARIO_CARRYOVER, n_agents=200, seed=SEED)
        assert r.effect < 0, (
            f"Carryover scenario should show adaptive benefit (lower error), got {r.effect}"
        )

    def test_carryover_affects_later_periods(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_CARRYOVER)
        agent = pop[0]
        trial_seed = derive_seed(SEED, "carryover_test", participant_id=agent.participant_id)
        r_no_carry = generate_trial_response(
            agent, TARGET, TARGET, "yoked", 1, 0,
            SCENARIO_CARRYOVER, False, trial_seed, prev_condition="fixed")
        r_carry = generate_trial_response(
            agent, TARGET, TARGET, "yoked", 1, 0,
            SCENARIO_CARRYOVER, False, trial_seed, prev_condition="adaptive")
        assert r_no_carry["composite_error"] != r_carry["composite_error"], (
            "Carryover from adaptive should change yoked outcome"
        )


class TestDropoutContract:
    """Differential dropout produces missingness biased toward low performers."""

    def test_produces_missingness(self):
        imagery, _ = _generate_study_data(SCENARIO_DROPOUT, 24, 3, 3, SEED)
        sessions_per_p = {}
        for d in imagery:
            sessions_per_p.setdefault(d["participant_id"], set()).add(d["session_index"])
        incomplete = sum(1 for s in sessions_per_p.values() if len(s) < 3)
        assert incomplete > 0

    def test_low_performers_more_likely_to_drop(self):
        pop = generate_population(200, seed=SEED, scenario=SCENARIO_DROPOUT)
        low = [a for a in pop if a.baseline_imagery_precision < 0.4]
        high = [a for a in pop if a.baseline_imagery_precision > 0.7]
        if len(low) < 5 or len(high) < 5:
            return
        low_drops = sum(
            1 for a in low
            if should_dropout(a, 2, SCENARIO_DROPOUT, random.Random(
                derive_seed(SEED, "dropout_test", participant_id=a.participant_id)))
        )
        high_drops = sum(
            1 for a in high
            if should_dropout(a, 2, SCENARIO_DROPOUT, random.Random(
                derive_seed(SEED, "dropout_test", participant_id=a.participant_id)))
        )
        assert low_drops / len(low) >= high_drops / len(high), (
            "Low performers should drop out more"
        )


class TestSmallAdaptiveContract:
    """Small adaptive: genuine causal effect (lower error for adaptive)."""

    def test_oracle_negative(self):
        r = compute_oracle_effect(SCENARIO_SMALL_ADAPTIVE, n_agents=200, seed=SEED)
        assert r.effect < 0, f"Small adaptive effect should be negative (lower error), got {r.effect}"

    def test_individual_po_differ(self):
        pop = generate_population(N_AGENTS, seed=SEED, scenario=SCENARIO_SMALL_ADAPTIVE)
        diffs = []
        for agent in pop:
            pos = _individual_potential_outcomes(SCENARIO_SMALL_ADAPTIVE, agent, 2, 0)
            diffs.append(pos["adaptive"]["composite_error"] - pos["yoked"]["composite_error"])
        mean_diff = sum(diffs) / len(diffs)
        assert mean_diff < 0, f"Expected negative mean PO difference, got {mean_diff}"


class TestMediumAdaptiveContract:
    """Medium adaptive: larger causal effect than small."""

    def test_oracle_negative_and_larger_than_small(self):
        small = compute_oracle_effect(SCENARIO_SMALL_ADAPTIVE, n_agents=200, seed=SEED)
        medium = compute_oracle_effect(SCENARIO_MEDIUM_ADAPTIVE, n_agents=200, seed=SEED)
        assert medium.effect < 0
        assert medium.effect < small.effect, (
            f"Medium ({medium.effect}) should be more negative than small ({small.effect})"
        )


class TestScenarioIsolation:
    """Scenarios with no objective adaptive effect must have exact null POs."""

    def test_all_null_objective_scenarios(self):
        null_objective_scenarios = [
            SCENARIO_STRICT_NULL,
            SCENARIO_SUBJECTIVE_ONLY,
            SCENARIO_PLACEBO_EXPECTANCY,
            SCENARIO_PRACTICE_ONLY,
            SCENARIO_PERCEPTUAL_ONLY,
        ]
        for scenario in null_objective_scenarios:
            pop = generate_population(10, seed=SEED, scenario=scenario)
            for agent in pop[:3]:
                pos = _individual_potential_outcomes(scenario, agent, 1, 0)
                a_err = pos["adaptive"]["composite_error"]
                y_err = pos["yoked"]["composite_error"]
                f_err = pos["fixed"]["composite_error"]
                assert a_err == f_err == y_err, (
                    f"Scenario {scenario.scenario_id}: POs not identical "
                    f"(a={a_err}, f={f_err}, y={y_err})"
                )


class TestTaskDiversity:
    def test_all_families_present(self):
        imagery, nc = _generate_study_data(SCENARIO_MEDIUM_ADAPTIVE, 12, 3, 3, SEED)
        families = {d["task_family"] for d in imagery + nc}
        for tf in ["feature_reconstruction", "imagery_manipulation", "delayed_imagery", "perceptual_control"]:
            assert tf in families, f"Missing task family: {tf}"
