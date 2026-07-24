"""Replay-determinism and export-serializability tests for C2 (Commit 8
CI: c2-replay-export), mirroring C1's test_neural_replay_export.py
convention: re-running the exact same LOSO classification pipeline
against identical synthetic input must reproduce bit-identical results,
and every result object persisted to JSON must round-trip without loss.
"""
from __future__ import annotations

import json

import numpy as np

from app.research.neural.c2_nested_validation import (
    aggregate_metric_across_folds,
    run_loso_nested_validation_classification,
    run_single_loso_fold_classification,
)


def _make_content_data(n_participants=6, n_per=20, seed=0):
    rng = np.random.RandomState(seed)
    participant_ids, x, y = [], [], []
    for p in range(n_participants):
        pid = f"p{p}"
        labels = rng.choice(["visual_square", "visual_face_male", "visual_face_female"], size=n_per)
        feats = rng.randn(n_per, 4)
        participant_ids.extend([pid] * n_per)
        x.append(feats)
        y.extend(labels)
    return np.vstack(x), np.array(y), participant_ids


class TestReplayDeterminism:
    def test_identical_input_gives_identical_fold_result(self):
        x, y, ids = _make_content_data()
        train_mask = np.array([i != "p0" for i in ids])
        test_mask = ~train_mask
        args = (
            x[train_mask], y[train_mask], [i for i in ids if i != "p0"],
            x[test_mask], y[test_mask], "p0", "content",
        )
        r1 = run_single_loso_fold_classification(*args)
        r2 = run_single_loso_fold_classification(*args)
        assert r1.chosen_l2 == r2.chosen_l2
        assert r1.checkpoint_hash == r2.checkpoint_hash
        assert r1.metrics == r2.metrics

    def test_identical_input_gives_identical_full_loso_result(self):
        x, y, ids = _make_content_data()
        r1 = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        r2 = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        assert [f.to_dict() for f in r1] == [f.to_dict() for f in r2]

    def test_replay_detects_divergence_from_a_changed_input(self):
        x, y, ids = _make_content_data(seed=0)
        x2, y2, ids2 = _make_content_data(seed=99)
        r1 = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        r2 = run_loso_nested_validation_classification(x2, y2, ids2, target_kind="content")
        assert [f.to_dict() for f in r1] != [f.to_dict() for f in r2]


class TestExportSchema:
    def test_fold_result_round_trips_through_json(self):
        x, y, ids = _make_content_data()
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        for result in results:
            payload = result.to_dict()
            round_tripped = json.loads(json.dumps(payload))
            assert round_tripped == payload
            required = {"held_out_participant", "n_train", "n_test", "metrics", "chosen_l2", "checkpoint_hash"}
            assert required <= round_tripped.keys()

    def test_aggregate_metric_round_trips_through_json(self):
        x, y, ids = _make_content_data()
        results = run_loso_nested_validation_classification(x, y, ids, target_kind="content")
        agg = aggregate_metric_across_folds(results, "class_weighted_log_loss")
        round_tripped = json.loads(json.dumps(agg))
        assert round_tripped == agg
        assert {"n_participants", "mean", "std", "per_participant"} <= round_tripped.keys()
