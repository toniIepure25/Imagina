"""Research dashboard summary API — clean JSON for frontend."""

import json
import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/research-dashboard", tags=["research"])


def _exports_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports", fn)


def _meta_path(fn):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "data", "external", "openmiir", "meta", fn)


@router.get("/summary")
async def summary():
    manifest = _load_json(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external", "openmiir", "manifest.json"
    ))
    eval_rpt = _load_json(_exports_path("dataset_eval_openmiir.json"))
    iqi = _load_json(_exports_path("openmiir_iqi_v2.json"))
    meta_report = _load_json(_meta_path("metadata_discovery_report.json"))
    stim_inv = _load_json(_exports_path("openmiir_stim_inventory.json"))
    sem_resolver = _load_json(_exports_path("openmiir_semantic_event_resolver.json"))
    timing = _load_json(_exports_path("openmiir_event_timing_analysis.json"))
    evidence_graph = _load_json(_exports_path("openmiir_candidate_evidence_graph.json"))
    seq_report = _load_json(_exports_path("openmiir_event_sequence_report.json"))
    draft_manifest = _load_json(_exports_path("openmiir_condition_manifest_draft.json"))
    cond_eval = _load_json(_exports_path("openmiir_condition_eval.json"))
    cond_exp = _load_json(_exports_path("openmiir_condition_eval_experimental.json"))
    cond_analysis = _load_json(_exports_path("openmiir_condition_analysis_experimental.json"))
    epoch_features = _load_json(_exports_path("openmiir_epoch_features_experimental.json"))
    epoch_bench = _load_json(_exports_path("openmiir_epoch_condition_benchmark_experimental.json"))
    excel_meta = _load_json(_exports_path("openmiir_excel_metadata_index.json"))
    matlab_meta = _load_json(_exports_path("openmiir_matlab_metadata_index.json"))
    stim_val = _load_json(_exports_path("openmiir_stimtracker_encoding_validation.json"))

    return {
        "release_candidate": "V3.0-final-candidate",
        "system_status": {
            "real_eeg_imported": True,
            "demo_status": "FIRST_REAL_EEG_EVALUATION_COMPLETE",
            "scientific_validation_complete": False,
        },
        "dataset": {
            "name": "OpenMIIR",
            "subjects": (manifest or {}).get("file_count", 0),
            "channels": (manifest or {}).get("channel_count"),
            "sampling_rate_hz": (manifest or {}).get("sampling_rate_hz"),
            "duration_seconds": (manifest or {}).get("duration_seconds"),
        },
        "signal_quality": eval_rpt.get("signal_quality", {}) if eval_rpt else None,
        "iqi_v2": {
            "available": iqi is not None,
            "metric_version": "v2.0" if iqi else None,
            "mean": iqi.get("cohort", {}).get("iqi_mean") if iqi else None,
            "std": iqi.get("cohort", {}).get("iqi_std") if iqi else None,
            "min": iqi.get("cohort", {}).get("iqi_min") if iqi else None,
            "max": iqi.get("cohort", {}).get("iqi_max") if iqi else None,
            "component_means": iqi.get("cohort", {}).get("component_means") if iqi else None,
            "component_count": len(iqi.get("cohort", {}).get("component_means", {})) if iqi else 0,
        },
        "openmiir_event_semantics": {
            "stim_channels_found": (stim_inv or {}).get("subjects_with_stim", 0) > 0 if stim_inv else False,
            "subjects_with_stim": (stim_inv or {}).get("subjects_with_stim", 0) if stim_inv else 0,
            "events_found": (stim_inv or {}).get("events_found", False) if stim_inv else False,
            "total_events": (timing or {}).get("total_events") if timing else None,
            "unique_event_codes_count": len((stim_inv or {}).get("unique_event_codes", [])),
            "unique_event_codes": (stim_inv or {}).get("unique_event_codes", [])[:52],
            "semantic_mapping_resolved": (sem_resolver or {}).get("semantic_mapping_resolved", False)
            if sem_resolver else False,
            "mapping_confidence_summary": (sem_resolver or {}).get("mapping_confidence_summary", {})
            if sem_resolver else {},
            "evidence_files_analyzed": (evidence_graph or {}).get("files_analyzed", 0)
            if evidence_graph else 0,
            "confirmed_mappings_count": (sem_resolver or {}).get("mapping_confidence_summary", {})
            .get("confirmed", 0) if sem_resolver else 0,
            "strong_hypothesis_count": (sem_resolver or {}).get("mapping_confidence_summary", {})
            .get("strong_hypothesis", 0) if sem_resolver else 0,
            "weak_hypothesis_count": (sem_resolver or {}).get("mapping_confidence_summary", {})
            .get("weak_hypothesis", 0) if sem_resolver else 0,
            "unresolved_codes_count": len((sem_resolver or {}).get("unresolved_codes", []))
            if sem_resolver else 0,
            "candidate_label_scores": (sem_resolver or {}).get("candidate_label_scores", {})
            if sem_resolver else {},
            "event_code_families": (sem_resolver or {}).get("event_code_families", {})
            if sem_resolver else {},
            "beat_file_structure": (sem_resolver or {}).get("beat_file_structure", {})
            if sem_resolver else {},
            "condition_manifest_exists": os.path.exists(_meta_path("condition_manifest.json")),
            "draft_manifest_exists": draft_manifest is not None,
            "blocked_reason": (sem_resolver or {}).get("blocked_reason", "unknown") if sem_resolver
            else (meta_report or {}).get("blocked_reason", "unknown"),
            "perception_imagery_evidence": (sem_resolver or {}).get("perception_imagery_evidence", {})
            if sem_resolver else {},
            "event_sequence_available": seq_report is not None,
        },
        "hard_metadata_recovery": {
            "xlsx_files_found": (excel_meta or {}).get("files_parsed", 0)
            if excel_meta else 0,
            "xlsx_files_parsed": (excel_meta or {}).get("files_parsed", 0)
            if excel_meta else 0,
            "matlab_files_found": (matlab_meta or {}).get("files_found", 0)
            if matlab_meta else 0,
            "matlab_files_parsed": (matlab_meta or {}).get("files_parsed", 0)
            if matlab_meta else 0,
            "excel_evidence_level": (excel_meta or {}).get("evidence_level", "none")
            if excel_meta else "none",
            "matlab_evidence_level": (matlab_meta or {}).get("evidence_level", "none")
            if matlab_meta else "none",
            "explicit_code_mappings_found": (
                len((matlab_meta or {}).get("explicit_code_mappings", [])) > 0
                if matlab_meta else False
            ),
            "trigger_semantics_confirmed": (
                sem_resolver or {}).get("matlab_evidence", {}).get("trigger_semantics_confirmed", False)
            if sem_resolver else False,
            "perception_imagery_mapping_confirmed": (
                sem_resolver or {}).get("perception_imagery_mapping_confirmed", False)
            if sem_resolver else False,
            "stimulus_mapping_confirmed": (
                sem_resolver or {}).get("stimulus_mapping_confirmed", False)
            if sem_resolver else False,
            "production_manifest_exists": os.path.exists(_meta_path("condition_manifest.json")),
            "draft_manifest_exists": draft_manifest is not None,
        },
        "stimtracker_validation": {
            "available": stim_val is not None,
            "overall_confidence": (stim_val or {}).get("overall_confidence", "not_available"),
            "overall_score": (stim_val or {}).get("overall_score", None),
            "empirical_mapping_validated": (
                (stim_val or {}).get("overall_confidence") == "empirically_validated_hypothesis"
            ),
            "production_unlock_allowed": (stim_val or {}).get("production_unlock_allowed", False),
            "perception_codes": (stim_val or {}).get("empirical_condition_code_map", {})
            .get("perception", []) if stim_val else [],
            "imagery_codes": (stim_val or {}).get("empirical_condition_code_map", {})
            .get("cued_imagery", []) if stim_val else [],
            "baseline_codes": (stim_val or {}).get("empirical_condition_code_map", {})
            .get("noise", []) if stim_val else [],
        },
        "experimental_condition_analysis": {
            "available": cond_analysis is not None,
            "status": (cond_analysis or {}).get("analysis_mode", "not_available"),
            "analysis_mode": "experimental_hypothesis_only" if cond_analysis else "not_available",
            "not_for_scientific_claims": True if cond_analysis else None,
            "production_valid": False if cond_analysis else None,
            "n_subjects": (cond_analysis or {}).get("dataset", {}).get("n_subjects_analyzed", 0)
            if cond_analysis else 0,
            "n_conditions": len((cond_analysis or {}).get("conditions", {}))
            if cond_analysis else 0,
            "fdr_significant_hits": (cond_analysis or {}).get("statistical_summary", {}).get(
                "fdr_significant_hits", 0) if cond_analysis else 0,
            "top_effects": (cond_analysis or {}).get("statistical_summary", {}).get(
                "top_effects", [])[:5] if cond_analysis else [],
            "figures_available": len((cond_analysis or {}).get("figures", []))
            if cond_analysis else 0,
            "limitations_short": [
                "Experimental hypothesis only — not validated",
                "N=10, single session",
            ],
        },
        "epoch_condition_benchmark": {
            "available": epoch_bench is not None,
            "n_subjects": (epoch_bench or epoch_features or {}).get("n_subjects", 0),
            "n_epochs_total": (epoch_bench or epoch_features or {}).get("n_epochs", 0),
            "n_features": (epoch_bench or epoch_features or {}).get("n_features", 0),
            "tasks_completed": (epoch_bench or {}).get("tasks_completed", []),
            "best_model_per_task": (epoch_bench or {}).get("best_model_per_task", {}),
            "leakage_detected": (epoch_bench or {}).get("leakage_detected", False),
            "group_cv_used": (epoch_bench or {}).get("group_cv_used", True),
            "ablation_available": len((epoch_bench or {}).get("ablation_results", {})) > 0,
            "feature_importance_available": len((epoch_bench or {}).get("feature_importance", {})) > 0,
            "figures_available": len((epoch_bench or {}).get("figures", [])),
            "not_for_scientific_claims": (epoch_bench or {}).get("not_for_scientific_claims", True),
            "production_valid": (epoch_bench or {}).get("production_valid", False),
            "production_unlock_allowed": (epoch_bench or {}).get("production_unlock_allowed", False),
        },
        "analysis_artifacts": {
            "scientific_eeg_analysis": os.path.exists(_exports_path("openmiir_scientific_analysis.json")),
            "cross_subject_eval": os.path.exists(_exports_path("cross_subject_eval.json")),
            "event_analysis": os.path.exists(_exports_path("openmiir_events_inventory.json")),
            "ml_baseline": os.path.exists(_exports_path("openmiir_ml_baseline_benchmark.json")),
            "deep_eeg_benchmark": os.path.exists(_exports_path("openmiir_deep_eeg_benchmark.json")),
            "representation_analysis": os.path.exists(_exports_path("openmiir_representation_analysis.json")),
            "iqi_v2": iqi is not None,
            "semantic_event_resolver": os.path.exists(_exports_path(
                "openmiir_semantic_event_resolver.json")),
            "event_timing": os.path.exists(_exports_path("openmiir_event_timing_analysis.json")),
            "candidate_evidence_graph": os.path.exists(_exports_path(
                "openmiir_candidate_evidence_graph.json")),
            "event_sequence_report": os.path.exists(_exports_path(
                "openmiir_event_sequence_report.json")),
            "condition_eval": os.path.exists(_exports_path("openmiir_condition_eval.json")),
        },
        "condition_analysis": {
            "status": "blocked" if (
                not (sem_resolver or {}).get("semantic_mapping_resolved", False) if sem_resolver else True
            ) else "ready",
            "metadata_available": (meta_report or {}).get("metadata_found", False),
            "trigger_semantics_confirmed": (
                sem_resolver or {}).get("matlab_evidence", {}).get("trigger_semantics_confirmed", False)
            if sem_resolver else False,
            "empirical_validation_available": (
                sem_resolver or {}).get("empirical_mapping_validated", False)
            if sem_resolver else False,
            "production_unlock_allowed": (
                sem_resolver or {}).get("production_unlock_allowed", False)
            if sem_resolver else False,
            "events_found": (stim_inv or {}).get("events_found", False) if stim_inv else False,
            "semantic_mapping_resolved": (sem_resolver or {}).get("semantic_mapping_resolved", False)
            if sem_resolver else False,
            "beat_file_mapping_confirmed": True,
            "draft_manifest_exists": draft_manifest is not None,
            "condition_manifest_exists": os.path.exists(_meta_path("condition_manifest.json")),
            "perception_codes": (sem_resolver or {}).get("condition_code_map", {}).get(
                "perception_codes", []) if sem_resolver else [],
            "imagery_codes": (sem_resolver or {}).get("condition_code_map", {}).get(
                "imagery_codes", []) if sem_resolver else [],
            "blocked_reason": (cond_eval or {}).get("blocked_reason",
                "events_found_but_semantic_mapping_unresolved") if cond_eval
                else "events_found_but_semantic_mapping_unresolved",
            "perception_imagery_map_confirmed": False,
        },
        "condition_eval": {
            "main_status": (cond_eval or {}).get("status", "unknown"),
            "main_artifact": "openmiir_condition_eval.json",
            "main_analysis_mode": (cond_eval or {}).get("analysis_mode", "unknown"),
            "experimental_available": cond_exp is not None,
            "experimental_status": (cond_exp or {}).get("status", "not_available"),
            "experimental_artifact": "openmiir_condition_eval_experimental.json",
            "experimental_not_for_scientific_claims": (
                cond_exp or {}).get("not_for_scientific_claims", True) if cond_exp else None,
            "production_valid": (cond_eval or {}).get("production_valid", False),
        },
        "limitations": [
            "Experimental EEG proxy metrics — not clinical",
            "No condition labels — perception/imagery analysis pending",
            "Single dataset, single session per subject",
            "Does not decode thoughts, dreams, or mental images",
            "Scientific validation requires controlled experiments",
        ],
        "privacy_note": "No raw EEG samples are exposed by this endpoint.",
        "scientific_disclaimer": "Experimental proxy features only. Not clinical EEG analysis.",
    }


