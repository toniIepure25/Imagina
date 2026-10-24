"""Real end-to-end C2 Commit 5 perception-to-imagery transfer evaluation.

For each LOSO fold, the SAME encoder training procedure Commit 4 used
(identical seed/hyperparameters/architecture) is reproduced
deterministically on perception data, then evaluated on FOUR conditions:

  perception train -> perception test   (primary, reproduces Commit 4)
  perception train -> imagery test      (PRIMARY TRANSFER TARGET, C2-H2)
  imagery train -> imagery test         (secondary)
  imagery train -> perception test      (secondary)

The "imagery" side here uses the EQUAL-DURATION common window (first
COMMON_WINDOW_DURATION_S of the 4.0s imagery phase, reusing
c2_data.build_common_window_imagery_trials) rather than the full imagery
epoch used by Commit 3's classical-feature content baseline or Commit 4's
own perception-only training: perception epochs are 2.0s (500 samples)
while the full imagery phase is 4.0s (1000 samples), and EEGNet/TCN's
architectures bake a fixed input length into their head layer, so a
perception-trained model cannot be evaluated on a different-length
imagery epoch. Truncating to the matched window is not just an
engineering necessity -- it also removes a "more temporal information
available" confound from the transfer comparison itself.

Imagery labels never enter perception-encoder fitting or hyperparameter
selection at any point -- the perception-trained model used for the
transfer evaluation is bit-for-bit the one trained in the "perception
train" step, with imagery data touched only at evaluation time.

Negative controls implemented here (cheap, no retraining required):
  within-participant label shuffle (imagery test labels shuffled before
  scoring the ALREADY-frozen perception-trained model)
  pre-cue EEG (same frozen model, evaluated on the pre-stimulus window
  instead of the imagery window)
Order-only and signal-quality-only nuisance checks are already covered by
Commit 3's baselines (results/c2_content_decoding.json baselines section)
and are referenced, not re-derived. Temporal-shift and channel-permutation
controls are the more expensive, exhaustive falsification battery that
Commit 7 owns for the whole C2 analysis (not duplicated here).

Not a CI-run script (real data isn't downloaded in CI). Run manually:

    python -m app.research.neural.run_c2_transfer
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.c2_data import (
    PRIMARY_CONTENT_CLASSES,
    build_common_window_imagery_trials,
    select_visual_content_trials,
)
from app.research.neural.c2_encoders import (
    CompactContrastiveContentStateEncoder,
    CompactTCNContentEncoder,
    EEGNetContentEncoder,
    content_class_indices,
)
from app.research.neural.c2_models import MulticlassFeatureModel
from app.research.neural.features import build_precue_trials
from app.research.neural.hashing import sha256_file
from app.research.neural.preprocessing import PreprocessingConfig, preprocess_recording
from app.research.neural.run_c1_confirmatory import DATA_ROOT, discover_subjects

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"
MIN_TRIALS_PER_CLASS = 6
TRAIN_LR = 1e-2
EPOCHS_BY_KIND = {"eegnet": 100, "tcn": 60, "contrastive": 60}


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def build_paired_epochs_for_subject(sub: str, session: str = "1"):
    """Returns a dict with perception/imagery/precue epoch arrays + labels
    for one subject, or {} if unusable for either phase.

    The "imagery" key here uses the EQUAL-DURATION common window (first
    COMMON_WINDOW_DURATION_S of the imagery phase, reusing
    c2_data.build_common_window_imagery_trials), not the full 4.0s imagery
    epoch -- perception epochs are 2.0s (500 samples @ 250Hz) while the
    full imagery phase is 4.0s (1000 samples), and EEGNet/TCN's
    architectures bake a fixed input length into their head layer's
    dimensions, so a perception-trained model cannot be evaluated on a
    different-length imagery epoch without a shape mismatch. Truncating to
    the matched window is not just an engineering fix: it also removes any
    trivial "more temporal information available" confound from the
    perception-to-imagery transfer comparison."""
    adapter = YotoAdapter(data_root=str(DATA_ROOT))
    recording, trials = adapter.ingest_recording(sub, session, "task")
    perception_trials = select_visual_content_trials(trials, "perception")
    imagery_trials = select_visual_content_trials(trials, "imagery")
    if len(perception_trials) < MIN_TRIALS_PER_CLASS * 3 or len(imagery_trials) < MIN_TRIALS_PER_CLASS * 3:
        return {}

    data_root = Path(DATA_ROOT)
    vhdr = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.vhdr"
    eeg = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.eeg"
    if not vhdr.exists() or not eeg.exists():
        return {}

    raw = mne.io.read_raw_brainvision(str(vhdr), preload=False, verbose="ERROR")
    raw_hash = sha256_file(str(eeg))
    config = PreprocessingConfig(run_ica=True)

    imagery_common_trials = build_common_window_imagery_trials(imagery_trials)
    out = {}
    for key, trial_set in (("perception", perception_trials), ("imagery", imagery_common_trials)):
        epochs_by_cond, kept, _manifest = preprocess_recording(raw, trial_set, raw_hash, config)
        cond_name = trial_set[0].condition
        if cond_name not in epochs_by_cond or len(kept) < MIN_TRIALS_PER_CLASS * 3:
            return {}
        labels = np.array([t.stimulus_id for t in kept])
        counts = Counter(labels.tolist())
        if any(counts.get(c, 0) < MIN_TRIALS_PER_CLASS for c in PRIMARY_CONTENT_CLASSES):
            return {}
        out[key] = (epochs_by_cond[cond_name], labels)

    precue_manifests = build_precue_trials(perception_trials)
    precue_epochs_by_cond, precue_kept, _pm = preprocess_recording(raw, precue_manifests, raw_hash, config)
    if "precue" in precue_epochs_by_cond and len(precue_kept) >= MIN_TRIALS_PER_CLASS * 3:
        precue_labels = np.array([t.stimulus_id for t in precue_kept])
        if all(np.sum(precue_labels == c) >= MIN_TRIALS_PER_CLASS for c in PRIMARY_CONTENT_CLASSES):
            out["precue"] = (precue_epochs_by_cond["precue"], precue_labels)

    return out


def _fit_encoder(kind: str, n_channels: int, n_samples: int, x_train: np.ndarray, y_train: np.ndarray):
    if kind in ("eegnet", "tcn"):
        cls = EEGNetContentEncoder if kind == "eegnet" else CompactTCNContentEncoder
        enc = cls(n_channels, n_samples, n_classes=3, seed=42)
        enc.fit(x_train, content_class_indices(y_train), n_epochs=EPOCHS_BY_KIND[kind], lr=TRAIN_LR)
        return enc, None
    enc = CompactContrastiveContentStateEncoder(n_channels, n_samples, embedding_dim=16, seed=42)
    enc.fit(x_train, y_train, n_epochs=EPOCHS_BY_KIND["contrastive"])
    probe = MulticlassFeatureModel(l2=1.0)
    probe.fit(enc.embed(x_train), y_train)
    return enc, probe


def _evaluate(kind: str, enc, probe, x_test: np.ndarray, y_test: np.ndarray) -> dict:
    if kind in ("eegnet", "tcn"):
        proba = enc.predict_proba(x_test)
        y_idx = content_class_indices(y_test)
        pred_idx = proba.argmax(axis=1)
        eps = 1e-12
        log_loss = float(-np.mean(np.log(np.clip(proba[np.arange(len(y_idx)), y_idx], eps, 1))))
        bal_acc = float(np.mean([
            np.mean(pred_idx[y_idx == c] == c) for c in set(y_idx.tolist()) if np.any(y_idx == c)
        ]))
    else:
        z_test = enc.embed(x_test)
        metrics = probe.evaluate(z_test, y_test)
        log_loss = metrics["class_weighted_log_loss"]
        bal_acc = metrics["balanced_accuracy"]
    return {"log_loss": log_loss, "balanced_accuracy": bal_acc, "n_test": len(y_test)}


def run_transfer_loso(
    pooled: dict[str, dict[str, tuple]], n_channels: int, n_samples_by_state: dict, kind: str,
) -> dict:
    """`pooled[state][participant] = (epochs, labels)`. Returns per-fold and
    aggregate results for all four train/test direction combinations, plus
    the label-shuffle and pre-cue negative controls for the primary
    (perception->imagery) direction."""
    participants = sorted(pooled["perception"].keys() & pooled["imagery"].keys())
    directions = {
        "perception_train_perception_test": ("perception", "perception"),
        "perception_train_imagery_test": ("perception", "imagery"),
        "imagery_train_imagery_test": ("imagery", "imagery"),
        "imagery_train_perception_test": ("imagery", "perception"),
    }
    per_direction_folds: dict[str, list] = {d: [] for d in directions}
    label_shuffle_folds: list = []
    precue_folds: list = []

    for held_out in participants:
        train_participants = [p for p in participants if p != held_out]

        # Train each (train_state) encoder ONCE per fold, reused across every
        # direction/control that shares that train_state -- e.g.
        # perception_train_perception_test and perception_train_imagery_test
        # both reuse the SAME perception-trained model object, never
        # retraining it a second time for the same fold.
        trained_by_train_state: dict[str, tuple] = {}
        for train_state in {ts for ts, _ in directions.values()}:
            x_train = np.concatenate([pooled[train_state][p][0] for p in train_participants], axis=0)
            y_train = np.concatenate([pooled[train_state][p][1] for p in train_participants], axis=0)
            trained_by_train_state[train_state] = _fit_encoder(
                kind, n_channels, n_samples_by_state[train_state], x_train, y_train,
            )

        for direction, (train_state, test_state) in directions.items():
            enc, probe = trained_by_train_state[train_state]
            x_test, y_test = pooled[test_state][held_out]
            metrics = _evaluate(kind, enc, probe, x_test, y_test)
            metrics["held_out_participant"] = held_out
            per_direction_folds[direction].append(metrics)

            if direction == "perception_train_imagery_test":
                rng = np.random.RandomState(42)
                y_shuffled = rng.permutation(y_test)
                label_shuffle_folds.append({
                    **_evaluate(kind, enc, probe, x_test, y_shuffled), "held_out_participant": held_out,
                })
                if held_out in pooled.get("precue", {}):
                    x_precue, y_precue = pooled["precue"][held_out]
                    precue_folds.append({
                        **_evaluate(kind, enc, probe, x_precue, y_precue), "held_out_participant": held_out,
                    })

        print(f"  [{kind}] held_out={held_out} done", file=sys.stderr)

    def _agg(folds):
        if not folds:
            return {"n_folds": 0, "log_loss_mean": None, "balanced_accuracy_mean": None}
        return {
            "n_folds": len(folds),
            "log_loss_mean": float(np.mean([f["log_loss"] for f in folds])),
            "log_loss_std": float(np.std([f["log_loss"] for f in folds])),
            "balanced_accuracy_mean": float(np.mean([f["balanced_accuracy"] for f in folds])),
            "per_participant_log_loss": {f["held_out_participant"]: f["log_loss"] for f in folds},
            "per_participant_balanced_accuracy": {f["held_out_participant"]: f["balanced_accuracy"] for f in folds},
        }

    return {
        "directions": {d: _agg(folds) for d, folds in per_direction_folds.items()},
        "negative_controls": {
            "label_shuffle_perception_train_imagery_test": _agg(label_shuffle_folds),
            "precue_perception_train_precue_test": _agg(precue_folds),
        },
    }


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)
    code_sha = _code_sha()

    pooled: dict[str, dict[str, tuple]] = {"perception": {}, "imagery": {}, "precue": {}}
    included, excluded = [], {}
    n_channels = None
    n_samples_by_state: dict[str, int] = {}

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            data = build_paired_epochs_for_subject(sub)
        except Exception as e:
            excluded[sub] = f"exception during processing: {e}"
            continue
        if not data:
            excluded[sub] = "unusable perception/imagery epochs (too few trials or missing floor classes)"
            continue
        included.append(sub)
        for key in ("perception", "imagery", "precue"):
            if key in data:
                epochs, labels = data[key]
                pooled[key][sub] = (epochs, labels)
                n_channels = epochs.shape[1]
                n_samples_by_state[key] = epochs.shape[2]

    print(f"Included: {len(included)} -> {included}", file=sys.stderr)
    print(f"Excluded: {excluded}", file=sys.stderr)
    print(f"Participants with usable precue: {len(pooled['precue'])}", file=sys.stderr)

    def _write(results: dict, complete: bool) -> None:
        payload = {
            "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "confirmatory_or_exploratory": "confirmatory" if len(included) >= 3 else "exploratory",
            "estimand_id": "C2_H2_PERCEPTION_IMAGERY_TRANSFER",
            "included_participants": included, "excluded_subjects": excluded,
            "n_channels": n_channels, "n_samples_by_state": n_samples_by_state,
            "n_participants_with_precue": len(pooled["precue"]),
            "training_hyperparameters": {"epochs_by_kind": EPOCHS_BY_KIND, "lr": TRAIN_LR},
            "results_by_architecture": results,
            "run_complete": complete,
            "note": (
                "Imagery labels never enter perception-encoder fitting or hyperparameter selection: "
                "the perception_train_imagery_test direction evaluates the SAME model object trained in "
                "perception_train_perception_test, only touching imagery data at evaluation time. "
                "Order-only and signal-quality-only nuisance checks are covered by Commit 3's baselines "
                "(results/c2_content_decoding.json); temporal-shift and channel-permutation controls are "
                "Commit 7's exhaustive falsification battery, not duplicated here."
                + ("" if complete else " INCOMPLETE: written after a partial subset of architectures "
                                        "as a checkpoint against long-run interruption; re-run to complete.")
            ),
        }
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_DIR / "c2_cross_state_transfer.json", "w") as f:
            json.dump(payload, f, indent=2, default=str)

    results = {}
    for kind in ("eegnet", "tcn", "contrastive"):
        print(f"Running transfer LOSO for encoder={kind} ...", file=sys.stderr)
        results[kind] = run_transfer_loso(pooled, n_channels, n_samples_by_state, kind)
        _write(results, complete=False)
        print(f"Checkpointed c2_cross_state_transfer.json after encoder={kind}", file=sys.stderr)

    _write(results, complete=True)
    print("Wrote final c2_cross_state_transfer.json (run_complete=true)", file=sys.stderr)


if __name__ == "__main__":
    main()
