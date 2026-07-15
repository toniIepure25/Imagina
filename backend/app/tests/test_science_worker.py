"""Tests for the durable science worker: claim, execute, restart, abort, resume, lease."""
import hashlib
import json

import aiosqlite
import pytest

from app.research.design_simulation import FROZEN_STRIDE, SimulationAccumulator, run_simulation_batch
from app.research.science_worker import CHECKPOINT_EVERY, ScienceWorker
from app.storage.migration_runner import run_migrations


async def _make_db(tmp_path):
    db_path = str(tmp_path / "test_worker.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    return db, db_path


@pytest.fixture
def tmp_path(request):
    import pathlib
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        yield pathlib.Path(d)


async def _factory(db_path):
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def _insert_run(db, study_id="test-run", n_iterations=15, **kwargs):
    defaults = dict(
        scenario_id="strict_null", mode="unit", n_participants=18,
        base_seed=42, status="queued",
    )
    defaults.update(kwargs)
    cols = ["study_id", "scenario_id", "mode", "n_iterations", "n_participants",
            "base_seed", "status", "started_at"]
    vals = [study_id, defaults["scenario_id"], defaults["mode"], n_iterations,
            defaults["n_participants"], defaults["base_seed"], defaults["status"], "2026-01-01 00:00:00"]
    extra_cols = []
    extra_vals = []
    for k in ("abort_requested", "lease_owner", "lease_expires_at",
              "checkpoint_iteration", "worker_attempt"):
        if k in defaults:
            extra_cols.append(k)
            extra_vals.append(defaults[k])
    all_cols = cols + extra_cols
    all_vals = vals + extra_vals
    placeholders = ", ".join(["?"] * len(all_vals))
    col_str = ", ".join(all_cols)
    await db.execute(f"INSERT INTO simulation_runs ({col_str}) VALUES ({placeholders})", all_vals)
    await db.commit()
    row = await (await db.execute("SELECT id FROM simulation_runs WHERE study_id = ?", (study_id,))).fetchone()
    return row["id"]


@pytest.mark.asyncio
async def test_post_creates_queued_run(tmp_path):
    db, _ = await _make_db(tmp_path)
    try:
        run_id = await _insert_run(db, "test-1")
        row = await (await db.execute("SELECT status FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["status"] == "queued"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_worker_claims_queued_run(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-claim")
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w1")
        run_id = await worker.claim_next(db)
        assert run_id is not None
        row = await (await db.execute(
            "SELECT status, lease_owner FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        assert row["status"] == "claimed"
        assert row["lease_owner"] == "w1"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_two_workers_cannot_claim_same_run(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-double")
        w1 = ScienceWorker(lambda: _factory(db_path), worker_id="w1")
        w2 = ScienceWorker(lambda: _factory(db_path), worker_id="w2")
        r1 = await w1.claim_next(db)
        assert r1 is not None
        db2 = await _factory(db_path)
        try:
            r2 = await w2.claim_next(db2)
            assert r2 is None
        finally:
            await db2.close()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_expired_lease_is_recovered(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-expire", status="claimed",
                          lease_owner="dead-worker", lease_expires_at="2020-01-01 00:00:00")
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-recover")
        run_id = await worker.claim_next(db)
        assert run_id is not None
        row = await (await db.execute("SELECT lease_owner FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["lease_owner"] == "w-recover"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_unexpired_lease_not_stolen(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-active", status="claimed",
                          lease_owner="active-worker", lease_expires_at="2099-01-01 00:00:00")
        thief = ScienceWorker(lambda: _factory(db_path), worker_id="thief")
        run_id = await thief.claim_next(db)
        assert run_id is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_worker_executes_and_completes(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-exec")
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-exec")
        run_id = await worker.claim_next(db)
        assert run_id is not None
        result = await worker.execute_run(run_id, db)
        assert result["status"] == "completed"
        row = await (await db.execute("SELECT status FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["status"] == "completed"
        summary = await (await db.execute("SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,))).fetchone()
        assert summary is not None
        assert summary["summary_json"] is not None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_idempotent_duplicate_post(tmp_path):
    db, _ = await _make_db(tmp_path)
    try:
        id1 = await _insert_run(db, "test-idem")
        existing = await (await db.execute(
            "SELECT id, status FROM simulation_runs WHERE study_id = 'test-idem'",
        )).fetchone()
        assert existing is not None
        assert existing["id"] == id1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_partial_execution_persists_checkpoint(tmp_path):
    """Partial execution must persist actual replicate evidence in checkpoint."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = CHECKPOINT_EVERY + 5
        await _insert_run(db, "test-partial", n_iterations=n_iters)
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-partial")
        run_id = await worker.claim_next(db)
        result = await worker.execute_run(run_id, db)
        assert result["status"] == "completed"

        cp = await (await db.execute(
            "SELECT * FROM simulation_checkpoints WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert cp is not None
        assert cp["checkpoint_iteration"] == n_iters
        acc_data = json.loads(cp["accumulator_json"])
        assert acc_data["valid_count"] + acc_data["invalid_count"] == n_iters
        assert len(acc_data["seeds"]) == n_iters
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_resume_skips_completed_replicates(tmp_path):
    """Resume from checkpoint must not rerun completed replicates."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = 20
        base_seed = 42
        from app.research.causal_oracle import compute_oracle_effect
        from app.research.cognitive_agent import SCENARIOS
        scenario = SCENARIOS["strict_null"]
        oracle = compute_oracle_effect(scenario, n_agents=100, seed=base_seed + 999999)

        first_batch = run_simulation_batch(
            scenario, replicate_start=0, replicate_count=10,
            n_participants=18, base_seed=base_seed, mode="unit",
            oracle_truth=oracle.effect,
        )

        run_id = await _insert_run(db, "test-resume", n_iterations=n_iters,
                                   status="checkpointed", checkpoint_iteration=10)
        acc_json = json.dumps(first_batch.accumulator.to_dict(), sort_keys=True,
                              separators=(",", ":"), default=str)
        acc_hash = hashlib.sha256(acc_json.encode()).hexdigest()
        await db.execute(
            """INSERT INTO simulation_checkpoints
               (run_id, checkpoint_iteration, accumulator_json, accumulator_hash,
                last_completed_seed, checkpoint_version, updated_at)
               VALUES (?, 10, ?, ?, ?, '1.0', '2026-01-01')""",
            (run_id, acc_json, acc_hash, base_seed + 9 * FROZEN_STRIDE),
        )
        await db.commit()

        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-resume")
        claimed = await worker.claim_next(db)
        assert claimed == run_id
        result = await worker.execute_run(run_id, db)
        assert result["status"] == "completed"

        cp = await (await db.execute(
            "SELECT * FROM simulation_checkpoints WHERE run_id = ?", (run_id,),
        )).fetchone()
        acc_final = json.loads(cp["accumulator_json"])
        assert acc_final["valid_count"] + acc_final["invalid_count"] == n_iters
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_resumed_and_uninterrupted_identical(tmp_path):
    """Resumed run must produce the same final summary as uninterrupted."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = 20
        base_seed = 42

        await _insert_run(db, "uninterrupted", n_iterations=n_iters)
        w_full = ScienceWorker(lambda: _factory(db_path), worker_id="w-full")
        rid_full = await w_full.claim_next(db)
        res_full = await w_full.execute_run(rid_full, db)
        assert res_full["status"] == "completed"

        from app.research.causal_oracle import compute_oracle_effect
        from app.research.cognitive_agent import SCENARIOS
        scenario = SCENARIOS["strict_null"]
        oracle = compute_oracle_effect(scenario, n_agents=100, seed=base_seed + 999999)

        split_at = 10
        first_batch = run_simulation_batch(
            scenario, replicate_start=0, replicate_count=split_at,
            n_participants=18, base_seed=base_seed, mode="unit",
            oracle_truth=oracle.effect,
        )

        rid_resume = await _insert_run(db, "resumed", n_iterations=n_iters,
                                       status="checkpointed", checkpoint_iteration=split_at)
        acc_json = json.dumps(first_batch.accumulator.to_dict(), sort_keys=True,
                              separators=(",", ":"), default=str)
        acc_hash = hashlib.sha256(acc_json.encode()).hexdigest()
        await db.execute(
            """INSERT INTO simulation_checkpoints
               (run_id, checkpoint_iteration, accumulator_json, accumulator_hash,
                last_completed_seed, checkpoint_version, updated_at)
               VALUES (?, ?, ?, ?, ?, '1.0', '2026-01-01')""",
            (rid_resume, split_at, acc_json, acc_hash, base_seed + (split_at - 1) * FROZEN_STRIDE),
        )
        await db.commit()

        w_resume = ScienceWorker(lambda: _factory(db_path), worker_id="w-resumed")
        claimed = await w_resume.claim_next(db)
        res_resumed = await w_resume.execute_run(claimed, db)
        assert res_resumed["status"] == "completed"

        full_summary = await (await db.execute(
            "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (rid_full,),
        )).fetchone()
        resumed_summary = await (await db.execute(
            "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (rid_resume,),
        )).fetchone()

        full_data = json.loads(full_summary["summary_json"])
        resumed_data = json.loads(resumed_summary["summary_json"])

        for key in ("n_valid_replicates", "n_invalid_replicates", "n_iterations"):
            assert full_data[key] == resumed_data[key], f"Exact mismatch on {key}"

        for key in ("power", "type_i_error", "coverage", "bias", "rmse",
                    "convergence_rate", "fallback_rate", "valid_inference_rate",
                    "oracle_effect"):
            fv = full_data[key]
            rv = resumed_data[key]
            if fv is None and rv is None:
                continue
            assert fv == pytest.approx(rv, abs=1e-5), f"Tolerance exceeded on {key}: {fv} vs {rv}"

        full_cp = await (await db.execute(
            "SELECT accumulator_json FROM simulation_checkpoints WHERE run_id = ?", (rid_full,),
        )).fetchone()
        resumed_cp = await (await db.execute(
            "SELECT accumulator_json FROM simulation_checkpoints WHERE run_id = ?", (rid_resume,),
        )).fetchone()
        full_acc = json.loads(full_cp["accumulator_json"])
        resumed_acc = json.loads(resumed_cp["accumulator_json"])
        assert full_acc["valid_count"] == resumed_acc["valid_count"]
        assert full_acc["invalid_count"] == resumed_acc["invalid_count"]
        assert full_acc["rejections"] == resumed_acc["rejections"]
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_abort_during_running_execution(tmp_path):
    """Abort requested while worker is mid-execution must result in aborted status.

    The abort_requested flag is set AFTER the run starts executing,
    not before execution begins.
    """
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = CHECKPOINT_EVERY * 3
        run_id = await _insert_run(db, "test-abort-mid", n_iterations=n_iters)

        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-abort")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        await db.execute(
            "UPDATE simulation_runs SET abort_requested = 1 WHERE id = ?", (run_id,),
        )
        await db.commit()

        result = await worker.execute_run(claimed, db)
        assert result["status"] == "aborted"

        row = await (await db.execute("SELECT status FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["status"] == "aborted"

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_abort_after_nonzero_checkpoint(tmp_path):
    """Abort after a nonzero checkpoint preserves checkpoint but no completed summary."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = CHECKPOINT_EVERY * 3
        base_seed = 42
        from app.research.causal_oracle import compute_oracle_effect
        from app.research.cognitive_agent import SCENARIOS
        scenario = SCENARIOS["strict_null"]
        oracle = compute_oracle_effect(scenario, n_agents=100, seed=base_seed + 999999)

        first_batch = run_simulation_batch(
            scenario, replicate_start=0, replicate_count=CHECKPOINT_EVERY,
            n_participants=18, base_seed=base_seed, mode="unit",
            oracle_truth=oracle.effect,
        )

        run_id = await _insert_run(db, "test-abort-cp", n_iterations=n_iters,
                                   status="checkpointed", checkpoint_iteration=CHECKPOINT_EVERY)
        acc_json = json.dumps(first_batch.accumulator.to_dict(), sort_keys=True,
                              separators=(",", ":"), default=str)
        acc_hash = hashlib.sha256(acc_json.encode()).hexdigest()
        await db.execute(
            """INSERT INTO simulation_checkpoints
               (run_id, checkpoint_iteration, accumulator_json, accumulator_hash,
                last_completed_seed, checkpoint_version, updated_at)
               VALUES (?, ?, ?, ?, ?, '1.0', '2026-01-01')""",
            (run_id, CHECKPOINT_EVERY, acc_json, acc_hash,
             base_seed + (CHECKPOINT_EVERY - 1) * FROZEN_STRIDE),
        )
        await db.commit()

        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-abort-cp")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        await db.execute("UPDATE simulation_runs SET abort_requested = 1 WHERE id = ?", (run_id,))
        await db.commit()

        result = await worker.execute_run(claimed, db)
        assert result["status"] == "aborted"

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None

        cp = await (await db.execute(
            "SELECT * FROM simulation_checkpoints WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert cp is not None
        assert cp["checkpoint_iteration"] == CHECKPOINT_EVERY
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_worker_cannot_finalize_after_losing_lease(tmp_path):
    """Worker that lost its lease cannot write completed status or summary."""
    db, db_path = await _make_db(tmp_path)
    try:
        run_id = await _insert_run(db, "test-lease-lost", n_iterations=15)

        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-victim")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        await db.execute(
            "UPDATE simulation_runs SET lease_owner = 'new-owner' WHERE id = ?", (run_id,),
        )
        await db.commit()

        result = await worker.execute_run(claimed, db)
        assert result["status"] == "failed"
        assert "lost_lease" in str(result.get("error", ""))

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_no_overlapping_replicate_ranges(tmp_path):
    """Two workers cannot process overlapping replicates for the same run."""
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-overlap", n_iterations=30)

        w1 = ScienceWorker(lambda: _factory(db_path), worker_id="w-a")
        w2 = ScienceWorker(lambda: _factory(db_path), worker_id="w-b")

        r1 = await w1.claim_next(db)
        assert r1 is not None

        db2 = await _factory(db_path)
        try:
            r2 = await w2.claim_next(db2)
            assert r2 is None
        finally:
            await db2.close()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_expired_worker_recovered_from_last_checkpoint(tmp_path):
    """Expired worker's run is recovered from last valid checkpoint."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = 20
        base_seed = 42
        from app.research.causal_oracle import compute_oracle_effect
        from app.research.cognitive_agent import SCENARIOS
        scenario = SCENARIOS["strict_null"]
        oracle = compute_oracle_effect(scenario, n_agents=100, seed=base_seed + 999999)

        first_batch = run_simulation_batch(
            scenario, replicate_start=0, replicate_count=10,
            n_participants=18, base_seed=base_seed, mode="unit",
            oracle_truth=oracle.effect,
        )

        run_id = await _insert_run(db, "test-expire-cp", n_iterations=n_iters,
                                   status="running", checkpoint_iteration=10,
                                   lease_owner="dead-worker",
                                   lease_expires_at="2020-01-01 00:00:00")
        acc_json = json.dumps(first_batch.accumulator.to_dict(), sort_keys=True,
                              separators=(",", ":"), default=str)
        acc_hash = hashlib.sha256(acc_json.encode()).hexdigest()
        await db.execute(
            """INSERT INTO simulation_checkpoints
               (run_id, checkpoint_iteration, accumulator_json, accumulator_hash,
                last_completed_seed, checkpoint_version, updated_at)
               VALUES (?, 10, ?, ?, ?, '1.0', '2026-01-01')""",
            (run_id, acc_json, acc_hash, base_seed + 9 * FROZEN_STRIDE),
        )
        await db.commit()

        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-recovery")
        claimed = await worker.claim_next(db)
        assert claimed == run_id

        result = await worker.execute_run(claimed, db)
        assert result["status"] == "completed"

        summary = await (await db.execute(
            "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        data = json.loads(summary["summary_json"])
        assert data["n_iterations"] == n_iters
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_checkpointed_run_recoverable(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await _insert_run(db, "test-checkpoint", status="checkpointed", checkpoint_iteration=5)
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-resume")
        run_id = await worker.claim_next(db)
        assert run_id is not None
        result = await worker.execute_run(run_id, db)
        assert result["status"] == "completed"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_queued_abort_becomes_aborted(tmp_path):
    """A queued run with abort_requested should be set to aborted on claim."""
    db, db_path = await _make_db(tmp_path)
    try:
        run_id = await _insert_run(db, "test-queued-abort", abort_requested=1)
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-qa")
        claimed = await worker.claim_next(db)
        assert claimed is None

        row = await (await db.execute("SELECT status FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["status"] == "aborted"
    finally:
        await db.close()


class _AbortAfterFirstBatch(ScienceWorker):
    """Injects a concurrent abort request right after the first batch's
    _check_abort call returns cleanly, simulating abort arriving while the
    batch is being computed (i.e. between batch completion and the checkpoint
    persistence that follows it)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._checks = 0

    async def _check_abort(self, db, run_id):
        self._checks += 1
        await super()._check_abort(db, run_id)
        if self._checks == 1:
            await db.execute(
                "UPDATE simulation_runs SET abort_requested = 1 WHERE id = ?", (run_id,),
            )
            await db.commit()


@pytest.mark.asyncio
async def test_batch_completion_not_discarded_by_concurrent_abort(tmp_path):
    """A fully completed batch's checkpoint must be persisted even when abort
    arrives during that batch's computation, not just between batches."""
    db, db_path = await _make_db(tmp_path)
    try:
        n_iters = CHECKPOINT_EVERY * 2
        run_id = await _insert_run(db, "test-abort-race", n_iterations=n_iters)

        worker = _AbortAfterFirstBatch(lambda: _factory(db_path), worker_id="w-race")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        result = await worker.execute_run(claimed, db)
        assert result["status"] == "aborted"

        row = await (await db.execute(
            "SELECT status FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        assert row["status"] == "aborted"

        cp = await (await db.execute(
            "SELECT * FROM simulation_checkpoints WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert cp is not None
        assert cp["checkpoint_iteration"] == CHECKPOINT_EVERY, (
            "the first fully completed batch must not be discarded"
        )

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_finalization_guard_prevents_completion_after_late_abort(tmp_path):
    """If abort_requested flips to 1 after the run loop finishes but before the
    guarded completion UPDATE commits, the run must end up aborted, never
    completed, and no summary may be inserted."""
    db, db_path = await _make_db(tmp_path)
    try:
        run_id = await _insert_run(db, "test-late-abort", n_iterations=15)
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-late-abort")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        row = await (await db.execute(
            "SELECT * FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        await db.execute(
            "UPDATE simulation_runs SET status = 'running' WHERE id = ?", (run_id,),
        )
        await db.commit()

        # Simulate the run loop finishing computation just as an abort request
        # lands, immediately before the guarded finalization UPDATE.
        await db.execute(
            "UPDATE simulation_runs SET abort_requested = 1 WHERE id = ?", (run_id,),
        )
        await db.commit()

        from app.research.design_simulation import SimulationAccumulator
        fake_acc = SimulationAccumulator(
            oracle_truth=0.0, scenario_id="strict_null", scenario_version="1.0",
        )
        fake_result = fake_acc.finalize(15, row["n_participants"], mode="unit")

        with pytest.raises(Exception):
            await worker._finalize_completion(db, run_id, fake_result)

        final_row = await (await db.execute(
            "SELECT status FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        assert final_row["status"] != "completed"

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_finalization_guard_stops_on_lost_lease(tmp_path):
    """If the lease is stolen before the guarded completion UPDATE, the
    original worker must stop with lost_lease and never write a summary."""
    db, db_path = await _make_db(tmp_path)
    try:
        run_id = await _insert_run(db, "test-finalize-lost-lease", n_iterations=15)
        worker = ScienceWorker(lambda: _factory(db_path), worker_id="w-victim")
        claimed = await worker.claim_next(db)
        assert claimed is not None

        row = await (await db.execute(
            "SELECT * FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        await db.execute(
            "UPDATE simulation_runs SET status = 'running', lease_owner = 'new-owner'"
            " WHERE id = ?", (run_id,),
        )
        await db.commit()

        from app.research.design_simulation import SimulationAccumulator
        fake_acc = SimulationAccumulator(
            oracle_truth=0.0, scenario_id="strict_null", scenario_version="1.0",
        )
        fake_result = fake_acc.finalize(15, row["n_participants"], mode="unit")

        with pytest.raises(Exception):
            await worker._finalize_completion(db, run_id, fake_result)

        final_row = await (await db.execute(
            "SELECT status FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        assert final_row["status"] != "completed"

        summary = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        assert summary is None
    finally:
        await db.close()


class TestSimulationAccumulator:
    def test_merge_is_additive(self):
        a = SimulationAccumulator(valid_count=5, invalid_count=1, rejections=2,
                                  oracle_truth=0.0, scenario_id="test", scenario_version="1.0",
                                  seeds=[1, 2, 3, 4, 5])
        b = SimulationAccumulator(valid_count=3, invalid_count=2, rejections=1,
                                  oracle_truth=0.0, scenario_id="test", scenario_version="1.0",
                                  seeds=[6, 7, 8])
        merged = a.merge(b)
        assert merged.valid_count == 8
        assert merged.invalid_count == 3
        assert merged.rejections == 3
        assert len(merged.seeds) == 8

    def test_round_trip_serialization(self):
        a = SimulationAccumulator(
            valid_count=5, rejections=2, estimate_sum=1.5,
            estimate_sum_sq=0.5, seeds=[42, 1042],
            oracle_truth=0.3, oracle_se=0.01,
            scenario_id="test", scenario_version="1.0",
        )
        data = a.to_dict()
        restored = SimulationAccumulator.from_dict(data)
        assert restored.valid_count == a.valid_count
        assert restored.estimate_sum == a.estimate_sum
        assert restored.seeds == a.seeds
        assert a.hash() == restored.hash()
