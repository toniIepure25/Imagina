"""Deterministic tests for the authoritative NSD-Imagery beta-row block
mapping. No NSD data is downloaded; these check the programmatic derivation
of run blocks from the frozen run-order + beta-multiplicity specification.
"""
from __future__ import annotations

from app.research.fmri.nsdimagery_row_mapping import (
    RUN_ORDER,
    block_for_row,
    compute_run_blocks,
    expected_counts,
    total_expected_beta_rows,
)

EXPECTED_BLOCKS = {
    "visA": (0, 48), "attA": (48, 144), "imgA_1": (144, 192),
    "visB": (192, 240), "attB": (240, 336), "imgB_1": (336, 384),
    "visC": (384, 432), "attC": (432, 528), "imgC_1": (528, 576),
    "imgA_2": (576, 624), "imgB_2": (624, 672), "imgC_2": (672, 720),
}


class TestRunBlocks:
    def test_total_beta_count_is_720(self):
        assert total_expected_beta_rows() == 720

    def test_blocks_match_expected_offsets(self):
        blocks = {b.run_name: (b.row_start, b.row_end) for b in compute_run_blocks()}
        assert blocks == EXPECTED_BLOCKS

    def test_blocks_are_contiguous_and_non_overlapping(self):
        blocks = compute_run_blocks()
        for i in range(1, len(blocks)):
            assert blocks[i].row_start == blocks[i - 1].row_end

    def test_run_order_has_12_runs(self):
        assert len(RUN_ORDER) == 12
        assert len(compute_run_blocks()) == 12

    def test_vision_beta_multiplicity_is_1(self):
        for b in compute_run_blocks():
            if b.kind == "vis":
                assert b.n_betas == b.n_trials == 48

    def test_imagery_beta_multiplicity_is_1(self):
        for b in compute_run_blocks():
            if b.kind == "img":
                assert b.n_betas == b.n_trials == 48

    def test_attention_beta_multiplicity_is_2(self):
        for b in compute_run_blocks():
            if b.kind == "att":
                assert b.n_betas == 2 * b.n_trials == 96


class TestExpectedCounts:
    def test_category_totals(self):
        counts = expected_counts()
        assert counts["total"] == 720
        assert counts["vision_rows"] == 144
        assert counts["imagery_rows"] == 288
        assert counts["attention_rows"] == 288

    def test_trial_totals_match_576_task_trials(self):
        counts = expected_counts()
        trial_total = counts["vision_trials"] + counts["imagery_trials"] + counts["attention_trials"]
        assert trial_total == 576

    def test_primary_and_secondary_imagery_subset_sizes(self):
        # Set B (complex, primary) = imgB_1 + imgB_2 = 96 trials; Set A
        # (simple, secondary) = imgA_1 + imgA_2 = 96 trials.
        blocks = compute_run_blocks()
        set_b_imagery = sum(b.n_trials for b in blocks if b.kind == "img" and b.stimulus_set == "B")
        set_a_imagery = sum(b.n_trials for b in blocks if b.kind == "img" and b.stimulus_set == "A")
        assert set_b_imagery == 96
        assert set_a_imagery == 96


class TestBlockForRow:
    def test_first_and_last_row_of_each_block(self):
        for run_name, (start, end) in EXPECTED_BLOCKS.items():
            assert block_for_row(start).run_name == run_name
            assert block_for_row(end - 1).run_name == run_name

    def test_row_719_is_last_block(self):
        assert block_for_row(719).run_name == "imgC_2"

    def test_out_of_range_raises(self):
        import pytest
        with pytest.raises(IndexError):
            block_for_row(720)
