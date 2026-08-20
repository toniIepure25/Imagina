"""Deterministic protocol-count invariants for the NSD-Imagery experiment
structure, and structural checks on the row-mapping blocker artifact.

No NSD data is downloaded; these are pure arithmetic/documentation
consistency checks plus a schema check on the (possibly BLOCKED) row-mapping
artifact when it is present in the working tree.
"""
from __future__ import annotations

import json
from pathlib import Path

RUNS_PER_TASK_TYPE = 3  # vision, attention: 3 runs each (A/B/C)
IMAGERY_RUNS_PER_SET = 2  # each of A/B/C imagery is split into _1 and _2
TRIALS_PER_RUN = 48
STIMULI_PER_SET = 6


class TestNSDImageryProtocolCounts:
    def test_task_trial_totals(self):
        vision = RUNS_PER_TASK_TYPE * TRIALS_PER_RUN
        attention = RUNS_PER_TASK_TYPE * TRIALS_PER_RUN
        imagery = (RUNS_PER_TASK_TYPE * IMAGERY_RUNS_PER_SET) * TRIALS_PER_RUN

        assert vision == 144
        assert attention == 144
        assert imagery == 288
        assert vision + attention + imagery == 576

    def test_imagery_breakdown_by_set(self):
        per_set = IMAGERY_RUNS_PER_SET * TRIALS_PER_RUN
        assert per_set == 96
        assert per_set == STIMULI_PER_SET * 16  # 6 stimuli x 16 repeats
        assert per_set * 3 == 288  # simple + complex + concepts

    def test_candidate_pool_size(self):
        # 6 simple (Set A) + 6 complex (Set B); Set C excluded from
        # image-ground-truth retrieval (no fixed ground-truth image).
        assert STIMULI_PER_SET * 2 == 12

    def test_raw_beta_row_discrepancy_is_144_not_smaller_or_larger(self):
        raw_beta_rows = 720
        task_rows = 576
        assert raw_beta_rows - task_rows == 144


class TestRowMappingArtifactSchema:
    """If results/c3_nsdimagery_row_mapping.json exists in the working tree,
    it must have a well-formed status and, if BLOCKED, must not silently
    imply a resolved mapping anywhere in the document.
    """

    def _load(self) -> dict | None:
        # backend/app/tests -> repo root is four parents up
        repo_root = Path(__file__).resolve().parents[4]
        path = repo_root / "results" / "c3_nsdimagery_row_mapping.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    def test_status_field_present_and_valid(self):
        data = self._load()
        if data is None:
            return  # nothing to check yet
        assert data["status"] in {
            "BLOCKED_IMAGERY_ROW_PROVENANCE",
            "CERTIFIED",
        }

    def test_blocked_status_documents_the_discrepancy(self):
        data = self._load()
        if data is None or data["status"] != "BLOCKED_IMAGERY_ROW_PROVENANCE":
            return
        assert "unexplained_row_discrepancy" in data
        assert data["unexplained_row_discrepancy"]["non_task_or_unexplained_rows"] == 144
        assert "decision" in data
        assert data["decision"]["status"] == "BLOCKED_IMAGERY_ROW_PROVENANCE"

    def test_blocked_status_documents_search_trail(self):
        data = self._load()
        if data is None or data["status"] != "BLOCKED_IMAGERY_ROW_PROVENANCE":
            return
        search = data["authoritative_metadata_file_search"]
        assert len(search["search_locations_checked"]) >= 3
        for entry in search["search_locations_checked"]:
            assert entry["result"] in {"NOT_FOUND", "FOUND"}
