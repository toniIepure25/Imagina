"""Real end-to-end C2 Commit 6 disentanglement probes.

Trains ONE global encoder per architecture (EEGNet, TCN, contrastive) on
ALL included participants' pooled perception data -- deliberately NOT a
LOSO sweep, since this commit's probes ask a different question from
Commits 3-5's cross-subject generalization claim: "does this frozen
representation, once trained, still let a simple linear probe recover
participant identity or signal-quality status" is a within-sample leakage
question, answerable only if the probe's label space includes the same
participants the encoder saw.

Content and state probes are reported here too, using the SAME stratified
K-fold scheme as the nuisance probes (a within-sample check, explicitly
NOT a repeat of the cross-subject LOSO claim already established in
Commits 3-5 -- those remain the confirmatory record for H1/H3).

Not a CI-run script (real data isn't downloaded in CI). Run manually:

    python -m app.research.neural.run_c2_disentanglement
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
from app.research.neural.c2_data import build_common_window_imagery_trials, select_visual_content_trials
from app.research.neural.c2_disentanglement import quality_bin_labels, run_binary_probe, run_multiclass_probe
from app.research.neural.c2_encoders import (
    CompactContrastiveContentStateEncoder,
    CompactTCNContentEncoder,
    EEGNetContentEncoder,
    content_class_indices,
)
from app.research.neural.hashing import sha256_file
from app.research.neural.preprocessing import PreprocessingConfig, preprocess_recording
from app.research.neural.run_c1_confirmatory import DATA_ROOT, discover_subjects
from app.research.neural.variants import extract_quality_only_features

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"
MIN_TRIALS_PER_CLASS = 6
EPOCHS_BY_KIND = {"eegnet": 100, "tcn": 60, "contrastive": 60}
TRAIN_LR = 1e-2


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def build_records_for_subject(sub: str, session: str = "1"):
    """Returns (perception_epochs, perception_labels, perception_quality,
    imagery_epochs, imagery_labels) for one subject, or None if unusable."""
    adapter = YotoAdapter(data_root=str(DATA_ROOT))
    recording, trials = adapter.ingest_recording(sub, session, "task")
    perception_trials = select_visual_content_trials(trials, "perception")
    imagery_trials = select_visual_content_trials(trials, "imagery")
    if len(perception_trials) < MIN_TRIALS_PER_CLASS * 3 or len(imagery_trials) < MIN_TRIALS_PER_CLASS * 3:
        return None

    data_root = Path(DATA_ROOT)
    vhdr = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.vhdr"
    eeg = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.eeg"
    if not vhdr.exists() or not eeg.exists():
        return None

    raw = mne.io.read_raw_brainvision(str(vhdr), preload=False, verbose="ERROR")
    raw_hash = sha256_file(str(eeg))
    config = PreprocessingConfig(run_ica=True)

    perception_epochs_by_cond, perception_kept, p_manifest = preprocess_recording(
        raw, perception_trials, raw_hash, config,
    )
    if "perception" not in perception_epochs_by_cond or len(perception_kept) < MIN_TRIALS_PER_CLASS * 3:
        return None
    perception_labels = np.array([t.stimulus_id for t in perception_kept])
    if any(np.sum(perception_labels == c) < MIN_TRIALS_PER_CLASS for c in
           ("visual_square", "visual_face_male", "visual_face_female")):
        return None

    imagery_common_trials = build_common_window_imagery_trials(imagery_trials)
    imagery_epochs_by_cond, imagery_kept, _i_manifest = preprocess_recording(
        raw, imagery_common_trials, raw_hash, config,
    )
    if "imagery_common_window" not in imagery_epochs_by_cond or len(imagery_kept) < MIN_TRIALS_PER_CLASS * 3:
        return None
    imagery_labels = np.array([t.stimulus_id for t in imagery_kept])

    perception_epochs = perception_epochs_by_cond["perception"]
    n_missing = len(p_manifest.excluded_channels)
    retained_fraction = len(perception_kept) / len(perception_trials)
    perception_quality = np.array([
        extract_quality_only_features(
            perception_epochs[i], 250.0, config.reject_peak_to_peak_v, n_missing, 0.0, retained_fraction,
        )["quality__mean_peak_to_peak"]
        for i in range(len(perception_kept))
    ])

    return (
        perception_epochs, perception_labels, perception_quality,
        imagery_epochs_by_cond["imagery_common_window"], imagery_labels,
    )


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)
    code_sha = _code_sha()

    included, excluded = [], {}
    all_perception_epochs, all_perception_labels, all_perception_quality = [], [], []
    all_perception_pid, all_imagery_pid = [], []
    all_imagery_epochs, all_imagery_labels = [], []
    n_channels = None
    n_samples = None

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            data = build_records_for_subject(sub)
        except Exception as e:
            excluded[sub] = f"exception during processing: {e}"
            continue
        if data is None:
            excluded[sub] = "unusable perception/imagery epochs (too few trials or missing floor classes)"
            continue
        p_epochs, p_labels, p_quality, i_epochs, i_labels = data
        included.append(sub)
        all_perception_epochs.append(p_epochs)
        all_perception_labels.append(p_labels)
        all_perception_quality.append(p_quality)
        all_perception_pid.extend([sub] * len(p_labels))
        all_imagery_epochs.append(i_epochs)
        all_imagery_labels.append(i_labels)
        all_imagery_pid.extend([sub] * len(i_labels))
        n_channels = p_epochs.shape[1]
        n_samples = p_epochs.shape[2]

    print(f"Included: {len(included)} -> {included}", file=sys.stderr)
    print(f"Excluded: {excluded}", file=sys.stderr)

    perception_epochs = np.concatenate(all_perception_epochs, axis=0)
    perception_labels = np.concatenate(all_perception_labels, axis=0)
    perception_quality = np.concatenate(all_perception_quality, axis=0)
    perception_pid = np.array(all_perception_pid)
    imagery_epochs = np.concatenate(all_imagery_epochs, axis=0)
    imagery_labels = np.concatenate(all_imagery_labels, axis=0)

    state_epochs = np.concatenate([perception_epochs, imagery_epochs], axis=0)
    state_labels = np.array(["perception"] * len(perception_labels) + ["imagery"] * len(imagery_labels))
    session_labels = np.array(["1"] * len(perception_pid))  # every included participant used session 1 only

    results_by_architecture: dict[str, dict] = {}
    for kind in ("eegnet", "tcn", "contrastive"):
        print(f"Training global {kind} encoder on pooled perception data ...", file=sys.stderr)
        if kind in ("eegnet", "tcn"):
            cls = EEGNetContentEncoder if kind == "eegnet" else CompactTCNContentEncoder
            enc = cls(n_channels, n_samples, n_classes=3, seed=42)
            perception_idx = content_class_indices(perception_labels)
            enc.fit(perception_epochs, perception_idx, n_epochs=EPOCHS_BY_KIND[kind], lr=TRAIN_LR)
        else:
            enc = CompactContrastiveContentStateEncoder(n_channels, n_samples, embedding_dim=16, seed=42)
            enc.fit(perception_epochs, perception_labels, n_epochs=EPOCHS_BY_KIND["contrastive"])

        perception_embed = enc.embed(perception_epochs)
        state_embed = enc.embed(state_epochs)

        content_probe = run_multiclass_probe(
            perception_embed, perception_labels, "content_category", "stratified_5fold_within_sample",
            note="Within-sample check; the confirmatory cross-subject claim is Commits 3-5's LOSO result.",
        )
        state_probe = run_binary_probe(state_embed, state_labels, "cognitive_state", "stratified_5fold_within_sample")
        participant_probe = run_multiclass_probe(
            perception_embed, perception_pid, "participant_identity", "stratified_5fold_within_sample",
        )
        session_probe = run_multiclass_probe(
            perception_embed, session_labels, "session_identity", "stratified_5fold_within_sample",
            note="Only session 1 was used for every included participant in this pipeline -- session identity "
                 "has zero variance and is not meaningfully testable here, reported honestly rather than faked.",
        )
        quality_bins = quality_bin_labels(perception_quality, n_bins=3)
        quality_probe = run_multiclass_probe(
            perception_embed, quality_bins, "signal_quality_bin", "stratified_5fold_within_sample",
        )

        print(f"  [{kind}] content={content_probe.mean_metric:.4f} state={state_probe.mean_metric:.4f} "
              f"participant={participant_probe.mean_metric:.4f} quality={quality_probe.mean_metric:.4f}",
              file=sys.stderr)

        results_by_architecture[kind] = {
            "content_category": content_probe.to_dict(),
            "cognitive_state": state_probe.to_dict(),
            "participant_identity": participant_probe.to_dict(),
            "session_identity": session_probe.to_dict(),
            "signal_quality_bin": quality_probe.to_dict(),
        }

        with open(RESULTS_DIR / "c2_disentanglement.json", "w") as f:
            json.dump({
                "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "confirmatory_or_exploratory": "exploratory",
                "estimand_id": "C2_H5_DISENTANGLEMENT",
                "included_participants": included, "excluded_subjects": excluded,
                "n_channels": n_channels, "n_samples": n_samples,
                "results_by_architecture": results_by_architecture,
                "run_complete": kind == "contrastive",
                "note": (
                    "Separate probe metrics reported per target (content, state, participant identity, "
                    "session identity, signal-quality bin) -- never combined into one disentanglement score, "
                    "per the task specification. Content/state probes here use within-sample stratified K-fold "
                    "(a leakage/recoverability check on the frozen representation), NOT a repeat of Commits "
                    "3-5's cross-subject LOSO claim, which remains the confirmatory record for H1/H3."
                ),
            }, f, indent=2, default=str)
        print(f"Checkpointed c2_disentanglement.json after encoder={kind}", file=sys.stderr)

    print("Wrote final c2_disentanglement.json", file=sys.stderr)


if __name__ == "__main__":
    main()
