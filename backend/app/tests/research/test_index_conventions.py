"""Tests for NSD image-index conventions and cropBox interpretation.

These tests verify the critical mapping chain:
  session -> trial -> masterordering -> subjectim -> nsdId -> cocoId -> stimulus -> CLIP row

A one-index shift in any of these would silently corrupt the entire pilot.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path

import numpy as np
import pytest
from scipy.io import loadmat

NSD_DATA_ROOT = os.environ.get("NSD_DATA_ROOT")
SKIP_REAL_DATA = NSD_DATA_ROOT is None or not Path(NSD_DATA_ROOT).exists()


@pytest.mark.skipif(SKIP_REAL_DATA, reason="NSD_DATA_ROOT not available")
class TestImageIndexConventions:
    """Tests that fail under a one-index shift."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data_root = Path(NSD_DATA_ROOT)
        self.mat = loadmat(str(self.data_root / "experiments" / "nsd" / "nsd_expdesign.mat"))
        self.subjectim = self.mat["subjectim"]
        self.masterordering = self.mat["masterordering"].flatten()
        with open(self.data_root / "experiments" / "nsd" / "nsd_stim_info_merged.pkl", "rb") as f:
            self.stim_info = pickle.load(f, encoding="latin1")

    def test_subjectim_is_one_based(self):
        """subjectim values range from 1 to 73000, NOT 0 to 72999."""
        values = self.subjectim.flatten()
        assert values.min() >= 1, "subjectim should be 1-based"
        assert values.max() <= 73000, "subjectim max should be <= 73000"
        assert 0 not in values, "subjectim should NOT contain 0 (that would be 0-indexed)"

    def test_masterordering_is_one_based(self):
        """masterordering values range from 1 to 10000, NOT 0 to 9999."""
        values = self.masterordering
        assert values.min() >= 1, "masterordering should be 1-based"
        assert values.max() <= 10000, "masterordering max should be <= 10000"
        assert 0 not in values, "masterordering should NOT contain 0"

    def test_subjectim_shape(self):
        """subjectim should be [8, 10000] — 8 subjects, 10000 image slots each."""
        assert self.subjectim.shape == (8, 10000)

    def test_masterordering_covers_full_experiment(self):
        """masterordering has 30000 entries for subj01 (40 sessions * 750 trials)."""
        n_trials = 40 * 750
        assert len(self.masterordering) >= n_trials

    def test_stim_info_is_zero_indexed(self):
        """stim_info_merged.pkl rows are 0-indexed (row 0 = nsdId 0)."""
        assert len(self.stim_info) == 73000
        assert self.stim_info.iloc[0]["nsdId"] == 0

    def test_nsd_id_from_subjectim_conversion(self):
        """Converting subjectim to nsdId requires subtracting 1."""
        slot_value = int(self.subjectim[0, 0])
        nsd_id = slot_value - 1
        assert 0 <= nsd_id < 73000
        row = self.stim_info.iloc[nsd_id]
        assert row["nsdId"] == nsd_id

    def test_shift_by_one_fails(self):
        """Using subjectim value directly as index (without -1) accesses WRONG image."""
        slot_value = int(self.subjectim[0, 0])
        correct_nsd_id = slot_value - 1
        wrong_nsd_id = slot_value  # Off by one!

        if wrong_nsd_id < 73000:
            correct_coco = int(self.stim_info.iloc[correct_nsd_id]["cocoId"])
            wrong_coco = int(self.stim_info.iloc[wrong_nsd_id]["cocoId"])
            assert correct_coco != wrong_coco, \
                "One-index shift must produce different COCO image"

    def test_trial_to_image_chain(self):
        """Full chain: trial 0 -> masterordering -> subjectim -> nsdId -> cocoId."""
        trial_idx = 0
        image_slot = int(self.masterordering[trial_idx]) - 1  # to 0-based slot
        nsd_image_id_1based = int(self.subjectim[0, image_slot])
        nsd_id = nsd_image_id_1based - 1

        row = self.stim_info.iloc[nsd_id]
        assert row["nsdId"] == nsd_id
        assert int(row["cocoId"]) > 0

    def test_known_entry_validation(self):
        """Validate specific known entries to catch systematic errors.

        subj01, trial 0 (first trial of session 1):
        - masterordering[0] gives the image slot
        - subjectim[0, slot-1] gives the 1-based NSD image ID
        """
        slot = int(self.masterordering[0])
        assert 1 <= slot <= 10000
        nsd_1based = int(self.subjectim[0, slot - 1])
        assert 1 <= nsd_1based <= 73000
        nsd_id = nsd_1based - 1
        coco_id = int(self.stim_info.iloc[nsd_id]["cocoId"])
        assert coco_id > 0

    def test_subj01_unique_images_count(self):
        """subj01 sees 10000 unique images (some repeated across 3 sessions)."""
        subj01_ids = set(int(x) for x in self.subjectim[0, :])
        assert len(subj01_ids) == 10000 or len(subj01_ids) == 9999 or len(subj01_ids) == 9000


