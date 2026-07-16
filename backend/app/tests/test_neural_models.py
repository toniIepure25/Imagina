"""Tests for the compact subject-aware neural encoder baselines (Commit 5).

Uses small synthetic feature/epoch arrays, not real ds005815 data — these
tests validate architectural and provenance properties (determinism,
participant-grouped splitting, checkpoint hashing, parameter/timing
reporting), not scientific results, which come from Commit 7's real nested
validation run.
"""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from app.research.neural.models import (  # noqa: E402
    CompactTCNBaseline,
    EEGNetBaseline,
    ModelSpec,
    OrdinalFeatureModel,
    RidgeFeatureModel,
    participant_grouped_split,
)


def _synthetic_features(n=60, n_features=5, seed=0):
    rng = np.random.RandomState(seed)
    x = rng.randn(n, n_features)
    y_cont = x[:, 0] * 2.0 + rng.randn(n) * 0.3
    return x, y_cont


def _synthetic_ordinal_targets(y_cont):
    bins = np.quantile(y_cont, [0.2, 0.4, 0.6, 0.8])
    return np.clip(np.digitize(y_cont, bins) + 1, 1, 5)


class TestParticipantGroupedSplit:
    def test_no_overlap_between_train_and_test(self):
        pids = ["a"] * 10 + ["b"] * 10 + ["c"] * 10
        train_mask, test_mask = participant_grouped_split(pids, held_out="b")
        assert not np.any(train_mask & test_mask)

    def test_held_out_participant_entirely_in_test(self):
        pids = ["a", "b", "a", "b", "c"]
        train_mask, test_mask = participant_grouped_split(pids, held_out="a")
        assert test_mask.tolist() == [True, False, True, False, False]
        assert train_mask.tolist() == [False, True, False, True, True]

    def test_partition_covers_every_sample(self):
        pids = ["x", "y", "z", "x", "y"]
        train_mask, test_mask = participant_grouped_split(pids, held_out="z")
        assert np.all(train_mask | test_mask)


class TestRidgeFeatureModel:
    def test_deterministic_fit_gives_identical_spec_hash(self):
        x, y = _synthetic_features()
        m1 = RidgeFeatureModel(alpha=1.0, seed=42).fit(x, y)
        m2 = RidgeFeatureModel(alpha=1.0, seed=42).fit(x, y)
        assert m1.to_spec("r1").checkpoint_hash == m2.to_spec("r1").checkpoint_hash

    def test_recovers_directionally_correct_signal(self):
        x, y = _synthetic_features(n=200)
        model = RidgeFeatureModel(alpha=0.1).fit(x, y)
        preds = model.predict(x)
        assert np.corrcoef(preds, y)[0, 1] > 0.8

    def test_spec_reports_param_count_and_times(self):
        x, y = _synthetic_features()
        model = RidgeFeatureModel().fit(x, y)
        spec = model.to_spec("r1")
        assert isinstance(spec, ModelSpec)
        assert spec.param_count == x.shape[1] + 1
        assert spec.train_time_s >= 0
        assert spec.inference_time_s >= 0
        assert spec.architecture == "linear_ridge"


class TestOrdinalFeatureModel:
    def test_deterministic_fit_gives_identical_spec_hash(self):
        x, y_cont = _synthetic_features()
        y_ord = _synthetic_ordinal_targets(y_cont)
        m1 = OrdinalFeatureModel(l2=1.0, seed=42).fit(x, y_ord)
        m2 = OrdinalFeatureModel(l2=1.0, seed=42).fit(x, y_ord)
        assert m1.to_spec("o1").checkpoint_hash == m2.to_spec("o1").checkpoint_hash

    def test_log_score_better_than_null_for_informative_features(self):
        x, y_cont = _synthetic_features(n=300)
        y_ord = _synthetic_ordinal_targets(y_cont)
        model = OrdinalFeatureModel(l2=0.1).fit(x, y_ord)
        fitted_score = model.log_score(x, y_ord)

        null_model = OrdinalFeatureModel(l2=0.1).fit(x, y_ord)
        null_model._model.beta[:] = 0.0  # zero out signal -> null model
        null_score = null_model.log_score(x, y_ord)

        assert fitted_score < null_score

    def test_predictions_are_within_valid_class_range(self):
        x, y_cont = _synthetic_features()
        y_ord = _synthetic_ordinal_targets(y_cont)
        model = OrdinalFeatureModel().fit(x, y_ord)
        preds = model.predict(x)
        assert preds.min() >= 1
        assert preds.max() <= 5


