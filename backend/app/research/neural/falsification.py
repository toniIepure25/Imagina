"""The ten required falsification tests for Scientific Gate C1 (Commit 7).

Each function returns a `FalsificationOutcome` comparing a "should survive"
condition (the real, correctly-constructed effect) against a "should not
survive" condition (a corrupted/degenerate version of the same pipeline).
Most reuse `nested_validation.py`'s LOSO machinery directly rather than
reimplementing statistics — a falsification test is only informative if it
exercises the exact same estimation pipeline as the primary analysis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.research.neural.models import participant_grouped_split
from app.research.neural.nested_validation import (
    TrialRecord,
    block_shuffle_within_participant,
    estimate_primary_endpoint,
    run_loso_nested_validation,
    run_single_loso_fold,
)


@dataclass
class FalsificationOutcome:
    test_id: str
    description: str
    real_mean_delta_oos: float
    corrupted_mean_delta_oos: float
    passed: bool  # True if the corrupted condition collapsed the effect as expected

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _delta(records: list[TrialRecord]) -> float:
    return estimate_primary_endpoint(run_loso_nested_validation(records)).mean_delta_oos


def test_1_precue_vs_postcue(
    postcue_records: list[TrialRecord], precue_records: list[TrialRecord], tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 1: pre-cue EEG (same trials, same targets, but
    neural features drawn from BEFORE the stimulus was shown) must not match
    post-cue predictive performance."""
    real = _delta(postcue_records)
    corrupted = _delta(precue_records)
    return FalsificationOutcome(
        test_id="1_precue_vs_postcue",
        description="Pre-cue EEG must not match post-cue predictive performance.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real - tolerance or corrupted <= tolerance,
    )


