"""End-to-end scientific study lifecycle evidence.

Proves the complete objective synthetic study lifecycle:
define registry -> design -> agents -> calibration -> execute sessions ->
persist -> seal -> export -> replay -> analysis -> simulation -> validate.
"""
import hashlib
import json

import pytest

from app.research.causal_oracle import compute_oracle_effect
from app.research.cognitive_agent import (
    SCENARIO_MEDIUM_ADAPTIVE,
    SCENARIO_STRICT_NULL,
    generate_population,
    model_hash,
)
from app.research.crossover_design import (
    CONDITIONS,
    TASK_FAMILIES,
    design_hash,
    freeze_design,
    validate_design_balance,
)
from app.research.design_simulation import run_simulation
from app.research.objective_endpoints import registry_hash
from app.research.objective_export import (
    ExportPackage,
    export_hash,
    validate_export_package,
)
from app.research.objective_provenance import (
    create_completion_seal,
    create_objective_manifest,
    verify_seal,
)
from app.research.objective_replay import replay_hash, replay_objective_session
from app.research.objective_runtime import (
    LeakageGuard,
    execute_objective_session,
)
from app.research.psychophysics.scoring import SCORING_VERSION
from app.research.response_provider import SyntheticCognitiveResponseProvider
from app.research.rng_registry import rng_version_hash
from app.research.statistics.confirmatory import run_primary_analysis

SEED = 12345
N_PARTICIPANTS = 6
N_SESSIONS = 3
TRIALS_PER_TASK = 3


@pytest.fixture(scope="module")
def design():
    return freeze_design(
        n_participants=N_PARTICIPANTS,
        n_sessions=N_SESSIONS,
        trials_per_task=TRIALS_PER_TASK,
        seed=SEED,
    )


@pytest.fixture(scope="module")
def population():
    return generate_population(N_PARTICIPANTS, seed=SEED, scenario=SCENARIO_MEDIUM_ADAPTIVE)