def _load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/artifacts")
async def artifacts():
    base = _exports_path("")
    meta_base = os.path.join(os.path.dirname(base), "external", "openmiir", "meta")

    def _a(name, path, atype="json"):
        full = os.path.join(base, path)
        if not os.path.exists(full) and "meta" in path:
            full = os.path.join(meta_base, path)
        return {"name": name, "path": path, "type": atype,
                "exists": os.path.exists(full),
                "raw_eeg_exposed": False}

    registry = [
        _a("scientific_eeg_analysis", "openmiir_scientific_analysis.json"),
        _a("cross_subject_eval", "cross_subject_eval.json"),
        _a("event_inventory", "openmiir_events_inventory.json"),
        _a("ml_baseline", "openmiir_ml_baseline_benchmark.json"),
        _a("deep_eeg_benchmark", "openmiir_deep_eeg_benchmark.json"),
        _a("representation_analysis", "openmiir_representation_analysis.json"),
        _a("iqi_v2", "openmiir_iqi_v2.json"),
        _a("metadata_import", "metadata_import_report.json"),
        _a("product_demo", "product_demo_report.json"),
        _a("release_artifacts", "release_artifacts.json"),
        _a("openmiir_candidate_evidence_graph", "openmiir_candidate_evidence_graph.json"),
        _a("openmiir_event_sequence_report", "openmiir_event_sequence_report.json"),
        _a("openmiir_event_sequence_motifs", "openmiir_event_sequence_motifs.csv", "csv"),
        _a("openmiir_semantic_event_resolver", "openmiir_semantic_event_resolver.json"),
        _a("openmiir_event_timing_analysis", "openmiir_event_timing_analysis.json"),
        _a("openmiir_event_transition_matrix", "openmiir_event_timing_transition_matrix.csv", "csv"),
        _a("openmiir_condition_manifest_draft", "openmiir_condition_manifest_draft.json"),
        _a("openmiir_condition_eval", "openmiir_condition_eval.json"),
        _a("openmiir_excel_metadata_index", "openmiir_excel_metadata_index.json"),
        _a("openmiir_matlab_metadata_index", "openmiir_matlab_metadata_index.json"),
        _a("stimtracker_encoding_validation", "openmiir_stimtracker_encoding_validation.json"),
        _a("experimental_condition_analysis", "openmiir_condition_analysis_experimental.json"),
        _a("epoch_features", "openmiir_epoch_features_experimental.json"),
        _a("epoch_benchmark", "openmiir_epoch_condition_benchmark_experimental.json"),
        _a("paper_ready_report", "openmiir_paper_ready_experimental_report.json"),
    ]
    return {
        "total": len(registry), "available": sum(1 for r in registry if r["exists"]),
        "no_raw_eeg_exposed": True, "artifacts": registry,
    }
