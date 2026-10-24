"""Real end-to-end C2 Commit 3 baseline evaluation: chance/majority,
order-only, block/session-only, signal-quality-only, and classical-feature
decoders for both the content (3-class) and state (binary) targets, over
the 14 real, matched-content-state participants built in Commit 2.

Every baseline uses the IDENTICAL LOSO nested-validation harness
(`c2_nested_validation.py`) -- only the feature construction differs per
baseline, matching C2_ANALYSIS_SPEC.md Section 6's model hierarchy and the
"same folds across compared models" guarantee from C2_PROTOCOL.md.

Not a CI-run script (real data isn't downloaded in CI). Run manually:

    python -m app.research.neural.run_c2_baselines
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.research.neural.c2_data import PRIMARY_CONTENT_CLASSES
from app.research.neural.c2_models import (
    STATE_CLASSES,
    block_session_only_features,
    chance_majority_content_baseline,
    order_only_features,
    quality_only_features,
)
from app.research.neural.c2_nested_validation import (
    aggregate_metric_across_folds,
    run_loso_nested_validation_classification,
)
from app.research.neural.run_c1_confirmatory import discover_subjects
from app.research.neural.run_c2_build_data_view import build_views_for_subject

RESULTS_DIR = Path(__file__).resolve().parents[4] / "results"
MIN_TRIALS_PER_CLASS = 6


def _code_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "unknown"


def _stack_quality(records) -> np.ndarray:
    return quality_only_features([r.signal_quality_features for r in records])


def _stack_classical(records) -> np.ndarray:
    return np.array([r.neural_features for r in records])


def run_content_baselines(imagery_records: list, participant_ids: list[str]) -> dict:
    y = np.array([r.stimulus_category for r in imagery_records])
    order = order_only_features(
        np.array([r.trial_order for r in imagery_records]), np.array([r.block_index for r in imagery_records]),
    )
    block_session = block_session_only_features(
        np.array([r.block_index for r in imagery_records]),
        np.array([int(r.session_id) for r in imagery_records]),
    )
    quality = _stack_quality(imagery_records)
    classical = _stack_classical(imagery_records)

    out = {"chance_majority": chance_majority_content_baseline(y, PRIMARY_CONTENT_CLASSES)}
    for name, x in (("order_only", order), ("block_session_only", block_session),
                     ("signal_quality_only", quality), ("classical_feature_decoder", classical)):
        fold_results = run_loso_nested_validation_classification(x, y, participant_ids, target_kind="content")
        out[name] = {
            "n_folds": len(fold_results),
            "class_weighted_log_loss": aggregate_metric_across_folds(fold_results, "class_weighted_log_loss"),
            "balanced_accuracy": aggregate_metric_across_folds(fold_results, "balanced_accuracy"),
            "macro_f1": aggregate_metric_across_folds(fold_results, "macro_f1"),
            "per_fold_chosen_l2": {r.held_out_participant: r.chosen_l2 for r in fold_results},
        }
    return out


def run_state_baselines(perception_records: list, imagery_common_records: list) -> dict:
    """State target combines perception (label 'perception') and
    imagery_common_window (label 'imagery') records into ONE pooled set,
    matched trial-for-trial by (participant_id, trial_id) so class balance
    is naturally 50/50 by construction."""
    perception_by_key = {(r.participant_id, r.trial_id): r for r in perception_records}
    imagery_by_key = {(r.participant_id, r.trial_id): r for r in imagery_common_records}
    shared_keys = sorted(set(perception_by_key) & set(imagery_by_key))

    pooled_quality, pooled_classical, pooled_order, pooled_block_session, y, ids = [], [], [], [], [], []
    for key in shared_keys:
        for label, rec in (("perception", perception_by_key[key]), ("imagery", imagery_by_key[key])):
            pooled_quality.append(rec.signal_quality_features)
            pooled_classical.append(rec.neural_features)
            pooled_order.append(rec.trial_order)
            pooled_block_session.append((rec.block_index, int(rec.session_id)))
            y.append(label)
            ids.append(rec.participant_id)

    y = np.array(y)
    ids = list(ids)
    order = order_only_features(np.array(pooled_order), np.array([b for b, _ in pooled_block_session]))
    block_session = block_session_only_features(
        np.array([b for b, _ in pooled_block_session]), np.array([s for _, s in pooled_block_session]),
    )
    quality = quality_only_features(pooled_quality)
    classical = np.array(pooled_classical)

    out: dict = {"n_shared_trials": len(shared_keys), "n_pooled_samples": len(y)}
    for name, x in (("order_only", order), ("block_session_only", block_session),
                     ("signal_quality_only", quality), ("classical_feature_decoder", classical)):
        fold_results = run_loso_nested_validation_classification(x, y, ids, target_kind="state")
        out[name] = {
            "n_folds": len(fold_results),
            "binary_log_loss": aggregate_metric_across_folds(fold_results, "binary_log_loss"),
            "balanced_accuracy": aggregate_metric_across_folds(fold_results, "balanced_accuracy"),
            "roc_auc": aggregate_metric_across_folds(fold_results, "roc_auc"),
            "per_fold_chosen_l2": {r.held_out_participant: r.chosen_l2 for r in fold_results},
        }
    return out


def main() -> None:
    subjects = discover_subjects()
    print(f"Discovered {len(subjects)} subjects on disk: {subjects}", file=sys.stderr)
    code_sha = _code_sha()

    included: list[str] = []
    excluded: dict[str, str] = {}
    pooled: dict[str, list] = {"perception": [], "imagery": [], "imagery_common_window": []}

    for sub in subjects:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            views, qc = build_views_for_subject(sub)
        except Exception as e:
            excluded[sub] = f"exception during processing: {e}"
            continue
        if not views:
            excluded[sub] = qc.get("excluded_reason", "no usable views produced")
            continue
        imagery_counts = Counter(r.stimulus_category for r in views["imagery"])
        under_floor = [c for c in PRIMARY_CONTENT_CLASSES if imagery_counts.get(c, 0) < MIN_TRIALS_PER_CLASS]
        if under_floor:
            excluded[sub] = f"below minimum trial floor for imagery classes: {under_floor}"
            continue
        included.append(sub)
        for key in pooled:
            pooled[key].extend(views[key])

    print(f"Included: {len(included)} -> {included}", file=sys.stderr)
    print(f"Excluded: {excluded}", file=sys.stderr)

    print("Running content baselines ...", file=sys.stderr)
    content_participant_ids = [r.participant_id for r in pooled["imagery"]]
    content_results = run_content_baselines(pooled["imagery"], content_participant_ids)

    print("Running state baselines ...", file=sys.stderr)
    state_results = run_state_baselines(pooled["perception"], pooled["imagery_common_window"])

    created_at = datetime.now(timezone.utc).isoformat()
    common_provenance = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha, "created_at": created_at,
        "confirmatory_or_exploratory": "confirmatory" if len(included) >= 3 else "exploratory",
        "included_participants": included, "excluded_subjects": excluded,
        "note": (
            "Commit 3 baselines only (chance/majority, order-only, block/session-only, "
            "signal-quality-only, classical-feature-decoder). Compact neural encoders "
            "(EEGNet/TCN/contrastive) and the regularized-raw-linear-EEG baseline are Commit 4."
        ),
    }

    content_payload = {
        **common_provenance, "estimand_id": "C2_H1_CONTENT_DECODING",
        "content_target_classes": list(PRIMARY_CONTENT_CLASSES), "baselines": content_results,
    }
    state_payload = {
        **common_provenance, "estimand_id": "C2_H3_STATE_DECODING",
        "state_target_classes": list(STATE_CLASSES), "baselines": state_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "c2_content_decoding.json", "w") as f:
        json.dump(content_payload, f, indent=2, default=str)
    print("Wrote c2_content_decoding.json (Commit 3 content baselines)", file=sys.stderr)

    with open(RESULTS_DIR / "c2_state_decoding.json", "w") as f:
        json.dump(state_payload, f, indent=2, default=str)
    print("Wrote c2_state_decoding.json (Commit 3 state baselines)", file=sys.stderr)


if __name__ == "__main__":
    main()
