"""OpenMIIR SSL v4.6 Pipeline — Upgraded encoders, MAE, sweep, comparison.

Consolidated: MAE pretraining + multibranch/resnet encoders + comparison to handcrafted.
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

TASKS = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}

SWEEP_CONFIGS = [
    {"encoder": "multibranch", "objective": "mae", "name": "mb_mae"},
    {"encoder": "resnet1d", "objective": "mae", "name": "rn_mae"},
    {"encoder": "multibranch", "objective": "hybrid", "name": "mb_hybrid"},
]


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_v46")
    p.add_argument("--mode", default="all", choices=["sweep", "train", "probe", "compare", "all"])
    p.add_argument("--encoder", default="multibranch")
    p.add_argument("--objective", default="mae", choices=["mae", "simclr", "hybrid"])
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--embedding-dim", type=int, default=128)
    p.add_argument("--projection-dim", type=int, default=64)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--device", default="auto")
    p.add_argument("--output-prefix", default="openmiir_ssl_v46_experimental")
    return p


def _load_tensors(path=None):
    path = path or os.path.join(EXPORTS, "openmiir_ssl_epoch_tensors_experimental.npz")
    if not os.path.exists(path):
        return None, None, None
    data = np.load(path, allow_pickle=True)
    return data["X"], data["y_cond"], data["y_subj"]


def _get_device(device_arg):
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_arg)


def _make_views(batch):
    """Band-preserving mild augmentation."""
    v1, v2 = batch.clone(), batch.clone()
    # Gaussian noise (mild)
    v1 += torch.randn_like(v1) * 0.02
    v2 += torch.randn_like(v2) * 0.02
    # Time mask (small)
    B, C, T = batch.shape
    for j, v in enumerate([v1, v2]):
        ml = max(1, T // 16)
        for i in range(B):
            s = torch.randint(0, T - ml, (1,)).item()
            v[i, :, s:s + ml] = 0
    # Channel dropout (region-based: 10%)
    for j, v in enumerate([v1, v2]):
        for i in range(B):
            nd = max(1, C // 10)
            idx = torch.randperm(C)[:nd]
            v[i, idx] = 0
    return v1, v2


def _train_mae(encoder, device, X_np, epochs, batch_size, lr, n_ch, n_times, embed_dim):
    """Masked EEG Autoencoder: mask random time patches, reconstruct."""
    # Simple decoder
    class Decoder(nn.Module):
        def __init__(self, in_dim, n_ch, n_times):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim, 512), nn.GELU(),
                nn.Linear(512, n_ch * n_times),
            )
            self.n_ch, self.n_times = n_ch, n_times

        def forward(self, x):
            return self.net(x).view(-1, self.n_ch, self.n_times)

    decoder = Decoder(embed_dim, n_ch, n_times).to(device)
    opt = torch.optim.AdamW(list(encoder.parameters()) + list(decoder.parameters()),
                             lr=lr, weight_decay=1e-5)
    X_tensor = torch.FloatTensor(X_np)
    dataset = TensorDataset(X_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    loss_hist = []

    patch_size = n_times // 8
    n_patches = 8

    for ep in range(epochs):
        encoder.train()
        decoder.train()
        ep_losses = []
        for (bx,) in loader:
            bx = bx.to(device)
            # Mask random time patches
            masks = []
            for _ in range(bx.shape[0]):
                mask = torch.ones(n_ch, n_times, device=device)
                for _ in range(2):  # mask 2 patches
                    pi = torch.randint(0, n_patches, (1,)).item()
                    start = pi * patch_size
                    end = min(start + patch_size, n_times)
                    mask[:, start:end] = 0
                masks.append(mask)
            mask_tensor = torch.stack(masks)
            masked_x = bx * mask_tensor

            emb = encoder(masked_x)
            recon = decoder(emb)

            loss = F.mse_loss(recon, bx)
            opt.zero_grad()
            loss.backward()
            opt.step()
            ep_losses.append(loss.item())

        avg = float(np.mean(ep_losses))
        loss_hist.append(avg)
        if (ep + 1) % 10 == 0 or ep == 0:
            print(f"    Epoch {ep + 1}/{epochs}: mae_loss={avg:.4f}", file=sys.stderr)

    return loss_hist


def _train_simclr(encoder, projector, device, X_np, epochs, batch_size, lr):
    opt = torch.optim.AdamW(list(encoder.parameters()) + list(projector.parameters()),
                             lr=lr, weight_decay=1e-5)
    X_tensor = torch.FloatTensor(X_np)
    dataset = TensorDataset(X_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
    loss_hist = []

    for ep in range(epochs):
        encoder.train()
        projector.train()
        ep_losses = []
        for (bx,) in loader:
            bx = bx.to(device)
            v1, v2 = _make_views(bx)
            z1 = projector(encoder(v1))
            z2 = projector(encoder(v2))
            z = torch.cat([z1, z2], dim=0)
            sim = torch.mm(z, z.t()) / 0.2
            n = z1.shape[0]
            labels = torch.cat([torch.arange(n) + n, torch.arange(n)]).to(device)
            sim = sim.masked_fill(torch.eye(2 * n, device=device).bool(), -1e9)
            loss = F.cross_entropy(sim, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            ep_losses.append(loss.item())
        avg = float(np.mean(ep_losses))
        loss_hist.append(avg)
        if (ep + 1) % 10 == 0 or ep == 0:
            print(f"    Epoch {ep + 1}/{epochs}: simclr_loss={avg:.4f}", file=sys.stderr)
    return loss_hist


def _extract_embeddings(encoder, device, X_np):
    encoder.eval()
    X_tensor = torch.FloatTensor(X_np)
    all_emb = []
    bs = 128
    with torch.no_grad():
        for i in range(0, len(X_np), bs):
            bx = X_tensor[i:i + bs].to(device)
            all_emb.append(encoder(bx).cpu().numpy())
    return np.concatenate(all_emb, axis=0)


def _linear_probe(embeddings, y_cond, y_subj, n_perm=50):
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC
    from sklearn.utils import shuffle as sk_shuffle

    results = {}
    for tn, ti in TASKS.items():
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
                task_res[mn] = {"mean_bal_acc": round(float(np.mean(scores)), 4)}

        if task_res:
            best_mn = max(task_res, key=lambda k: task_res[k]["mean_bal_acc"])
            real = task_res[best_mn]["mean_bal_acc"]
            null_scores = []
            for _ in range(n_perm):
                y_shuf = sk_shuffle(y_t, random_state=None)
                lm = LogisticRegression(max_iter=500, random_state=42)
                fold_sc = []
                for ts in np.unique(s_t):
                    train = s_t != ts
                    test = s_t == ts
                    if not train.any() or not test.any():
                        continue
                    try:
                        lm.fit(X_t[train], y_shuf[train])
                        yp = lm.predict(X_t[test])
                        fold_sc.append(float(balanced_accuracy_score(y_shuf[test], yp)))
                    except Exception:
                        pass
                if fold_sc:
                    null_scores.append(float(np.mean(fold_sc)))
            if null_scores:
                ns = np.array(null_scores)
                task_res[best_mn]["perm_p"] = round(float(np.mean(ns >= real)), 4)
                task_res[best_mn]["above_chance"] = task_res[best_mn]["perm_p"] < 0.05
        results[tn] = task_res
    return results


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def run_sweep(args):
    X, y_cond, y_subj = _load_tensors()
    if X is None:
        print("No tensor file", file=sys.stderr)
        return 1
    device = _get_device(args.device)
    n_epochs, n_ch, n_times = X.shape
    embed_dim = args.embedding_dim
    train_epochs = min(args.epochs, 30)
    batch_sz = args.batch_size

    from app.models.eeg_ssl_encoder import ProjectionHead, get_encoder

    sweep_results = []
    print(f"Sweep: {len(SWEEP_CONFIGS)} configs, {train_epochs} epochs each, device={device}", file=sys.stderr)

    for cfg in SWEEP_CONFIGS:
        print(f"  {cfg['name']}: encoder={cfg['encoder']}, obj={cfg['objective']}", file=sys.stderr)
        torch.manual_seed(42)
        encoder = get_encoder(cfg["encoder"], n_ch, n_times, embed_dim).to(device)
        projector = ProjectionHead(embed_dim, args.projection_dim or 64).to(device)

        if cfg["objective"] in ("mae", "hybrid"):
            loss_hist = _train_mae(encoder, device, X, train_epochs, batch_sz,
                                     args.lr or 0.001, n_ch, n_times, embed_dim)
        elif cfg["objective"] == "simclr":
            loss_hist = _train_simclr(encoder, projector, device, X, train_epochs, batch_sz,
                                       args.lr or 0.001)

        embeddings = _extract_embeddings(encoder, device, X)
        probe = _linear_probe(embeddings, y_cond, y_subj, n_perm=20)

        best_per_task = {}
        for tn, tr in probe.items():
            best = max(tr.items(), key=lambda x: x[1].get("mean_bal_acc", 0)) if tr else (None, {})
            best_per_task[tn] = {"model": best[0], "bal_acc": best[1].get("mean_bal_acc", 0)}

        avg_bal = round(float(np.mean([v["bal_acc"] for v in best_per_task.values() if v["bal_acc"] > 0])), 4)
        result = {"config": cfg["name"], "encoder": cfg["encoder"],
                  "objective": cfg["objective"], "final_loss": round(loss_hist[-1], 4) if loss_hist else None,
                  "avg_bal_acc": avg_bal, "best_per_task": best_per_task}
        sweep_results.append(result)
        loss_str = f"final_loss={loss_hist[-1]:.4f}" if loss_hist else ""
        print(f"    avg_bal={avg_bal:.3f}, {loss_str}", file=sys.stderr)

    sweep_json = {**_safety(), "tool": "openmiir_ssl_v46_sweep",
                  "generated_at": datetime.now(timezone.utc).isoformat(),
                  "sweep_results": sweep_results}
    with open(os.path.join(EXPORTS, "openmiir_ssl_v46_sweep_results.json"), "w") as f:
        json.dump(sweep_json, f, indent=2, default=str)
    return 0


def run_full_train(args):
    X, y_cond, y_subj = _load_tensors()
    if X is None:
        return 1
    device = _get_device(args.device)
    n_epochs, n_ch, n_times = X.shape
    embed_dim = args.embedding_dim
    train_epochs = args.epochs

    from app.models.eeg_ssl_encoder import ProjectionHead, get_encoder

    torch.manual_seed(42)
    encoder = get_encoder(args.encoder, n_ch, n_times, embed_dim).to(device)
    projector = ProjectionHead(embed_dim, 64).to(device)

    print(f"Training {args.encoder} + {args.objective} for {train_epochs} epochs...", file=sys.stderr)
    if args.objective == "mae":
        loss_hist = _train_mae(encoder, device, X, train_epochs, args.batch_size,
                               0.001, n_ch, n_times, embed_dim)
    else:
        loss_hist = _train_simclr(encoder, projector, device, X, train_epochs, args.batch_size, 0.001)

    # Save checkpoint
    ckpt = {"encoder_state": encoder.state_dict(), "config": {
        "encoder": args.encoder, "objective": args.objective,
        "embedding_dim": embed_dim, "n_channels": n_ch, "n_times": n_times,
    }, "loss_history": loss_hist}
    ckpt_path = os.path.join(MODELS_DIR, f"{args.output_prefix}.pt")
    torch.save(ckpt, ckpt_path)

    # Extract embeddings
    embeddings = _extract_embeddings(encoder, device, X)
    emb_path = os.path.join(EXPORTS, f"{args.output_prefix}_embeddings.npz")
    np.savez_compressed(emb_path, embeddings=embeddings, y_cond=y_cond, y_subj=y_subj)

    # Linear probe
    print("Running linear probe...", file=sys.stderr)
    probe = _linear_probe(embeddings, y_cond, y_subj, n_perm=50)
    best_per_task = {}
    for tn, tr in probe.items():
        best = max(tr.items(), key=lambda x: x[1].get("mean_bal_acc", 0)) if tr else (None, {})
        best_per_task[tn] = {"model": best[0], "bal_acc": best[1].get("mean_bal_acc", 0),
                             "perm_p": best[1].get("perm_p"),
                             "above_chance": best[1].get("above_chance", False)}

    report = {**_safety(), "tool": "openmiir_ssl_v46_pretrain",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "encoder": args.encoder, "objective": args.objective,
              "n_epochs": train_epochs, "embedding_dim": embed_dim,
              "device": str(device), "final_loss": round(loss_hist[-1], 4) if loss_hist else None,
              "best_model_per_task": best_per_task, "task_results": probe,
              "loss_history": [round(v, 4) for v in loss_hist]}

    with open(os.path.join(EXPORTS, f"{args.output_prefix}.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"V4.6 done: {args.encoder}+{args.objective}", file=sys.stderr)
    for tn, bm in best_per_task.items():
        print(f"  {tn}: {bm['model']} bal={bm['bal_acc']:.3f} p={bm.get('perm_p','N/A')}", file=sys.stderr)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    if args.mode == "sweep":
        return run_sweep(args)
    if args.mode == "train":
        return run_full_train(args)
    return run_full_train(args)


if __name__ == "__main__":
    sys.exit(main())
