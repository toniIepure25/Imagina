"""Tests for persistent replay: fail-closed with sealed provenance from DB."""
import json

import aiosqlite
import pytest

from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE, generate_population
from app.research.objective_provenance import (
    create_completion_seal,
    create_objective_manifest,
    persist_manifest_and_seal,
)
from app.research.objective_replay import replay_from_db
from app.research.objective_runtime import (
    LeakageGuard,
    execute_objective_session_persistent,
)
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
    db_path = str(tmp_path / "test_replay.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    return db


async def _persist_session(db, session_id="replay-test-s1"):
    import hashlib as _hl
    pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
    from app.research.response_provider import SyntheticCognitiveResponseProvider
    provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
    guard = LeakageGuard()

    normalized_specs = []
    for s in TRIAL_SPECS:
        normalized_specs.append({
            "trial_index": s["trial_index"],
            "task_family": s["task_family"],
            "target_orientation": float(s["target_orientation"]),
            "target_hue": float(s["target_hue"]),
            "target_sf": float(s["target_sf"]),
            "target_pos_x": float(s["target_pos_x"]),
            "target_pos_y": float(s["target_pos_y"]),
            "target_size": float(s["target_size"]),
            "delay_s": float(s.get("delay_s", 0)),
            "is_perceptual_control": bool(s.get("is_perceptual_control", False)),
        })
    schedule_hash = _hl.sha256(
        json.dumps(normalized_specs, sort_keys=True).encode()
    ).hexdigest()[:16]

    result = await execute_objective_session_persistent(
        db, session_id, pop[0].participant_id, "adaptive", 0,
        TRIAL_SPECS, provider, guard, 42,
    )

    s_dict = json.dumps(SCENARIO_MEDIUM_ADAPTIVE.to_dict(), sort_keys=True, separators=(",", ":"))
    s_hash = _hl.sha256(s_dict.encode()).hexdigest()[:16]
    manifest = create_objective_manifest(
        response_provider_id="synthetic_cognitive",
        response_provider_version="1.0",
        response_provider_config_hash="test_config_hash",
        schedule_hash=schedule_hash,
        scoring_hash="test_scoring",
        design_hash="test_design",
        scenario_hash=s_hash,
        cognitive_agent_version="medium_adaptive",
        root_seed=42,
        previous_condition=None,
        participant_generation_index=0,
        scenario_id="medium_adaptive",
    )
    seal = create_completion_seal(result, manifest)
    await persist_manifest_and_seal(db, session_id, manifest, seal)
    return result, manifest, seal


@pytest.mark.asyncio
async def test_exact_persisted_replay(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db)
        result = await replay_from_db(db, "replay-test-s1")
        assert result.manifest_verified
        assert result.seal_verified
        assert result.schedule_verified
        assert result.scoring_verified
        assert result.response_provider_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_missing_manifest_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        from app.research.response_provider import SyntheticCognitiveResponseProvider
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()

        result = await execute_objective_session_persistent(
            db, "no-manifest", pop[0].participant_id, "adaptive", 0,
            TRIAL_SPECS, provider, guard, 42,
        )
        seal_data = create_completion_seal(result, create_objective_manifest(response_provider_id="synth"))
        await db.execute(
            """INSERT INTO objective_completion_seals
               (study_id, session_id, seal_hash, content_hash,
                manifest_hash, trial_count, target_hash,
                response_hash, score_hash, rating_hash,
                leakage_audit_hash, calibration_ref, valid, seal_version, seal_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '1.0', ?)""",
            ("no-manifest", "no-manifest", seal_data.seal_hash(),
             seal_data.content_hash, seal_data.manifest_hash,
             seal_data.trial_count, seal_data.target_hash,
             seal_data.response_hash, seal_data.score_hash,
             seal_data.rating_hash, seal_data.leakage_audit_hash,
             "", json.dumps(seal_data.to_dict())),
        )
        await db.commit()

        replay = await replay_from_db(db, "no-manifest")
        assert not replay.exact_match
        assert any(d.field == "manifest" for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_missing_seal_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        from app.research.response_provider import SyntheticCognitiveResponseProvider
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()

        await execute_objective_session_persistent(
            db, "no-seal", pop[0].participant_id, "adaptive", 0,
            TRIAL_SPECS, provider, guard, 42,
        )

        replay = await replay_from_db(db, "no-seal")
        assert not replay.exact_match
        assert any(d.field == "seal" for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_invalid_seal_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "invalid-seal")

        await db.execute(
            "UPDATE objective_completion_seals SET content_hash = 'tampered' WHERE session_id = 'invalid-seal'"
        )
        await db.commit()

        replay = await replay_from_db(db, "invalid-seal")
        assert not replay.exact_match
        assert not replay.seal_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_tampered_target_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db, "tampered-target")

        await db.execute(
            "UPDATE objective_trial_specs SET target_orientation = 999 WHERE block_id = 1 AND trial_index = 0"
        )
        await db.commit()

        replay = await replay_from_db(db, "tampered-target")
        assert not replay.exact_match
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_tampered_response_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db, "tampered-resp")

        await db.execute(
            "UPDATE objective_trial_responses SET response_orientation = 999 WHERE trial_spec_id = 1"
        )
        await db.commit()

        replay = await replay_from_db(db, "tampered-resp")
        assert not replay.exact_match
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_tampered_score_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db, "tampered-score")

        await db.execute(
            "UPDATE objective_trial_scores SET composite_error = 999 WHERE response_id = 1"
        )
        await db.commit()

        replay = await replay_from_db(db, "tampered-score")
        assert not replay.exact_match
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_scoring_version_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "scoring-mismatch")

        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'scoring-mismatch'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["scoring_version"] = "0.0.0-fake"
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "scoring-mismatch")
        assert not replay.exact_match
        assert not replay.scoring_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_manifest_hash_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db, "hash-mismatch")

        await db.execute(
            "UPDATE objective_manifests SET manifest_hash = 'wrong' WHERE study_id = 'hash-mismatch'"
        )
        await db.commit()

        replay = await replay_from_db(db, "hash-mismatch")
        assert not replay.exact_match
        assert not replay.manifest_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_replay_persisted_on_success(tmp_path):
    db = await _make_db(tmp_path)
    try:
        await _persist_session(db)
        await replay_from_db(db, "replay-test-s1")

        runs = await (await db.execute(
            "SELECT * FROM objective_replay_runs WHERE session_id = 'replay-test-s1'"
        )).fetchall()
        assert len(runs) >= 1

        results = await (await db.execute(
            "SELECT * FROM objective_replay_results WHERE replay_run_id = ?", (runs[0]["id"],)
        )).fetchall()
        assert len(results) >= 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_replay_persisted_on_failure(tmp_path):
    db = await _make_db(tmp_path)
    try:
        pop = generate_population(1, seed=42, scenario=SCENARIO_MEDIUM_ADAPTIVE)
        from app.research.response_provider import SyntheticCognitiveResponseProvider
        provider = SyntheticCognitiveResponseProvider(pop[0], SCENARIO_MEDIUM_ADAPTIVE)
        guard = LeakageGuard()

        await execute_objective_session_persistent(
            db, "fail-persist", pop[0].participant_id, "adaptive", 0,
            TRIAL_SPECS, provider, guard, 42,
        )

        replay = await replay_from_db(db, "fail-persist")
        assert not replay.exact_match

        runs = await (await db.execute(
            "SELECT * FROM objective_replay_runs WHERE session_id = 'fail-persist'"
        )).fetchall()
        assert len(runs) >= 1
        assert runs[0]["exact_match"] == 0
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_response_provider_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "rp-mismatch")

        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'rp-mismatch'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["response_provider_id"] = ""
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "rp-mismatch")
        assert not replay.exact_match
        assert not replay.response_provider_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_missing_root_seed_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "no-seed")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'no-seed'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata.pop("root_seed", None)
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "no-seed")
        assert not replay.exact_match
        assert any(d.field == "root_seed" for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_wrong_root_seed_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "wrong-seed")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'wrong-seed'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["root_seed"] = 99999
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "wrong-seed")
        assert not replay.exact_match
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_unresolved_scenario_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "bad-scenario")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'bad-scenario'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["scenario_hash"] = "nonexistent_hash"
        mdata["scenario_id"] = "nonexistent_id"
        mdata["cognitive_agent_version"] = "nonexistent"
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "bad-scenario")
        assert not replay.exact_match
        assert any(d.field == "scenario" for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_scenario_hash_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "hash-scenario")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'hash-scenario'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["scenario_hash"] = "wrong_hash_value"
        mdata["scenario_id"] = "medium_adaptive"
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "hash-scenario")
        assert not replay.exact_match
        assert any("scenario_hash mismatch" in str(d.replayed) for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_rng_version_mismatch_diverges(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "rng-mismatch")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'rng-mismatch'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["rng_version"] = "0.0.0-fake"
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "rng-mismatch")
        assert any(d.field == "rng_version" for d in replay.divergences)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_schedule_db_manifest_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "sched-mismatch")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'sched-mismatch'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["schedule_hash"] = "different_schedule_hash"
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "sched-mismatch")
        assert not replay.exact_match
        assert not replay.schedule_verified
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_provider_config_mismatch_fails(tmp_path):
    db = await _make_db(tmp_path)
    try:
        result, manifest, seal = await _persist_session(db, "config-mismatch")
        manifest_row = await (await db.execute(
            "SELECT id, manifest_json FROM objective_manifests WHERE study_id = 'config-mismatch'"
        )).fetchone()
        mdata = json.loads(manifest_row["manifest_json"])
        mdata["response_provider_config_hash"] = ""
        await db.execute(
            "UPDATE objective_manifests SET manifest_json = ? WHERE id = ?",
            (json.dumps(mdata, sort_keys=True, separators=(",", ":")), manifest_row["id"]),
        )
        await db.commit()

        replay = await replay_from_db(db, "config-mismatch")
        assert not replay.exact_match
        assert not replay.response_provider_verified
    finally:
        await db.close()
