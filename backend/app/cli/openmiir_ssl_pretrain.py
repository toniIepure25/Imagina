"""OpenMIIR SSL Pretraining v4.5 — SimCLR-style contrastive learning for EEG.

Real PyTorch training with GPU support, NT-Xent loss, and augmentation views.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
MODELS_DIR = os.path.join(EXPORTS, "models")
FIGURES_DIR = os.path.join(EXPORTS, "figures")

TASKS_DEF = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_pretrain")
    p.add_argument("--tensor-file", default=None)
    p.add_argument("--encoder", default="temporal_cnn")
    p.add_argument("--embedding-dim", type=int, default=128)
    p.add_argument("--projection-dim", type=int, default=64)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--device", default="auto")
    p.add_argument("--quick", type=str, default="false")
    p.add_argument("--output-prefix", default="openmiir_ssl_pretrain_experimental")
    return p


def nt_xent_loss(z1, z2, temperature=0.2):
    z = torch.cat([z1, z2], dim=0)
    sim = torch.mm(z, z.t()) / temperature
    n = z1.shape[0]
    labels = torch.cat([torch.arange(n) + n, torch.arange(n)]).to(z.device)
    mask = torch.eye(2 * n, device=z.device).bool()
    sim = sim.masked_fill(mask, -1e9)
    return F.cross_entropy(sim, labels)


def _linear_probe(embeddings, y_cond, y_subj, tasks_def, n_perm=50):
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
                p_val = float(np.mean(ns >= real))
                task_res[best_mn]["perm_p"] = round(p_val, 4)
                task_res[best_mn]["above_chance"] = p_val < 0.05
        results[tn] = task_res
    return results


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    tensor_path = args.tensor_file or os.path.join(EXPORTS, "openmiir_ssl_epoch_tensors_experimental.npz")
    if not os.path.exists(tensor_path):
        print("Tensor file not found", file=sys.stderr)
        return 1

    data = np.load(tensor_path, allow_pickle=True)
    X, y_cond, y_subj = data["X"], data["y_cond"], data["y_subj"]
    n_epochs, n_ch, n_times = X.shape

    # Device
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    quick = args.quick.lower() in ("true", "1", "yes")
    train_epochs = min(args.epochs, 5 if quick else args.epochs)
    batch_size = args.batch_size

    print(f"Device: {device}, epochs: {train_epochs}, samples: {n_epochs}, "
          f"shape: ({n_ch}, {n_times})", file=sys.stderr)

    from app.models.eeg_ssl_encoder import ProjectionHead, get_encoder
    from app.services.eeg_ssl_augmentations import make_ssl_views

    # Build model
    encoder = get_encoder(args.encoder, n_ch, n_times, args.embedding_dim).to(device)
    projector = ProjectionHead(args.embedding_dim, args.projection_dim).to(device)
    optimizer = torch.optim.AdamW(list(encoder.parameters()) + list(projector.parameters()),
                                   lr=args.lr, weight_decay=1e-5)

    # Data loader
    X_tensor = torch.FloatTensor(X)
    dataset = TensorDataset(X_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    # Training
    loss_history = []
    aug_config = {"noise_std": 0.05, "time_mask_ratio": 0.125, "ch_drop_ratio": 0.1}

    print(f"Training {args.encoder} for {train_epochs} epochs...", file=sys.stderr)

    for epoch in range(train_epochs):
        encoder.train()
        projector.train()
        epoch_losses = []

        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            v1, v2 = make_ssl_views(batch_x, aug_config)
            v1, v2 = v1.to(device), v2.to(device)

            z1 = projector(encoder(v1))
            z2 = projector(encoder(v2))

            loss = nt_xent_loss(z1, z2, temperature=0.2)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_losses.append(loss.item())

        avg_loss = float(np.mean(epoch_losses))
        loss_history.append(avg_loss)
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1}/{train_epochs}: loss={avg_loss:.4f}", file=sys.stderr)

    final_loss = loss_history[-1] if loss_history else float("inf")

    # Save checkpoint
    ckpt_path = os.path.join(MODELS_DIR, f"{args.output_prefix}.pt")
    torch.save({
        "encoder_state": encoder.state_dict(),
        "projector_state": projector.state_dict(),
        "config": {"encoder": args.encoder, "embedding_dim": args.embedding_dim,
                    "projection_dim": args.projection_dim, "n_channels": n_ch,
                    "n_times": n_times},
        "loss_history": loss_history,
        "final_loss": final_loss,
    }, ckpt_path)

    # Extract embeddings
    encoder.eval()
    all_embeddings = []
    bs = 128
    with torch.no_grad():
        for i in range(0, n_epochs, bs):
            batch_x = X_tensor[i:i + bs].to(device)
            emb = encoder(batch_x).cpu().numpy()
            all_embeddings.append(emb)
    embeddings = np.concatenate(all_embeddings, axis=0)

    # Save embeddings
    emb_path = os.path.join(EXPORTS, "openmiir_ssl_embeddings_experimental.npz")
    np.savez_compressed(emb_path, embeddings=embeddings, y_cond=y_cond,
                         y_subj=y_subj)

    # Linear probe
    results = _linear_probe(embeddings, y_cond, y_subj, TASKS_DEF, args.epochs // 2)
    best_per_task = {}
    for tn, tr in results.items():
        best = max(tr.items(), key=lambda x: x[1].get("mean_bal_acc", 0)) if tr else (None, {})
        best_per_task[tn] = {"model": best[0], "bal_acc": best[1].get("mean_bal_acc", 0),
                             "perm_p": best[1].get("perm_p"),
                             "above_chance": best[1].get("above_chance", False)}

    # Training report
    report = {
        "tool": "openmiir_ssl_pretrain_v4.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_mode": "experimental_hypothesis_only",
        "not_for_scientific_claims": True,
        "production_valid": False,
        "production_unlock_allowed": False,
        "no_raw_eeg_exposed": True,
        "encoder_type": args.encoder,
        "loss_type": "nt_xent_simclr",
        "n_epochs_trained": train_epochs,
        "final_loss": round(final_loss, 4),
        "best_loss": round(min(loss_history), 4) if loss_history else None,
        "device": str(device),
        "embedding_dim": args.embedding_dim,
        "projection_dim": args.projection_dim,
        "n_epochs_total": n_epochs,
        "n_subjects": len(np.unique(y_subj)),
        "best_model_per_task": best_per_task,
        "task_results": results,
        "loss_history": [round(val, 4) for val in loss_history],
    }

    json_path = os.path.join(EXPORTS, f"{args.output_prefix}.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Loss CSV
    loss_csv = os.path.join(EXPORTS, f"{args.output_prefix}_loss_curve.csv")
    with open(loss_csv, "w") as f:
        f.write("epoch,loss\n")
        for i, val in enumerate(loss_history):
            f.write(f"{i + 1},{val:.4f}\n")

    # Training curve figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(range(1, len(loss_history) + 1), loss_history, color="steelblue")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("NT-Xent Loss")
        ax.set_title(f"SSL Training — {args.encoder} (Exp. Only)", fontsize=10)
        fig.tight_layout()
        fig.savefig(os.path.join(FIGURES_DIR, f"{args.output_prefix}_training_curve.png"),
                    dpi=150, facecolor="white")
        plt.close(fig)
    except Exception:
        pass

    print(f"SSL pretrain: encoder={args.encoder} epochs={train_epochs} "
          f"final_loss={final_loss:.4f} probe_tasks={len(results)}", file=sys.stderr)
    for tn, bm in best_per_task.items():
        print(f"  {tn}: {bm['model']} bal={bm['bal_acc']:.3f} p={bm.get('perm_p','N/A')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
