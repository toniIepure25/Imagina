"""Compact content-state neural representations for Scientific Gate C2
(Commit 4). Three architectures, in increasing novelty, per the commit
plan -- deliberately not starting with a large transformer:

1. `EEGNetContentEncoder` -- C1's EEGNetBaseline architecture (Lawhern et
   al. 2018 depthwise/separable CNN) with a softmax classification head
   instead of a regression head.
2. `CompactTCNContentEncoder` -- C1's CompactTCNBaseline architecture with
   a classification head, giving architectural diversity from EEGNet's
   depthwise-separable design.
3. `CompactContrastiveContentStateEncoder` -- a compact temporal-conv
   embedding trained with a supervised contrastive objective that pulls
   together same-content epochs regardless of state and pushes apart
   different-content epochs, so the resulting representation is organized
   by content similarity without ever using state as a grouping signal.
   Content decoding on top of the frozen embedding uses a simple linear
   probe (`c2_models.MulticlassFeatureModel`), not a second deep head.

Every encoder reports the same `ModelSpec` provenance convention as C1's
`models.py` (seed, param count, train/inference time, checkpoint hash),
plus input window and channel set recorded by the caller (Commit 4's
runner script), since those are properties of the data view, not the model.
"""
from __future__ import annotations

import hashlib
import io
import time

import numpy as np

from app.research.neural.c2_models import PRIMARY_CONTENT_CLASSES
from app.research.neural.models import ModelSpec

C2_ENCODERS_VERSION = "1.0.0"


def _require_torch():
    import torch
    return torch


class EEGNetContentEncoder:
    """EEGNet-style compact CNN with a softmax content-classification head."""

    def __init__(self, n_channels: int, n_samples: int, n_classes: int = 3, f1: int = 8, d: int = 2, seed: int = 42):
        torch = _require_torch()
        self.seed = seed
        self.n_channels = n_channels
        self.n_samples = n_samples
        self.n_classes = n_classes
        torch.manual_seed(seed)

        class _Net(torch.nn.Module):
            def __init__(self, n_channels, n_samples, f1, d, n_classes):
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
                self.head = torch.nn.Linear(flat_dim, n_classes)

            def _forward_features(self, x):
                x = torch.nn.functional.elu(self.bn1(self.temporal(x)))
                x = torch.nn.functional.elu(self.bn2(self.depthwise(x)))
                x = self.pool1(x)
                x = torch.nn.functional.elu(self.bn3(self.separable(x)))
                x = self.pool2(x)
                return x.flatten(1)

            def forward(self, x):
                return self.head(self._forward_features(x))

        self.net = _Net(n_channels, n_samples, f1, d, n_classes)
        self._train_time_s = 0.0

    def fit(self, x: np.ndarray, y_idx: np.ndarray, n_epochs: int = 30, lr: float = 1e-3) -> "EEGNetContentEncoder":
        torch = _require_torch()
        t0 = time.perf_counter()
        x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)
        y_t = torch.tensor(y_idx, dtype=torch.long)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.net.train()
        for _ in range(n_epochs):
            opt.zero_grad()
            logits = self.net(x_t)
            loss = torch.nn.functional.cross_entropy(logits, y_t)
            loss.backward()
            opt.step()
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)
            return torch.nn.functional.softmax(self.net(x_t), dim=-1).numpy()

    def embed(self, x: np.ndarray) -> np.ndarray:
        """Pre-head (post-conv, flattened) features -- the frozen
        representation Commit 6's disentanglement probes operate on,
        distinct from the final content-classification logits/proba."""
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)
            return self.net._forward_features(x_t).numpy()

    def to_spec(self, model_id: str) -> ModelSpec:
        torch = _require_torch()
        param_count = sum(p.numel() for p in self.net.parameters())
        t0 = time.perf_counter()
        _ = self.predict_proba(np.zeros((1, self.n_channels, self.n_samples), dtype=np.float32))
        inference_time_s = time.perf_counter() - t0
        buf = io.BytesIO()
        torch.save(self.net.state_dict(), buf)
        checkpoint_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        return ModelSpec(
            model_id=model_id, model_version=C2_ENCODERS_VERSION, architecture="eegnet_content_classifier",
            hyperparameters={"n_channels": self.n_channels, "n_samples": self.n_samples, "n_classes": self.n_classes},
            random_seed=self.seed, param_count=param_count, train_time_s=self._train_time_s,
            inference_time_s=inference_time_s, checkpoint_hash=checkpoint_hash,
        )


