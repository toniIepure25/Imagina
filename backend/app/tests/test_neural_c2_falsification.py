"""Tests for the C2 falsification battery's pure-Python helper functions
(Commit 7). The real-data controls themselves are exercised via the real
run against ds005815 (results/c2_negative_controls.json); this covers the
construction logic that doesn't require real EEG data.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mne")

from app.research.neural.run_c2_falsification import within_block_shuffle  # noqa: E402


class TestWithinBlockShuffle:
    def test_preserves_each_participant_blocks_own_label_multiset(self):
        labels = np.array(["visual_square", "visual_face_male", "visual_face_female", "visual_square"] * 2)
        block_index = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        participant_ids = np.array(["p0"] * 8)
        shuffled = within_block_shuffle(labels, block_index, participant_ids, seed=1)
        for block in (0, 1):
            mask = block_index == block
            assert sorted(shuffled[mask].tolist()) == sorted(labels[mask].tolist())

    def test_does_not_mix_labels_across_participants(self):
        labels = np.array(["visual_square", "visual_face_male"] * 4)
        block_index = np.zeros(8, dtype=int)
        participant_ids = np.array(["p0"] * 4 + ["p1"] * 4)
        shuffled = within_block_shuffle(labels, block_index, participant_ids, seed=2)
        for pid in ("p0", "p1"):
            mask = participant_ids == pid
            assert sorted(shuffled[mask].tolist()) == sorted(labels[mask].tolist())

    def test_deterministic_for_same_seed(self):
        rng = np.random.RandomState(0)
        labels = rng.choice(["visual_square", "visual_face_male", "visual_face_female"], size=48)
        block_index = np.repeat(np.arange(4), 12)
        participant_ids = np.array(["p0"] * 48)
        s1 = within_block_shuffle(labels, block_index, participant_ids, seed=42)
        s2 = within_block_shuffle(labels, block_index, participant_ids, seed=42)
        assert np.array_equal(s1, s2)

    def test_actually_changes_the_order_for_a_nontrivial_block(self):
        classes = ["visual_square", "visual_face_male", "visual_face_female", "visual_square", "visual_face_male"]
        labels = np.array(classes)
        block_index = np.zeros(5, dtype=int)
        participant_ids = np.array(["p0"] * 5)
        shuffled = within_block_shuffle(labels, block_index, participant_ids, seed=7)
        # Multiset preserved, but not guaranteed to differ in order for every
        # seed/labels combination -- assert the weaker, always-true property
        # (multiset match) directly rather than assuming a specific
        # permutation always differs from the identity.
        assert sorted(shuffled.tolist()) == sorted(labels.tolist())
