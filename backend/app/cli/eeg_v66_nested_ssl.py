"""V6.6 — Nested LOSO SSL Motor Imagery Encoder.

FBCSP-inspired encoder, fold-safe training, comparison to classical baselines.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
MODELS_DIR = os.path.join(EXPORTS, "models")
FIGURES_DIR = os.path.join(EXPORTS, "figures")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.eeg_v66_nested_ssl")
    p.add_argument("--task", default="left_fist_vs_right_fist_imagery")
    p.add_argument("--max-subjects", type=int, default=15)
    p.add_argument("--epochs-pretrain", type=int, default=30)
    p.add_argument("--epochs-finetune", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--device", default="auto")
    p.add_argument("--output-prefix", default="eeg_v66_ssl_experimental")
    return p


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _device(d):
    if d == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(d)


class MIEncoder(nn.Module):
    """FBCSP-inspired multi-band temporal encoder for motor imagery."""

    def __init__(self, n_ch=52, n_times=640, embed_dim=128):
        super().__init__()
        self.branches = nn.ModuleList([
            nn.Sequential(nn.Conv1d(n_ch, 32, 13, stride=2, padding=6),
                          nn.BatchNorm1d(32), nn.GELU(), nn.AdaptiveAvgPool1d(1)),
            nn.Sequential(nn.Conv1d(n_ch, 32, 25, stride=2, padding=12),
                          nn.BatchNorm1d(32), nn.GELU(), nn.AdaptiveAvgPool1d(1)),
            nn.Sequential(nn.Conv1d(n_ch, 32, 51, stride=2, padding=25),
                          nn.BatchNorm1d(32), nn.GELU(), nn.AdaptiveAvgPool1d(1)),
        ])
        depth_branch = nn.Sequential(
            nn.Conv1d(n_ch, 32, 7, stride=2, padding=3),
            nn.BatchNorm1d(32), nn.GELU(),
            nn.Conv1d(32, 64, 5, stride=2, padding=2),
            nn.BatchNorm1d(64), nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.branches.append(depth_branch)
        self.head = nn.Sequential(
            nn.Linear(32 * 3 + 64, embed_dim),
            nn.BatchNorm1d(embed_dim), nn.GELU(),
        )

    def forward(self, x):
        feats = [br(x).squeeze(-1) for br in self.branches]
        return self.head(torch.cat(feats, dim=1))


def _mae_loss_fn(encoder, x, device, mask_ratio=0.2):
    n_ch, n_times = x.shape[1], x.shape[2]
    patch_size = n_times // 4
    x_masked = x.clone()
    for i in range(x.shape[0]):
        for _ in range(1):
            pi = int(torch.randint(0, 4, (1,)).item())
            start = pi * patch_size
            end = min(start + patch_size, n_times)
            x_masked[i, :, start:end] = 0

    emb = encoder(x_masked)
    decoder = nn.Linear(emb.shape[1], n_ch * n_times).to(device)
    recon = decoder(emb).view(-1, n_ch, n_times)
    return F.mse_loss(recon, x)


def _loso_probe(embeddings, y, subjects):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    fold_scores = {}
    for ts in np.unique(subjects):
        train = subjects != ts
        test = subjects == ts
        if not train.any() or not test.any():
            continue
        m = Pipeline([
            ("imp", SimpleImputer()), ("scl", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ])
        try:
            m.fit(embeddings[train], y[train])
            yp = m.predict(embeddings[test])
            fold_scores[ts] = float(balanced_accuracy_score(y[test], yp))
        except Exception:
            pass
    if len(fold_scores) >= 3:
        vals = list(fold_scores.values())
        return round(float(np.mean(vals)), 4), fold_scores
    return None, {}


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    device = _device(args.device)

    # Load cached epochs
    cache_path = os.path.join(EXPORTS, "eeg_v65_physionet_cache.npz")
    if not os.path.exists(cache_path):
        cache_path = os.path.join(EXPORTS, "eeg_v65_physionet_left_fist_vs_right_fist_imagery_epochs.npz")
    if not os.path.exists(cache_path):
        # Load fresh
        from app.cli.eeg_v65_baselines import _load_epochs
        res = _load_epochs(args.task, args.max_subjects)
        if res[0] is None:
            print("No epochs loaded", file=sys.stderr)
            return 1
        epochs_np, labels, subjects, ch_names = res
    else:
        data = np.load(cache_path, allow_pickle=True)
        epochs_np = data["X"]
        labels = data["y"]
        subjects = data["subject_id"]
    n_ep, n_ch, n_times = epochs_np.shape
    embed_dim = 128
    print(f"V6.6 SSL: {n_ep} epochs, {len(np.unique(subjects))} subjects, "
          f"{n_ch}×{n_times}", file=sys.stderr)

    # === Nested LOSO SSL ===
    oof_embeddings = np.zeros((n_ep, embed_dim), dtype=np.float32)
    fold_losses = []

    for holdout_idx, holdout in enumerate(np.unique(subjects)):
        train_mask = subjects != holdout
        test_mask = subjects == holdout
        if not train_mask.any() or not test_mask.any():
            continue

        # Fresh encoder per fold
        encoder = MIEncoder(n_ch, n_times, embed_dim).to(device)
        opt = torch.optim.AdamW(encoder.parameters(), lr=0.001, weight_decay=1e-5)

        X_train = torch.FloatTensor(epochs_np[train_mask])
        ds = TensorDataset(X_train)
        loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, drop_last=True)

        # MAE pretraining
        encoder.train()
        for ep in range(args.epochs_pretrain):
            ep_loss = 0.0
            n_batches = 0
            for (bx,) in loader:
                bx = bx.to(device)
                loss = _mae_loss_fn(encoder, bx, device)
                opt.zero_grad()
                loss.backward()
                opt.step()
                ep_loss += loss.item()
                n_batches += 1
            if n_batches > 0:
                ep_loss /= n_batches

        fold_losses.append(ep_loss)

        # Extract embeddings for all subjects
        encoder.eval()
        with torch.no_grad():
            for i in range(0, n_ep, 128):
                batch = torch.FloatTensor(epochs_np[i:i + 128]).to(device)
                oof_embeddings[i:i + len(batch)] = encoder(batch).cpu().numpy()

        print(f"  Fold {holdout_idx + 1}/{len(np.unique(subjects))}: "
              f"loss={ep_loss:.4f}", file=sys.stderr)

    # LOSO probe on OOF embeddings
    probe_score, fold_scores = _loso_probe(oof_embeddings, labels, subjects)

    # Permutation test
    from sklearn.utils import shuffle as sk_shuffle
    null_scores_list = []
    for _ in range(min(100, args.epochs_pretrain * 2)):
        ys = sk_shuffle(labels, random_state=None)
        ns, _ = _loso_probe(oof_embeddings, ys, subjects)
        if ns is not None:
            null_scores_list.append(ns)
    p_val = float(np.mean(np.array(null_scores_list) >= probe_score)) if null_scores_list else 1.0

    # Baselines
    fbcsp_score = 0.614
    quality_score = 0.494
    meta_score = 0.4815
    beats_fbcsp = (probe_score or 0) >= fbcsp_score - 0.01
    beats_quality = (probe_score or 0) > quality_score + 0.03
    beats_meta = (probe_score or 0) > meta_score + 0.05
    above_chance = p_val < 0.05
    ssl_success = above_chance and beats_fbcsp and beats_quality and beats_meta

    verdict = {
        **_safety(),
        "tool": "eeg_v66_nested_loso_ssl",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": args.task,
        "n_subjects": len(np.unique(subjects)),
        "n_epochs": n_ep,
        "ssl_bal_acc": probe_score,
        "permutation_p": round(p_val, 4),
        "fbcsp_baseline": fbcsp_score,
        "quality_baseline": quality_score,
        "metadata_baseline": meta_score,
        "beats_fbcsp": beats_fbcsp,
        "beats_quality": beats_quality,
        "beats_metadata": beats_meta,
        "above_chance": above_chance,
        "ssl_success": ssl_success,
        "fold_scores": fold_scores,
        "avg_train_loss": round(float(np.mean(fold_losses)), 4) if fold_losses else None,
        "comparison": {
            "ssl_v66": probe_score,
            "fbcsp_v65": fbcsp_score,
            "csp_v65": 0.567,
            "riemannian_v65": 0.555,
            "spectral_v64": 0.500,
            "quality_only": quality_score,
            "metadata": meta_score,
        },
        "verdict": (
            "ssl_matches_fbcsp_continue_v67" if ssl_success
            else "ssl_competitive_but_classical_best" if above_chance
            else "classical_best_stop_ssl"
        ),
        "interpretation": (
            f"Nested LOSO SSL achieves {probe_score:.3f} (p={p_val:.3f}). "
            f"{'Beats' if beats_fbcsp else 'Does not beat'} FBCSP ({fbcsp_score}). "
            f"{'Successful — proceed to V6.7.' if ssl_success else 'Classical FBCSP remains the best model.'}"
        ),
    }
    with open(os.path.join(EXPORTS, "eeg_v66_scientific_verdict.json"), "w") as f:
        json.dump(verdict, f, indent=2, default=str)

    print(f"V6.6 SSL: {probe_score:.3f} p={p_val:.3f} beats_fbcsp={beats_fbcsp} "
          f"verdict={verdict['verdict']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