class CompactTCNContentEncoder:
    """Compact dilated-temporal-conv classifier, architecturally distinct
    from EEGNet's depthwise-separable design."""

    def __init__(self, n_channels: int, n_samples: int, n_classes: int = 3, hidden: int = 16, seed: int = 42):
        torch = _require_torch()
        self.seed = seed
        self.n_channels = n_channels
        self.n_samples = n_samples
        self.n_classes = n_classes
        torch.manual_seed(seed)

        class _Net(torch.nn.Module):
            def __init__(self, n_channels, hidden, n_classes):
                super().__init__()
                self.conv1 = torch.nn.Conv1d(n_channels, hidden, kernel_size=7, padding=3, dilation=1)
                self.conv2 = torch.nn.Conv1d(hidden, hidden, kernel_size=7, padding=6, dilation=2)
                self.pool = torch.nn.AdaptiveAvgPool1d(1)
                self.head = torch.nn.Linear(hidden, n_classes)

            def _forward_features(self, x):
                x = torch.nn.functional.relu(self.conv1(x))
                x = torch.nn.functional.relu(self.conv2(x))
                return self.pool(x).squeeze(-1)

            def forward(self, x):
                return self.head(self._forward_features(x))

        self.net = _Net(n_channels, hidden, n_classes)
        self._train_time_s = 0.0

    def fit(self, x: np.ndarray, y_idx: np.ndarray, n_epochs: int = 30, lr: float = 1e-3) -> "CompactTCNContentEncoder":
        torch = _require_torch()
        t0 = time.perf_counter()
        x_t = torch.tensor(x, dtype=torch.float32)
        y_t = torch.tensor(y_idx, dtype=torch.long)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.net.train()
        for _ in range(n_epochs):
            opt.zero_grad()
            logits = self.net(x_t)
            loss = torch.nn.functional.cross_entropy(logits, y_t)
            loss.backward()
            opt.step()
        self._train_time_s = time.perf_counter() - t0
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32)
            return torch.nn.functional.softmax(self.net(x_t), dim=-1).numpy()

    def embed(self, x: np.ndarray) -> np.ndarray:
        """Pre-head pooled features -- the frozen representation Commit
        6's disentanglement probes operate on."""
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32)
            return self.net._forward_features(x_t).numpy()

    def to_spec(self, model_id: str) -> ModelSpec:
        torch = _require_torch()
        param_count = sum(p.numel() for p in self.net.parameters())
        t0 = time.perf_counter()
        _ = self.predict_proba(np.zeros((1, self.n_channels, self.n_samples), dtype=np.float32))
        inference_time_s = time.perf_counter() - t0
        buf = io.BytesIO()
        torch.save(self.net.state_dict(), buf)
        checkpoint_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        return ModelSpec(
            model_id=model_id, model_version=C2_ENCODERS_VERSION, architecture="compact_tcn_content_classifier",
            hyperparameters={"n_channels": self.n_channels, "n_samples": self.n_samples, "n_classes": self.n_classes},
            random_seed=self.seed, param_count=param_count, train_time_s=self._train_time_s,
            inference_time_s=inference_time_s, checkpoint_hash=checkpoint_hash,
        )


