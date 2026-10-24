"""EEG decoding baselines. All take epochs shaped (n_trials, n_channels, n_times) and expose sklearn's
fit/predict/predict_proba API so they plug into ``app.multimodal.evaluation.cross_validate``."""
from __future__ import annotations

import numpy as np
from scipy import linalg
from scipy import signal as sps
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.covariance import LedoitWolf
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def _quiet_csp(**kw):
    from mne.decoding import CSP
    from mne.utils import use_log_level

    class QuietCSP(CSP):
        def fit(self, x, y):
            with use_log_level("error"):
                return super().fit(x, y)

        def transform(self, x):
            with use_log_level("error"):
                return super().transform(x)

    return QuietCSP(**kw)


def make_csp_lda(n_components: int = 4):
    return make_pipeline(_quiet_csp(n_components=n_components, log=True, reg="ledoit_wolf"),
                         LinearDiscriminantAnalysis())


class FilterBankCSP(BaseEstimator, TransformerMixin):
    def __init__(self, fs: float = 128.0, bands=((4, 8), (8, 12), (12, 16), (16, 24), (24, 32)),
                 n_components: int = 2):
        self.fs = fs
        self.bands = bands
        self.n_components = n_components

    def _filt(self, x, lo, hi):
        sos = sps.butter(4, [lo / (self.fs / 2), min(hi / (self.fs / 2), 0.99)], btype="band", output="sos")
        return sps.sosfiltfilt(sos, x, axis=-1)

    def fit(self, x, y):
        self.csps_ = []
        for lo, hi in self.bands:
            csp = _quiet_csp(n_components=self.n_components, log=True, reg="ledoit_wolf")
            csp.fit(self._filt(x, lo, hi), y)
            self.csps_.append(csp)
        return self

    def transform(self, x):
        return np.hstack([c.transform(self._filt(x, lo, hi)) for c, (lo, hi) in zip(self.csps_, self.bands)])


def make_fbcsp_lda(fs: float):
    return make_pipeline(FilterBankCSP(fs=fs), StandardScaler(),
                         LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))


def _covariances(x: np.ndarray) -> np.ndarray:
    return np.array([LedoitWolf().fit(e.T).covariance_ for e in x])


def _powm(c: np.ndarray, p: float) -> np.ndarray:
    w, v = linalg.eigh(c)
    return (v * np.clip(w, 1e-12, None) ** p) @ v.T


def _logm(c: np.ndarray) -> np.ndarray:
    w, v = linalg.eigh(c)
    return (v * np.log(np.clip(w, 1e-12, None))) @ v.T


class TangentSpace(BaseEstimator, TransformerMixin):
    """Riemannian tangent-space mapping at the log-Euclidean mean of training covariances."""

    def fit(self, x, y=None):
        covs = _covariances(x)
        mean_log = np.mean([_logm(c) for c in covs], axis=0)
        w, v = linalg.eigh(mean_log)
        self.ref_ = (v * np.exp(w)) @ v.T
        self.isqrt_ = _powm(self.ref_, -0.5)
        return self

    def transform(self, x):
        covs = _covariances(x)
        n = covs.shape[1]
        iu = np.triu_indices(n)
        coef = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
        return np.array([_logm(self.isqrt_ @ c @ self.isqrt_)[iu] * coef for c in covs])


def make_tangent_lr():
    return make_pipeline(TangentSpace(), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))


class ShallowNet(BaseEstimator, ClassifierMixin):
    """Small ShallowConvNet-style network (temporal conv -> spatial conv -> square -> pool -> log -> linear)."""

    def __init__(self, n_filters: int = 8, epochs: int = 30, lr: float = 3e-3, seed: int = 0):
        self.n_filters = n_filters
        self.epochs = epochs
        self.lr = lr
        self.seed = seed

    def _build(self, n_ch, n_t, n_cls):
        import torch.nn as nn

        k = min(13, n_t // 4)

        class Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.temporal = nn.Conv2d(1, self.n_filters, (1, k))
                s.spatial = nn.Conv2d(self.n_filters, self.n_filters, (n_ch, 1), bias=False)
                s.bn = nn.BatchNorm2d(self.n_filters)
                s.pool = nn.AvgPool2d((1, max(n_t // 8, 2)), stride=(1, max(n_t // 16, 1)))
                s.drop = nn.Dropout(0.3)
                s.head = nn.LazyLinear(n_cls)

            def forward(s, x):
                import torch

                h = s.bn(s.spatial(s.temporal(x)))
                h = torch.log(torch.clamp(s.pool(h * h), min=1e-6))
                return s.head(s.drop(h.flatten(1)))

        return Net()

    def fit(self, x, y):
        import torch

        torch.manual_seed(self.seed)
        self.classes_ = np.unique(y)
        yi = np.searchsorted(self.classes_, y)
        self.scale_ = float(np.std(x)) + 1e-9
        xt = torch.tensor(x / self.scale_, dtype=torch.float32)[:, None]
        yt = torch.tensor(yi, dtype=torch.long)
        self.net_ = self._build(x.shape[1], x.shape[2], len(self.classes_))
        self.net_(xt[:2])
        opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr, weight_decay=1e-3)
        g = torch.Generator().manual_seed(self.seed)
        self.net_.train()
        for _ in range(self.epochs):
            perm = torch.randperm(len(yt), generator=g)
            for i in range(0, len(yt), 32):
                b = perm[i:i + 32]
                opt.zero_grad()
                loss = torch.nn.functional.cross_entropy(self.net_(xt[b]), yt[b])
                loss.backward()
                opt.step()
        return self

    def predict_proba(self, x):
        import torch

        self.net_.eval()
        with torch.no_grad():
            out = self.net_(torch.tensor(x / self.scale_, dtype=torch.float32)[:, None])
            return torch.softmax(out, dim=1).numpy()

    def predict(self, x):
        return self.classes_[self.predict_proba(x).argmax(axis=1)]


def baseline_factories(fs: float) -> dict:
    return {
        "csp_lda": make_csp_lda,
        "fbcsp_lda": lambda: make_fbcsp_lda(fs),
        "tangent_space_lr": make_tangent_lr,
        "shallow_net": lambda: ShallowNet(),
    }
