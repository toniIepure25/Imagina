"""Tests for the Stage 0D model-signature tournament."""
from __future__ import annotations

import pytest

from app.research.crt.theory import (
    MODELS,
    SIGNATURE_NAMES,
    THEORY_SIGNATURES,
    TheoryConfig,
    check_theory,
    classify_signature,
    run_theory_tournament,
    signature_distance,
    signature_vector,
)

pytestmark = [pytest.mark.research, pytest.mark.simulation]


def test_every_model_has_a_complete_signature() -> None:
    assert set(THEORY_SIGNATURES) == set(MODELS)
    for model in MODELS:
        signature = signature_vector(model)
        assert len(signature) == len(SIGNATURE_NAMES)


def test_crt_and_eig_only_have_distinct_predictions() -> None:
    crt = dict(zip(SIGNATURE_NAMES, signature_vector("crt_meta_eig")))
    eig = dict(zip(SIGNATURE_NAMES, signature_vector("eig_only")))
    assert crt["prediction_advantage"] > eig["prediction_advantage"]
    assert crt["specificity_gain"] > eig["specificity_gain"]
    assert crt["prediction_error_update"] > eig["prediction_error_update"]


def test_noise_free_signatures_classify_to_their_model() -> None:
    for model in MODELS:
        assert classify_signature(signature_vector(model)) == model


def test_signature_distance_is_zero_for_exact_match() -> None:
    for model in MODELS:
        assert signature_distance(signature_vector(model), model) == pytest.approx(0.0)


def test_invalid_model_and_signature_length_are_rejected() -> None:
    with pytest.raises(ValueError):
        signature_vector("not-a-model")
    with pytest.raises(ValueError):
        classify_signature((0.0, 0.0))
    with pytest.raises(ValueError):
        TheoryConfig(n_observations=0)
    with pytest.raises(ValueError):
        TheoryConfig(noise_sd=-0.1)


def test_tournament_is_deterministic_and_reports_a_confusion_matrix() -> None:
    first = run_theory_tournament(TheoryConfig(n_observations=10, noise_sd=0.02, seed=11))
    second = run_theory_tournament(TheoryConfig(n_observations=10, noise_sd=0.02, seed=11))
    assert first == second
    assert set(first["confusion"]) == set(MODELS)
    for row in first["confusion"].values():
        assert sum(row.values()) == 10


def test_theory_gate_passes_for_separable_signatures() -> None:
    report = check_theory()
    assert report["decision"] == "CRT_STAGE0D_THEORY_PASS"
    assert report["balanced_accuracy"] >= report["config"]["recovery_threshold"]
