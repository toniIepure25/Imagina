from app.research.analysis_pipeline import (
    aggregate_by_condition,
    compute_cohens_d,
    compute_condition_means_by_session,
    lmm_specification,
    validate_iqi_pid_relationship,
)
from app.research.power_analysis import required_sample_size, sensitivity_table
from app.research.synthetic_data import (
    export_to_csv_rows,
    generate_synthetic_dataset,
)


class TestPowerAnalysis:
    def test_medium_effect_reasonable_n(self):
        result = required_sample_size(effect_size_d=0.50, power=0.80)
        assert result["n_per_sequence_with_dropout"] > 0
        assert result["n_per_sequence_with_dropout"] <= 100

    def test_larger_effect_needs_fewer(self):
        r_small = required_sample_size(effect_size_d=0.30)
        r_large = required_sample_size(effect_size_d=0.80)
        assert r_large["n_per_sequence_with_dropout"] < r_small["n_per_sequence_with_dropout"]

    def test_higher_power_needs_more(self):
        r_80 = required_sample_size(power=0.80)
        r_95 = required_sample_size(power=0.95)
        assert r_95["n_per_sequence_with_dropout"] >= r_80["n_per_sequence_with_dropout"]

    def test_dropout_increases_n(self):
        r_no_drop = required_sample_size(dropout_rate=0.0)
        r_drop = required_sample_size(dropout_rate=0.20)
        assert r_drop["n_per_sequence_with_dropout"] >= r_no_drop["n_per_sequence_with_dropout"]

    def test_output_fields(self):
        result = required_sample_size()
        assert "total_participants" in result
        assert "total_sessions" in result
        assert "method" in result
        assert "note" in result

    def test_sensitivity_table(self):
        table = sensitivity_table(n_values=[12, 24], effect_sizes=[0.40, 0.60])
        assert len(table) == 4
        for row in table:
            assert "n_target" in row
            assert "sufficient" in row
            assert isinstance(row["sufficient"], bool)


class TestSyntheticData:
    def test_generates_correct_structure(self):
        ds = generate_synthetic_dataset(n_participants=6, seed=42)
        assert "metadata" in ds
        assert "participants" in ds
        assert "trials" in ds
        assert len(ds["participants"]) == 6

    def test_trial_count(self):
        ds = generate_synthetic_dataset(
            n_participants=4,
            n_sessions_per_condition=2,
            trials_per_session=3,
        )
        expected = 4 * 3 * 2 * 3
        assert len(ds["trials"]) == expected

    def test_deterministic(self):
        ds1 = generate_synthetic_dataset(n_participants=4, seed=123)
        ds2 = generate_synthetic_dataset(n_participants=4, seed=123)
        assert ds1["trials"] == ds2["trials"]
        assert ds1["participants"] == ds2["participants"]

    def test_different_seeds_differ(self):
        ds1 = generate_synthetic_dataset(n_participants=4, seed=1)
        ds2 = generate_synthetic_dataset(n_participants=4, seed=2)
        assert ds1["trials"] != ds2["trials"]

    def test_vividness_in_range(self):
        ds = generate_synthetic_dataset(n_participants=10, seed=42)
        for t in ds["trials"]:
            assert 1 <= t["vividness"] <= 7
            assert 1 <= t["confidence"] <= 7
            assert 0.0 <= t["iqi"] <= 1.0
            assert 0.0 <= t["pid"] <= 1.0

    def test_adaptive_shows_improvement(self):
        ds = generate_synthetic_dataset(n_participants=30, seed=42)
        adaptive = [t for t in ds["trials"] if t["condition"] == "adaptive"]
        early = [t["vividness"] for t in adaptive if t["session_index"] == 0]
        late = [t["vividness"] for t in adaptive if t["session_index"] == 2]
        assert sum(late) / len(late) > sum(early) / len(early)

    def test_vviq_scores_in_range(self):
        ds = generate_synthetic_dataset(n_participants=10, seed=42)
        for p in ds["participants"]:
            assert 16 <= p["pre_vviq2"] <= 80
            assert 16 <= p["post_vviq2"] <= 80

    def test_export_csv_rows(self):
        ds = generate_synthetic_dataset(n_participants=4, seed=42)
        participants, trials = export_to_csv_rows(ds)
        assert len(participants) == 4
        assert len(trials) > 0


class TestAnalysisPipeline:
    def _make_dataset(self):
        return generate_synthetic_dataset(n_participants=12, seed=42)

    def test_aggregate_by_condition(self):
        ds = self._make_dataset()
        agg = aggregate_by_condition(ds["trials"])
        assert "adaptive" in agg
        assert "fixed" in agg
        assert "yoked" in agg
        for cond in agg.values():
            assert cond["n_trials"] > 0
            assert cond["n_participants"] > 0
            assert "vividness" in cond
            assert "iqi" in cond

    def test_condition_means_by_session(self):
        ds = self._make_dataset()
        means = compute_condition_means_by_session(ds["trials"])
        assert len(means) > 0
        for row in means:
            assert "participant_id" in row
            assert "condition" in row
            assert "session_index" in row
            assert "mean_vividness" in row

    def test_cohens_d_nonzero(self):
        g1 = [4.0, 5.0, 4.5, 5.5, 4.0]
        g2 = [3.0, 3.5, 3.0, 4.0, 3.5]
        d = compute_cohens_d(g1, g2)
        assert d > 0

    def test_cohens_d_zero_for_identical(self):
        g = [4.0, 4.0, 4.0, 4.0]
        d = compute_cohens_d(g, g)
        assert d == 0.0

    def test_iqi_pid_inverse_relationship(self):
        ds = self._make_dataset()
        result = validate_iqi_pid_relationship(ds["trials"])
        assert "pearson_r" in result
        assert result["expected_negative"] is True
        assert result["n_trials"] > 0

    def test_lmm_specification(self):
        spec = lmm_specification()
        assert spec["model_family"] == "Linear Mixed-Effects Model (LMM)"
        assert len(spec["dependent_variables"]) >= 3
        assert len(spec["fixed_effects"]) >= 3
        assert len(spec["random_effects"]) >= 1
        assert len(spec["contrasts"]) >= 3
