"""Real-data execution of C1 falsification tests 2 (temporal shift), 4
(channel-label permutation), 5 (frontal/ocular-proxy-only), and 7
(signal-quality-only) -- the four controls left `deferred` in the original
Commit 7 confirmatory run.

Does NOT modify, retune, or re-derive the accepted primary result: reuses
the FROZEN usable_participants list from the already-committed
results/c1_incremental_validity.json rather than re-deriving inclusion, and
never changes the target, primary metric, outer folds, or regularization
grid. Every variant is built from the identical retained epochs and trial
identities the primary analysis used; only the feature-construction step
differs per variant. See `variants.py` for the provenance-aware variant
system this script drives.

Not a CI-run script (real data isn't downloaded in CI) -- a controlled
research workflow script, matching `run_c1_confirmatory.py`. Run manually:

    python -m app.research.neural.run_c1_falsification_closure
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import mne
import numpy as np

from app.research.neural.adapters.yoto import YotoAdapter
from app.research.neural.hashing import sha256_file
from app.research.neural.nested_validation import (
    TrialRecord,
    add_lagged_prior_vividness,
    bootstrap_ci,
    broad_stimulus_category,
    estimate_primary_endpoint,
    exact_sign_flip_test,
    run_loso_nested_validation,
)
from app.research.neural.preprocessing import PreprocessingConfig, preprocess_recording
from app.research.neural.run_c1_confirmatory import (
    DATA_ROOT,
    RESULTS_DIR,
    TRIALS_PER_BLOCK,
    _code_sha,
    _trial_index_from_trial_id,
)
from app.research.neural.variants import (
    CHANNEL_PERMUTATION_SEEDS,
    build_channel_permuted_variant,
    build_frontal_proxy_variant,
    build_full_channel_variant,
    build_late_shift_trials,
    build_quality_only_variant,
    neighboring_trial_rejection_rate,
)

VARIANT_KEYS = [
    "aligned_full", "temporally_shifted_precue", "temporally_shifted_late",
    "frontal_proxy_only", "signal_quality_only",
]
VARIANT_KEYS += [f"channel_group_permuted_seed{seed}" for seed in CHANNEL_PERMUTATION_SEEDS]


def _load_frozen_usable_participants() -> list[str]:
    """The FROZEN participant set from the accepted primary result -- never
    re-derived here, per the explicit instruction not to change usable
    participants based on any control's performance."""
    path = os.path.join(RESULTS_DIR, "c1_incremental_validity.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return list(data["usable_participants"])


def build_variant_records_for_subject(sub: str, code_sha: str, session: str = "1") -> dict[str, list[TrialRecord]]:
    """Returns {variant_key: [TrialRecord, ...]} for one participant, built
    from the SAME retained imagery epochs and trial identities as the
    primary analysis (aligned_full/channel_permuted/frontal_proxy/quality_only),
    plus two independently-preprocessed temporal controls (precue, late_shift)."""
    adapter = YotoAdapter(data_root=DATA_ROOT)
    recording, trials = adapter.ingest_recording(sub, session, "task")
    imagery_trials = [t for t in trials if t.condition == "imagery"]
    if len(imagery_trials) < 10:
        return {}

    vhdr = os.path.join(DATA_ROOT, sub, f"ses-{session}", "eeg", f"{sub}_ses-{session}_task-task_eeg.vhdr")
    eeg = os.path.join(DATA_ROOT, sub, f"ses-{session}", "eeg", f"{sub}_ses-{session}_task-task_eeg.eeg")
    if not os.path.exists(vhdr) or not os.path.exists(eeg):
        return {}

    raw = mne.io.read_raw_brainvision(vhdr, preload=False, verbose="ERROR")
    raw_hash = sha256_file(eeg)
    config = PreprocessingConfig(run_ica=True)

    epochs_by_cond, kept, manifest = preprocess_recording(raw, imagery_trials, raw_hash, config)
    if "imagery" not in epochs_by_cond or len(kept) < 10:
        return {}

    channels = list(manifest.included_channels)
    all_manifest_indices = [_trial_index_from_trial_id(t.trial_id) for t in imagery_trials]
    kept_indices = {_trial_index_from_trial_id(t.trial_id) for t in kept}
    n_missing_channels = len(manifest.excluded_channels)
    recording_retained_fraction = len(kept) / len(imagery_trials)

    def _record_from(variant_key: str, epoch: np.ndarray, features: np.ndarray, t) -> TrialRecord:
        trial_idx = _trial_index_from_trial_id(t.trial_id)
        modality_prefix = t.stimulus_id.split("_")[0]
        modality = modality_prefix if modality_prefix in ("visual", "auditory", "mix") else "mix"
        return TrialRecord(
            participant_id=sub, session_id=session, trial_index_in_session=trial_idx, modality=modality,
            prior_vividness=None, vividness=float(t.behavioral_target), neural_features=features,
            session_index=int(session), block_index=trial_idx // TRIALS_PER_BLOCK,
            trial_index_in_block=trial_idx % TRIALS_PER_BLOCK, stimulus_category=broad_stimulus_category(t.stimulus_id),
        )

    out: dict[str, list[TrialRecord]] = {key: [] for key in VARIANT_KEYS}
    for i, t in enumerate(kept):
        if t.behavioral_target is None:
            continue
        epoch = epochs_by_cond["imagery"][i]
        trial_idx = _trial_index_from_trial_id(t.trial_id)

        aligned = build_full_channel_variant(epoch, 250.0, channels, sub, session, t.trial_id, code_sha)
        out["aligned_full"].append(_record_from("aligned_full", epoch, aligned.feature_vector(), t))

        frontal = build_frontal_proxy_variant(epoch, 250.0, channels, sub, session, t.trial_id, code_sha)
        out["frontal_proxy_only"].append(_record_from("frontal_proxy_only", epoch, frontal.feature_vector(), t))

        quality = build_quality_only_variant(
            epoch, 250.0, channels, config.reject_peak_to_peak_v, n_missing_channels,
            neighboring_trial_rejection_rate(trial_idx, all_manifest_indices, kept_indices),
            recording_retained_fraction, sub, session, t.trial_id, code_sha,
        )
        out["signal_quality_only"].append(_record_from("signal_quality_only", epoch, quality.feature_vector(), t))

        for seed in CHANNEL_PERMUTATION_SEEDS:
            permuted = build_channel_permuted_variant(epoch, 250.0, channels, seed, sub, session, t.trial_id, code_sha)
            out[f"channel_group_permuted_seed{seed}"].append(
                _record_from(f"channel_group_permuted_seed{seed}", epoch, permuted.feature_vector(), t),
            )

    postcue_by_trial_idx = {r.trial_index_in_session: r for r in out["aligned_full"]}

    # Temporal control 1: pre-cue (same construction as falsification test 1).
    from app.research.neural.features import build_precue_trials
    perception_trials = [t for t in trials if t.condition == "perception"]
    precue_manifests = build_precue_trials(perception_trials)
    precue_epochs, precue_kept, precue_manifest = preprocess_recording(raw, precue_manifests, raw_hash, config)
    if "precue" in precue_epochs:
        precue_channels = list(precue_manifest.included_channels)
        for i, t in enumerate(precue_kept):
            trial_idx = _trial_index_from_trial_id(t.trial_id)
            match = postcue_by_trial_idx.get(trial_idx)
            if match is None:
                continue
            variant = build_full_channel_variant(
                precue_epochs["precue"][i], 250.0, precue_channels, sub, session, t.trial_id, code_sha,
                variant_id="temporally_shifted_precue", condition="precue",
            )
            out["temporally_shifted_precue"].append(TrialRecord(
                participant_id=sub, session_id=session, trial_index_in_session=trial_idx, modality=match.modality,
                prior_vividness=None, vividness=match.vividness, neural_features=variant.feature_vector(),
                session_index=match.session_index, block_index=match.block_index,
                trial_index_in_block=match.trial_index_in_block, stimulus_category=match.stimulus_category,
            ))

    # Temporal control 2: late-shift (NEW).
    late_shift_manifests = build_late_shift_trials(imagery_trials)
    late_epochs, late_kept, late_manifest = preprocess_recording(raw, late_shift_manifests, raw_hash, config)
    if "late_shift" in late_epochs:
        late_channels = list(late_manifest.included_channels)
        for i, t in enumerate(late_kept):
            trial_idx = _trial_index_from_trial_id(t.trial_id)
            match = postcue_by_trial_idx.get(trial_idx)
            if match is None:
                continue
            variant = build_full_channel_variant(
                late_epochs["late_shift"][i], 250.0, late_channels, sub, session, t.trial_id, code_sha,
                variant_id="temporally_shifted_late", condition="late_shift",
            )
            out["temporally_shifted_late"].append(TrialRecord(
                participant_id=sub, session_id=session, trial_index_in_session=trial_idx, modality=match.modality,
                prior_vividness=None, vividness=match.vividness, neural_features=variant.feature_vector(),
                session_index=match.session_index, block_index=match.block_index,
                trial_index_in_block=match.trial_index_in_block, stimulus_category=match.stimulus_category,
            ))

    return out


def _run_variant(records: list[TrialRecord]) -> dict:
    records = sorted(records, key=lambda r: (r.participant_id, r.session_id, r.trial_index_in_session))
    records = add_lagged_prior_vividness(records)
    fold_results = run_loso_nested_validation(records)
    primary = estimate_primary_endpoint(fold_results)
    return {"n_trials": len(records), "n_participants": primary.n_participants, "endpoint": primary}


def _paired_decision(deltas_a: dict[str, float], deltas_b: dict[str, float]) -> dict:
    """Paired per-participant comparison (a minus b): mean, bootstrap CI,
    and exact sign-flip p-value on the SAME machinery as the primary
    estimand's own inference, applied to a difference-of-deltas array."""
    common = sorted(set(deltas_a) & set(deltas_b))
    diffs = np.array([deltas_a[p] - deltas_b[p] for p in common])
    ci_low, ci_high = bootstrap_ci(diffs)
    p_value = exact_sign_flip_test(diffs)
    return {
        "n_participants": len(common), "mean_diff": float(diffs.mean()) if len(diffs) else float("nan"),
        "ci_low": ci_low, "ci_high": ci_high, "sign_flip_p_value": p_value,
        "per_participant_diff": {p: deltas_a[p] - deltas_b[p] for p in common},
    }


def main() -> None:
    usable_participants = _load_frozen_usable_participants()
    print(f"Reusing frozen usable participants (n={len(usable_participants)}): {usable_participants}", file=sys.stderr)
    code_sha = _code_sha()

    pooled: dict[str, list[TrialRecord]] = {key: [] for key in VARIANT_KEYS}
    per_subject_status: dict[str, str] = {}

    for sub in usable_participants:
        print(f"Processing {sub} ...", file=sys.stderr)
        try:
            variant_records = build_variant_records_for_subject(sub, code_sha)
        except Exception as e:
            per_subject_status[sub] = f"exception: {e}"
            continue
        if not variant_records.get("aligned_full"):
            per_subject_status[sub] = "no_aligned_full_records_produced"
            continue
        per_subject_status[sub] = "ok"
        for key in VARIANT_KEYS:
            pooled[key].extend(variant_records.get(key, []))

    print(f"Per-subject status: {per_subject_status}", file=sys.stderr)

    endpoints: dict[str, dict] = {}
    for key in VARIANT_KEYS:
        if len({r.participant_id for r in pooled[key]}) < 3:
            endpoints[key] = None
            continue
        print(f"Running LOSO for variant={key} (n_trials={len(pooled[key])}) ...", file=sys.stderr)
        endpoints[key] = _run_variant(pooled[key])

    created_at = datetime.now(timezone.utc).isoformat()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    def _endpoint_summary(key: str) -> dict | None:
        e = endpoints.get(key)
        if e is None:
            return None
        return {
            "n_trials": e["n_trials"], "n_participants": e["n_participants"],
            "mean_delta_oos": e["endpoint"].mean_delta_oos, "ci_low": e["endpoint"].ci_low,
            "ci_high": e["endpoint"].ci_high, "sign_flip_p_value": e["endpoint"].exact_sign_flip_p_value,
            "per_participant_deltas": e["endpoint"].per_participant_deltas,
        }

    aligned_summary = _endpoint_summary("aligned_full")
    precue_summary = _endpoint_summary("temporally_shifted_precue")
    late_summary = _endpoint_summary("temporally_shifted_late")

    temporal_result = {
        "aligned_full": aligned_summary, "temporally_shifted_precue": precue_summary,
        "temporally_shifted_late": late_summary,
    }
    if aligned_summary and precue_summary:
        temporal_result["aligned_minus_precue"] = _paired_decision(
            aligned_summary["per_participant_deltas"], precue_summary["per_participant_deltas"],
        )
    if aligned_summary and late_summary:
        temporal_result["aligned_minus_late_shift"] = _paired_decision(
            aligned_summary["per_participant_deltas"], late_summary["per_participant_deltas"],
        )

    permuted_summaries = {
        f"seed{seed}": _endpoint_summary(f"channel_group_permuted_seed{seed}") for seed in CHANNEL_PERMUTATION_SEEDS
    }
    frontal_summary = _endpoint_summary("frontal_proxy_only")
    quality_summary = _endpoint_summary("signal_quality_only")

    payload = {
        "dataset_id": "ds005815", "dataset_version": "2.0.1", "code_sha": code_sha, "created_at": created_at,
        "confirmatory_or_exploratory": "confirmatory",
        "usable_participants": usable_participants, "per_subject_status": per_subject_status,
        "channel_permutation_seeds": list(CHANNEL_PERMUTATION_SEEDS),
        "test_2_temporal_shift": temporal_result,
        "test_4_channel_permutation": {
            "primary_aligned": aligned_summary, "permuted_by_seed": permuted_summaries,
        },
        "test_5_frontal_proxy_only": {
            "primary_aligned": aligned_summary, "frontal_proxy": frontal_summary,
            "aligned_minus_frontal": (
                _paired_decision(aligned_summary["per_participant_deltas"], frontal_summary["per_participant_deltas"])
                if aligned_summary and frontal_summary else None
            ),
        },
        "test_7_signal_quality_only": {
            "primary_aligned": aligned_summary, "quality_only": quality_summary,
            "aligned_minus_quality": (
                _paired_decision(aligned_summary["per_participant_deltas"], quality_summary["per_participant_deltas"])
                if aligned_summary and quality_summary else None
            ),
        },
    }
    out_path = os.path.join(RESULTS_DIR, "c1_falsification_closure.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
