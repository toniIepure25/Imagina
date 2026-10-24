from app.research.multimodal_evaluation import (
    compute_convergent_validity,
    compute_incremental_validity_summary,
    compute_modality_baselines,
    group_aware_evaluation,
)
from app.research.synthetic_data import generate_synthetic_dataset


def _make_dataset():
    return generate_synthetic_dataset(n_participants=18, seed=42)


class TestModalityBaselines:
    def test_all_modalities_present(self):
        ds = _make_dataset()
        baselines = compute_modality_baselines(ds["trials"])
        assert "self_report" in baselines
        assert "behavioral" in baselines
        assert "proxy_metric" in baselines

    def test_self_report_variables(self):
        ds = _make_dataset()
        baselines = compute_modality_baselines(ds["trials"])
        sr = baselines["self_report"]["variables"]
        assert "vividness" in sr
        assert "confidence" in sr
        assert sr["vividness"]["n"] > 0

    def test_proxy_variables(self):
        ds = _make_dataset()
        baselines = compute_modality_baselines(ds["trials"])
        proxy = baselines["proxy_metric"]["variables"]
        assert "iqi" in proxy
        assert "pid" in proxy


class TestConvergentValidity:
    def test_correlation_structure(self):
        ds = _make_dataset()
        cv = compute_convergent_validity(ds["trials"])
        assert "correlations" in cv
        assert "expected_directions" in cv
        assert cv["n_trials"] > 0

    def test_iqi_pid_negative(self):
        ds = _make_dataset()
        cv = compute_convergent_validity(ds["trials"])
        r_iqi_pid = cv["correlations"]["iqi_pid"]["r"]
        assert r_iqi_pid < 0

    def test_vividness_confidence_positive(self):
        ds = _make_dataset()
        cv = compute_convergent_validity(ds["trials"])
        r = cv["correlations"]["vividness_confidence"]["r"]
        assert r > 0

    def test_expected_directions_documented(self):
        ds = _make_dataset()
        cv = compute_convergent_validity(ds["trials"])
        assert cv["expected_directions"]["vividness_pid"] == "negative"
        assert cv["expected_directions"]["vividness_iqi"] == "positive"


class TestIncrementalValidity:
    def test_summary_structure(self):
        ds = _make_dataset()
        summary = compute_incremental_validity_summary(ds["trials"])
        assert "incremental_validity_specification" in summary
        assert summary["n_trials"] > 0
        assert summary["n_conditions"] == 3

    def test_condition_improvements(self):
        ds = _make_dataset()
        summary = compute_incremental_validity_summary(ds["trials"])
        improvements = summary["condition_improvements"]
        assert "adaptive" in improvements
        assert improvements["adaptive"]["improvement"] > 0

    def test_specification_steps(self):
        ds = _make_dataset()
        summary = compute_incremental_validity_summary(ds["trials"])
        spec = summary["incremental_validity_specification"]
        assert "step_1" in spec
        assert "step_2" in spec
        assert "step_3" in spec


class TestGroupAwareEvaluation:
    def test_median_split(self):
        ds = _make_dataset()
        result = group_aware_evaluation(ds["trials"], ds["participants"])
        assert result["n_low_imagers"] > 0
        assert result["n_high_imagers"] > 0
        assert result["n_low_imagers"] + result["n_high_imagers"] == len(ds["participants"])

    def test_high_imagers_higher_vividness(self):
        ds = _make_dataset()
        result = group_aware_evaluation(ds["trials"], ds["participants"])
        assert result["high_imagers"]["mean_vividness"] >= result["low_imagers"]["mean_vividness"]

    def test_note_present(self):
        ds = _make_dataset()
        result = group_aware_evaluation(ds["trials"], ds["participants"])
        assert "covariate" in result["note"].lower()
