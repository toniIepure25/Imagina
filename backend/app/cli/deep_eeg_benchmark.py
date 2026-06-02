"""Deep EEG benchmark — PyTorch-based EEGNet/ShallowConvNet models for subject classification."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import torch


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _figures_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "figures")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def _models_path(fn):
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", "models")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, fn)


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m app.cli.deep_eeg_benchmark")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--task", default="auto")
    p.add_argument("--model", default="eegnet")
    p.add_argument("--max-subjects", type=int, default=5)
    p.add_argument("--max-windows-per-subject", type=int, default=200)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--output-prefix", default="openmiir_deep_eeg")
    return p


class EEGNet(torch.nn.Module):
    def __init__(self, n_channels, n_classes, n_times=256):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(1, 8, (1, 51), padding=(0, 25), bias=False)
        self.bn1 = torch.nn.BatchNorm2d(8)
        self.conv2 = torch.nn.Conv2d(8, 16, (n_channels, 1), groups=1, bias=False)
        self.bn2 = torch.nn.BatchNorm2d(16)
        self.elu = torch.nn.ELU()
        self.pool = torch.nn.AvgPool2d((1, 4))
        self.dropout = torch.nn.Dropout(0.25)
        fc_in = 16 * (n_times // 16)
        self.fc = torch.nn.Linear(fc_in, n_classes)

    def forward(self, x):
        x = self.elu(self.bn1(self.conv1(x)))
        x = self.pool(x)
        x = self.elu(self.bn2(self.conv2(x)))
        x = self.pool(x)
        x = self.dropout(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


class EEGDataset(torch.utils.data.Dataset):
    def __init__(self, windows, labels):
        self.x = torch.tensor(windows, dtype=torch.float32)
        self.y = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.x)

    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]


def main(argv=None):
    args = build_parser().parse_args(argv)
    import torch

    torch.manual_seed(42)
    np.random.seed(42)

    mp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..",
        "data", "external", args.dataset, "manifest.json",
    )
    if not os.path.exists(mp):
        print(f"No manifest for '{args.dataset}'", file=sys.stderr)
        return 1

    from app.datasets.loaders import safe_read_raw
    from app.datasets.windowing import windows_from_raw
    with open(mp) as f:
        files = json.load(f).get("files", [])[: args.max_subjects]
    if len(files) < 2:
        print("Need >=2 subjects", file=sys.stderr)
        return 1

    all_windows = []
    all_labels = []
    all_subjects = []
    for idx, fif in enumerate(files):
        subj = os.path.splitext(os.path.basename(fif))[0]
        try:
            raw = safe_read_raw(fif)
            dur = min(raw.n_times / raw.info["sfreq"], 30)
            raw.crop(tmax=dur)
            windows = windows_from_raw(raw, max_windows=args.max_windows_per_subject)
            for w in windows:
                if w.samples and len(w.samples) >= 100:
                    arr = np.array(w.samples, dtype=np.float32)
                    chs = min(arr.shape[1], 8)
                    n_times = min(arr.shape[0], 256)
                    all_windows.append(arr[:n_times, :chs].T)
                    all_labels.append(idx)
                    all_subjects.append(subj)
        except Exception:
            pass

    if len(all_windows) < 10:
        print("Not enough windows", file=sys.stderr)
        return 1

    n_classes = len(set(all_labels))
    x_data = np.stack(all_windows)[:, np.newaxis, :, :]
    y_data = np.array(all_labels)
    n_train = int(len(x_data) * 0.7)
    n_val = int(len(x_data) * 0.15)
    indices = np.random.permutation(len(x_data))
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train_ds = EEGDataset(x_data[train_idx], y_data[train_idx])
    val_ds = EEGDataset(x_data[val_idx], y_data[val_idx])
    test_ds = EEGDataset(x_data[test_idx], y_data[test_idx])
    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=args.batch_size)

    n_ch = x_data.shape[2]
    n_t = x_data.shape[3]
    model = EEGNet(n_channels=n_ch, n_classes=n_classes, n_times=n_t)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss()

    train_losses, val_losses = [], []
    best_val = float("inf")
    patience = 5
    no_improve = 0

    for epoch in range(args.epochs):
        model.train()
        tl = 0.0
        for bx, by in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            tl += loss.item()
        train_losses.append(tl / len(train_loader))

        model.eval()
        vl = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                vl += criterion(model(bx), by).item()
        val_losses.append(vl / len(val_loader))

        if val_losses[-1] < best_val:
            best_val = val_losses[-1]
            no_improve = 0
            torch.save(model.state_dict(), _models_path(f"{args.output_prefix}_eegnet.pt"))
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    model.eval()
    te_loader = torch.utils.data.DataLoader(test_ds, batch_size=args.batch_size)
    correct = 0
    total = 0
    with torch.no_grad():
        for bx, by in te_loader:
            pred = model(bx).argmax(dim=1)
            correct += (pred == by).sum().item()
            total += by.size(0)
    test_acc = correct / total if total > 0 else 0

    report = {
        "tool": "imagina_deep_eeg_benchmark",
        "release_candidate": "V3.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "EEGNet",
        "dataset": args.dataset,
        "subjects_used": len(files),
        "windows_used": len(all_windows),
        "n_classes": n_classes,
        "train_size": n_train,
        "val_size": n_val,
        "test_size": len(test_idx),
        "epochs_run": len(train_losses),
        "test_accuracy": round(test_acc, 4),
        "task": "subject_classification_sanity_check",
        "disclaimer": "Deep learning engineering benchmark. Not a validated imagery decoder or clinical tool.",
    }

    jp = _exports_path(f"{args.output_prefix}_benchmark.json")
    rp = _exports_path(f"{args.output_prefix}_benchmark.md")
    with open(jp, "w") as f:
        json.dump(report, f, indent=2, default=str)
    lines = [
        "# Deep EEG Benchmark",
        f"Model: EEGNet | Subjects: {len(files)} | Windows: {len(all_windows)}",
        f"Test accuracy: {test_acc:.4f} | Epochs: {len(train_losses)}",
        "",
        "## Limitations",
        "- Subject classification sanity check only — no condition labels",
        "- Random train/val/test split (not subject-aware)",
        "- Single dataset, small model, brief training",
        "- Not a validated imagery decoder",
    ]
    with open(rp, "w") as f:
        f.write("\n".join(lines))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(train_losses, label="train")
        ax.plot(val_losses, label="val")
        ax.set_title("EEGNet Training Curve")
        ax.legend()
        fig.savefig(_figures_path(f"{args.output_prefix}_training_curve.png"), dpi=100)
        plt.close(fig)
    except Exception:
        pass

    print(f"Deep EEG benchmark: {jp}", file=sys.stderr)
    print(f"  Test accuracy: {test_acc:.4f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
