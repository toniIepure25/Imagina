"""Tests for the C2 compact content-state neural encoders (Commit 4).
Small synthetic epoch arrays -- validates architectural/provenance/
determinism properties and that each architecture CAN learn a strong
synthetic signal given enough training budget, not scientific results.
"""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from app.research.neural.c2_encoders import (  # noqa: E402
    CompactContrastiveContentStateEncoder,
    CompactTCNContentEncoder,
    EEGNetContentEncoder,
    content_class_indices,
)
from app.research.neural.c2_models import PRIMARY_CONTENT_CLASSES, MulticlassFeatureModel  # noqa: E402

N_CHANNELS = 30
N_SAMPLES = 250


def _synthetic_classification_data(seed=0, n=60, signal_strength=3e-5):
    rng = np.random.RandomState(seed)
    x = (rng.randn(n, N_CHANNELS, N_SAMPLES) * 1e-5).astype(np.float32)
    labels = rng.choice(PRIMARY_CONTENT_CLASSES, size=n)
    for i, cls in enumerate(PRIMARY_CONTENT_CLASSES):
        x[labels == cls, :, :] += i * signal_strength
    return x, labels


class TestContentClassIndices:
    def test_maps_labels_to_consistent_indices(self):
        labels = np.array(["visual_square", "visual_face_male", "visual_face_female", "visual_square"])
        idx = content_class_indices(labels)
        assert idx[0] == idx[3]
        assert len(set(idx.tolist())) == 3


class TestEEGNetContentEncoder:
    def test_deterministic_checkpoint_for_same_seed(self):
        e1 = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        e2 = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        assert e1.to_spec("m").checkpoint_hash == e2.to_spec("m").checkpoint_hash

    def test_predict_proba_shape_and_normalization(self):
        x, labels = _synthetic_classification_data()
        y_idx = content_class_indices(labels)
        enc = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        enc.fit(x, y_idx, n_epochs=5, lr=1e-2)
        proba = enc.predict_proba(x)
        assert proba.shape == (60, 3)
        assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-5)

    def test_learns_a_strong_synthetic_signal_given_enough_training(self):
        x, labels = _synthetic_classification_data(signal_strength=5e-5)
        y_idx = content_class_indices(labels)
        enc = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        enc.fit(x, y_idx, n_epochs=100, lr=1e-2)
        proba = enc.predict_proba(x)
        train_acc = (proba.argmax(axis=1) == y_idx).mean()
        assert train_acc > 0.5  # well above 1/3 chance

    def test_spec_reports_expected_architecture(self):
        enc = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        spec = enc.to_spec("m")
        assert spec.architecture == "eegnet_content_classifier"
        assert spec.param_count > 0


class TestCompactTCNContentEncoder:
    def test_deterministic_checkpoint_for_same_seed(self):
        e1 = CompactTCNContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        e2 = CompactTCNContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        assert e1.to_spec("m").checkpoint_hash == e2.to_spec("m").checkpoint_hash

    def test_learns_a_strong_synthetic_signal_given_enough_training(self):
        x, labels = _synthetic_classification_data(signal_strength=5e-5)
        y_idx = content_class_indices(labels)
        enc = CompactTCNContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        enc.fit(x, y_idx, n_epochs=100, lr=1e-2)
        proba = enc.predict_proba(x)
        train_acc = (proba.argmax(axis=1) == y_idx).mean()
        assert train_acc > 0.5

    def test_different_architecture_from_eegnet(self):
        eegnet = EEGNetContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        tcn = CompactTCNContentEncoder(N_CHANNELS, N_SAMPLES, n_classes=3, seed=42)
        assert eegnet.to_spec("m").architecture != tcn.to_spec("m").architecture


class TestCompactContrastiveContentStateEncoder:
    def test_embedding_is_l2_normalized(self):
        x, labels = _synthetic_classification_data()
        enc = CompactContrastiveContentStateEncoder(N_CHANNELS, N_SAMPLES, embedding_dim=8, seed=42)
        enc.fit(x, labels, n_epochs=5)
        z = enc.embed(x)
        norms = np.linalg.norm(z, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-4)

    def test_deterministic_checkpoint_for_same_seed(self):
        e1 = CompactContrastiveContentStateEncoder(N_CHANNELS, N_SAMPLES, embedding_dim=8, seed=42)
        e2 = CompactContrastiveContentStateEncoder(N_CHANNELS, N_SAMPLES, embedding_dim=8, seed=42)
        assert e1.to_spec("m").checkpoint_hash == e2.to_spec("m").checkpoint_hash

    def test_frozen_embedding_plus_linear_probe_separates_strong_synthetic_content(self):
        x, labels = _synthetic_classification_data(signal_strength=5e-5)
        enc = CompactContrastiveContentStateEncoder(N_CHANNELS, N_SAMPLES, embedding_dim=8, seed=42)
        enc.fit(x, labels, n_epochs=60)
        z = enc.embed(x)
        probe = MulticlassFeatureModel(l2=1.0)
        probe.fit(z, labels)
        metrics = probe.evaluate(z, labels)
        assert metrics["balanced_accuracy"] > 0.5

    def test_spec_reports_embedding_dim(self):
        enc = CompactContrastiveContentStateEncoder(N_CHANNELS, N_SAMPLES, embedding_dim=8, seed=42)
        spec = enc.to_spec("m")
        assert spec.hyperparameters["embedding_dim"] == 8
        assert spec.architecture == "compact_contrastive_content_state"
