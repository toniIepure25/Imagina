"""Replay-determinism and export-serializability tests for C1 (Commit 8 CI:
c1-replay-export).

Mirrors the replay-fail-closed / provenance-complete-export convention
established in Scientific Gate C0.2, adapted to C1's offline research
artifacts (no live API replay endpoint exists for the neural pipeline):
re-running the exact same estimation code against identical synthetic
input must reproduce bit-identical results (replay), and every result
object the real confirmatory run persists to JSON must round-trip through
`json.dumps`/`json.loads` without loss and carry the fields the frozen
result-artifact schema (`C1_ANALYSIS_SPEC.md` Section 10) requires.
"""
from __future__ import annotations

import json

import numpy as np

from app.research.neural.models import participant_grouped_split
from app.research.neural.nested_validation import (
    TrialRecord,
    add_lagged_prior_vividness,
    estimate_primary_endpoint,
    run_loso_nested_validation,
    run_single_loso_fold,
)


def _make_records(n_participants=6, n_trials=20, seed=0, signal_strength=1.5):
    rng = np.random.RandomState(seed)
    records = []
    for p in range(n_participants):
        pid = f"p{p}"
        for t in range(n_trials):
            modality = ["visual", "auditory", "mix"][t % 3]
            neural = rng.randn(3)
            latent = neural[0] * signal_strength + rng.randn() * 0.5
            bins = [-1.0, -0.3, 0.3, 1.0]
            vividness = float(np.clip(np.digitize(latent, bins) + 1, 1, 5))
            records.append(TrialRecord(pid, "1", t, modality, None, vividness, neural))
    return add_lagged_prior_vividness(records)


class TestSingleFoldReplayDeterminism:
    def test_identical_input_gives_identical_fold_result(self):
        records = _make_records(n_participants=6, n_trials=20)
        train_mask, test_mask = participant_grouped_split(
            [r.participant_id for r in records], held_out="p0",
        )
        train = [r for r, m in zip(records, train_mask) if m]
        test = [r for r, m in zip(records, test_mask) if m]

        result_a = run_single_loso_fold(train, test, "p0")
        result_b = run_single_loso_fold(train, test, "p0")

        assert result_a.chosen_l2 == result_b.chosen_l2
        assert result_a.behavior_plus_neural_checkpoint_hash == result_b.behavior_plus_neural_checkpoint_hash
        assert result_a.behavior_only_log_score == result_b.behavior_only_log_score
        assert result_a.behavior_plus_neural_log_score == result_b.behavior_plus_neural_log_score
        assert result_a.delta_oos == result_b.delta_oos


class TestFullLosoReplayDeterminism:
    def test_identical_input_gives_identical_primary_estimand(self):
        records = _make_records(n_participants=6, n_trials=20)

        primary_a = estimate_primary_endpoint(run_loso_nested_validation(records))
        primary_b = estimate_primary_endpoint(run_loso_nested_validation(records))

        assert primary_a.to_dict() == primary_b.to_dict()

    def test_replay_detects_divergence_from_a_changed_input(self):
        """A replay check is only meaningful if it can fail: perturbing
        the input must change the reported result, not just reproduce a
        cached/hardcoded answer."""
        records = _make_records(n_participants=6, n_trials=20, seed=0)
        perturbed = _make_records(n_participants=6, n_trials=20, seed=99)

        primary_original = estimate_primary_endpoint(run_loso_nested_validation(records))
        primary_perturbed = estimate_primary_endpoint(run_loso_nested_validation(perturbed))

        assert primary_original.to_dict() != primary_perturbed.to_dict()


class TestResultArtifactExportSchema:
    """Every C1 result artifact carries dataset_id, dataset_version,
    code_sha, created_at, confirmatory_or_exploratory at minimum
    (C1_ANALYSIS_SPEC.md Section 10); this verifies the underlying result
    objects serialize cleanly into that shape without losing information."""

    def test_outer_fold_result_round_trips_through_json(self):
        records = _make_records(n_participants=4, n_trials=15)
        results = run_loso_nested_validation(records)
        assert len(results) == 4

        for result in results:
            payload = result.to_dict()
            round_tripped = json.loads(json.dumps(payload))
            assert round_tripped == payload
            assert {
                "held_out_participant", "n_train", "n_test",
                "behavior_only_log_score", "behavior_plus_neural_log_score",
                "delta_oos", "chosen_l2", "behavior_plus_neural_checkpoint_hash",
            } <= round_tripped.keys()

    def test_primary_estimand_round_trips_through_json_with_full_provenance_shape(self):
        records = _make_records(n_participants=6, n_trials=20)
        primary = estimate_primary_endpoint(run_loso_nested_validation(records))
        payload = primary.to_dict()

        round_tripped = json.loads(json.dumps(payload))
        assert round_tripped == payload
        assert {
            "n_participants", "mean_delta_oos", "std_delta_oos",
            "ci_low", "ci_high", "exact_sign_flip_p_value", "per_participant_deltas",
        } <= round_tripped.keys()

        # per_participant_deltas is the unit the primary estimand's inference
        # (participant-level sign-flip test) is actually computed over -- it
        # must be present and complete, not summarized away.
        assert set(round_tripped["per_participant_deltas"].keys()) == {
            r.participant_id for r in records
        }

    def test_full_result_artifact_shape_matches_c1_analysis_spec_minimum_fields(self):
        """Simulates the minimal provenance envelope every
        results/c1_*.json artifact carries, wrapped around a real
        (synthetic-data) primary estimand -- confirms the wrapping survives
        a JSON round-trip without silently dropping or mutating fields."""
        records = _make_records(n_participants=5, n_trials=15)
        primary = estimate_primary_endpoint(run_loso_nested_validation(records))

        artifact = {
            "dataset_id": "ci-fixture",
            "dataset_version": "0.0.0-ci",
            "code_sha": "deadbeef",
            "estimand_id": "H2_incremental_validity_ordinal_log_score",
            "created_at": "2026-01-01T00:00:00+00:00",
            "confirmatory_or_exploratory": "exploratory",
            "primary_estimand": primary.to_dict(),
        }
        round_tripped = json.loads(json.dumps(artifact))
        assert round_tripped == artifact
        required = {
            "dataset_id", "dataset_version", "code_sha",
            "created_at", "confirmatory_or_exploratory",
        }
        assert required <= round_tripped.keys()
