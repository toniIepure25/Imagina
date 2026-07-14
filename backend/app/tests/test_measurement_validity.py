"""Tests for measurement reliability and construct-validity diagnostics."""

from app.research.measurement_validity import (
    compute_test_retest,
    convergent_validity,
    known_groups_discrimination,
    run_validity_diagnostics,
    split_half_reliability,
    within_person_measurement_error,
)


class TestReliability:
    def test_split_half_perfect(self):
        scores = [float(i) for i in range(20)]
        result = split_half_reliability(scores)
        assert result["spearman_brown"] > 0.8

    def test_split_half_random(self):
        import random
        rng = random.Random(42)
        scores = [rng.random() for _ in range(100)]
        result = split_half_reliability(scores)
        assert -0.5 < result["raw_r"] < 0.5

    def test_split_half_too_few(self):
        result = split_half_reliability([1.0, 2.0])
        assert result["raw_r"] == 0.0

    def test_test_retest(self):
        block1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        block2 = [1.1, 2.1, 3.0, 3.9, 5.1]
        result = compute_test_retest(block1, block2)
        assert result["r"] > 0.9

    def test_within_person_error(self):
        scores = {
            "P001": [0.3, 0.35, 0.32],
            "P002": [0.5, 0.55, 0.48],
        }
        result = within_person_measurement_error(scores)
        assert result["mean_within_sd"] > 0
        assert result["n_participants"] == 2


class TestValidity:
    def test_convergent_correlation(self):
        observed = [1.0, 2.0, 3.0, 4.0, 5.0]
        latent = [1.1, 1.9, 3.1, 4.0, 5.2]
        result = convergent_validity(observed, latent, "test")
        assert result["r"] > 0.9

    def test_known_groups_distinguishes(self):
        high = [0.2, 0.3, 0.25, 0.22, 0.28]
        low = [0.7, 0.8, 0.75, 0.72, 0.78]
        result = known_groups_discrimination(high, low, "test")
        assert abs(result["cohens_d"]) > 1.0


class TestFullDiagnostics:
    def test_diagnostics_run(self):
        results = run_validity_diagnostics(n_participants=20, n_trials=10, seed=42)
        assert "split_half" in results
        assert "test_retest" in results
        assert "convergent_precision" in results
        assert "known_groups_precision" in results
        assert "perceptual_control_baseline" in results
        assert results["version"] == "1.0"

    def test_precision_correlates_with_latent(self):
        results = run_validity_diagnostics(n_participants=50, n_trials=15, seed=42)
        r = results["convergent_precision"]["r"]
        assert r < -0.2 or r > 0.2, f"Expected meaningful correlation, got r={r}"

    def test_known_groups_nonzero_effect(self):
        results = run_validity_diagnostics(n_participants=50, n_trials=15, seed=42)
        d = results["known_groups_precision"]["cohens_d"]
        assert abs(d) > 0.2, f"Expected nonzero known-groups effect, got d={d}"