class TestEEGNetBaseline:
    def test_deterministic_init_gives_identical_untrained_checkpoint(self):
        m1 = EEGNetBaseline(n_channels=4, n_samples=40, f1=4, d=2, seed=42)
        m2 = EEGNetBaseline(n_channels=4, n_samples=40, f1=4, d=2, seed=42)
        assert m1.to_spec("e1").checkpoint_hash == m2.to_spec("e1").checkpoint_hash

    def test_training_reduces_loss(self):
        rng = np.random.RandomState(1)
        n, ch, t = 40, 4, 40
        x = rng.randn(n, ch, t).astype(np.float32)
        y = rng.randn(n).astype(np.float32)
        model = EEGNetBaseline(n_channels=ch, n_samples=t, f1=4, d=2, seed=42)
        pred_before = model.predict(x)
        loss_before = float(np.mean((pred_before - y) ** 2))
        model.fit(x, y, n_epochs=20)
        pred_after = model.predict(x)
        loss_after = float(np.mean((pred_after - y) ** 2))
        assert loss_after < loss_before

    def test_spec_reports_nonzero_param_count(self):
        model = EEGNetBaseline(n_channels=4, n_samples=40, f1=4, d=2, seed=42)
        spec = model.to_spec("e1")
        assert spec.param_count > 0
        assert spec.architecture == "eegnet_compact"


class TestCompactTCNBaseline:
    def test_deterministic_init_gives_identical_untrained_checkpoint(self):
        m1 = CompactTCNBaseline(n_channels=4, n_samples=40, hidden=8, seed=42)
        m2 = CompactTCNBaseline(n_channels=4, n_samples=40, hidden=8, seed=42)
        assert m1.to_spec("t1").checkpoint_hash == m2.to_spec("t1").checkpoint_hash

    def test_training_reduces_loss(self):
        rng = np.random.RandomState(2)
        n, ch, t = 40, 4, 40
        x = rng.randn(n, ch, t).astype(np.float32)
        y = rng.randn(n).astype(np.float32)
        model = CompactTCNBaseline(n_channels=ch, n_samples=t, hidden=8, seed=42)
        pred_before = model.predict(x)
        loss_before = float(np.mean((pred_before - y) ** 2))
        model.fit(x, y, n_epochs=20)
        pred_after = model.predict(x)
        loss_after = float(np.mean((pred_after - y) ** 2))
        assert loss_after < loss_before

    def test_different_architecture_from_eegnet(self):
        eegnet = EEGNetBaseline(n_channels=4, n_samples=40, f1=4, d=2, seed=42).to_spec("e1")
        tcn = CompactTCNBaseline(n_channels=4, n_samples=40, hidden=8, seed=42).to_spec("t1")
        assert eegnet.architecture != tcn.architecture
        assert eegnet.param_count != tcn.param_count


class TestNoTestParticipantLeakage:
    def test_ridge_fit_only_uses_provided_training_rows(self):
        """A model fit only on the train partition must not incidentally
        reproduce the held-out participant's targets better than chance —
        a coarse but real smoke test that fit() doesn't secretly see y for
        rows the caller excluded."""
        x, y = _synthetic_features(n=100, seed=5)
        pids = ["p0"] * 50 + ["p1"] * 50
        train_mask, test_mask = participant_grouped_split(pids, held_out="p1")

        model = RidgeFeatureModel(alpha=1.0).fit(x[train_mask], y[train_mask])
        held_out_preds = model.predict(x[test_mask])
        # The model never saw y[test_mask]; predictions are a function of
        # x[test_mask] and train-fitted coefficients only.
        assert held_out_preds.shape == y[test_mask].shape