class CompactContrastiveContentStateEncoder:
    """Compact temporal-conv embedding (architecture shared with the TCN
    encoder, minus the classification head) trained with a supervised
    contrastive loss over CONTENT labels only -- same-content epochs are
    pulled together, different-content epochs pushed apart, regardless of
    which state (perception/imagery) they came from. State is never used
    as a positive/negative-pair criterion, so nothing in the training
    objective can organize the embedding by state -- any state information
    that survives is incidental, not trained for (probed explicitly in
    Commit 6's disentanglement analysis, not claimed here)."""

    def __init__(self, n_channels: int, n_samples: int, embedding_dim: int = 16, hidden: int = 16, seed: int = 42):
        torch = _require_torch()
        self.seed = seed
        self.n_channels = n_channels
        self.n_samples = n_samples
        self.embedding_dim = embedding_dim
        torch.manual_seed(seed)

        class _Net(torch.nn.Module):
            def __init__(self, n_channels, hidden, embedding_dim):
                super().__init__()
                self.conv1 = torch.nn.Conv1d(n_channels, hidden, kernel_size=7, padding=3, dilation=1)
                self.conv2 = torch.nn.Conv1d(hidden, hidden, kernel_size=7, padding=6, dilation=2)
                self.pool = torch.nn.AdaptiveAvgPool1d(1)
                self.proj = torch.nn.Linear(hidden, embedding_dim)

            def forward(self, x):
                x = torch.nn.functional.relu(self.conv1(x))
                x = torch.nn.functional.relu(self.conv2(x))
                x = self.pool(x).squeeze(-1)
                z = self.proj(x)
                return torch.nn.functional.normalize(z, dim=-1)

        self.net = _Net(n_channels, hidden, embedding_dim)
        self._train_time_s = 0.0

    def fit(
        self, x: np.ndarray, content_labels: np.ndarray, n_epochs: int = 50, lr: float = 1e-3, temperature: float = 0.2,
    ) -> "CompactContrastiveContentStateEncoder":
        """Supervised contrastive loss (Khosla et al. 2020 SupCon,
        simplified): for each anchor, positives are all OTHER samples in
        the same minibatch sharing its content label; negatives are every
        other sample. State is not part of this label at all."""
        torch = _require_torch()
        t0 = time.perf_counter()
        x_t = torch.tensor(x, dtype=torch.float32)
        classes = sorted(set(content_labels.tolist()))
        label_idx = torch.tensor([classes.index(c) for c in content_labels], dtype=torch.long)
        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.net.train()
        for _ in range(n_epochs):
            opt.zero_grad()
            z = self.net(x_t)  # (n, embedding_dim), already L2-normalized
            sim = z @ z.T / temperature  # (n, n) cosine similarity / temperature
            n = sim.shape[0]
            mask_self = torch.eye(n, dtype=torch.bool)
            sim = sim.masked_fill(mask_self, float("-inf"))
            same_label = label_idx.unsqueeze(0) == label_idx.unsqueeze(1)
            same_label = same_label & ~mask_self
            log_prob = sim - torch.logsumexp(sim, dim=1, keepdim=True)
            pos_counts = same_label.sum(dim=1).clamp(min=1)
            loss = -(log_prob * same_label).sum(dim=1) / pos_counts
            loss = loss.mean()
            loss.backward()
            opt.step()
        self._train_time_s = time.perf_counter() - t0
        return self

    def embed(self, x: np.ndarray) -> np.ndarray:
        torch = _require_torch()
        self.net.eval()
        with torch.no_grad():
            x_t = torch.tensor(x, dtype=torch.float32)
            return self.net(x_t).numpy()

    def to_spec(self, model_id: str) -> ModelSpec:
        torch = _require_torch()
        param_count = sum(p.numel() for p in self.net.parameters())
        t0 = time.perf_counter()
        _ = self.embed(np.zeros((1, self.n_channels, self.n_samples), dtype=np.float32))
        inference_time_s = time.perf_counter() - t0
        buf = io.BytesIO()
        torch.save(self.net.state_dict(), buf)
        checkpoint_hash = hashlib.sha256(buf.getvalue()).hexdigest()
        return ModelSpec(
            model_id=model_id, model_version=C2_ENCODERS_VERSION, architecture="compact_contrastive_content_state",
            hyperparameters={
                "n_channels": self.n_channels, "n_samples": self.n_samples, "embedding_dim": self.embedding_dim,
            },
            random_seed=self.seed, param_count=param_count, train_time_s=self._train_time_s,
            inference_time_s=inference_time_s, checkpoint_hash=checkpoint_hash,
        )


def content_class_indices(labels: np.ndarray, classes: tuple[str, ...] = PRIMARY_CONTENT_CLASSES) -> np.ndarray:
    class_to_idx = {c: i for i, c in enumerate(classes)}
    return np.array([class_to_idx[label] for label in labels])