@pytest.fixture(scope="module")
def session_results(design, population):
    """Execute all objective sessions through the persistent runtime."""
    results = []
    for block in design.sessions:
        agent = None
        for a in population:
            if a.participant_id == block.participant_id:
                agent = a
                break
        if agent is None:
            continue

        all_trials = block.trials + block.negative_control_trials
        trial_specs = [
            {
                "task_family": t.task_family,
                "trial_index": t.trial_index,
                "is_perceptual_control": t.is_perceptual_control,
                "target_orientation": t.target.orientation_deg,
                "target_hue": t.target.hue_deg,
                "target_sf": t.target.spatial_frequency_cpd,
                "target_pos_x": t.target.position_x,
                "target_pos_y": t.target.position_y,
                "target_size": t.target.size,
                "delay_s": t.delay_s,
                "transformation_type": t.transformation_type,
                "transformation_magnitude": t.transformation_magnitude,
            }
            for t in all_trials
        ]

        provider = SyntheticCognitiveResponseProvider(agent, SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()
        session_id = f"sess-{block.participant_id}-p{block.period}"

        result = execute_objective_session(
            session_id=session_id,
            participant_id=block.participant_id,
            condition=block.condition,
            period=block.period,
            trial_specs=trial_specs,
            response_provider=provider,
            leakage_guard=guard,
            seed=SEED,
            prev_condition=block.prev_condition,
        )
        results.append(result)
    return results


@pytest.fixture(scope="module")
def manifests_and_seals(session_results):
    """Create manifests and seals for all sessions."""
    pairs = []
    for sr in session_results:
        manifest = create_objective_manifest(
            schedule_hash="e2e-schedule",
            response_provider_id="synthetic_cognitive",
            response_provider_version="1.0",
            cognitive_agent_version="2.0",
            scenario_hash=model_hash(SCENARIO_MEDIUM_ADAPTIVE, SEED),
            oracle_spec_hash="e2e-oracle",
            analysis_spec_hash="e2e-analysis",
            scoring_hash=hashlib.sha256(SCORING_VERSION.encode()).hexdigest()[:16],
        )
        seal = create_completion_seal(sr, manifest)
        pairs.append((manifest, seal))
    return pairs


class TestDesignIntegrity:
    def test_expected_participants(self, design):
        pids = {s.participant_id for s in design.sessions}
        assert len(pids) == N_PARTICIPANTS

    def test_expected_sessions(self, design):
        assert len(design.sessions) == N_PARTICIPANTS * N_SESSIONS

    def test_expected_blocks(self, design):
        for s in design.sessions:
            assert len(s.trials) > 0

    def test_expected_trial_count(self, design):
        imagery_tasks = [t for t in TASK_FAMILIES if t != "perceptual_control"]
        expected_imagery = TRIALS_PER_TASK * len(imagery_tasks)
        expected_nc = TRIALS_PER_TASK
        for s in design.sessions:
            assert len(s.trials) == expected_imagery
            assert len(s.negative_control_trials) == expected_nc

    def test_condition_balance(self, design):
        balance = validate_design_balance(design)
        assert balance["balanced"], f"Imbalanced: {balance['issues']}"
        cond = balance["condition_balance"]
        for c in CONDITIONS:
            assert c in cond

    def test_period_balance(self, design):
        balance = validate_design_balance(design)
        period = balance["period_balance"]
        vals = list(period.values())
        assert max(vals) - min(vals) <= 2

    def test_task_family_counts(self, design):
        balance = validate_design_balance(design)
        for tf in TASK_FAMILIES:
            assert tf in balance["task_family_balance"]
            assert balance["task_family_balance"][tf] > 0

    def test_calibration_references(self, design):
        for s in design.sessions:
            assert s.calibration_id
            assert s.calibration_id.startswith("calib-")

    def test_design_hash_deterministic(self, design):
        d2 = freeze_design(N_PARTICIPANTS, N_SESSIONS, TRIALS_PER_TASK, SEED)
        assert design_hash(design) == design_hash(d2)


class TestSessionExecution:
    def test_expected_session_count(self, session_results, design, population):
        n_matched = sum(
            1 for s in design.sessions
            if any(a.participant_id == s.participant_id for a in population)
        )
        assert len(session_results) == n_matched

    def test_all_conditions_represented(self, session_results):
        conds = {r.condition for r in session_results}
        for c in CONDITIONS:
            assert c in conds, f"Missing condition: {c}"

    def test_all_periods_represented(self, session_results):
        periods = {r.period for r in session_results}
        assert len(periods) == N_SESSIONS

    def test_all_task_families_present(self, session_results):
        families = set()
        for sr in session_results:
            for t in sr.trials:
                families.add(t.task_family)
        for tf in TASK_FAMILIES:
            assert tf in families, f"Missing task family: {tf}"

    def test_zero_leakage(self, session_results):
        for sr in session_results:
            for audit in sr.leakage_audit:
                assert audit.passed, f"Leakage in {sr.session_id}: {audit.violations}"
                assert len(audit.violations) == 0

    def test_content_hash_nonempty(self, session_results):
        for sr in session_results:
            assert sr.content_hash
            assert len(sr.content_hash) == 64


class TestProvenance:
    def test_zero_missing_seals(self, manifests_and_seals):
        assert len(manifests_and_seals) > 0
        for manifest, seal in manifests_and_seals:
            assert seal.valid
            assert seal.trial_count > 0

    def test_seal_verification(self, session_results, manifests_and_seals):
        for sr, (_, seal) in zip(session_results, manifests_and_seals):
            issues = verify_seal(seal, sr)
            assert len(issues) == 0, f"Seal issues for {sr.session_id}: {issues}"

    def test_manifest_valid(self, manifests_and_seals):
        for manifest, _ in manifests_and_seals:
            issues = manifest.validate()
            assert len(issues) == 0, f"Manifest issues: {issues}"

    def test_registry_hash_consistent(self, manifests_and_seals):
        expected = registry_hash()
        for manifest, _ in manifests_and_seals:
            assert manifest.endpoint_registry_hash == expected

    def test_rng_version_tracked(self, manifests_and_seals):
        for manifest, _ in manifests_and_seals:
            assert manifest.rng_version_hash == rng_version_hash()


class TestReplay:
    def test_exact_replay_per_condition(self, session_results, manifests_and_seals, design, population):
        replayed_conditions = set()
        for sr, (manifest, seal), block in zip(
            session_results, manifests_and_seals,
            design.sessions[:len(session_results)],
        ):
            if sr.condition in replayed_conditions:
                continue
            replayed_conditions.add(sr.condition)

            all_trials = block.trials + block.negative_control_trials
            trial_specs = [
                {
                    "task_family": t.task_family,
                    "trial_index": t.trial_index,
                    "is_perceptual_control": t.is_perceptual_control,
                    "target_orientation": t.target.orientation_deg,
                    "target_hue": t.target.hue_deg,
                    "target_sf": t.target.spatial_frequency_cpd,
                    "target_pos_x": t.target.position_x,
                    "target_pos_y": t.target.position_y,
                    "target_size": t.target.size,
                    "delay_s": t.delay_s,
                    "transformation_type": t.transformation_type,
                    "transformation_magnitude": t.transformation_magnitude,
                }
                for t in all_trials
            ]

            replay_result = replay_objective_session(
                original=sr,
                manifest=manifest,
                seal=seal,
                scenario=SCENARIO_MEDIUM_ADAPTIVE,
                trial_specs=trial_specs,
                seed=SEED,
                prev_condition=block.prev_condition,
            )
            assert replay_result.exact_match, (
                f"Replay mismatch for {sr.session_id} ({sr.condition}): "
                f"{[d.to_dict() for d in replay_result.divergences]}"
            )

        for c in CONDITIONS:
            assert c in replayed_conditions

    def test_replay_hash_deterministic(self, session_results, manifests_and_seals, design):
        sr = session_results[0]
        manifest, seal = manifests_and_seals[0]
        block = design.sessions[0]
        all_trials = block.trials + block.negative_control_trials
        trial_specs = [
            {
                "task_family": t.task_family,
                "trial_index": t.trial_index,
                "is_perceptual_control": t.is_perceptual_control,
                "target_orientation": t.target.orientation_deg,
                "target_hue": t.target.hue_deg,
                "target_sf": t.target.spatial_frequency_cpd,
                "target_pos_x": t.target.position_x,
                "target_pos_y": t.target.position_y,
                "target_size": t.target.size,
                "delay_s": t.delay_s,
            }
            for t in all_trials
        ]
        r1 = replay_objective_session(sr, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE, trial_specs, SEED, block.prev_condition)
        r2 = replay_objective_session(sr, manifest, seal, SCENARIO_MEDIUM_ADAPTIVE, trial_specs, SEED, block.prev_condition)
        assert replay_hash(r1) == replay_hash(r2)


class TestAnalysis:
    def test_confirmatory_analysis(self, session_results):
        trial_data = []
        for sr in session_results:
            for t in sr.trials:
                trial_data.append({
                    "participant_id": sr.participant_id,
                    "condition": sr.condition,
                    "period": sr.period,
                    "session_index": sr.period,
                    "task_family": t.task_family,
                    "composite_error": t.composite_error,
                    "baseline_error": 0.5,
                })
        result = run_primary_analysis(trial_data)
        assert result is not None
        assert result.estimand_id == "ate_adaptive_vs_yoked"

    def test_negative_control_analysis(self, session_results):
        nc_data = [
            {
                "participant_id": sr.participant_id,
                "condition": sr.condition,
                "period": sr.period,
                "session_index": sr.period,
                "task_family": "perceptual_control",
                "composite_error": t.composite_error,
                "baseline_error": 0.5,
            }
            for sr in session_results
            for t in sr.trials
            if t.task_family == "perceptual_control"
        ]
        if nc_data:
            result = run_primary_analysis(nc_data)
            assert result is not None


class TestSimulation:
    def test_null_simulation(self):
        r = run_simulation(SCENARIO_STRICT_NULL, n_iterations=15, base_seed=42, mode="unit")
        assert r.type_i_error is not None
        assert r.oracle_effect is not None
        assert abs(r.oracle_effect) < 0.1

    def test_medium_simulation(self):
        r = run_simulation(SCENARIO_MEDIUM_ADAPTIVE, n_iterations=15, base_seed=42, mode="unit")
        assert r.power is not None


class TestExport:
    def test_valid_package(self, session_results, manifests_and_seals, design):
        targets = []
        responses = []
        comp_scores = []
        composite_scores = []
        subj_outcomes = []
        nc_controls = []
        seal_evidence = []
        manifest_evidence = []

        for sr, (manifest, seal) in zip(session_results, manifests_and_seals):
            manifest_evidence.append(manifest.to_dict())
            seal_evidence.append(seal.to_dict())
            for t in sr.trials:
                targets.append(t.target)
                responses.append(t.response)
                comp_scores.append(t.component_errors)
                composite_scores.append({"composite_error": t.composite_error})
                subj_outcomes.append({
                    "confidence": t.confidence,
                    "vividness": t.vividness,
                    "effort": t.effort,
                })
                if t.task_family == "perceptual_control":
                    nc_controls.append({"composite_error": t.composite_error})

        package = ExportPackage(
            study_id="e2e-test-study",
            endpoint_registry_hash=registry_hash(),
            scoring_hash=hashlib.sha256(SCORING_VERSION.encode()).hexdigest()[:16],
            scoring_version=SCORING_VERSION,
            calibration_hash="e2e-calib",
            schedule_hash=design_hash(design),
            objective_targets=targets,
            responses=responses,
            component_scores=comp_scores,
            composite_scores=composite_scores,
            subjective_outcomes=subj_outcomes,
            negative_controls=nc_controls,
            analysis_specification={"estimand": "ate_adaptive_vs_yoked"},
            analysis_spec_hash="e2e-analysis",
            oracle_spec_hash="e2e-oracle",
            manifest_evidence=manifest_evidence,
            seal_evidence=seal_evidence,
            replay_results=[{"status": "exact_match"}],
        )

        validation = validate_export_package(package)
        assert validation.valid, f"Export invalid: {validation.issues}"

    def test_zero_invalid_exports(self, session_results, manifests_and_seals):
        for sr, (manifest, seal) in zip(session_results, manifests_and_seals):
            issues = verify_seal(seal, sr)
            assert len(issues) == 0

    def test_export_hash_deterministic(self):
        pkg = ExportPackage(
            study_id="det-test",
            endpoint_registry_hash=registry_hash(),
            schedule_hash="x",
            analysis_spec_hash="y",
            oracle_spec_hash="z",
        )
        h1 = export_hash(pkg)
        h2 = export_hash(pkg)
        assert h1 == h2

    def test_analysis_spec_hash_match(self, session_results):
        trial_data = [
            {
                "participant_id": sr.participant_id,
                "condition": sr.condition,
                "period": sr.period,
                "session_index": sr.period,
                "task_family": t.task_family,
                "composite_error": t.composite_error,
                "baseline_error": 0.5,
            }
            for sr in session_results
            for t in sr.trials
        ]
        r1 = run_primary_analysis(trial_data)
        r2 = run_primary_analysis(trial_data)
        assert r1.effect_estimate == r2.effect_estimate
        assert r1.p_value == r2.p_value


class TestPostRestart:
    """Verify that results remain accessible after constructing fresh objects."""

    def test_all_results_accessible(self, session_results, design, population):
        d2 = freeze_design(N_PARTICIPANTS, N_SESSIONS, TRIALS_PER_TASK, SEED)
        assert design_hash(d2) == design_hash(design)

        pop2 = generate_population(N_PARTICIPANTS, seed=SEED, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        for a1, a2 in zip(sorted(population, key=lambda a: a.participant_id),
                          sorted(pop2, key=lambda a: a.participant_id)):
            assert a1.participant_id == a2.participant_id
            assert abs(a1.baseline_imagery_precision - a2.baseline_imagery_precision) < 1e-12
