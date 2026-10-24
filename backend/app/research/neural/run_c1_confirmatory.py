"""Real end-to-end C1 confirmatory run: ingest, preprocess, extract features,
and run the full LOSO nested validation + falsification tests + sensitivity
analysis against every downloaded ds005815 participant.

Not a CI-run script (real data isn't downloaded in CI); a controlled
research workflow script per the task's own CI/full-run distinction. Run
manually:

    python -m app.research.neural.run_c1_confirmatory
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import mne
import numpy as np

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.falsification import (
    test_1_precue_vs_postcue,
    test_3_label_shuffle_within_blocks,
    test_6_participant_id_only,
    test_8_no_duplicate_stimulus_leakage,
    test_9_hyperparameter_selection_blind_to_outer_test,
    test_10_behavior_plus_random_noise,
)
from app.research.neural.features import build_precue_trials, extract_classical_features
from app.research.neural.hashing import sha256_file
from app.research.neural.nested_validation import (
    TrialRecord,
    add_lagged_prior_vividness,
    broad_stimulus_category,
    estimate_primary_endpoint,
    run_loso_nested_validation,
)
from app.research.neural.preprocessing import FRONTAL_PROXY_CHANNELS, PreprocessingConfig, preprocess_recording

DATA_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "external", "neural", "ds005815",
))
RESULTS_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "results",
))
TRIALS_PER_BLOCK = 48  # per the dataset's own methods text, verified in Commit 2


_TRIAL_INDEX_RE = re.compile(r"_t(\d+)_code")


def _trial_index_from_trial_id(trial_id: str) -> int:
    """Extract the numeric trial index from a YotoAdapter trial_id, e.g.
    'sub-01_ses-1_task_t0000_code37' -> 0.

    Naive `trial_id.split("_t")[1]` is WRONG here: the run_id segment
    ("task") itself contains the substring "_t" (as "...ses-1_**t**ask..."
    is not what happens, but "..._**t**ask_t0000..." IS — the literal
    substring "_t" appears both before "ask" and before "0000"), so
    `.split("_t")` yields more than two parts and `[1]` grabs "ask" instead
    of the index. This broke 15/20 subjects in the first confirmatory run
    (`invalid literal for int(): 'ask'`) before being caught and fixed by
    anchoring a regex to the unambiguous "_t<digits>_code" pattern instead.
    """
    m = _TRIAL_INDEX_RE.search(trial_id)
    if m is None:
        raise ValueError(f"trial_id does not match expected pattern: {trial_id!r}")
    return int(m.group(1))


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=os.path.dirname(__file__)).decode().strip()
    except Exception:
        return "unknown"


def discover_subjects() -> list[str]:
    if not os.path.isdir(DATA_ROOT):
        return []
    return sorted(
        d for d in os.listdir(DATA_ROOT)
        if d.startswith("sub-") and os.path.isdir(os.path.join(DATA_ROOT, d))
    )


def build_trial_records_for_subject(
    sub: str, session: str = "1", channel_group: str = "full",
) -> tuple[list[TrialRecord], list[TrialRecord], dict]:
    """Returns (postcue_imagery_records, precue_records, qc_info) for one
    subject/session. `channel_group`: "full" | "ocular" restricts feature
    extraction to a channel subset (used by falsification test 5)."""
    adapter = YotoAdapter(data_root=DATA_ROOT)
    recording, trials = adapter.ingest_recording(sub, session, "task")
    imagery_trials = [t for t in trials if t.condition == "imagery"]
    if len(imagery_trials) < 10:
        return [], [], {
            "excluded_reason": "too few imagery trials in manifest",
            "n_manifest_trials": len(imagery_trials),
        }

    vhdr = os.path.join(DATA_ROOT, sub, f"ses-{session}", "eeg", f"{sub}_ses-{session}_task-task_eeg.vhdr")
    eeg = os.path.join(DATA_ROOT, sub, f"ses-{session}", "eeg", f"{sub}_ses-{session}_task-task_eeg.eeg")
    if not os.path.exists(vhdr) or not os.path.exists(eeg):
        return [], [], {
            "excluded_reason": "raw file missing from download",
            "vhdr_exists": os.path.exists(vhdr), "eeg_exists": os.path.exists(eeg),
        }

    raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
    raw_hash = sha256_file(eeg)
    config = PreprocessingConfig(run_ica=True)
    epochs_by_cond, kept, manifest = preprocess_recording(raw, imagery_trials, raw_hash, config)
    if "imagery" not in epochs_by_cond or len(kept) < 10:
        return [], [], {
            "excluded_reason": "too few trials survived preprocessing/artifact rejection",
            "n_kept": len(kept), "n_manifest_trials": len(imagery_trials),
        }

    channels = list(manifest.included_channels)
    if channel_group == "ocular":
        keep_idx = [i for i, c in enumerate(channels) if c in FRONTAL_PROXY_CHANNELS]
        channels_for_features = [channels[i] for i in keep_idx]
    else:
        keep_idx = list(range(len(channels)))
        channels_for_features = channels

    postcue_records: list[TrialRecord] = []
    for i, t in enumerate(kept):
        if t.behavioral_target is None:
            continue
        epoch = epochs_by_cond["imagery"][i][keep_idx, :]
        fv = extract_classical_features(
            epoch, 250.0, channels_for_features, trial_id=t.trial_id, condition=t.condition, stimulus_id=t.stimulus_id,
        )
        feature_vec = np.array(list(fv.features.values()))
        trial_idx = _trial_index_from_trial_id(t.trial_id)
        modality_prefix = fv.stimulus_id.split("_")[0]
        modality = modality_prefix if modality_prefix in ("visual", "auditory", "mix") else "mix"
        postcue_records.append(TrialRecord(
            participant_id=sub, session_id=session, trial_index_in_session=trial_idx,
            modality=modality,
            prior_vividness=None, vividness=float(t.behavioral_target), neural_features=feature_vec,
            session_index=int(session), block_index=trial_idx // TRIALS_PER_BLOCK,
            trial_index_in_block=trial_idx % TRIALS_PER_BLOCK,
            stimulus_category=broad_stimulus_category(t.stimulus_id),
        ))

    # Pre-cue control: same trials, features from the fixation window before
    # the perception phase (falsification test 1).
    perception_trials = [t for t in trials if t.condition == "perception"]
    precue_trial_manifests = build_precue_trials(perception_trials)
    precue_epochs, precue_kept, precue_manifest = preprocess_recording(raw, precue_trial_manifests, raw_hash, config)
    precue_records: list[TrialRecord] = []
    if "precue" in precue_epochs:
        precue_channels = list(precue_manifest.included_channels)
        # Match each surviving pre-cue epoch back to its corresponding
        # post-cue (imagery) record by trial_index_in_session, reusing that
        # record's modality/stimulus_category/behavioral target -- pre-cue
        # trials carry no self-report of their own (see build_precue_trials).
        postcue_by_trial_idx = {r.trial_index_in_session: r for r in postcue_records}
        for i, t in enumerate(precue_kept):
            trial_idx = _trial_index_from_trial_id(t.trial_id)
            match = postcue_by_trial_idx.get(trial_idx)
            if match is None:
                continue
            epoch = precue_epochs["precue"][i]
            fv = extract_classical_features(
                epoch, 250.0, precue_channels, trial_id=t.trial_id, condition="precue", stimulus_id=t.stimulus_id,
            )
            feature_vec = np.array(list(fv.features.values()))
            precue_records.append(TrialRecord(
                participant_id=sub, session_id=session, trial_index_in_session=trial_idx,
                modality=match.modality, prior_vividness=None, vividness=match.vividness,
                neural_features=feature_vec, session_index=match.session_index,
                block_index=match.block_index, trial_index_in_block=match.trial_index_in_block,
                stimulus_category=match.stimulus_category,
            ))

    qc_info = {
        "n_manifest_trials": len(imagery_trials), "n_kept_after_preprocessing": len(kept),
        "n_with_behavioral_target": len(postcue_records), "n_precue_matched": len(precue_records),
        "retained_fraction": len(kept) / len(imagery_trials) if imagery_trials else 0.0,
    }
    return postcue_records, precue_records, qc_info


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)

    all_postcue: list[TrialRecord] = []
    all_precue: list[TrialRecord] = []
    per_subject_qc: dict[str, dict] = {}
    excluded_subjects: dict[str, str] = {}

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            postcue, precue, qc = build_trial_records_for_subject(sub)
        except Exception as e:
            excluded_subjects[sub] = f"exception during processing: {e}"
            continue
        per_subject_qc[sub] = qc
        if not postcue:
            excluded_subjects[sub] = qc.get("excluded_reason", "no usable trials")
            continue
        all_postcue.extend(postcue)
        all_precue.extend(precue)

    all_postcue.sort(key=lambda r: (r.participant_id, r.session_id, r.trial_index_in_session))
    all_postcue = add_lagged_prior_vividness(all_postcue)
    usable_participants = sorted({r.participant_id for r in all_postcue})
    print(f"Usable participants: {len(usable_participants)} -> {usable_participants}", file=sys.stderr)
    print(f"Excluded: {excluded_subjects}", file=sys.stderr)

    if len(usable_participants) < 3:
        print("Too few usable participants for LOSO; aborting confirmatory run.", file=sys.stderr)
        fold_results = []
        primary = None
    else:
        fold_results = run_loso_nested_validation(all_postcue)
        primary = estimate_primary_endpoint(fold_results)

    created_at = datetime.now(timezone.utc).isoformat()
    code_sha = _code_sha()

    incremental_validity = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha,
        "estimand_id": "H2_incremental_validity_ordinal_log_score", "created_at": created_at,
        "confirmatory_or_exploratory": "confirmatory" if len(usable_participants) >= 3 else "exploratory",
        "usable_participants": usable_participants, "n_usable_participants": len(usable_participants),
        "excluded_subjects": excluded_subjects, "per_subject_qc": per_subject_qc,
        "primary_estimand": primary.to_dict() if primary else None,
        "per_fold": [f.to_dict() for f in fold_results],
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "c1_incremental_validity.json"), "w") as f:
        json.dump(incremental_validity, f, indent=2, default=str)
    print("Wrote c1_incremental_validity.json", file=sys.stderr)

    negative_controls: dict = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha,
        "created_at": created_at, "confirmatory_or_exploratory": "confirmatory",
        "n_participants": len(usable_participants),
    }
    if len(usable_participants) >= 3 and all_precue:
        precue_by_participant = {
            p for p in usable_participants if any(r.participant_id == p for r in all_precue)
        }
        if len(precue_by_participant) >= 3:
            matched_postcue = [r for r in all_postcue if r.participant_id in precue_by_participant]
            matched_precue = [r for r in all_precue if r.participant_id in precue_by_participant]
            negative_controls["test_1_precue_vs_postcue"] = (
                test_1_precue_vs_postcue(matched_postcue, matched_precue).to_dict()
            )
    if len(usable_participants) >= 3:
        negative_controls["test_3_label_shuffle_within_blocks"] = (
            test_3_label_shuffle_within_blocks(all_postcue).to_dict()
        )
        negative_controls["test_6_participant_id_only"] = (
            test_6_participant_id_only(all_postcue).to_dict()
        )
        negative_controls["test_8_no_duplicate_stimulus_leakage"] = (
            test_8_no_duplicate_stimulus_leakage(all_postcue).to_dict()
        )
        negative_controls["test_9_hyperparameter_selection_blind_to_outer_test"] = (
            test_9_hyperparameter_selection_blind_to_outer_test(all_postcue).to_dict()
        )
        negative_controls["test_10_behavior_plus_random_noise"] = (
            test_10_behavior_plus_random_noise(all_postcue).to_dict()
        )
    negative_controls["not_run_this_session"] = {
        "test_2_temporal_shift": "requires a temporally-shifted feature extraction pass, deferred",
        "test_4_random_channel_permutation": "requires a channel-permuted feature extraction pass, deferred",
        "test_5_ocular_only_control": "requires an ocular-only feature extraction pass, deferred",
        "test_7_signal_quality_only": "requires a quality-only feature extraction pass, deferred",
    }
    with open(os.path.join(RESULTS_DIR, "c1_negative_controls.json"), "w") as f:
        json.dump(negative_controls, f, indent=2, default=str)
    print("Wrote c1_negative_controls.json", file=sys.stderr)

    split_manifest = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha,
        "created_at": created_at,
        "outer_cv": "leave_one_usable_participant_out",
        "inner_cv": "participant_grouped_k_fold_within_outer_train",
        "n_trials": len(all_postcue),
        "usable_participants": usable_participants,
        "excluded_subjects": excluded_subjects,
        "folds": [
            {
                "held_out_participant": f.held_out_participant,
                "train_participants": sorted(
                    p for p in usable_participants if p != f.held_out_participant
                ),
                "test_participants": [f.held_out_participant],
                "n_train_trials": f.n_train,
                "n_test_trials": f.n_test,
                "chosen_l2": f.chosen_l2,
            }
            for f in fold_results
        ],
    }
    with open(os.path.join(RESULTS_DIR, "c1_split_manifest.json"), "w") as f:
        json.dump(split_manifest, f, indent=2, default=str)
    print("Wrote c1_split_manifest.json", file=sys.stderr)


if __name__ == "__main__":
    main()
