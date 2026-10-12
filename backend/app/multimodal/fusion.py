"""Quality-aware multimodal fusion with missing-modality support.

Encoders standardize each modality's features using statistics fit on training data only. Three baselines:
early (concatenation + mask indicators), late (quality-weighted log-odds of per-modality models) and intermediate
(PyTorch per-modality encoders, quality-weighted pooling, modality dropout). No fusion strategy is assumed to beat
unimodal models; use ``ablation`` to measure it.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.multimodal import SCHEMA_VERSION
from app.multimodal.schemas import Modality


@dataclass
class MultimodalDataset:
    features: dict[Modality, np.ndarray]
    quality: dict[Modality, np.ndarray]
    feature_names: dict[Modality, list[str]]
    y: np.ndarray
    groups: np.ndarray
    source_kinds: list[str]

    @property
    def modalities(self) -> list[Modality]:
        return list(self.features)

    def available(self, m: Modality) -> np.ndarray:
        return ~np.all(np.isnan(self.features[m]), axis=1) & (self.quality[m] > 0)

    def subset(self, idx: np.ndarray, modalities: list[Modality] | None = None) -> MultimodalDataset:
        mods = modalities or self.modalities
        return MultimodalDataset({m: self.features[m][idx] for m in mods}, {m: self.quality[m][idx] for m in mods},
                                 {m: self.feature_names[m] for m in mods}, self.y[idx], self.groups[idx],
                                 self.source_kinds)

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for m in sorted(self.features, key=lambda k: k.value):
            h.update(m.value.encode())
            h.update(np.nan_to_num(self.features[m], nan=-9e9).round(8).tobytes())
        h.update(self.y.astype(str).astype("S").tobytes())
        return h.hexdigest()


class ModalityEncoder:
    def fit(self, x: np.ndarray) -> ModalityEncoder:
        self.median_ = np.nanmedian(x, axis=0)
        q75, q25 = np.nanpercentile(x, [75, 25], axis=0)
        self.scale_ = np.where((q75 - q25) > 1e-12, (q75 - q25) / 1.349, 1.0)
        self.median_ = np.nan_to_num(self.median_)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        return np.clip((x - self.median_) / self.scale_, -6, 6)


class _Base:
    name = "base"

    def _encode(self, ds: MultimodalDataset, fit: bool) -> dict[Modality, np.ndarray]:
        if fit:
            self.encoders_ = {m: ModalityEncoder().fit(ds.features[m][ds.available(m)]) for m in ds.modalities}
            self.modalities_ = ds.modalities
        return {m: self.encoders_[m].transform(ds.features[m]) for m in self.modalities_}

    def predict(self, ds: MultimodalDataset) -> np.ndarray:
        return self.classes_[self.predict_proba(ds).argmax(axis=1)]


class EarlyFusion(_Base):
    name = "early"

    def fit(self, ds: MultimodalDataset) -> EarlyFusion:
        self.classes_ = np.unique(ds.y)
        self.clf_ = LogisticRegression(max_iter=2000, C=0.5).fit(self._matrix(ds, fit=True), ds.y)
        return self

    def _matrix(self, ds, fit=False):
        enc = self._encode(ds, fit)
        cols = []
        for m in self.modalities_:
            avail = ds.available(m)
            z = np.where(avail[:, None], np.nan_to_num(enc[m]), 0.0)
            cols += [z * ds.quality[m][:, None], avail[:, None].astype(float)]
        return np.hstack(cols)

    def predict_proba(self, ds):
        return self.clf_.predict_proba(self._matrix(ds))


class LateFusion(_Base):
    name = "late"

    def fit(self, ds: MultimodalDataset) -> LateFusion:
        self.classes_ = np.unique(ds.y)
        enc = self._encode(ds, fit=True)
        self.models_ = {}
        for m in self.modalities_:
            a = ds.available(m)
            if a.sum() >= 10 and len(np.unique(ds.y[a])) == len(self.classes_):
                self.models_[m] = LogisticRegression(max_iter=2000, C=0.5).fit(np.nan_to_num(enc[m][a]), ds.y[a])
        prior = np.array([np.mean(ds.y == c) for c in self.classes_])
        self.prior_logit_ = np.log(prior[1] / prior[0]) if len(prior) == 2 else 0.0
        return self

    def modality_logits(self, ds) -> dict[Modality, np.ndarray]:
        enc = self._encode(ds, fit=False)
        out = {}
        for m, clf in self.models_.items():
            p = clf.predict_proba(np.nan_to_num(enc[m]))[:, 1].clip(1e-6, 1 - 1e-6)
            out[m] = np.where(ds.available(m), np.log(p / (1 - p)), np.nan)
        return out

    def predict_proba(self, ds):
        logits = self.modality_logits(ds)
        num = np.zeros(len(ds.y))
        for m, lg in logits.items():
            w = np.where(np.isnan(lg), 0.0, ds.quality[m])
            num += w * np.nan_to_num(lg - self.prior_logit_)
        fused = self.prior_logit_ + num
        p1 = 1 / (1 + np.exp(-fused))
        return np.column_stack([1 - p1, p1])

    def disagreement(self, ds) -> np.ndarray:
        lg = np.array(list(self.modality_logits(ds).values()))
        p = 1 / (1 + np.exp(-lg))
        return np.nanstd(p, axis=0) if lg.size else np.zeros(len(ds.y))


class IntermediateFusion(_Base):
    name = "intermediate"

    def __init__(self, embed_dim: int = 16, epochs: int = 60, modality_dropout: float = 0.3, seed: int = 0,
                 lr: float = 1e-2):
        self.embed_dim = embed_dim
        self.epochs = epochs
        self.modality_dropout = modality_dropout
        self.seed = seed
        self.lr = lr

    def _tensors(self, ds, fit=False):
        import torch

        enc = self._encode(ds, fit)
        xs = [torch.tensor(np.nan_to_num(enc[m]), dtype=torch.float32) for m in self.modalities_]
        qs = torch.tensor(np.column_stack([np.where(ds.available(m), ds.quality[m], 0.0) for m in self.modalities_]),
                          dtype=torch.float32)
        return xs, qs

    def _build(self, dims):
        import torch
        import torch.nn as nn

        e = self.embed_dim

        class Net(nn.Module):
            def __init__(s):
                super().__init__()
                s.enc = nn.ModuleList([nn.Sequential(nn.Linear(d, e), nn.GELU(), nn.Dropout(0.2), nn.Linear(e, e))
                                       for d in dims])
                s.head = nn.Sequential(nn.Linear(e, e), nn.GELU(), nn.Dropout(0.2), nn.Linear(e, 2))

            def forward(s, xs, q):
                z = torch.stack([enc(x) for enc, x in zip(s.enc, xs)], dim=1)
                w = q / q.sum(dim=1, keepdim=True).clamp(min=1e-6)
                pooled = (z * w.unsqueeze(-1)).sum(dim=1)
                return s.head(pooled)

        return Net()

    def fit(self, ds: MultimodalDataset) -> IntermediateFusion:
        import torch

        torch.manual_seed(self.seed)
        self.classes_ = np.unique(ds.y)
        xs, qs = self._tensors(ds, fit=True)
        y = torch.tensor(np.searchsorted(self.classes_, ds.y), dtype=torch.long)
        self.net_ = self._build([x.shape[1] for x in xs])
        opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr, weight_decay=1e-3)
        g = torch.Generator().manual_seed(self.seed)
        self.net_.train()
        for _ in range(self.epochs):
            perm = torch.randperm(len(y), generator=g)
            for i in range(0, len(y), 64):
                b = perm[i:i + 64]
                q = qs[b].clone()
                drop = torch.rand(q.shape, generator=g) < self.modality_dropout
                keep_one = q.argmax(dim=1)
                drop[torch.arange(len(b)), keep_one] = False
                q[drop] = 0.0
                opt.zero_grad()
                loss = torch.nn.functional.cross_entropy(self.net_([x[b] for x in xs], q), y[b])
                loss.backward()
                opt.step()
        return self

    def predict_proba(self, ds):
        import torch

        xs, qs = self._tensors(ds)
        self.net_.eval()
        with torch.no_grad():
            return torch.softmax(self.net_(xs, qs), dim=1).numpy()

    def mc_dropout_std(self, ds, n: int = 20) -> np.ndarray:
        import torch

        xs, qs = self._tensors(ds)
        torch.manual_seed(self.seed)
        self.net_.train()
        with torch.no_grad():
            p = np.stack([torch.softmax(self.net_(xs, qs), dim=1)[:, 1].numpy() for _ in range(n)])
        self.net_.eval()
        return p.std(axis=0)


FUSION_MODELS = {"early": EarlyFusion, "late": LateFusion, "intermediate": IntermediateFusion}


def evaluate_fusion(make, ds: MultimodalDataset, scheme: str = "loso", seed: int = 0) -> dict:
    from app.multimodal.evaluation import check_group_leakage, expected_calibration_error, splits

    accs, eces, probs_all, y_all = [], [], [], []
    for tr, te in splits(ds.y, ds.groups, scheme, seed=seed):
        if scheme == "loso":
            check_group_leakage(ds.groups[tr], ds.groups[te])
        m = make().fit(ds.subset(tr))
        te_ds = ds.subset(te)
        p = m.predict_proba(te_ds)
        pred = m.classes_[p.argmax(axis=1)]
        accs.append(float(np.mean(pred == te_ds.y)))
        eces.append(expected_calibration_error(p, np.searchsorted(m.classes_, te_ds.y)))
        probs_all.append(p)
        y_all.append(te_ds.y)
    return {"accuracy": float(np.mean(accs)), "fold_accuracy": accs, "ece": float(np.mean(eces)),
            "n_folds": len(accs), "source_kinds": ds.source_kinds}


def ablation(ds: MultimodalDataset, fusion: str = "late", scheme: str = "loso") -> dict:
    make = FUSION_MODELS[fusion]
    out = {"all": evaluate_fusion(make, ds, scheme)}
    for m in ds.modalities:
        out[f"only_{m.value}"] = evaluate_fusion(make, ds.subset(np.arange(len(ds.y)), [m]), scheme)
        rest = [k for k in ds.modalities if k != m]
        if rest:
            out[f"without_{m.value}"] = evaluate_fusion(make, ds.subset(np.arange(len(ds.y)), rest), scheme)
    best_uni = max(v["accuracy"] for k, v in out.items() if k.startswith("only_"))
    out["_summary"] = {"fusion": fusion, "scheme": scheme, "all_minus_best_unimodal": out["all"]["accuracy"] - best_uni,
                       "note": "Difference is descriptive; a fusion benefit claim needs a preregistered test on "
                               "real paired data."}
    return out


def measure_latency(model, ds: MultimodalDataset, n_repeats: int = 50) -> dict:
    one = ds.subset(np.arange(1))
    times = []
    for _ in range(n_repeats):
        t0 = time.perf_counter()
        model.predict_proba(one)
        times.append((time.perf_counter() - t0) * 1e3)
    return {"p50_ms": float(np.percentile(times, 50)), "p95_ms": float(np.percentile(times, 95)), "n": n_repeats}


class ModelRegistry:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, model, name: str, ds: MultimodalDataset, metrics: dict, validation_status: str = "UNVALIDATED",
             ) -> dict:
        blob = pickle.dumps(model)
        digest = hashlib.sha256(blob).hexdigest()
        path = self.root / f"{name}-{digest[:12]}.pkl"
        path.write_bytes(blob)
        card = {
            "schema_version": SCHEMA_VERSION, "name": name, "model_class": type(model).__name__,
            "checkpoint": path.name, "checkpoint_sha256": digest, "training_data_sha256": ds.content_hash(),
            "modalities": [m.value for m in ds.modalities], "feature_names": {m.value: n for m, n in
                                                                                 ds.feature_names.items()},
            "source_kinds": ds.source_kinds, "n_training_samples": int(len(ds.y)),
            "n_training_groups": int(len(np.unique(ds.groups))), "metrics": metrics,
            "validation_status": validation_status, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (self.root / f"{name}-{digest[:12]}.json").write_text(json.dumps(card, indent=2, default=float))
        return card

    def load(self, card_file: str):
        card = json.loads((self.root / card_file).read_text())
        blob = (self.root / card["checkpoint"]).read_bytes()
        if hashlib.sha256(blob).hexdigest() != card["checkpoint_sha256"]:
            raise ValueError("checkpoint hash mismatch")
        return pickle.loads(blob), card

    def list(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self.root.glob("*.json"))]


@dataclass
class SyntheticFusionSpec:
    snr: dict[Modality, float] = field(default_factory=lambda: {
        Modality.EEG: 0.8, Modality.ECG: 0.5, Modality.EDA: 0.6, Modality.RESPIRATION: 0.3, Modality.FNIRS: 0.7})
    n_features: int = 4
    missing_rate: float = 0.2


def synthetic_fusion_dataset(n_subjects: int = 8, n_trials: int = 60, spec: SyntheticFusionSpec | None = None,
                             seed: int = 0, effect: float = 1.0) -> MultimodalDataset:
    """SYNTHETIC feature-level dataset: each modality carries independent, noisy evidence about a binary label."""
    spec = spec or SyntheticFusionSpec()
    rng = np.random.default_rng(seed)
    feats = {m: [] for m in spec.snr}
    qual = {m: [] for m in spec.snr}
    ys, gs = [], []
    dirs = {m: rng.normal(0, 1, spec.n_features) for m in spec.snr}
    for s in range(n_subjects):
        offset = {m: rng.normal(0, 0.5, spec.n_features) for m in spec.snr}
        y = rng.integers(0, 2, n_trials)
        for m, snr in spec.snr.items():
            x = rng.normal(0, 1, (n_trials, spec.n_features)) + offset[m]
            x += effect * snr * (2 * y[:, None] - 1) * dirs[m] / np.linalg.norm(dirs[m])
            q = rng.uniform(0.5, 1.0, n_trials)
            miss = rng.random(n_trials) < spec.missing_rate
            x[miss] = np.nan
            q[miss] = 0.0
            feats[m].append(x)
            qual[m].append(q)
        ys.append(y)
        gs.append(np.full(n_trials, s))
    return MultimodalDataset(
        {m: np.vstack(v) for m, v in feats.items()}, {m: np.concatenate(v) for m, v in qual.items()},
        {m: [f"{m.value}_f{i}" for i in range(spec.n_features)] for m in spec.snr},
        np.concatenate(ys), np.concatenate(gs), ["SYNTHETIC"])
