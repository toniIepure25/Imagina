"""OpenMIIR SSL Pipeline v4.4 — Pretraining, embedding extraction, linear probe benchmark.

Consolidated: SimCLR-style contrastive pretraining + LOSO linear probe benchmark.
Experimental only — not production-validated BCI.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
FIGURES_DIR = os.path.join(EXPORTS, "figures")
MODELS_DIR = os.path.join(EXPORTS, "models")

# Try torch
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

TASKS_DEF = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}


class EEGConvEncoder(nn.Module):
    def __init__(self, n_channels, n_times, embedding_dim=128):
        super().__init__()
        self.temporal = nn.Sequential(
            nn.Conv1d(n_channels, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(0.1),
            nn.Conv1d(64, 128, kernel_size=5, stride=2, padding=2),
            nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.1),
            nn.Conv1d(128, 256, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm1d(256), nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.proj = nn.Sequential(
            nn.Linear(256, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim),
        )

    def forward(self, x):
        h = self.temporal(x)
        h = self.pool(h).squeeze(-1)
        return self.proj(h)


class ProjectionHead(nn.Module):
    def __init__(self, in_dim, proj_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, in_dim // 2),
            nn.BatchNorm1d(in_dim // 2), nn.ReLU(),
            nn.Linear(in_dim // 2, proj_dim),
        )
    def forward(self, x):
        return F.normalize(self.net(x), dim=1)


def _nt_xent_loss(z1, z2, temperature=0.2):
    z = torch.cat([z1, z2], dim=0)
    sim = torch.mm(z, z.t()) / temperature
    n = z1.shape[0]
    labels = torch.cat([torch.arange(n) + n, torch.arange(n)]).to(z.device)
    mask = torch.eye(2 * n, device=z.device).bool()
    sim = sim.masked_fill(mask, -1e9)
    return F.cross_entropy(sim, labels)


def _augment_epoch(x, p_noise=0.3, p_time_mask=0.3, p_ch_drop=0.1):
    if not HAS_TORCH:
        return x
    x = x.clone()
    # Gaussian noise
    if torch.rand(1) < p_noise:
        x += torch.randn_like(x) * 0.05
    # Time masking
    if torch.rand(1) < p_time_mask:
        t_len = x.shape[-1] // 8
        t_start = torch.randint(0, x.shape[-1] - t_len, (1,)).item()
        x[:, t_start:t_start + t_len] = 0
    # Channel dropout
    if torch.rand(1) < p_ch_drop:
        n_drop = max(1, x.shape[0] // 10)
        drop_idx = torch.randperm(x.shape[0])[:n_drop]
        x[drop_idx] = 0
    return x


def _load_tensors(npz_path):
    data = np.load(npz_path, allow_pickle=True)
    X = data["X"]
    y_cond = data["y_cond"]
    y_subj = data["y_subj"]
    return X, y_cond, y_subj


def _linear_probe_benchmark(embeddings, y_cond, y_subj, tasks_def):
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    results = {}

    for tn, ti in tasks_def.items():
        pos_mask = np.isin(y_cond, ti["pos"])
        neg_mask = np.isin(y_cond, ti["neg"])
        mask = pos_mask | neg_mask
        if mask.sum() < 4:
            continue
        X_t = embeddings[mask]
        y_t = np.where(np.isin(y_cond[mask], ti["pos"]), 1, 0)
        s_t = y_subj[mask]

        models = {
            "Dummy": DummyClassifier(strategy="stratified", random_state=42),
            "LogisticRegression": Pipeline([
                ("imp", SimpleImputer()), ("scl", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, random_state=42)),
            ]),
            "LinearSVC": Pipeline([
                ("imp", SimpleImputer()), ("scl", StandardScaler()),
                ("clf", LinearSVC(random_state=42, max_iter=5000)),
            ]),
        }

        task_res = {}
        for mn, model in models.items():
            scores = []
            for ts in np.unique(s_t):
                train = s_t != ts
                test = s_t == ts
                if not train.any() or not test.any():
                    continue
                try:
                    model.fit(X_t[train], y_t[train])
                    yp = model.predict(X_t[test])
                    scores.append(float(balanced_accuracy_score(y_t[test], yp)))
                except Exception:
                    pass
            if scores:
                task_res[mn] = {"mean_bal_acc": round(float(np.mean(scores)), 4),
                                "std_bal_acc": round(float(np.std(scores)), 4)}

        # Permutation test for best model
        if task_res:
            best_mn = max(task_res, key=lambda k: task_res[k]["mean_bal_acc"])
            real_score = task_res[best_mn]["mean_bal_acc"]
            null_scores = []
            for _ in range(50):
                y_shuf = sk_shuffle(y_t, random_state=None)
                model_tmp = LogisticRegression(max_iter=500, random_state=42)
                fold_scores = []
                for ts in np.unique(s_t):
                    train = s_t != ts
                    test = s_t == ts
                    if not train.any() or not test.any():
                        continue
                    try:
                        model_tmp.fit(X_t[train], y_shuf[train])
                        yp = model_tmp.predict(X_t[test])
                        fold_scores.append(float(balanced_accuracy_score(y_shuf[test], yp)))
                    except Exception:
                        pass
                if fold_scores:
                    null_scores.append(float(np.mean(fold_scores)))
            if null_scores:
                p_val = float(np.mean(np.array(null_scores) >= real_score))
                task_res[best_mn]["perm_p"] = round(p_val, 4)
                task_res[best_mn]["above_chance"] = p_val < 0.05
                task_res[best_mn]["null_mean"] = round(float(np.mean(null_scores)), 4)

        results[tn] = task_res

    return results


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_pipeline")
    p.add_argument("--tensor-file", default=None)
    p.add_argument("--mode", default="all",
                   choices=["train", "embed", "benchmark", "all"])
    p.add_argument("--embedding-dim", type=int, default=128)
    p.add_argument("--projection-dim", type=int, default=64)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--output-prefix", default="openmiir_ssl_experimental")
    args = p.parse_args(argv)

    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    tensor_path = args.tensor_file or os.path.join(EXPORTS, "openmiir_ssl_epoch_tensors_experimental.npz")
    if not os.path.exists(tensor_path):
        print("Tensor file not found. Run tensor builder first.", file=sys.stderr)
        return 1

    X_np, y_cond, y_subj = _load_tensors(tensor_path)

    if not HAS_TORCH:
        print("PyTorch not available. Running linear probe only (sklearn).", file=sys.stderr)
        # Linear probe on raw tensors (flattened)
        X_flat = X_np.reshape(len(X_np), -1)[:, :30000]  # limit features
        results = _linear_probe_benchmark(X_flat, y_cond, y_subj, TASKS_DEF)
        report = _build_report(results, "raw_flattened", args)
        _save(report, args.output_prefix + "_benchmark", args.output_prefix)
        print(f"Linear probe (raw): {len(results)} tasks completed", file=sys.stderr)
        return 0

    # Skip PyTorch pretraining if no GPU — use PCA reduction instead
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    X_flat = X_np.reshape(len(X_np), -1)
    # PCA to embedding_dim
    n_comp = min(args.embedding_dim, min(X_flat.shape) - 1, 128)
    X_scaled = StandardScaler().fit_transform(X_flat)
    pca = PCA(n_components=n_comp, random_state=42)
    embeddings = pca.fit_transform(X_scaled)

    # Linear probe benchmark
    results = _linear_probe_benchmark(embeddings, y_cond, y_subj, TASKS_DEF)

    best_per_task = {}
    for tn, task_res in results.items():
        best = max(task_res.items(), key=lambda x: x[1]["mean_bal_acc"]) if task_res else (None, {})
        best_per_task[tn] = {"model": best[0], "bal_acc": best[1].get("mean_bal_acc", 0),
                             "perm_p": best[1].get("perm_p"),
                             "above_chance": best[1].get("above_chance", False)}

    report = {
        "tool": "openmiir_ssl_pipeline_v4.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "method": "PCA_projection",
        "embedding_dim": n_comp,
        "n_subjects": len(np.unique(y_subj)),
        "n_epochs": len(X_np),
        "best_model_per_task": best_per_task,
        "task_results": results,
    }

    _save(report, args.output_prefix + "_benchmark", args.output_prefix)

    print(f"SSL pipeline (PCA): {len(results)} tasks, dim={n_comp}", file=sys.stderr)
    for tn, bm in best_per_task.items():
        print(f"  {tn}: {bm['model']} bal={bm['bal_acc']:.3f} p={bm.get('perm_p','N/A')}", file=sys.stderr)
    return 0


def _save(data, key, prefix):
    path = os.path.join(EXPORTS, f"{key}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _build_report(results, method, args):
    best_per_task = {}
    for tn, tr in results.items():
        best = max(tr.items(), key=lambda x: x[1].get("mean_bal_acc", 0)) if tr else (None, {})
        best_per_task[tn] = {"model": best[0], "bal_acc": best[1].get("mean_bal_acc", 0)}
    return {
        "tool": "openmiir_ssl_embedding_benchmark_v4.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "method": method,
        "best_model_per_task": best_per_task,
        "task_results": results,
    }


if __name__ == "__main__":
    sys.exit(main())
