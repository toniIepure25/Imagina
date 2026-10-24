"""Compact, subject-aware EEG representation baselines for Scientific Gate C1.

Four architectures, in increasing complexity, as required by the commit
plan — deliberately not starting with a large transformer:

1. `RidgeFeatureModel` — linear ridge regression on classical features
   (Commit 4), treating vividness (1-5) as continuous.
2. `OrdinalFeatureModel` — the proportional-odds ordinal model
   (`ordinal.py`) on classical features, matching the frozen primary metric
   family (`C1_ANALYSIS_SPEC.md` Section 1).
3. `EEGNetBaseline` — a compact depthwise/separable CNN in the style of
   Lawhern et al. 2018, operating directly on raw (channels, time) epochs.
4. `CompactTCNBaseline` — a small temporal-convolutional stack, giving
   architectural diversity from EEGNet's depthwise-separable design.

Every model reports a `ModelSpec` (deterministic seed, parameter count,
train/inference time, a SHA-256 checkpoint hash) so results are auditable
and replayable per the C0.2 evidence convention. No model here sees a
test-participant's data during fitting — that boundary is enforced by the
caller (`participant_grouped_split`), not by anything internal to a model.
"""
from __future__ import annotations

import hashlib
import io
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.research.neural.ordinal import OrdinalLogisticModel, fit_ordinal_logistic

MODELS_VERSION = "1.0.0"