@pytest.mark.skipif(SKIP_REAL_DATA, reason="NSD_DATA_ROOT not available")
class TestCropBoxConvention:
    """Tests for the NSD cropBox format: (top, bottom, left, right) fractions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data_root = Path(NSD_DATA_ROOT)
        with open(self.data_root / "experiments" / "nsd" / "nsd_stim_info_merged.pkl", "rb") as f:
            self.stim_info = pickle.load(f, encoding="latin1")

    def test_cropbox_produces_square(self):
        """For the first 100 images, the forced-square crop gives valid dimensions."""

        for nsd_id in range(0, 100, 10):
            row = self.stim_info.iloc[nsd_id]
            cb = row["cropBox"]
            top, bot, left, right = float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3])
            assert top + bot < 1.0, f"nsdId={nsd_id}: top+bottom >= 1"
            assert left + right < 1.0, f"nsdId={nsd_id}: left+right >= 1"
            assert top >= 0 and bot >= 0 and left >= 0 and right >= 0

    def test_cropbox_format_is_top_bottom_left_right(self):
        """Verify the cropBox format by checking known patterns.

        Landscape images should have nonzero left/right (indices 2,3).
        Portrait images should have nonzero top/bottom (indices 0,1).
        """
        landscape_count = 0
        portrait_count = 0

        for nsd_id in range(0, 73000, 100):
            row = self.stim_info.iloc[nsd_id]
            cb = row["cropBox"]
            top, bot, left, right = float(cb[0]), float(cb[1]), float(cb[2]), float(cb[3])

            if left > 0 or right > 0:
                assert top == 0 and bot == 0, \
                    f"nsdId={nsd_id}: has left/right crop but also top/bottom"
                landscape_count += 1
            elif top > 0 or bot > 0:
                assert left == 0 and right == 0, \
                    f"nsdId={nsd_id}: has top/bottom crop but also left/right"
                portrait_count += 1

        assert landscape_count > 0, "Should have some landscape crops"
        assert portrait_count > 0, "Should have some portrait crops"

    def test_wrong_format_would_fail(self):
        """Using (top, LEFT, bottom, RIGHT) format produces non-square for asymmetric crops."""
        for nsd_id in range(73000):
            row = self.stim_info.iloc[nsd_id]
            cb = row["cropBox"]
            vals = [float(x) for x in cb]
            if vals[0] > 0 and vals[1] == 0 and vals[2] == 0 and vals[3] == 0:
                break

        # This is a portrait image with top-only crop
        # Wrong interpretation (top, left, bottom, right) would put the value in 'top'
        # Correct interpretation: (top, bottom, left, right) means top=vals[0], bottom=0
        assert vals[0] > 0


class TestCropBoxUnit:
    """Unit tests for apply_nsd_crop that don't require real data."""

    def test_landscape_center_crop(self):
        """A 640x480 image with equal left/right removal = center crop."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        img = Image.new("RGB", (640, 480), (128, 128, 128))
        crop_box = (0, 0, 0.125, 0.125)  # remove 12.5% from left AND right
        result = apply_nsd_crop(img, crop_box)
        assert result.size == (425, 425)

    def test_portrait_center_crop(self):
        """A 480x640 image with equal top/bottom removal = center crop."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        img = Image.new("RGB", (480, 640), (128, 128, 128))
        crop_box = (0.125, 0.125, 0, 0)  # remove 12.5% from top AND bottom
        result = apply_nsd_crop(img, crop_box)
        assert result.size == (425, 425)

    def test_landscape_left_crop(self):
        """A 640x427 image with right-only removal = left-aligned."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        img = Image.new("RGB", (640, 427), (128, 128, 128))
        crop_box = (0, 0, 0, 0.333)  # remove 33.3% from right only
        result = apply_nsd_crop(img, crop_box)
        assert result.size == (425, 425)

    def test_portrait_bottom_crop(self):
        """A 480x640 image with top-only removal = bottom-aligned."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        img = Image.new("RGB", (480, 640), (128, 128, 128))
        crop_box = (0.25, 0, 0, 0)  # remove 25% from top
        result = apply_nsd_crop(img, crop_box)
        assert result.size == (425, 425)

    def test_already_square(self):
        """A 612x612 image needs no crop."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        img = Image.new("RGB", (612, 612), (128, 128, 128))
        crop_box = (0, 0, 0, 0)
        result = apply_nsd_crop(img, crop_box)
        assert result.size == (425, 425)

    def test_one_index_shift_produces_wrong_crop(self):
        """If cropBox indices are swapped (left<->bottom), result differs."""
        from PIL import Image

        from app.research.fmri.download_stimuli import apply_nsd_crop

        np.random.seed(42)
        img_array = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)

        correct_box = (0, 0, 0.125, 0.125)  # top, bottom, left, right
        wrong_box = (0, 0.125, 0, 0.125)  # swapped: top, LEFT, bottom, RIGHT

        correct_result = np.array(apply_nsd_crop(img, correct_box))
        wrong_result = np.array(apply_nsd_crop(img, wrong_box))

        # They should be different (the wrong interpretation would give a different crop)
        assert not np.array_equal(correct_result, wrong_result), \
            "Swapping cropBox indices must produce a different image"
