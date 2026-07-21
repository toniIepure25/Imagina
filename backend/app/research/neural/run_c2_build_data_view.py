"""Real end-to-end C2 Commit 2 data-view build: ingest, preprocess, and
construct the matched content-state trial view (perception, imagery, and
equal-duration common-window state-decoding views) for every downloaded
ds005815 participant, restricted to the primary 3-class visual content
subset. Persists results/c2_data_eligibility.json and
results/c2_split_manifest.json.

Not a CI-run script (real data isn't downloaded in CI) -- a controlled
research workflow script, matching C1's `run_c1_confirmatory.py`. Run
manually:

    python -m app.research.neural.run_c2_build_data_view
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import mne

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.c2_data import (
    COMMON_WINDOW_DURATION_S,
    PRIMARY_CONTENT_CLASSES,
    build_common_window_imagery_trials,
    make_matched_record,
    select_visual_content_trials,
)
from app.research.neural.hashing import sha256_file
from app.research.neural.preprocessing import PreprocessingConfig, preprocess_recording
from app.research.neural.run_c1_confirmatory import DATA_ROOT, discover_subjects
from app.research.neural.variants import neighboring_trial_rejection_rate

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"
TRIALS_PER_BLOCK = 48
MIN_TRIALS_PER_CLASS = 6  # frozen floor, C2_ANALYSIS_SPEC.md Section 3

_TRIAL_INDEX_RE = re.compile(r"_t(\d+)_code")


def _trial_index(trial_id: str) -> int:
    m = _TRIAL_INDEX_RE.search(trial_id)
    if m is None:
        raise ValueError(f"trial_id does not match expected pattern: {trial_id!r}")
    return int(m.group(1))


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def build_views_for_subject(sub: str, session: str = "1") -> tuple[dict[str, list], dict]:
    """Returns ({"perception": [...], "imagery": [...], "imagery_common_window": [...]}, qc_info)."""
    adapter = YotoAdapter(data_root=str(DATA_ROOT))
    recording, trials = adapter.ingest_recording(sub, session, "task")

    perception_trials = select_visual_content_trials(trials, "perception")
    imagery_trials = select_visual_content_trials(trials, "imagery")
    if len(perception_trials) < MIN_TRIALS_PER_CLASS * 3 or len(imagery_trials) < MIN_TRIALS_PER_CLASS * 3:
        return {}, {
            "excluded_reason": "too few manifest visual-content trials",
            "n_perception": len(perception_trials), "n_imagery": len(imagery_trials),
        }

    data_root = Path(DATA_ROOT)
    vhdr = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.vhdr"
    eeg = data_root / sub / f"ses-{session}" / "eeg" / f"{sub}_ses-{session}_task-task_eeg.eeg"
    if not vhdr.exists() or not eeg.exists():
        return {}, {"excluded_reason": "raw file missing from download"}

    raw = mne.io.read_raw_brainvision(str(vhdr), preload=False, verbose="ERROR")
    raw_hash = sha256_file(str(eeg))
    config = PreprocessingConfig(run_ica=True)

    views: dict[str, list] = {"perception": [], "imagery": [], "imagery_common_window": []}
    qc: dict = {}

    for state_key, trial_set in (
        ("perception", perception_trials), ("imagery", imagery_trials),
        ("imagery_common_window", build_common_window_imagery_trials(imagery_trials)),
    ):
        epochs_by_cond, kept, manifest = preprocess_recording(raw, trial_set, raw_hash, config)
        cond_name = trial_set[0].condition if trial_set else state_key
        if cond_name not in epochs_by_cond:
            qc[state_key] = {"n_kept": 0, "n_manifest": len(trial_set)}
            continue

        all_indices = [_trial_index(t.trial_id) for t in trial_set]
        kept_indices = {_trial_index(t.trial_id) for t in kept}
        n_missing_channels = len(manifest.excluded_channels)
        retained_fraction = len(kept) / len(trial_set) if trial_set else 0.0
        channels = list(manifest.included_channels)

        for i, t in enumerate(kept):
            epoch = epochs_by_cond[cond_name][i]
            trial_idx = _trial_index(t.trial_id)
            record = make_matched_record(
                epoch, 250.0, config.reject_peak_to_peak_v, n_missing_channels,
                neighboring_trial_rejection_rate(trial_idx, all_indices, kept_indices),
                retained_fraction, sub, session, t.trial_id, t.stimulus_id, state_key,
                trial_idx // TRIALS_PER_BLOCK, trial_idx, manifest.output_hash,
            )
            views[state_key].append(record)

        qc[state_key] = {
            "n_manifest": len(trial_set), "n_kept": len(kept), "retained_fraction": retained_fraction,
            "class_balance": dict(Counter(t.stimulus_id for t in kept)),
            "channels_used": len(channels),
        }

    return views, qc


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)
    code_sha = _code_sha()

    per_subject_qc: dict[str, dict] = {}
    excluded_subjects: dict[str, str] = {}
    included_subjects: list[str] = []
    pooled_records: dict[str, list] = {"perception": [], "imagery": [], "imagery_common_window": []}

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            views, qc = build_views_for_subject(sub)
        except Exception as e:
            excluded_subjects[sub] = f"exception during processing: {e}"
            continue
        if not views:
            excluded_subjects[sub] = qc.get("excluded_reason", "no usable views produced")
            continue
        per_subject_qc[sub] = qc

        imagery_class_counts = Counter(r.stimulus_category for r in views["imagery"])
        under_floor = [c for c in PRIMARY_CONTENT_CLASSES if imagery_class_counts.get(c, 0) < MIN_TRIALS_PER_CLASS]
        if under_floor:
            excluded_subjects[sub] = (
                f"below minimum trial floor ({MIN_TRIALS_PER_CLASS}/class) for imagery classes: {under_floor}"
            )
            continue

        included_subjects.append(sub)
        for key in pooled_records:
            pooled_records[key].extend(views[key])

    print(f"Included: {len(included_subjects)} -> {included_subjects}", file=sys.stderr)
    print(f"Excluded: {excluded_subjects}", file=sys.stderr)

    created_at = datetime.now(timezone.utc).isoformat()

    eligibility = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha, "created_at": created_at,
        "confirmatory_or_exploratory": "confirmatory" if len(included_subjects) >= 3 else "exploratory",
        "estimand_id": "C2_DATA_ELIGIBILITY",
        "minimum_trials_per_class": MIN_TRIALS_PER_CLASS,
        "common_window_duration_s": COMMON_WINDOW_DURATION_S,
        "included_participants": included_subjects, "n_included_participants": len(included_subjects),
        "excluded_subjects": excluded_subjects, "per_subject_qc": per_subject_qc,
        "trial_counts": {key: len(records) for key, records in pooled_records.items()},
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "c2_data_eligibility.json", "w") as f:
        json.dump(eligibility, f, indent=2, default=str)
    print("Wrote c2_data_eligibility.json", file=sys.stderr)

    if len(included_subjects) < 3:
        print("Too few included participants for LOSO; skipping split manifest folds.", file=sys.stderr)
        folds = []
    else:
        folds = [
            {
                "held_out_participant": held_out,
                "train_participants": sorted(p for p in included_subjects if p != held_out),
                "test_participants": [held_out],
                "n_perception_test_trials": sum(
                    1 for r in pooled_records["perception"] if r.participant_id == held_out
                ),
                "n_imagery_test_trials": sum(
                    1 for r in pooled_records["imagery"] if r.participant_id == held_out
                ),
            }
            for held_out in included_subjects
        ]

    split_manifest = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha, "created_at": created_at,
        "outer_cv": "leave_one_subject_out", "inner_cv": "participant_grouped_k_fold_within_outer_train",
        "session_grouping": (
            "single-session (ses-1) analysis; a participant's trials never split by session across folds"
        ),
        "block_grouping": "block_index retained as covariate only, never a split criterion",
        "included_participants": included_subjects, "excluded_subjects": excluded_subjects,
        "trial_counts": eligibility["trial_counts"], "folds": folds,
    }
    with open(RESULTS_DIR / "c2_split_manifest.json", "w") as f:
        json.dump(split_manifest, f, indent=2, default=str)
    print("Wrote c2_split_manifest.json", file=sys.stderr)


if __name__ == "__main__":
    main()
