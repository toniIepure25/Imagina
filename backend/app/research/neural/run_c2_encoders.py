"""Real end-to-end C2 Commit 4 encoder training: EEGNet, compact TCN, and
compact contrastive content-state encoders, trained via LOSO on
PERCEPTION-phase visual-content epochs (the target state for the frozen
perception encoder Commit 5's transfer analysis reuses).

Raw epoch arrays are not persisted to disk (matching this project's
established convention of favoring deterministic re-derivation over
checkpoint caching -- see C1's bit-exact reproduction verification).
Training is fully deterministic given a fixed seed/hyperparameters/data,
so Commit 5 reproduces the identical "frozen perception encoder" by
re-running this same training procedure on the same data, rather than by
loading a serialized checkpoint.

Not a CI-run script (real data isn't downloaded in CI). Run manually:

    python -m app.research.neural.run_c2_encoders
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.c2_data import PRIMARY_CONTENT_CLASSES, select_visual_content_trials
from app.research.neural.c2_encoders import (
    CompactContrastiveContentStateEncoder,
    CompactTCNContentEncoder,
    EEGNetContentEncoder,
    content_class_indices,
)
from app.research.neural.c2_models import MulticlassFeatureModel
from app.research.neural.hashing import sha256_file
from app.research.neural.models import participant_grouped_split
from app.research.neural.preprocessing import PreprocessingConfig, preprocess_recording
from app.research.neural.run_c1_confirmatory import DATA_ROOT, discover_subjects

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"
MIN_TRIALS_PER_CLASS = 6
TRAIN_LR = 1e-2
# EEGNet's depthwise/separable design converges more slowly than the TCN's
# simpler dilated-conv stack (verified empirically on synthetic data before
# this real run: EEGNet needed ~100 epochs to clear chance-level accuracy
# reliably, while the TCN reached comparable accuracy by ~60), and EEGNet
# is also the more expensive architecture per epoch -- separate budgets
# keep the real run's wall-clock time proportionate to what each
# architecture actually needs, rather than over- or under-training either.
EPOCHS_BY_KIND = {"eegnet": 100, "tcn": 60, "contrastive": 60}


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def build_perception_epochs_for_subject(sub: str, session: str = "1"):
    """Returns (epochs: np.ndarray[n,ch,samples], labels: np.ndarray[str],
    n_channels, n_samples) or (None, None, None, None) if unusable."""
    adapter = YotoAdapter(data_root=str(DATA_ROOT))
    recording, trials = adapter.ingest_recording(sub, session, "task")
    perception_trials = select_visual_content_trials(trials, "perception")
    if len(perception_trials) < MIN_TRIALS_PER_CLASS * 3:
        return None, None, None, None

    data_root = Path(DATA_ROOT)
    vhdr = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.vhdr"
    eeg = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.eeg"
    if not vhdr.exists() or not eeg.exists():
        return None, None, None, None

    raw = mne.io.read_raw_brainvision(str(vhdr), preload=False, verbose="ERROR")
    raw_hash = sha256_file(str(eeg))
    config = PreprocessingConfig(run_ica=True)
    epochs_by_cond, kept, manifest = preprocess_recording(raw, perception_trials, raw_hash, config)
    if "perception" not in epochs_by_cond or len(kept) < MIN_TRIALS_PER_CLASS * 3:
        return None, None, None, None

    labels = np.array([t.stimulus_id for t in kept])
    from collections import Counter
    counts = Counter(labels.tolist())
    if any(counts.get(c, 0) < MIN_TRIALS_PER_CLASS for c in PRIMARY_CONTENT_CLASSES):
        return None, None, None, None

    epochs = epochs_by_cond["perception"]
    return epochs, labels, epochs.shape[1], epochs.shape[2]


def run_encoder_loso(
    pooled_x: np.ndarray, pooled_y: np.ndarray, pooled_ids: list[str],
    n_channels: int, n_samples: int, encoder_kind: str,
) -> list[dict]:
    """One LOSO sweep for one encoder architecture on the content target."""
    participants = sorted(set(pooled_ids))
    fold_results = []
    for held_out in participants:
        train_mask, test_mask = participant_grouped_split(pooled_ids, held_out=held_out)
        x_train, y_train = pooled_x[train_mask], pooled_y[train_mask]
        x_test, y_test = pooled_x[test_mask], pooled_y[test_mask]
        if len(x_test) < 2:
            continue

        if encoder_kind in ("eegnet", "tcn"):
            cls = EEGNetContentEncoder if encoder_kind == "eegnet" else CompactTCNContentEncoder
            enc = cls(n_channels, n_samples, n_classes=3, seed=42)
            y_train_idx = content_class_indices(y_train)
            enc.fit(x_train, y_train_idx, n_epochs=EPOCHS_BY_KIND[encoder_kind], lr=TRAIN_LR)
            proba = enc.predict_proba(x_test)
            y_test_idx = content_class_indices(y_test)
            pred_idx = proba.argmax(axis=1)
            eps = 1e-12
            log_loss = float(-np.mean(np.log(np.clip(proba[np.arange(len(y_test_idx)), y_test_idx], eps, 1))))
            balanced_acc = float(np.mean([
                np.mean(pred_idx[y_test_idx == c] == c) for c in set(y_test_idx.tolist()) if np.any(y_test_idx == c)
            ]))
            spec = enc.to_spec(f"c2_encoder_{encoder_kind}_fold_{held_out}")
        elif encoder_kind == "contrastive":
            enc = CompactContrastiveContentStateEncoder(n_channels, n_samples, embedding_dim=16, seed=42)
            enc.fit(x_train, y_train, n_epochs=EPOCHS_BY_KIND["contrastive"])
            z_train, z_test = enc.embed(x_train), enc.embed(x_test)
            probe = MulticlassFeatureModel(l2=1.0)
            probe.fit(z_train, y_train)
            metrics = probe.evaluate(z_test, y_test)
            log_loss = metrics["class_weighted_log_loss"]
            balanced_acc = metrics["balanced_accuracy"]
            spec = enc.to_spec(f"c2_encoder_{encoder_kind}_fold_{held_out}")
        else:
            raise ValueError(f"unknown encoder_kind: {encoder_kind!r}")

        fold_results.append({
            "held_out_participant": held_out, "n_train": len(x_train), "n_test": len(x_test),
            "log_loss": log_loss, "balanced_accuracy": balanced_acc,
            "architecture": spec.architecture, "param_count": spec.param_count,
            "seed": spec.random_seed, "train_time_s": spec.train_time_s,
            "inference_time_s": spec.inference_time_s, "checkpoint_hash": spec.checkpoint_hash,
        })
        print(
            f"  [{encoder_kind}] held_out={held_out} log_loss={log_loss:.4f} bal_acc={balanced_acc:.4f}",
            file=sys.stderr,
        )
    return fold_results


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)
    code_sha = _code_sha()

    pooled_x, pooled_y, pooled_ids = [], [], []
    included, excluded = [], {}
    n_channels = n_samples = None

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            epochs, labels, nc, ns = build_perception_epochs_for_subject(sub)
        except Exception as e:
            excluded[sub] = f"exception during processing: {e}"
            continue
        if epochs is None:
            excluded[sub] = "unusable perception epochs (too few trials or missing floor classes)"
            continue
        included.append(sub)
        n_channels, n_samples = nc, ns
        pooled_x.append(epochs)
        pooled_y.append(labels)
        pooled_ids.extend([sub] * len(labels))

    print(f"Included: {len(included)} -> {included}", file=sys.stderr)
    print(f"Excluded: {excluded}", file=sys.stderr)

    pooled_x = np.concatenate(pooled_x, axis=0).astype(np.float32)
    pooled_y = np.concatenate(pooled_y, axis=0)

    results = {}
    for kind in ("eegnet", "tcn", "contrastive"):
        print(f"Running LOSO for encoder={kind} ...", file=sys.stderr)
        fold_results = run_encoder_loso(pooled_x, pooled_y, pooled_ids, n_channels, n_samples, kind)
        log_losses = [f["log_loss"] for f in fold_results]
        bal_accs = [f["balanced_accuracy"] for f in fold_results]
        results[kind] = {
            "n_folds": len(fold_results),
            "class_weighted_log_loss": {
                "mean": float(np.mean(log_losses)) if log_losses else float("nan"),
                "std": float(np.std(log_losses)) if log_losses else float("nan"),
                "per_participant": {f["held_out_participant"]: f["log_loss"] for f in fold_results},
            },
            "balanced_accuracy": {
                "mean": float(np.mean(bal_accs)) if bal_accs else float("nan"),
                "std": float(np.std(bal_accs)) if bal_accs else float("nan"),
                "per_participant": {f["held_out_participant"]: f["balanced_accuracy"] for f in fold_results},
            },
            "per_fold": fold_results,
        }

    created_at = datetime.now(timezone.utc).isoformat()

    # Merge into the existing c2_content_decoding.json (Commit 3 baselines +
    # Commit 4 encoders), so all content-decoding evidence lives in one artifact.
    content_path = RESULTS_DIR / "c2_content_decoding.json"
    existing = json.loads(content_path.read_text(encoding="utf-8")) if content_path.exists() else {}
    existing["code_sha"] = code_sha
    existing["created_at"] = created_at
    existing["encoders"] = {
        "training_window": "perception_phase_full_2s",
        "training_hyperparameters": {
            "epochs_by_kind": EPOCHS_BY_KIND, "lr": TRAIN_LR,
        },
        "included_participants": included, "excluded_subjects": excluded,
        "n_channels": n_channels, "n_samples": n_samples,
        "results": results,
        "note": (
            "Encoders trained on PERCEPTION-phase epochs specifically, since this is the "
            "'frozen perception encoder' Commit 5's transfer analysis (perception train -> "
            "imagery test) reuses. Not persisted as a checkpoint file -- training is "
            "deterministic given the fixed seed/hyperparameters/data here, so Commit 5 "
            "reproduces the identical encoder by re-running this same procedure."
        ),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(content_path, "w") as f:
        json.dump(existing, f, indent=2, default=str)
    print(f"Updated {content_path} with Commit 4 encoder results", file=sys.stderr)


if __name__ == "__main__":
    main()
