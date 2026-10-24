"""Tests for frozen crossover design."""
from app.research.crossover_design import (
    design_hash,
    freeze_design,
    validate_design_balance,
)


class TestFreezeDesign:
    def test_deterministic(self):
        d1 = freeze_design(n_participants=12, seed=42)
        d2 = freeze_design(n_participants=12, seed=42)
        assert design_hash(d1) == design_hash(d2)

    def test_session_count(self):
        d = freeze_design(n_participants=12, n_sessions=3, seed=42)
        assert len(d.sessions) == 12 * 3

    def test_all_conditions_present(self):
        d = freeze_design(n_participants=12, seed=42)
        conditions = {s.condition for s in d.sessions}
        assert conditions == {"adaptive", "fixed", "yoked"}

    def test_all_task_families_present(self):
        d = freeze_design(n_participants=6, trials_per_task=3, seed=42)
        families = set()
        for s in d.sessions:
            for t in s.trials + s.negative_control_trials:
                families.add(t.task_family)
        assert "feature_reconstruction" in families
        assert "imagery_manipulation" in families
        assert "delayed_imagery" in families
        assert "perceptual_control" in families

    def test_negative_control_separation(self):
        d = freeze_design(n_participants=6, trials_per_task=3, seed=42)
        for s in d.sessions:
            for t in s.trials:
                assert not t.is_perceptual_control
            for t in s.negative_control_trials:
                assert t.is_perceptual_control


class TestDesignBalance:
    def test_balanced(self):
        d = freeze_design(n_participants=18, seed=42)
        result = validate_design_balance(d)
        assert result["balanced"]

    def test_condition_balance(self):
        d = freeze_design(n_participants=18, seed=42)
        result = validate_design_balance(d)
        cond = result["condition_balance"]
        assert cond["adaptive"] == cond["fixed"] == cond["yoked"]

    def test_period_balance(self):
        d = freeze_design(n_participants=18, seed=42)
        result = validate_design_balance(d)
        period = result["period_balance"]
        assert period[0] == period[1] == period[2]


class TestDesignHash:
    def test_different_seed(self):
        d1 = freeze_design(n_participants=6, seed=42)
        d2 = freeze_design(n_participants=6, seed=99)
        assert design_hash(d1) != design_hash(d2)

    def test_different_n(self):
        d1 = freeze_design(n_participants=6, seed=42)
        d2 = freeze_design(n_participants=12, seed=42)
        assert design_hash(d1) != design_hash(d2)
