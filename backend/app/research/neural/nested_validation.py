"""Nested leave-one-subject-out validation for the C1 primary estimand (H2).

Builds matched behavior-only and behavior-plus-neural models over IDENTICAL
outer (LOSO) and inner (participant-grouped) folds, computes the frozen
primary estimand (Delta_OOS, the subject-level paired difference in ordinal
log-score), and runs leakage-safe, repeated-measures-respecting permutation
inference. Participant is the inferential unit throughout, per
`C1_PROTOCOL.md` Sections 5-6.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.models import OrdinalFeatureModel, participant_grouped_split

TASK_FAMILY_ORDER = ("visual", "auditory", "mix")
STIMULUS_CATEGORY_ORDER = (
    "face", "square", "speech", "music", "face_speech", "face_music", "square_speech", "square_music",
    "unknown",
)


@dataclass
class TrialRecord:
    """One trial's worth of behavior-only covariates, neural features, and
    the frozen target — the unit nested_validation operates on."""
    participant_id: str
    session_id: str
    trial_index_in_session: int
    modality: str  # "visual" | "auditory" | "mix"
    prior_vividness: float | None  # lagged, same participant -- never the current trial's own target
    vividness: float
    neural_features: np.ndarray
    session_index: int = 0
    block_index: int = 0
    trial_index_in_block: int = 0
    stimulus_category: str = "unknown"


def broad_stimulus_category(stimulus_id: str) -> str:
    tags = set(stimulus_id.split("_"))
    if "face" in tags and "speech" in tags:
        return "face_speech"
    if "face" in tags and "music" in tags:
        return "face_music"
    if "square" in tags and "speech" in tags:
        return "square_speech"
    if "square" in tags and "music" in tags:
        return "square_music"
    if "face" in tags:
        return "face"
    if "square" in tags:
        return "square"
    if "speech" in tags:
        return "speech"
    if "music" in tags:
        return "music"
    return "unknown"


def build_behavior_only_matrix(records: list[TrialRecord]) -> np.ndarray:
    """Prespecified, non-neural covariates only (C1_ANALYSIS_SPEC.md Section
    2): prior behavioral performance (lagged vividness, 0 if unavailable —
    the first trial of a session/participant has no history, a real
    constraint, not an imputation choice) plus one-hot modality and the
    trial index within session."""
    rows = []
    for r in records:
        modality_onehot = [1.0 if r.modality == m else 0.0 for m in TASK_FAMILY_ORDER]
        prior = r.prior_vividness if r.prior_vividness is not None else 0.0
        has_prior = 1.0 if r.prior_vividness is not None else 0.0
        category = r.stimulus_category if r.stimulus_category in STIMULUS_CATEGORY_ORDER else "unknown"
        category_onehot = [1.0 if category == c else 0.0 for c in STIMULUS_CATEGORY_ORDER]
        rows.append([
            prior,
            has_prior,
            float(r.session_index),
            float(r.block_index),
            float(r.trial_index_in_block),
            float(r.trial_index_in_session),
            *modality_onehot,
            *category_onehot,
        ])
    return np.array(rows)


def build_behavior_plus_neural_matrix(records: list[TrialRecord]) -> np.ndarray:
    behavior_only = build_behavior_only_matrix(records)
    neural = np.array([r.neural_features for r in records])
    return np.concatenate([behavior_only, neural], axis=1)


def add_lagged_prior_vividness(trials_by_participant_session: list[TrialRecord]) -> list[TrialRecord]:
    """Fill in `prior_vividness` from the immediately preceding trial of the
    SAME participant and session, in trial-index order. Must be called on
    trials already sorted by (participant_id, session_id,
    trial_index_in_session); returns new records, does not mutate targets."""
    out: list[TrialRecord] = []
    last_by_key: dict[tuple[str, str], float] = {}
    for r in trials_by_participant_session:
        key = (r.participant_id, r.session_id)
        prior = last_by_key.get(key)
        out.append(TrialRecord(
            participant_id=r.participant_id, session_id=r.session_id,
            trial_index_in_session=r.trial_index_in_session, modality=r.modality,
            prior_vividness=prior, vividness=r.vividness, neural_features=r.neural_features,
            session_index=r.session_index, block_index=r.block_index,
            trial_index_in_block=r.trial_index_in_block, stimulus_category=r.stimulus_category,
        ))
        last_by_key[key] = r.vividness
    return out


@dataclass
class OuterFoldResult:
    held_out_participant: str
    n_train: int
    n_test: int
    behavior_only_log_score: float
    behavior_plus_neural_log_score: float
    delta_oos: float  # behavior_only - behavior_plus_neural; positive = neural improves prediction
    chosen_l2: float  # the inner-CV-selected hyperparameter, exposed for provenance/falsification checks
    behavior_plus_neural_checkpoint_hash: str  # of the model fit on train_records only

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def run_loso_nested_validation(
    records: list[TrialRecord], inner_l2_grid: tuple[float, ...] = (0.1, 1.0, 10.0), inner_k: int = 5,
) -> list[OuterFoldResult]:
    """LOSO outer CV; inner CV (participant-grouped) selects l2 by mean
    behavior-plus-neural log-score among the outer-training participants
    only, then both models are refit on the FULL outer-training set with
    that hyperparameter and evaluated once on the held-out participant.
    Never inspects the outer-test participant's data at any point."""
    participants = sorted({r.participant_id for r in records})
    results: list[OuterFoldResult] = []

    for held_out in participants:
        train_mask, test_mask = participant_grouped_split(
            [r.participant_id for r in records], held_out=held_out,
        )
        train_records = [r for r, m in zip(records, train_mask) if m]
        test_records = [r for r, m in zip(records, test_mask) if m]
        result = run_single_loso_fold(train_records, test_records, held_out, inner_l2_grid, inner_k=inner_k)
        if result is not None:
            results.append(result)

    return results


