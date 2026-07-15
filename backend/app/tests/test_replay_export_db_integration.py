"""Real DB-built export integration tests.

Builds a complete export package via build_export_from_db() against migrated
DB evidence (objective session, manifest, seal, successful replay,
confirmatory analysis, and campaign evidence) and validates it with
validate_export_package(). A hand-constructed ExportPackage is not sufficient
evidence that the DB-backed builder itself is correct — these tests exercise
the real persistence path end to end, then probe specific corruption modes
that must make the package invalid.
"""
import hashlib
import json

import aiosqlite
import pytest

from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, generate_population
from app.research.objective_export import build_export_from_db, validate_export_package
from app.research.objective_provenance import (
    create_completion_seal,
    create_objective_manifest,
    persist_manifest_and_seal,
)
from app.research.objective_replay import replay_from_db
from app.research.objective_runtime import LeakageGuard, execute_objective_session_persistent
from app.research.response_provider import SyntheticCognitiveResponseProvider
from app.storage.migration_runner import run_migrations

TRIAL_SPECS = [
    {"trial_index": i, "task_family": "feature_reconstruction",
     "target_orientation": 45, "target_hue": 120, "target_sf": 3.0,
     "target_pos_x": 500, "target_pos_y": 400, "target_size": 50,
     "is_perceptual_control": False, "delay_s": 0.0}
    for i in range(3)
]


@pytest.fixture
def tmp_path(request):
    import pathlib
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        yield pathlib.Path(d)