@dataclass
class ModelSpec:
    model_id: str
    model_version: str
    architecture: str
    hyperparameters: dict[str, Any]
    random_seed: int
    param_count: int
    train_time_s: float
    inference_time_s: float
    checkpoint_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def participant_grouped_split(
    participant_ids: list[str], held_out: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (train_mask, test_mask) boolean arrays such that every sample
    belonging to `held_out` is in the test set and nowhere in train — the
    minimal building block nested CV (Commit 7) composes into LOSO/inner
    folds. No test-participant sample can leak into train by construction:
    this is a pure boolean partition on participant_ids, not a stochastic
    process."""
    ids = np.array(participant_ids)
    test_mask = ids == held_out
    train_mask = ~test_mask
    return train_mask, test_mask


# --- Classical-feature models -------------------------------------------

@dataclass
class RidgeFeatureModel:
    alpha: float = 1.0
    seed: int = 42
    _coef: np.ndarray | None = field(default=None, repr=False)
    _intercept: float = field(default=0.0, repr=False)
    _mean: np.ndarray | None = field(default=None, repr=False)
    _std: np.ndarray | None = field(default=None, repr=False)
    _train_time_s: float = field(default=0.0, repr=False)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "RidgeFeatureModel":
        from sklearn.linear_model import Ridge

        t0 = time.perf_counter()
        # Standardization is fit here, on whatever x is passed in — callers
        # (Commit 7) are responsible for only ever passing this the outer-
        # training fold's data, never the held-out participant's.
        self._mean = x.mean(axis=0)
        self._std = x.std(axis=0) + 1e-9
        x_std = (x - self._mean) / self._std
        model = Ridge(alpha=self.alpha, random_state=self.seed)
        model.fit(x_std, y)
        self._coef = model.coef_
        self._intercept = float(model.intercept_)
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        x_std = (x - self._mean) / self._std
        return x_std @ self._coef + self._intercept

    def to_spec(self, model_id: str) -> ModelSpec:
        t0 = time.perf_counter()
        if self._coef is not None:
            _ = self.predict(np.zeros((1, len(self._coef))))
        inference_time_s = time.perf_counter() - t0
        checkpoint_bytes = np.concatenate([self._coef, [self._intercept]]).tobytes() if self._coef is not None else b""
        return ModelSpec(
            model_id=model_id, model_version=MODELS_VERSION, architecture="linear_ridge",
            hyperparameters={"alpha": self.alpha}, random_seed=self.seed,
            param_count=(len(self._coef) + 1) if self._coef is not None else 0,
            train_time_s=self._train_time_s, inference_time_s=inference_time_s,
            checkpoint_hash=hashlib.sha256(checkpoint_bytes).hexdigest(),
        )


@dataclass
class OrdinalFeatureModel:
    l2: float = 1.0
    seed: int = 42
    n_classes: int = 5
    _model: OrdinalLogisticModel | None = field(default=None, repr=False)
    _mean: np.ndarray | None = field(default=None, repr=False)
    _std: np.ndarray | None = field(default=None, repr=False)
    _train_time_s: float = field(default=0.0, repr=False)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "OrdinalFeatureModel":
        t0 = time.perf_counter()
        self._mean = x.mean(axis=0)
        self._std = x.std(axis=0) + 1e-9
        x_std = (x - self._mean) / self._std
        self._model = fit_ordinal_logistic(x_std, y, n_classes=self.n_classes, l2=self.l2, seed=self.seed)
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        x_std = (x - self._mean) / self._std
        return self._model.predict(x_std)

    def log_score(self, x: np.ndarray, y: np.ndarray) -> float:
        x_std = (x - self._mean) / self._std
        return self._model.log_score(x_std, y)

    def to_spec(self, model_id: str) -> ModelSpec:
        t0 = time.perf_counter()
        if self._model is not None:
            _ = self.predict(np.zeros((1, len(self._model.beta))))
        inference_time_s = time.perf_counter() - t0
        checkpoint_bytes = (
            np.concatenate([self._model.beta, self._model.thresholds]).tobytes() if self._model is not None else b""
        )
        return ModelSpec(
            model_id=model_id, model_version=MODELS_VERSION, architecture="ordinal_logistic",
            hyperparameters={"l2": self.l2, "n_classes": self.n_classes}, random_seed=self.seed,
            param_count=(len(self._model.beta) + len(self._model.thresholds)) if self._model is not None else 0,
            train_time_s=self._train_time_s, inference_time_s=inference_time_s,
            checkpoint_hash=hashlib.sha256(checkpoint_bytes).hexdigest(),
        )


# --- Raw-epoch (torch) encoders -----------------------------------------

def _require_torch():
    import torch
    return torch


class EEGNetBaseline:
    """Compact depthwise/separable CNN, in the style of Lawhern et al. 2018
    "EEGNet: A Compact Convolutional Network for EEG-based Brain-Computer
    Interfaces" — F1 temporal filters, D depthwise spatial filters per
    temporal filter, then a separable conv, then a linear regression head
    (vividness treated as continuous for this compact baseline; the ordinal
    feature model above carries the frozen primary ordinal metric)."""

    def __init__(self, n_channels: int, n_samples: int, f1: int = 8, d: int = 2, seed: int = 42):
        torch = _require_torch()
        self.seed = seed
        self.n_channels = n_channels
        self.n_samples = n_samples
        torch.manual_seed(seed)

        class _Net(torch.nn.Module):
            def __init__(self, n_channels, n_samples, f1, d):
                super().__init__()
                f2 = f1 * d
                self.temporal = torch.nn.Conv2d(1, f1, (1, 32), padding=(0, 16), bias=False)
                self.bn1 = torch.nn.BatchNorm2d(f1)
                self.depthwise = torch.nn.Conv2d(f1, f2, (n_channels, 1), groups=f1, bias=False)
                self.bn2 = torch.nn.BatchNorm2d(f2)
                self.pool1 = torch.nn.AvgPool2d((1, 4))
                self.separable = torch.nn.Conv2d(f2, f2, (1, 16), padding=(0, 8), groups=f2, bias=False)
                self.bn3 = torch.nn.BatchNorm2d(f2)
                self.pool2 = torch.nn.AvgPool2d((1, 8))
                with torch.no_grad():
                    dummy = torch.zeros(1, 1, n_channels, n_samples)
                    flat_dim = self._forward_features(dummy).shape[-1]
                self.head = torch.nn.Linear(flat_dim, 1)

            def _forward_features(self, x):
                x = torch.nn.functional.elu(self.bn1(self.temporal(x)))
                x = torch.nn.functional.elu(self.bn2(self.depthwise(x)))
                x = self.pool1(x)
                x = torch.nn.functional.elu(self.bn3(self.separable(x)))
                x = self.pool2(x)
                return x.flatten(1)

            def forward(self, x):
                return self.head(self._forward_features(x)).squeeze(-1)

        self.net = _Net(n_channels, n_samples, f1, d)
        self._train_time_s = 0.0

    def fit(self, x: np.ndarray, y: np.ndarray, n_epochs: int = 30, lr: float = 1e-3) -> "EEGNetBaseline":
        torch = _require_torch()
        t0 = time.perf_counter()
        x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)  # (n, 1, ch, time)
        y_t = torch.tensor(y, dtype=torch.float32)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.net.train()
        for _ in range(n_epochs):
            opt.zero_grad()
            pred = self.net(x_t)
            loss = torch.nn.functional.mse_loss(pred, y_t)
            loss.backward()
            opt.step()
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)
            return self.net(x_t).numpy()

    def to_spec(self, model_id: str) -> ModelSpec:
        torch = _require_torch()
        param_count = sum(p.numel() for p in self.net.parameters())
        t0 = time.perf_counter()
        _ = self.predict(np.zeros((1, self.n_channels, self.n_samples), dtype=np.float32))
        inference_time_s = time.perf_counter() - t0
        buf = io.BytesIO()
        torch.save(self.net.state_dict(), buf)
        checkpoint_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        return ModelSpec(
            model_id=model_id, model_version=MODELS_VERSION, architecture="eegnet_compact",
            hyperparameters={"n_channels": self.n_channels, "n_samples": self.n_samples},
            random_seed=self.seed, param_count=param_count,
            train_time_s=self._train_time_s, inference_time_s=inference_time_s,
            checkpoint_hash=checkpoint_hash,
        )


class CompactTCNBaseline:
    """A small temporal-convolutional stack: 1D dilated convolutions over
    time, average-pooled across channels first — architecturally distinct
    from EEGNet's depthwise-separable design, giving genuine diversity
    rather than a second copy of the same inductive bias."""

    def __init__(self, n_channels: int, n_samples: int, hidden: int = 16, seed: int = 42):
        torch = _require_torch()
        self.seed = seed
        self.n_channels = n_channels
        self.n_samples = n_samples
        torch.manual_seed(seed)

        class _Net(torch.nn.Module):
            def __init__(self, n_channels, hidden):
                super().__init__()
                self.conv1 = torch.nn.Conv1d(n_channels, hidden, kernel_size=7, padding=3, dilation=1)
                self.conv2 = torch.nn.Conv1d(hidden, hidden, kernel_size=7, padding=6, dilation=2)
                self.pool = torch.nn.AdaptiveAvgPool1d(1)
                self.head = torch.nn.Linear(hidden, 1)

            def forward(self, x):
                x = torch.nn.functional.relu(self.conv1(x))
                x = torch.nn.functional.relu(self.conv2(x))
                x = self.pool(x).squeeze(-1)
                return self.head(x).squeeze(-1)

        self.net = _Net(n_channels, hidden)
        self._train_time_s = 0.0

    def fit(self, x: np.ndarray, y: np.ndarray, n_epochs: int = 30, lr: float = 1e-3) -> "CompactTCNBaseline":
        torch = _require_torch()
        t0 = time.perf_counter()
        x_t = torch.tensor(x, dtype=torch.float32)  # (n, ch, time)
        y_t = torch.tensor(y, dtype=torch.float32)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.net.train()
        for _ in range(n_epochs):
            opt.zero_grad()
            pred = self.net(x_t)
            loss = torch.nn.functional.mse_loss(pred, y_t)
            loss.backward()
            opt.step()
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32)
            return self.net(x_t).numpy()

    def to_spec(self, model_id: str) -> ModelSpec:
        torch = _require_torch()
        param_count = sum(p.numel() for p in self.net.parameters())
        t0 = time.perf_counter()
        _ = self.predict(np.zeros((1, self.n_channels, self.n_samples), dtype=np.float32))
        inference_time_s = time.perf_counter() - t0
        buf = io.BytesIO()
        torch.save(self.net.state_dict(), buf)
        checkpoint_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        return ModelSpec(
            model_id=model_id, model_version=MODELS_VERSION, architecture="compact_tcn",
            hyperparameters={"n_channels": self.n_channels, "n_samples": self.n_samples},
            random_seed=self.seed, param_count=param_count,
            train_time_s=self._train_time_s, inference_time_s=inference_time_s,
            checkpoint_hash=checkpoint_hash,
        )