def run_single_loso_fold(
    train_records: list[TrialRecord], test_records: list[TrialRecord],
    held_out_label: str, inner_l2_grid: tuple[float, ...] = (0.1, 1.0, 10.0), inner_k: int = 5,
) -> OuterFoldResult | None:
    """One LOSO fold in isolation: inner CV over `train_records` only
    selects the hyperparameter, both models are fit on the full
    `train_records`, then evaluated once on `test_records`. Extracted from
    `run_loso_nested_validation` so falsification test 9 can corrupt a
    single fold's test targets without touching any other fold's training
    data (corrupting a participant's targets in the full sweep would also
    corrupt that participant's contribution to every OTHER fold's training
    set, which tests something different from what test 9 needs)."""
    if len(test_records) < 2:
        return None

    train_participants = sorted({r.participant_id for r in train_records})
    best_l2 = inner_l2_grid[0]
    best_inner_score = float("inf")
    if len(train_participants) >= 3:
        n_inner_folds = max(2, min(inner_k, len(train_participants)))
        participant_folds = [
            set(fold.tolist()) for fold in np.array_split(np.array(train_participants), n_inner_folds)
        ]
        for l2 in inner_l2_grid:
            inner_scores = []
            for val_participants in participant_folds:
                inner_train = [r for r in train_records if r.participant_id not in val_participants]
                inner_val = [r for r in train_records if r.participant_id in val_participants]
                if len(inner_val) < 2 or len(inner_train) < 2:
                    continue
                x_tr = build_behavior_plus_neural_matrix(inner_train)
                y_tr = np.array([r.vividness for r in inner_train])
                x_val = build_behavior_plus_neural_matrix(inner_val)
                y_val = np.array([r.vividness for r in inner_val])
                m = OrdinalFeatureModel(l2=l2).fit(x_tr, y_tr)
                inner_scores.append(m.log_score(x_val, y_val))
            if inner_scores and np.mean(inner_scores) < best_inner_score:
                best_inner_score = np.mean(inner_scores)
                best_l2 = l2

    x_train_behavior = build_behavior_only_matrix(train_records)
    x_train_neural = build_behavior_plus_neural_matrix(train_records)
    y_train = np.array([r.vividness for r in train_records])
    x_test_behavior = build_behavior_only_matrix(test_records)
    x_test_neural = build_behavior_plus_neural_matrix(test_records)
    y_test = np.array([r.vividness for r in test_records])

    behavior_model = OrdinalFeatureModel(l2=best_l2).fit(x_train_behavior, y_train)
    neural_model = OrdinalFeatureModel(l2=best_l2).fit(x_train_neural, y_train)

    behavior_score = behavior_model.log_score(x_test_behavior, y_test)
    neural_score = neural_model.log_score(x_test_neural, y_test)

    return OuterFoldResult(
        held_out_participant=held_out_label, n_train=len(train_records), n_test=len(test_records),
        behavior_only_log_score=behavior_score, behavior_plus_neural_log_score=neural_score,
        delta_oos=behavior_score - neural_score, chosen_l2=best_l2,
        behavior_plus_neural_checkpoint_hash=neural_model.to_spec("neural_model").checkpoint_hash,
    )