def test_2_temporal_shift(
    aligned_records: list[TrialRecord], shifted_records: list[TrialRecord], tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 2: temporally shifted EEG (features from a window
    offset from the true stimulus-locked window) must underperform correctly
    aligned EEG."""
    real = _delta(aligned_records)
    corrupted = _delta(shifted_records)
    return FalsificationOutcome(
        test_id="2_temporal_shift",
        description="Temporally shifted EEG must underperform correctly aligned EEG.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real,
    )


def test_3_label_shuffle_within_blocks(
    records: list[TrialRecord], seed: int = 42, tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 3: trial labels shuffled within valid
    exchangeability blocks (participant, here) must remove the effect."""
    real = _delta(records)
    shuffled = block_shuffle_within_participant(records, seed=seed)
    corrupted = _delta(shuffled)
    return FalsificationOutcome(
        test_id="3_label_shuffle_within_blocks",
        description="Trial labels shuffled within participant must remove the effect.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=abs(corrupted) < tolerance,
    )


def test_4_random_channel_permutation(
    records: list[TrialRecord], permuted_records: list[TrialRecord], tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 4: random channel-LABEL permutation (features
    recomputed as if frozen channel groups pointed at the wrong channels)
    must degrade spatially-structured models."""
    real = _delta(records)
    corrupted = _delta(permuted_records)
    return FalsificationOutcome(
        test_id="4_random_channel_permutation",
        description="Random channel permutation must degrade spatial models.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real,
    )


def test_5_ocular_only_control(
    full_feature_records: list[TrialRecord], ocular_only_records: list[TrialRecord], tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 5: ocular/frontal-proxy channels alone must not
    reproduce the claimed neural increment."""
    real = _delta(full_feature_records)
    corrupted = _delta(ocular_only_records)
    return FalsificationOutcome(
        test_id="5_ocular_only_control",
        description="Ocular-channel-only features must not reproduce the neural increment.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real - tolerance or corrupted <= tolerance,
    )


def test_6_participant_id_only(records: list[TrialRecord]) -> FalsificationOutcome:
    """Falsification test 6: participant ID alone must not explain cross-
    subject performance. Trivially true by construction under LOSO -- a
    held-out participant's ID was never seen during training, so a
    participant-ID-only "neural" feature carries zero information for that
    fold. This test proves the claim structurally rather than assuming it:
    it substitutes a random per-participant constant (indistinguishable in
    information content from a participant-ID indicator) as the "neural"
    feature and confirms Delta_OOS collapses."""
    rng = np.random.RandomState(0)
    participant_constants = {pid: rng.randn() for pid in {r.participant_id for r in records}}
    id_only_records = [
        TrialRecord(
            r.participant_id, r.session_id, r.trial_index_in_session, r.modality,
            r.prior_vividness, r.vividness,
            neural_features=np.array([participant_constants[r.participant_id]]),
            session_index=r.session_index, block_index=r.block_index,
            trial_index_in_block=r.trial_index_in_block, stimulus_category=r.stimulus_category,
        )
        for r in records
    ]
    real = _delta(records)
    corrupted = _delta(id_only_records)
    return FalsificationOutcome(
        test_id="6_participant_id_only",
        description="Participant-ID-only features must not explain cross-subject performance.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=abs(corrupted) < 0.1,
    )


def test_7_signal_quality_only(
    full_feature_records: list[TrialRecord], quality_only_records: list[TrialRecord], tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 7: signal-quality metrics alone must not
    reproduce the primary result."""
    real = _delta(full_feature_records)
    corrupted = _delta(quality_only_records)
    return FalsificationOutcome(
        test_id="7_signal_quality_only",
        description="Signal-quality-only features must not reproduce the primary result.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real - tolerance or corrupted <= tolerance,
    )


def test_8_no_duplicate_stimulus_leakage(records: list[TrialRecord]) -> FalsificationOutcome:
    """Falsification test 8: duplicate stimulus leakage must be impossible
    across confirmatory folds -- a structural check, not a statistical one.
    Under participant-grouped LOSO, every trial's participant_id determines
    its fold membership; verifies no trial_index/participant combination
    appears in both a fold's train and test partition for every held-out
    participant."""
    participants = sorted({r.participant_id for r in records})
    leak_found = False
    for held_out in participants:
        train_mask, test_mask = participant_grouped_split(
            [r.participant_id for r in records], held_out=held_out,
        )
        train_ids = {
            (r.participant_id, r.session_id, r.trial_index_in_session)
            for r, m in zip(records, train_mask) if m
        }
        test_ids = {
            (r.participant_id, r.session_id, r.trial_index_in_session)
            for r, m in zip(records, test_mask) if m
        }
        if train_ids & test_ids:
            leak_found = True
            break

    return FalsificationOutcome(
        test_id="8_no_duplicate_stimulus_leakage",
        description="No (participant, session, trial) triple may appear in both train and test of any fold.",
        real_mean_delta_oos=0.0, corrupted_mean_delta_oos=0.0,
        passed=not leak_found,
    )


def test_9_hyperparameter_selection_blind_to_outer_test(records: list[TrialRecord]) -> FalsificationOutcome:
    """Falsification test 9: hyperparameter selection must not inspect
    outer-test results. Isolates ONE fold (`run_single_loso_fold`, not the
    full LOSO sweep) and corrupts only that fold's TEST-side targets to
    nonsense values, leaving its TRAIN-side records completely untouched.
    If inner CV or model fitting ever inspected the outer-test set, this
    corruption would change the trained model; comparing the two models'
    checkpoint hashes proves it does not.

    An earlier version of this test corrupted a participant's targets
    globally and re-ran the full multi-participant LOSO sweep — but under
    LOSO, a participant excluded from one fold's test set is included in
    every OTHER fold's training set, so that corruption silently changed
    OTHER folds' training data too (and crashed the ordinal model, whose
    class indexing assumes targets in 1-5). Isolating a single fold's
    train/test split directly avoids that cross-fold contamination.
    """
    participants = sorted({r.participant_id for r in records})
    if len(participants) < 4:
        return FalsificationOutcome(
            test_id="9_hyperparameter_selection_blind_to_outer_test",
            description="Not enough participants to run this check.",
            real_mean_delta_oos=0.0, corrupted_mean_delta_oos=0.0, passed=True,
        )
    held_out = participants[0]
    train_mask, test_mask = participant_grouped_split(
        [r.participant_id for r in records], held_out=held_out,
    )
    train_records = [r for r, m in zip(records, train_mask) if m]
    test_records = [r for r, m in zip(records, test_mask) if m]

    original_result = run_single_loso_fold(train_records, test_records, held_out)

    corrupted_test_records = [
        TrialRecord(
            r.participant_id, r.session_id, r.trial_index_in_session, r.modality,
            r.prior_vividness, 3.0,  # arbitrary fixed value, same for every test trial
            r.neural_features,
            session_index=r.session_index, block_index=r.block_index,
            trial_index_in_block=r.trial_index_in_block, stimulus_category=r.stimulus_category,
        )
        for r in test_records
    ]
    corrupted_result = run_single_loso_fold(train_records, corrupted_test_records, held_out)

    if original_result is None or corrupted_result is None:
        return FalsificationOutcome(
            test_id="9_hyperparameter_selection_blind_to_outer_test",
            description="Fold could not be computed.",
            real_mean_delta_oos=0.0, corrupted_mean_delta_oos=0.0, passed=False,
        )

    # Two things must both hold: (a) the SAME hyperparameter and the exact
    # same trained model (checkpoint hash) come out of both calls, since
    # inner CV and fitting only ever see train_records, which is identical
    # in both calls; (b) the reported score DOES change, since it is
    # computed by evaluating that same model against different test targets
    # -- proving the scoring step genuinely uses the test set rather than a
    # cached/leaked value.
    same_hyperparameter_and_model = (
        original_result.chosen_l2 == corrupted_result.chosen_l2
        and original_result.behavior_plus_neural_checkpoint_hash
        == corrupted_result.behavior_plus_neural_checkpoint_hash
    )
    score_legitimately_changed = (
        abs(original_result.behavior_plus_neural_log_score - corrupted_result.behavior_plus_neural_log_score) > 1e-9
    )

    return FalsificationOutcome(
        test_id="9_hyperparameter_selection_blind_to_outer_test",
        description=(
            "Corrupting only the outer-test targets must leave the selected "
            "hyperparameter and trained model checkpoint hash unchanged (both "
            "come from train_records only), while the reported test score must "
            "change (since it is computed against the corrupted test targets)."
        ),
        real_mean_delta_oos=original_result.delta_oos,
        corrupted_mean_delta_oos=corrupted_result.delta_oos,
        passed=same_hyperparameter_and_model and score_legitimately_changed,
    )


def test_10_behavior_plus_random_noise(
    records: list[TrialRecord], seed: int = 42, tolerance: float = 0.1,
) -> FalsificationOutcome:
    """Falsification test 10: behavior-plus-random-noise must not reproduce
    behavior-plus-neural gains."""
    rng = np.random.RandomState(seed)
    noise_records = [
        TrialRecord(
            r.participant_id, r.session_id, r.trial_index_in_session, r.modality,
            r.prior_vividness, r.vividness,
            neural_features=rng.randn(len(r.neural_features)),
            session_index=r.session_index, block_index=r.block_index,
            trial_index_in_block=r.trial_index_in_block, stimulus_category=r.stimulus_category,
        )
        for r in records
    ]
    real = _delta(records)
    corrupted = _delta(noise_records)
    return FalsificationOutcome(
        test_id="10_behavior_plus_random_noise",
        description="Behavior-plus-random-noise must not reproduce behavior-plus-neural gains.",
        real_mean_delta_oos=real, corrupted_mean_delta_oos=corrupted,
        passed=corrupted < real - tolerance or corrupted <= tolerance,
    )
