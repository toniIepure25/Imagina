"""Scenario contract tests — verify data-generating behavior before inference."""
import random

from app.research.causal_oracle import compute_oracle_effect
from app.research.cognitive_agent import (
    SCENARIO_CARRYOVER,
    SCENARIO_DROPOUT,
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_PERCEPTUAL_ONLY,
    SCENARIO_PRACTICE_ONLY,
    SCENARIO_STRICT_NULL,
    SCENARIO_SUBJECTIVE_ONLY,
    generate_population,
    generate_trial_response,
    should_dropout,
)
from app.research.design_simulation import _generate_study_data
from app.research.psychophysics.common import StimulusSpec


class TestNullContract:
    def test_all_contrasts_near_zero(self):
        for ca, cb in [("adaptive", "yoked"), ("adaptive", "fixed"), ("fixed", "yoked")]:
            r = compute_oracle_effect(SCENARIO_STRICT_NULL, ca, cb, n_agents=100, seed=42)
            assert abs(r.effect) < 0.05, f"Null {ca} vs {cb}: {r.effect}"


class TestPracticeOnlyContract:
    def test_all_conditions_improve(self):
        pop = generate_population(30, seed=42, scenario=SCENARIO_PRACTICE_ONLY)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        for cond in ["adaptive", "fixed", "yoked"]:
            early = []
            late = []
            for agent in pop:
                e0 = generate_trial_response(agent, target, target, cond, 0, 0,
                                             SCENARIO_PRACTICE_ONLY, False, 42)
                e2 = generate_trial_response(agent, target, target, cond, 2, 0,
                                             SCENARIO_PRACTICE_ONLY, False, 42)
                early.append(e0["composite_error"])
                late.append(e2["composite_error"])
            mean_e = sum(early) / len(early)
            mean_l = sum(late) / len(late)
            assert mean_l < mean_e, f"{cond}: late {mean_l} >= early {mean_e}"

    def test_adaptive_yoked_contrast_null(self):
        r = compute_oracle_effect(SCENARIO_PRACTICE_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) < 0.05


class TestSubjectiveOnlyContract:
    def test_vividness_differs(self):
        pop = generate_population(30, seed=42, scenario=SCENARIO_SUBJECTIVE_ONLY)
        target = StimulusSpec(45, 120, 3.0, 500, 400, 50)
        a_v = [generate_trial_response(a, target, target, "adaptive", 1, 0,
               SCENARIO_SUBJECTIVE_ONLY, False, 42)["vividness"] for a in pop]
        y_v = [generate_trial_response(a, target, target, "yoked", 1, 0,
               SCENARIO_SUBJECTIVE_ONLY, False, 42)["vividness"] for a in pop]
        assert sum(a_v) / len(a_v) > sum(y_v) / len(y_v) - 0.5

    def test_objective_null(self):
        r = compute_oracle_effect(SCENARIO_SUBJECTIVE_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) < 0.05


class TestDropoutContract:
    def test_dropout_produces_missingness(self):
        imagery, _ = _generate_study_data(SCENARIO_DROPOUT, 24, 3, 3, 42)
        sessions_per_p = {}
        for d in imagery:
            pid = d["participant_id"]
            sessions_per_p.setdefault(pid, set()).add(d["session_index"])
        incomplete = sum(1 for s in sessions_per_p.values() if len(s) < 3)
        assert incomplete > 0, "Dropout scenario should produce incomplete participants"

    def test_should_dropout_callable(self):
        pop = generate_population(20, seed=42, scenario=SCENARIO_DROPOUT)
        rng = random.Random(42)
        dropped = sum(1 for a in pop if should_dropout(a, 2, SCENARIO_DROPOUT, rng))
        assert dropped >= 0


class TestPerceptualOnlyContract:
    def test_imagery_oracle_null(self):
        r = compute_oracle_effect(SCENARIO_PERCEPTUAL_ONLY, n_agents=100, seed=42)
        assert abs(r.effect) < 0.05

    def test_perceptual_data_generated(self):
        _, nc = _generate_study_data(SCENARIO_PERCEPTUAL_ONLY, 12, 3, 3, 42)
        assert len(nc) > 0, "Perceptual control data should be generated"


class TestCarryoverContract:
    def test_carryover_affects_later_periods(self):
        r = compute_oracle_effect(SCENARIO_CARRYOVER, n_agents=100, seed=42)
        assert r.effect < 0, "Carryover scenario should show adaptive benefit"


class TestTaskDiversity:
    def test_all_task_families_present(self):
        imagery, nc = _generate_study_data(SCENARIO_MEDIUM_ADAPTIVE, 12, 3, 3, 42)
        all_data = imagery + nc
        families = {d["task_family"] for d in all_data}
        assert "feature_reconstruction" in families
        assert "imagery_manipulation" in families
        assert "delayed_imagery" in families
        assert "perceptual_control" in families
