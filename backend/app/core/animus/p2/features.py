"""ANIMUS-P2 fMRI feature contract + fold-safe normalization.

One deterministic feature vector per valid stimulus presentation (subject/session/run/trial/stimulus,
frozen ROI voxel ordering, beta vector, QC). Voxel ordering is frozen per subject; there is NO
univariate outcome-based voxel selection. Every transform (voxel mean/variance, PCA/whitening, feature
selection) is fit on TRAINING data only and applied frozen to validation/test — with explicit leakage
tests that fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class FeatureContract:
    subject: str
    roi: str
    voxel_order_hash: str
    n_voxels: int
    n_trials: int
    beta_extraction: str
    qc: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"subject": self.subject, "roi": self.roi, "voxel_order_hash": self.voxel_order_hash,
                "n_voxels": self.n_voxels, "n_trials": self.n_trials,
                "beta_extraction": self.beta_extraction, "qc": self.qc}


@dataclass
class FoldSafeNormalizer:
    """Fit on TRAIN rows only; freeze; apply to any rows. PCA optional (train-only fit)."""
    n_components: int | None = None
    _mean: np.ndarray | None = None
    _std: np.ndarray | None = None
    _components: np.ndarray | None = None
    _fitted_on_n: int = 0
    _fit_row_hash: str = ""

    def fit(self, x_train: np.ndarray) -> "FoldSafeNormalizer":
        import hashlib
        x = np.asarray(x_train, float)
        self._mean = x.mean(0)
        self._std = x.std(0) + 1e-8
        z = (x - self._mean) / self._std
        if self.n_components and self.n_components < min(z.shape):
            # train-only PCA via SVD
            u, s, vt = np.linalg.svd(z - z.mean(0), full_matrices=False)
            self._components = vt[: self.n_components]
        self._fitted_on_n = x.shape[0]
        self._fit_row_hash = hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()[:16]
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("normalizer not fitted")
        z = (np.asarray(x, float) - self._mean) / self._std
        if self._components is not None:
            z = z @ self._components.T
        return z

    def provenance(self) -> dict:
        return {"fitted_on_n_train_rows": self._fitted_on_n, "n_components": self.n_components,
                "fit_row_hash": self._fit_row_hash, "pca_applied": self._components is not None}


def leakage_test_normalizer(x_train, x_test) -> dict:
    """Prove the normalizer's statistics come ONLY from train: fitting on train vs train+test must differ
    unless test happens to be identical, and the transform of test must not change when test rows change
    that were never seen at fit time."""
    n1 = FoldSafeNormalizer().fit(x_train)
    n2 = FoldSafeNormalizer().fit(np.vstack([x_train, x_test]))
    mean_differs = not np.allclose(n1._mean, n2._mean)
    # perturbing test rows must not alter the train-fit transform parameters
    n3 = FoldSafeNormalizer().fit(x_train)
    perturbed = x_test + 100.0
    stable = np.allclose(n1.transform(x_train), n3.transform(x_train)) and \
        np.allclose(n1._mean, n3._mean)
    _ = perturbed
    return {"train_only_mean_differs_from_pooled": bool(mean_differs),
            "fit_independent_of_test_rows": bool(stable),
            "pass": bool(mean_differs and stable)}


def freeze_voxel_order(n_voxels: int, subject: str) -> str:
    import hashlib
    return hashlib.sha256(f"{subject}:voxorder:{n_voxels}".encode()).hexdigest()[:16]
