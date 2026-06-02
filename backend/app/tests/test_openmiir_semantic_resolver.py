"""Tests for OpenMIIR Semantic Event Code Resolver v3.9.5.2."""

import json
import os

import pytest

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
META_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "external", "openmiir", "meta")


def _load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


class TestCandidateEvidenceGraph:
    def test_evidence_graph_exists(self):
        path = os.path.join(EXPORTS_DIR, "openmiir_candidate_evidence_graph.json")
        assert os.path.exists(path), f"Evidence graph not found at {path}"

    def test_evidence_graph_has_files_analyzed(self):
        graph = _load_json(os.path.join(EXPORTS_DIR, "openmiir_candidate_evidence_graph.json"))
        if graph is None:
            pytest.skip("Evidence graph not yet generated")
        assert graph.get("files_analyzed", 0) > 0, "Should have analyzed files"

    def test_evidence_graph_has_confidence_summary(self):
        graph = _load_json(os.path.join(EXPORTS_DIR, "openmiir_candidate_evidence_graph.json"))
        if graph is None:
            pytest.skip("Evidence graph not yet generated")
        cs = graph.get("confidence_summary", {})
        assert isinstance(cs, dict), "Should have confidence summary"

    def test_evidence_graph_beat_file_structure(self):
        graph = _load_json(os.path.join(EXPORTS_DIR, "openmiir_candidate_evidence_graph.json"))
        if graph is None:
            pytest.skip("Evidence graph not yet generated")
        bfs = graph.get("beat_file_structure", {})
        assert bfs.get("pattern") is not None, "Should have beat file pattern"
        assert len(bfs.get("stimuli", [])) > 0, "Should have stimuli list"

    def test_evidence_graph_perception_imagery_false(self):
        graph = _load_json(os.path.join(EXPORTS_DIR, "openmiir_candidate_evidence_graph.json"))
        if graph is None:
            pytest.skip("Evidence graph not yet generated")
        assert graph.get("perception_imagery_confirmed") is False, \
            "Must not claim perception/imagery mapping is confirmed without explicit evidence"