async def _make_db(tmp_path):
    db_path = str(tmp_path / "test_export_db_integration.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    return db


def _normalized_schedule_hash():
    normalized_specs = []
    for s in TRIAL_SPECS:
        normalized_specs.append({
            "trial_index": s["trial_index"], "task_family": s["task_family"],
            "target_orientation": float(s["target_orientation"]),
            "target_hue": float(s["target_hue"]),
            "target_sf": float(s["target_sf"]),
            "target_pos_x": float(s["target_pos_x"]),
            "target_pos_y": float(s["target_pos_y"]),
            "target_size": float(s["target_size"]),
            "delay_s": float(s.get("delay_s", 0)),
            "is_perceptual_control": bool(s.get("is_perceptual_control", False)),
        })
    return hashlib.sha256(
        json.dumps(normalized_specs, sort_keys=True).encode()
    ).hexdigest()[:16]


async def _build_complete_study(
    db, study_id, *, period=0, condition="adaptive",
    previous_condition=None, participant_generation_index=0,
    manifest_overrides=None,
):
    """Persist one full objective session + manifest + seal + confirmatory
    analysis evidence + passing campaign evidence for study_id. Does not run
    replay — call replay_from_db(db, study_id) separately once the caller has
    applied any manifest corruption."""
    pop = generate_population(
        participant_generation_index + 1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE,
    )
    provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
    guard = LeakageGuard()

    schedule_hash = _normalized_schedule_hash()

    result = await execute_objective_session_persistent(
        db, study_id, pop[0].participant_id, condition, period,
        TRIAL_SPECS, provider, guard, 42, prev_condition=previous_condition,
    )

    s_dict = json.dumps(SCENARIO_MEDIUM_ADAPTIVE.to_dict(), sort_keys=True, separators=(",", ":"))
    s_hash = hashlib.sha256(s_dict.encode()).hexdigest()[:16]

    manifest_kwargs = dict(
        response_provider_id="synthetic_cognitive",
        response_provider_version="1.0",
        response_provider_config_hash=provider.get_config().config_hash,
        schedule_hash=schedule_hash,
        scoring_hash="test-scoring-hash",
        design_hash="test-design-hash",
        scenario_hash=s_hash,
        cognitive_agent_version="medium_adaptive",
        root_seed=42,
        previous_condition=previous_condition,
        participant_generation_index=participant_generation_index,
        scenario_id="medium_adaptive",
    )
    if manifest_overrides:
        manifest_kwargs.update(manifest_overrides)

    manifest = create_objective_manifest(**manifest_kwargs)
    seal = create_completion_seal(result, manifest)
    await persist_manifest_and_seal(db, study_id, manifest, seal)

    await db.execute(
        """INSERT INTO analysis_specifications
           (study_id, spec_type, formula, estimand_id, model_version, spec_hash)
           VALUES (?, 'confirmatory', 'y ~ condition', 'ate_adaptive_vs_yoked', '1.0', ?)""",
        (study_id, "test-analysis-spec-hash"),
    )
    spec_row = await (await db.execute(
        "SELECT id FROM analysis_specifications WHERE study_id = ?", (study_id,),
    )).fetchone()
    await db.execute(
        """INSERT INTO analysis_runs (spec_id, status, started_at, seed, mode)
           VALUES (?, 'completed', datetime('now'), 42, 'confirmatory')""",
        (spec_row["id"],),
    )
    run_row = await (await db.execute(
        "SELECT id FROM analysis_runs WHERE spec_id = ?", (spec_row["id"],),
    )).fetchone()
    await db.execute(
        """INSERT INTO analysis_results
           (run_id, estimator_type, effect_estimate, standard_error, ci_lower, ci_upper,
            p_value, converged, is_fallback, inference_valid, n_participants, n_trials, result_json)
           VALUES (?, 'primary', 0.5, 0.1, 0.3, 0.7, 0.01, 1, 0, 1, 18, 54, '{}')""",
        (run_row["id"],),
    )

    await db.execute(
        """INSERT INTO oracle_estimands
           (scenario_id, contrast_id, oracle_effect, oracle_se, n_agents,
            oracle_seed, oracle_version, endpoint_id, spec_hash)
           VALUES (?, 'adaptive_vs_yoked', 0.5, 0.05, 100, 99999, '1.0', 'primary', ?)""",
        (study_id, "test-oracle-spec-hash"),
    )

    await db.execute(
        """INSERT INTO simulation_runs
           (study_id, scenario_id, mode, n_iterations, n_participants, base_seed,
            status, started_at, completed_at)
           VALUES (?, 'medium_adaptive', 'unit', 15, 18, 42, 'completed',
                   datetime('now'), datetime('now'))""",
        (study_id,),
    )
    sim_run_row = await (await db.execute(
        "SELECT id FROM simulation_runs WHERE study_id = ?", (study_id,),
    )).fetchone()
    summary_json = json.dumps({"campaign_valid": True, "scenario_id": "medium_adaptive"})
    await db.execute(
        """INSERT INTO simulation_summaries
           (run_id, power, type_i_error, coverage, bias, rmse, convergence_rate,
            fallback_rate, valid_inference_rate, nc_fp_rate, oracle_effect, oracle_se, summary_json)
           VALUES (?, 0.9, 0.05, 0.95, 0.0, 0.1, 1.0, 0.0, 1.0, 0.05, 0.0, 0.01, ?)""",
        (sim_run_row["id"], summary_json),
    )

    await db.commit()
    return result, manifest, seal


async def _corrupt_manifest(db, study_id, mutate):
    row = await (await db.execute(
        "SELECT id, manifest_json FROM objective_manifests WHERE study_id = ? ORDER BY id DESC LIMIT 1",
        (study_id,),
    )).fetchone()
    mdata = json.loads(row["manifest_json"])
    mutate(mdata)
    await db.execute(
        "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
        (json.dumps(mdata, sort_keys=True, separators=(",", ":")), row["id"]),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_build_export_from_db_produces_valid_package(tmp_path):
    """The full DB-backed path — real session, manifest, seal, replay,
    analysis, and campaign evidence — must build a valid export package."""
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-success"
        await _build_complete_study(db, study_id)

        replay = await replay_from_db(db, study_id)
        assert replay.exact_match, [d.to_dict() for d in replay.divergences]
        assert replay.content_hash_match

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert validation.valid, validation.issues
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_absent_participant_generation_index_invalidates_export(tmp_path):
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-absent-gen-index"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.pop("participant_generation_index", None))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_wrong_participant_index_invalidates_export(tmp_path):
    """A manifest claiming a different (but validly generated) participant
    index than the one actually recorded must fail closed, never silently
    substitute the recorded participant."""
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-wrong-participant"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.__setitem__("participant_generation_index", 1))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match
        assert any(d.field == "participant_generation_index" for d in replay.divergences)

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_absent_previous_condition_key_invalidates_export(tmp_path):
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-absent-prev-condition"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.pop("previous_condition", None))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_period_gt_zero_with_null_previous_condition_invalidates_export(tmp_path):
    """previous_condition may be explicitly null at period 0 only. A period > 0
    session recording null previous_condition must fail closed."""
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-period-null-prev"
        await _build_complete_study(
            db, study_id, period=1, condition="fixed", previous_condition=None,
        )

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match
        assert any(d.field == "previous_condition" for d in replay.divergences)

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_provider_version_mismatch_invalidates_export(tmp_path):
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-provider-version"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.__setitem__("response_provider_version", "9.9.9"))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match
        assert not replay.response_provider_verified

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_provider_config_mismatch_invalidates_export(tmp_path):
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-provider-config"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.__setitem__("response_provider_config_hash", "wrong"))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match
        assert not replay.response_provider_verified

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_rng_hash_mismatch_invalidates_export(tmp_path):
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-rng-hash"
        await _build_complete_study(db, study_id)
        await _corrupt_manifest(db, study_id, lambda m: m.__setitem__("rng_version_hash", "wrong-hash"))

        replay = await replay_from_db(db, study_id)
        assert not replay.exact_match

        package = await build_export_from_db(db, study_id)
        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_missing_persisted_content_hash_match_invalidates_export(tmp_path):
    """A replay run whose content_hash_match column was never persisted
    (defaults to 0) must not be treated as a successful replay, even if
    exact_match is 1."""
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-missing-persisted-flag"
        await _build_complete_study(db, study_id)
        replay = await replay_from_db(db, study_id)
        assert replay.exact_match

        await db.execute(
            "UPDATE objective_replay_runs SET content_hash_match = 0 WHERE study_id = ?",
            (study_id,),
        )
        await db.commit()

        package = await build_export_from_db(db, study_id)
        assert package.replay_results[0]["exact_match"] is True
        assert package.replay_results[0]["content_hash_match"] is False

        validation = validate_export_package(package)
        assert not validation.valid
        assert any("missing flags" in i for i in validation.issues)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_exact_match_with_content_hash_match_false_invalidates_export(tmp_path):
    """The export builder must source content_hash_match from the persisted
    column, not from trusting exact_match — an inconsistent persisted row
    (exact_match=1, content_hash_match=0) must still fail validation."""
    db = await _make_db(tmp_path)
    try:
        study_id = "export-db-inconsistent-flag"
        await _build_complete_study(db, study_id)
        replay = await replay_from_db(db, study_id)
        assert replay.exact_match
        assert replay.content_hash_match

        # Simulate a persisted row where content_hash_match diverged from
        # exact_match (e.g. written by an older code path). The builder must
        # not paper over this by inferring content_hash_match from exact_match.
        await db.execute(
            "UPDATE objective_replay_runs SET content_hash_match = 0"
            " WHERE study_id = ? AND exact_match = 1",
            (study_id,),
        )
        await db.commit()

        package = await build_export_from_db(db, study_id)
        replay_entry = package.replay_results[0]
        assert replay_entry["exact_match"] is True
        assert replay_entry["content_hash_match"] is False

        validation = validate_export_package(package)
        assert not validation.valid
    finally:
        await db.close()
