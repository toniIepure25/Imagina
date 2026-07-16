"""Tests for perception-imagery representation transfer (RSA, CKA, cross-
state retrieval, temporal generalization, subject-level summaries)."""
import numpy as np
import pytest

from app.research.neural.alignment import (
    SubjectAlignmentSummary,
    chance_retrieval_accuracy,
    cross_state_retrieval_accuracy,
    linear_cka,
    representational_dissimilarity_matrix,
    rsa,
    summarize_alignment_across_subjects,
    temporal_generalization_matrix,
)


class TestRSA:
    def test_identical_embeddings_give_rsa_of_one(self):
        rng = np.random.RandomState(0)
        emb = rng.randn(10, 6)
        assert rsa(emb, emb) == pytest.approx(1.0, abs=1e-9)

    def test_too_few_items_returns_nan(self):
        emb = np.random.RandomState(0).randn(2, 6)
        assert np.isnan(rsa(emb, emb))

    def test_mismatched_item_counts_returns_nan(self):
        a = np.random.RandomState(0).randn(5, 6)
        b = np.random.RandomState(1).randn(6, 6)
        assert np.isnan(rsa(a, b))

    def test_rdm_diagonal_is_zero(self):
        emb = np.random.RandomState(0).randn(5, 4)
        rdm = representational_dissimilarity_matrix(emb)
        assert np.allclose(np.diag(rdm), 0.0, atol=1e-9)


class TestCKA:
    def test_identical_representations_give_cka_of_one(self):
        rng = np.random.RandomState(0)
        x = rng.randn(20, 8)
        assert linear_cka(x, x) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_random_representations_give_low_cka(self):
        rng = np.random.RandomState(0)
        x = rng.randn(50, 8)
        y = rng.randn(50, 8)
        # not guaranteed exactly 0, but should be well below the self-similarity value
        assert linear_cka(x, y) < 0.9

    def test_cka_invariant_to_orthogonal_rotation(self):
        rng = np.random.RandomState(0)
        x = rng.randn(30, 5)
        rotation, _ = np.linalg.qr(rng.randn(5, 5))
        y = x @ rotation
        assert linear_cka(x, y) == pytest.approx(1.0, abs=1e-6)


class TestCrossStateRetrieval:
    def test_perfect_retrieval_for_near_identical_embeddings(self):
        rng = np.random.RandomState(0)
        percep = rng.randn(5, 8)
        ids = ["a", "b", "c", "d", "e"]
        imagery = percep + rng.randn(5, 8) * 0.001
        acc = cross_state_retrieval_accuracy(percep, ids, imagery, ids)
        assert acc == 1.0

    def test_chance_level_uses_unique_stimulus_count(self):
        assert chance_retrieval_accuracy(["a", "b", "c", "d"]) == pytest.approx(0.25)
        assert chance_retrieval_accuracy(["a", "a", "a"]) == pytest.approx(1.0)

    def test_empty_inputs_return_nan(self):
        assert np.isnan(cross_state_retrieval_accuracy(np.zeros((0, 4)), [], np.zeros((0, 4)), []))


class TestTemporalGeneralization:
    def test_diagonal_accuracy_high_for_discriminable_window(self):
        rng = np.random.RandomState(0)
        n, ch, t = 40, 4, 50
        sfreq = 100.0
        labels = np.arange(n) % 2
        epochs = rng.randn(n, ch, t) * 0.05
        for i in range(n):
            if labels[i] == 1:
                epochs[i, :, 20:30] += 3.0
        result = temporal_generalization_matrix(epochs, labels, sfreq, window_s=0.1, step_s=0.1)
        # the window covering samples 20-30 (index 2 at step=10 samples) must
        # separate its own labels well above chance.
        assert result.accuracy_matrix[2, 2] > 0.9

    def test_returns_zero_matrix_with_single_class(self):
        epochs = np.random.RandomState(0).randn(10, 2, 20)
        labels = np.zeros(10)
        result = temporal_generalization_matrix(epochs, labels, sfreq=100.0)
        assert np.all(result.accuracy_matrix == 0.0)

    def test_to_dict_is_json_serializable(self):
        import json
        epochs = np.random.RandomState(0).randn(10, 2, 20)
        labels = np.arange(10) % 2
        result = temporal_generalization_matrix(epochs, labels, sfreq=100.0)
        json.dumps(result.to_dict())


class TestSubjectLevelSummary:
    def test_participant_is_the_unit_not_trials(self):
        summaries = [
            SubjectAlignmentSummary("sub-01", rsa_perception_imagery=0.5, cka_perception_imagery=0.6,
                                     cross_state_retrieval_accuracy=0.4, chance_retrieval_accuracy=0.2),
            SubjectAlignmentSummary("sub-02", rsa_perception_imagery=0.3, cka_perception_imagery=0.4,
                                     cross_state_retrieval_accuracy=0.3, chance_retrieval_accuracy=0.2),
        ]
        agg = summarize_alignment_across_subjects(summaries)
        assert agg["n_participants"] == 2
        assert agg["retrieval_accuracy_mean"] == pytest.approx(0.35)
        assert len(agg["per_participant"]) == 2

    def test_empty_summaries_reports_zero_participants(self):
        agg = summarize_alignment_across_subjects([])
        assert agg == {"n_participants": 0}

    def test_nan_rsa_values_excluded_from_mean(self):
        summaries = [
            SubjectAlignmentSummary("sub-01", rsa_perception_imagery=float("nan"), cka_perception_imagery=0.5,
                                     cross_state_retrieval_accuracy=0.3, chance_retrieval_accuracy=0.2),
            SubjectAlignmentSummary("sub-02", rsa_perception_imagery=0.6, cka_perception_imagery=0.5,
                                     cross_state_retrieval_accuracy=0.3, chance_retrieval_accuracy=0.2),
        ]
        agg = summarize_alignment_across_subjects(summaries)
        assert agg["rsa_mean"] == pytest.approx(0.6)