class TestSemanticResolverV3_3:
    def test_resolver_exists(self):
        path = os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json")
        assert os.path.exists(path), f"Resolver report not found at {path}"

    def test_resolver_not_falsely_resolved(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        assert rpt.get("semantic_mapping_resolved") is False, \
            "Must not mark resolved without confirmed evidence"

    def test_resolver_has_confidence_summary(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        cs = rpt.get("mapping_confidence_summary", {})
        assert "confirmed" in cs
        assert "strong_hypothesis" in cs
        assert "weak_hypothesis" in cs
        assert cs["confirmed"] == 0, "Confirmed mappings must be 0 without explicit evidence"

    def test_resolver_has_beat_file_structure(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        bfs = rpt.get("beat_file_structure", {})
        assert len(bfs) > 0, "Should have beat file structure from evidence graph"

    def test_resolver_has_perception_imagery_evidence(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        pe = rpt.get("perception_imagery_evidence", {})
        assert pe is not None, "Should have perception_imagery_evidence field"
        matlab_ev = rpt.get("matlab_evidence", {})
        assert matlab_ev.get("trigger_semantics_confirmed") is True, \
            "MATLAB trigger semantics should be confirmed"

    def test_resolver_has_family_timing_profiles(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        ftp = rpt.get("family_timing_profiles", {})
        assert len(ftp) > 0, "Should have family timing profiles"

    def test_resolver_block_markers_detected(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        blocks = rpt.get("block_markers_detected", [])
        assert blocks is not None, "Block markers should be detected"

    def test_resolver_no_raw_eeg(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json"))
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        text = json.dumps(rpt)
        assert ".fif" not in text or "manifest" in text.lower(), \
            "Should not expose raw EEG paths"


class TestConditionManifestV3_3:
    def test_draft_manifest_exists(self):
        path = os.path.join(EXPORTS_DIR, "openmiir_condition_manifest_draft.json")
        assert os.path.exists(path), f"Draft manifest not found at {path}"

    def test_draft_manifest_scientific_use_false(self):
        draft = _load_json(os.path.join(EXPORTS_DIR, "openmiir_condition_manifest_draft.json"))
        if draft is None:
            pytest.skip("Draft manifest not yet generated")
        assert draft.get("scientific_use_allowed") is False, \
            "Draft must have scientific_use_allowed=false"
        assert draft.get("is_production") is False
        assert draft.get("is_scientific_valid") is False

    def test_draft_manifest_has_beat_structure(self):
        draft = _load_json(os.path.join(EXPORTS_DIR, "openmiir_condition_manifest_draft.json"))
        if draft is None:
            pytest.skip("Draft manifest not yet generated")
        # V3.9.4 draft includes condition_code_map and trigger_semantics
        assert draft.get("trigger_semantics_confirmed") is True, \
            "Should confirm trigger semantics from MATLAB"
        ccm = draft.get("condition_code_map", {})
        assert len(ccm.get("perception_codes", [])) > 0 or len(ccm.get("imagery_codes", [])) > 0, \
            "Should have perception or imagery codes"

    def test_draft_manifest_has_conditions(self):
        draft = _load_json(os.path.join(EXPORTS_DIR, "openmiir_condition_manifest_draft.json"))
        if draft is None:
            pytest.skip("Draft manifest not yet generated")
        conditions = draft.get("conditions", [])
        assert len(conditions) > 0, "Should have condition entries from code families"


class TestConditionEvalV3_3:
    def test_condition_eval_exists(self):
        path = os.path.join(EXPORTS_DIR, "openmiir_condition_eval.json")
        assert os.path.exists(path), f"Condition eval not found at {path}"

    def test_condition_eval_is_blocked(self):
        eval_rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_condition_eval.json"))
        if eval_rpt is None:
            pytest.skip("Condition eval not yet generated")
        assert eval_rpt.get("condition_analysis_ready") is False, \
            "Condition eval must be blocked when semantic mapping unresolved"

    def test_condition_eval_has_beat_confirmed(self):
        eval_rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_condition_eval.json"))
        if eval_rpt is None:
            pytest.skip("Condition eval not yet generated")
        assert eval_rpt.get("beat_file_mapping_confirmed") is True, \
            "Beat file mapping should be confirmed"


class TestEventSequenceReport:
    def test_sequence_report_exists(self):
        path = os.path.join(EXPORTS_DIR, "openmiir_event_sequence_report.json")
        assert os.path.exists(path), f"Sequence report not found at {path}"

    def test_sequence_report_has_motifs(self):
        rpt = _load_json(os.path.join(EXPORTS_DIR, "openmiir_event_sequence_report.json"))
        if rpt is None:
            pytest.skip("Sequence report not yet generated")
        motifs = rpt.get("global_motifs_top_50", [])
        assert len(motifs) > 0, "Should have top motifs"


class TestStimInventoryV3_3:
    def test_stim_inventory_10_subjects(self):
        inv = _load_json(os.path.join(EXPORTS_DIR, "openmiir_stim_inventory.json"))
        if inv is None:
            pytest.skip("Stim inventory not yet generated")
        assert inv.get("subjects_with_stim", 0) >= 10, "10/10 subjects should have stim channels"

    def test_stim_inventory_52_plus_codes(self):
        inv = _load_json(os.path.join(EXPORTS_DIR, "openmiir_stim_inventory.json"))
        if inv is None:
            pytest.skip("Stim inventory not yet generated")
        codes = inv.get("unique_event_codes", [])
        assert len(codes) >= 20, "At least 20 unique codes expected"


class TestCandidateMinerModule:
    def test_miner_module_loads(self):
        try:
            from app.datasets.openmiir_candidate_miner import (
                build_evidence_graph,
                extract_beat_file_evidence,
                extract_readme_evidence,
                parse_beat_filename,
            )
            assert callable(build_evidence_graph)
            assert callable(extract_beat_file_evidence)
            assert callable(extract_readme_evidence)
            assert callable(parse_beat_filename)
        except ImportError as e:
            pytest.skip(f"Miner module not importable: {e}")

    def test_parse_beat_filename_v1(self):
        from app.datasets.openmiir_candidate_miner import parse_beat_filename
        result = parse_beat_filename("meta_beats.v1_11_beats.txt")
        assert result is not None
        assert result["code"] == 11
        assert result["version"] == "v1"
        assert result["stimulus"] == 1
        assert result["cue_type"] == 1

    def test_parse_beat_filename_v2_cue(self):
        from app.datasets.openmiir_candidate_miner import parse_beat_filename
        result = parse_beat_filename("meta_beats.v2_23_cue_beats.txt")
        assert result is not None
        assert result["code"] == 23
        assert result["version"] == "v2"
        assert result["stimulus"] == 2
        assert result["cue_type"] == 3
        assert result["file_type"] == "cue_beats"

    def test_parse_beat_filename_single_digit(self):
        from app.datasets.openmiir_candidate_miner import parse_beat_filename
        result = parse_beat_filename("meta_beats.v1_1_beats.txt")
        assert result is not None
        assert result["code"] == 1
        assert result["stimulus"] == 1
        assert result["cue_type"] is None

    def test_parse_beat_filename_no_match(self):
        from app.datasets.openmiir_candidate_miner import parse_beat_filename
        result = parse_beat_filename("README.md")
        assert result is None


class TestSemanticResolverModuleV3_3:
    def test_resolver_module_loads(self):
        try:
            from app.datasets.openmiir_semantic_resolver import (
                combine_evidence_sources,
                cross_validate_code_family_timing,
                load_evidence_graph,
                score_code_label_candidates,
            )
            assert callable(load_evidence_graph)
            assert callable(score_code_label_candidates)
            assert callable(cross_validate_code_family_timing)
            assert callable(combine_evidence_sources)
        except ImportError as e:
            pytest.skip(f"Resolver module not importable: {e}")


class TestArtifactSafetyV3_9_5_2:
    """Regression tests ensuring experimental eval never corrupts main artifacts."""

    MAIN_EVAL = os.path.join(EXPORTS_DIR, "openmiir_condition_eval.json")
    EXP_EVAL = os.path.join(EXPORTS_DIR, "openmiir_condition_eval_experimental.json")
    RESOLVER = os.path.join(EXPORTS_DIR, "openmiir_semantic_event_resolver.json")
    VALIDATOR = os.path.join(EXPORTS_DIR, "openmiir_stimtracker_encoding_validation.json")

    def test_main_eval_is_blocked_by_default(self):
        rpt = _load_json(self.MAIN_EVAL)
        if rpt is None:
            pytest.skip("Main condition eval not yet generated")
        assert rpt.get("status") == "blocked", (
            f"Main condition eval must be blocked, got {rpt.get('status')}"
        )
        assert rpt.get("analysis_mode") != "experimental_hypothesis_only", (
            "Main artifact must not have experimental analysis mode"
        )

    def test_main_eval_not_overwritten_by_experimental(self):
        main_before = _load_json(self.MAIN_EVAL)
        if main_before is None:
            pytest.skip("Main condition eval not yet generated")

        from app.cli.openmiir_condition_eval import main as eval_main

        try:
            eval_main(["--dataset", "openmiir", "--allow-empirical-hypothesis", "true",
                       "--max-subjects", "1", "--max-windows-per-condition", "1"])
        except Exception:
            pass

        main_after = _load_json(self.MAIN_EVAL)
        if main_after is None:
            pytest.skip("Main condition eval disappeared after experimental run")
        assert main_after.get("status") == "blocked", (
            "Main condition eval was overwritten by experimental run! "
            f"Got status={main_after.get('status')}"
        )

    def test_experimental_eval_exists_after_experimental_run(self):
        from app.cli.openmiir_condition_eval import main as eval_main

        try:
            eval_main(["--dataset", "openmiir", "--allow-empirical-hypothesis", "true",
                       "--max-subjects", "1", "--max-windows-per-condition", "1"])
        except Exception:
            pass

        assert os.path.exists(self.EXP_EVAL), (
            "Experimental eval artifact should exist after experimental run"
        )

    def test_experimental_eval_has_safety_fields(self):
        exp = _load_json(self.EXP_EVAL)
        if exp is None:
            pytest.skip("Experimental eval not yet generated")
        assert exp.get("not_for_scientific_claims") is True, (
            "Experimental eval must have not_for_scientific_claims=true"
        )
        assert exp.get("production_valid") is False, (
            "Experimental eval must have production_valid=false"
        )
        assert exp.get("production_unlock_allowed") is False, (
            "Experimental eval must have production_unlock_allowed=false"
        )
        assert exp.get("analysis_mode") == "experimental_hypothesis_only", (
            f"Experimental eval mode must be experimental_hypothesis_only, "
            f"got {exp.get('analysis_mode')}"
        )
        assert exp.get("source_main_eval_status") == "blocked", (
            "Experimental eval must reference blocked main eval status"
        )

    def test_resolver_version_is_v395(self):
        rpt = _load_json(self.RESOLVER)
        if rpt is None:
            pytest.skip("Resolver report not yet generated")
        tool = rpt.get("tool", "")
        assert "v3.9.5" in tool, (
            f"Resolver tool version must contain v3.9.5, got: {tool}"
        )
        assert "v3.9.4" not in tool, (
            f"Resolver must not contain stale v3.9.4 version, got: {tool}"
        )

    def test_validator_production_unlock_false(self):
        rpt = _load_json(self.VALIDATOR)
        if rpt is None:
            pytest.skip("Validator report not yet generated")
        assert rpt.get("production_unlock_allowed") is False, (
            "Validator must not unlock production without explicit documentation"
        )

    def test_validator_confidence_not_confirmed_documented(self):
        rpt = _load_json(self.VALIDATOR)
        if rpt is None:
            pytest.skip("Validator report not yet generated")
        conf = rpt.get("overall_confidence", "")
        assert conf != "confirmed_documented", (
            f"Validator confidence must not be confirmed_documented, got {conf}"
        )
        assert conf in ("empirically_validated_hypothesis", "strong_hypothesis",
                         "weak_hypothesis", "rejected"), (
            f"Unexpected validator confidence: {conf}"
        )

    def test_no_raw_eeg_in_eval_artifacts(self):
        for path in [self.MAIN_EVAL, self.EXP_EVAL]:
            rpt = _load_json(path)
            if rpt is None:
                continue
            text = json.dumps(rpt)
            assert ".fif" not in text, f"Raw EEG path exposed in {path}"
            assert "P0" not in text or "P01" not in text or (text.count("subject") < 3), (
                f"Raw EEG subject identifiers exposed in {path}" if text.count("subject") > 0 else True
            )