@dataclass
class PrimaryEstimandResult:
    n_participants: int
    mean_delta_oos: float
    std_delta_oos: float
    ci_low: float
    ci_high: float
    exact_sign_flip_p_value: float
    per_participant_deltas: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def sampled_sign_flip_p_value(deltas: np.ndarray, n_samples: int = 20000, seed: int = 42) -> float:
    """Monte Carlo approximation of the two-sided sign-flip test: a large
    random sample of sign-flip patterns rather than full enumeration.
    Appropriate whenever an approximate p-value is acceptable (e.g. inside a
    power simulation, where the test is itself called thousands of times) or
    when n is too large to enumerate exactly."""
    n = len(deltas)
    if n == 0:
        return 1.0
    observed = np.abs(deltas.mean())
    rng = np.random.RandomState(seed)
    signs = rng.choice([-1, 1], size=(n_samples, n))
    null_means = np.abs((signs * deltas).mean(axis=1))
    return float((null_means >= observed - 1e-12).mean())


def exact_sign_flip_test(deltas: np.ndarray) -> float:
    """Exact two-sided sign-flip permutation test on the mean of paired
    per-participant differences — exact (not approximated) whenever
    2**n_participants is small enough to enumerate, which it is for the
    LOSO participant counts this project ever produces (<= ~25)."""
    n = len(deltas)
    if n == 0:
        return 1.0
    observed = np.abs(deltas.mean())
    if n > 20:
        # fall back to a large random sample of sign flips rather than full
        # enumeration (2**n becomes impractically large past ~20)
        return sampled_sign_flip_p_value(deltas, n_samples=20000, seed=42)

    count_ge = 0
    total = 0
    for signs in itertools.product([-1, 1], repeat=n):
        total += 1
        # abs() of the MEAN (after signed summation), not the mean of abs()
        # values -- the latter is sign-invariant per element and would
        # silently destroy the cancellation a sign-flip test depends on,
        # always returning p=1.0 regardless of the data.
        null_mean = np.abs((np.array(signs) * deltas).mean())
        if null_mean >= observed - 1e-12:
            count_ge += 1
    return count_ge / total


def bootstrap_ci(deltas: np.ndarray, n_boot: int = 2000, seed: int = 42, alpha: float = 0.05) -> tuple[float, float]:
    """Participant-level bootstrap (resampling participants with
    replacement) confidence interval for the mean paired difference."""
    if len(deltas) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.RandomState(seed)
    n = len(deltas)
    boot_means = np.array([
        rng.choice(deltas, size=n, replace=True).mean() for _ in range(n_boot)
    ])
    lo = float(np.percentile(boot_means, 100 * alpha / 2))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return lo, hi


def estimate_primary_endpoint(fold_results: list[OuterFoldResult]) -> PrimaryEstimandResult:
    deltas = np.array([r.delta_oos for r in fold_results])
    per_participant = {r.held_out_participant: r.delta_oos for r in fold_results}
    ci_low, ci_high = bootstrap_ci(deltas)
    p_value = exact_sign_flip_test(deltas)
    return PrimaryEstimandResult(
        n_participants=len(fold_results),
        mean_delta_oos=float(deltas.mean()) if len(deltas) else float("nan"),
        std_delta_oos=float(deltas.std()) if len(deltas) else float("nan"),
        ci_low=ci_low, ci_high=ci_high,
        exact_sign_flip_p_value=p_value,
        per_participant_deltas=per_participant,
    )


def block_shuffle_within_participant(records: list[TrialRecord], seed: int = 42) -> list[TrialRecord]:
    """Leakage-safe permutation null: shuffle the vividness TARGET among
    trials WITHIN each participant (never across participants), preserving
    the repeated-measures structure per C1_ANALYSIS_SPEC.md Section 6. Used
    by falsification test 3 (Commit 7 requirement)."""
    rng = np.random.RandomState(seed)
    by_participant: dict[str, list[int]] = {}
    for i, r in enumerate(records):
        by_participant.setdefault(r.participant_id, []).append(i)

    shuffled_targets = [r.vividness for r in records]
    for _pid, idxs in by_participant.items():
        vals = [records[i].vividness for i in idxs]
        rng.shuffle(vals)
        for i, v in zip(idxs, vals):
            shuffled_targets[i] = v

    return [
        TrialRecord(
            participant_id=r.participant_id, session_id=r.session_id,
            trial_index_in_session=r.trial_index_in_session, modality=r.modality,
            prior_vividness=r.prior_vividness, vividness=shuffled_targets[i],
            neural_features=r.neural_features,
            session_index=r.session_index, block_index=r.block_index,
            trial_index_in_block=r.trial_index_in_block, stimulus_category=r.stimulus_category,
        )
        for i, r in enumerate(records)
    ]
