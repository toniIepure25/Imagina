"""Shared pytest configuration and automatic test classification.

Markers are applied based on file-level classification. See pyproject.toml
for marker definitions and AGENTS.md for classification criteria.

To run only the merge-gate (hermetic) suite:
    pytest -m "core or research" --timeout=300

To run artifact-dependent / legacy tests (requires generated artifacts):
    pytest -m "artifact_dependent or legacy" --timeout=600

To run external-dataset tests (requires OpenMIIR download):
    pytest -m "external_dataset" --timeout=600

To run hardware-dependent tests (requires pylsl):
    pytest -m "hardware" --timeout=300
"""

import pytest

_FILE_MARKERS: dict[str, list[str]] = {
    "test_api_smoke": ["core"],
    "test_calibration_service": ["core"],
    "test_curriculum_manager": ["core"],
    "test_dataset_eval_exports": ["core"],
    "test_dataset_fixture": ["core", "science_deps"],
    "test_dataset_import": ["core", "science_deps"],
    "test_dataset_quality_cli": ["core"],
    "test_eeg_dsp": ["core", "science_deps"],
    "test_evaluation_harness": ["core"],
    "test_feedback_policy": ["core"],
    "test_pid_iqi_engine": ["core"],
    "test_profile_experiment_exports": ["core", "integration"],
    "test_real_data_preflight": ["core"],
    "test_replay_determinism": ["core"],
    "test_report_service": ["core", "integration"],
    "test_safety_monitor": ["core"],
    "test_session_service": ["core", "integration"],
    "test_signal_providers": ["core"],
    "test_dataset_acquire_real": ["core"],

    "test_biosignal_acquisition": ["research"],
    "test_experiment_engine": ["research"],
    "test_multimodal_evaluation": ["research"],
    "test_research_governance": ["research"],
    "test_statistical_framework": ["research"],
    "test_migration_runner": ["research", "integration"],
    "test_governance_gates": ["research", "integration"],
    "test_sequence_allocator": ["research", "integration"],
    "test_api_blinding": ["research", "integration"],
    "test_state_machines": ["research", "integration"],
    "test_runtime": ["research", "integration"],
    "test_feedback_policies": ["research"],
    "test_yoked_library": ["research", "integration"],
    "test_synthetic_orchestrator": ["research", "integration"],
    "test_replay_validator": ["research", "integration"],
    "test_regression_gate_a": ["research", "integration"],
    "test_run_service": ["research", "integration"],
    "test_outbox": ["research", "integration"],
    "test_manifest": ["research", "integration"],
    "test_export_service": ["research", "integration"],
    "test_unified_db_integration": ["research", "integration"],
    "test_abort": ["research", "integration"],
    "test_objective_endpoints": ["research", "psychophysics"],
    "test_psychophysics": ["research", "psychophysics"],
    "test_calibration": ["research", "psychophysics"],
    "test_cognitive_agent": ["research", "simulation"],
    "test_estimands": ["research", "statistical"],
    "test_statistics": ["research", "statistical", "science_deps"],
    "test_design_simulation": ["research", "simulation", "science_deps"],
    "test_measurement_validity": ["research", "psychophysics"],
    "test_objective_runtime": ["research", "psychophysics"],
    "test_falsification": ["research", "simulation", "science_deps"],
    "test_rng_registry": ["research", "core"],
    "test_causal_oracle": ["research", "simulation", "science_deps"],
    "test_scenario_contracts": ["research", "simulation", "science_deps"],
    "test_crossover_design": ["research", "simulation"],
    "test_sample_size": ["research", "simulation", "science_deps"],
    "test_objective_runtime_integration": ["research", "simulation"],
    "test_objective_provenance": ["research", "simulation"],
    "test_objective_replay": ["research", "simulation"],
    "test_objective_export": ["research", "simulation"],
    "test_e2e_scientific_study": ["research", "simulation", "integration"],

    "test_openmiir_semantic_resolver": ["artifact_dependent"],

    "test_dataset_api_integration": ["external_dataset"],

    "test_lsl_provider": ["hardware"],
    "test_lsl_smoke_cli": ["hardware"],

    "test_imagina_personalization": ["legacy"],
    "test_v31_scientific": ["legacy", "artifact_dependent"],
    "test_v32_events": ["legacy", "artifact_dependent"],
    "test_v33_ml": ["legacy", "artifact_dependent"],
    "test_v34_deep": ["legacy", "artifact_dependent"],
    "test_v35_repr": ["legacy", "artifact_dependent"],
    "test_v36_iqi": ["legacy", "artifact_dependent"],
    "test_v361_iqi_hardening": ["legacy", "artifact_dependent"],
    "test_v3_final_contracts": ["legacy", "artifact_dependent"],
    "test_v3_final_part2": ["legacy", "artifact_dependent"],
    "test_v3_final_real_data": ["legacy", "external_dataset"],
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        module_name = item.module.__name__.rsplit(".", 1)[-1] if item.module else ""
        markers = _FILE_MARKERS.get(module_name, [])
        for marker_name in markers:
            item.add_marker(getattr(pytest.mark, marker_name))
