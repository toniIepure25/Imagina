"""Tests for objective task runtime integration and leakage prevention."""

from app.research.objective_runtime import (
    TASK_TYPES,
    LeakageGuard,
    compute_objective_manifest_hash,
    manifest_objective_fields,
    serialize_trial_record,
)


class TestManifestIntegration:
    def test_manifest_fields_complete(self):
        fields = manifest_objective_fields(
            calibration_hash="abc123",
            trial_schedule_hash="def456",
        )
        assert fields["objective_battery_version"] is not None
        assert fields["endpoint_registry_version"] is not None
        assert fields["endpoint_registry_hash"] is not None
        assert fields["scoring_version"] is not None
        assert fields["calibration_hash"] == "abc123"

    def test_manifest_hash_deterministic(self):
        fields = manifest_objective_fields(calibration_hash="abc")
        h1 = compute_objective_manifest_hash(fields)
        h2 = compute_objective_manifest_hash(fields)
        assert h1 == h2

    def test_manifest_hash_changes_on_version(self):
        f1 = manifest_objective_fields(calibration_hash="abc")
        f2 = manifest_objective_fields(calibration_hash="def")
        assert compute_objective_manifest_hash(f1) != compute_objective_manifest_hash(f2)


class TestTrialSerialization:
    def test_serialize_complete_record(self):
        record = serialize_trial_record(
            trial_id="t001",
            task_family="imagery_reconstruction",
            stimulus_spec={"orientation_deg": 45},
            target_features={"orientation_deg": 45},
            transform_spec=None,
            response_features={"orientation_deg": 48},
            component_errors={"orientation": 0.033},
            composite_score=0.033,
            response_latency_ms=2100,
            confidence=5.0,
            vividness=6.0,
            effort=3.0,
            invalidity_flags=[],
        )
        assert record["trial_id"] == "t001"
        assert record["scoring_version"] is not None
        assert record["composite_endpoint_score"] == 0.033


class TestLeakageGuard:
    def test_clean_context_passes(self):
        guard = LeakageGuard()
        context = {"iqi": 0.5, "pid": 0.3, "attention": 0.6}
        violations = guard.check_policy_input(context)
        assert violations == []

    def test_leaked_composite_detected(self):
        guard = LeakageGuard()
        context = {"iqi": 0.5, "composite_endpoint_score": 0.2}
        violations = guard.check_policy_input(context)
        assert "composite_endpoint_score" in violations

    def test_leaked_component_error_detected(self):
        guard = LeakageGuard()
        context = {"iqi": 0.5, "component_errors": {"orientation": 0.1}}
        violations = guard.check_policy_input(context)
        assert "component_errors" in violations

    def test_leaked_objective_prefix_detected(self):
        guard = LeakageGuard()
        context = {"iqi": 0.5, "objective_score": 0.3}
        violations = guard.check_policy_input(context)
        assert "objective_score" in violations

    def test_finalize_trial(self):
        guard = LeakageGuard()
        assert not guard.is_trial_finalized("t001")
        guard.finalize_trial("t001")
        assert guard.is_trial_finalized("t001")


class TestTaskTypes:
    def test_all_task_families_registered(self):
        assert "imagery_reconstruction" in TASK_TYPES
        assert "imagery_manipulation" in TASK_TYPES
        assert "imagery_stability" in TASK_TYPES
        assert "perceptual_control" in TASK_TYPES
        assert "self_report" in TASK_TYPES
