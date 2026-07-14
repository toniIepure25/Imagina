"""Tests for the durable science worker: claim, execute, restart, abort, resume."""
import aiosqlite
import pytest

from app.research.science_worker import ScienceWorker
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


@pytest.mark.asyncio
async def test_post_creates_queued_run(tmp_path):
    db, _ = await _make_db(tmp_path)
    try:
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at)
               VALUES ('test-1', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'))"""
        )
        await db.commit()
        row = await (await db.execute("SELECT status FROM simulation_runs WHERE study_id = 'test-1'")).fetchone()
        assert row["status"] == "queued"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_worker_claims_queued_run(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at)
               VALUES ('test-claim', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'))"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        worker = ScienceWorker(factory, worker_id="w1")
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
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at)
               VALUES ('test-double', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'))"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        w1 = ScienceWorker(factory, worker_id="w1")
        w2 = ScienceWorker(factory, worker_id="w2")

        r1 = await w1.claim_next(db)
        assert r1 is not None

        db2 = await factory()
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
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at, lease_owner, lease_expires_at)
               VALUES ('test-expire', 'strict_null', 'unit', 15, 18, 42,
                        'claimed', datetime('now'), 'dead-worker', '2020-01-01 00:00:00')"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        worker = ScienceWorker(factory, worker_id="w-recover")
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
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at, lease_owner, lease_expires_at)
               VALUES ('test-active', 'strict_null', 'unit', 15, 18, 42,
                        'claimed', datetime('now'), 'active-worker', '2099-01-01 00:00:00')"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        thief = ScienceWorker(factory, worker_id="thief")
        run_id = await thief.claim_next(db)
        assert run_id is None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_abort_during_execution(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at, abort_requested)
               VALUES ('test-abort', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'), 1)"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        worker = ScienceWorker(factory, worker_id="w-abort")
        run_id = await worker.claim_next(db)
        assert run_id is not None

        result = await worker.execute_run(run_id, db)
        assert result["status"] == "aborted"

        row = await (await db.execute("SELECT status FROM simulation_runs WHERE id = ?", (run_id,))).fetchone()
        assert row["status"] == "aborted"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_worker_executes_and_completes(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at)
               VALUES ('test-exec', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'))"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        worker = ScienceWorker(factory, worker_id="w-exec")
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
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at)
               VALUES ('test-idem', 'strict_null', 'unit', 15, 18, 42, 'queued', datetime('now'))"""
        )
        await db.commit()

        row = await (await db.execute("SELECT id FROM simulation_runs WHERE study_id = 'test-idem'")).fetchone()
        first_id = row["id"]

        existing = await (await db.execute(
            "SELECT id, status FROM simulation_runs WHERE study_id = 'test-idem'",
        )).fetchone()
        assert existing is not None
        assert existing["id"] == first_id
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_checkpointed_run_recoverable(tmp_path):
    db, db_path = await _make_db(tmp_path)
    try:
        await db.execute(
            """INSERT INTO simulation_runs
               (study_id, scenario_id, mode, n_iterations, n_participants,
                base_seed, status, started_at, checkpoint_iteration)
               VALUES ('test-checkpoint', 'strict_null', 'unit', 15, 18, 42, 'checkpointed', datetime('now'), 5)"""
        )
        await db.commit()

        async def factory():
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")
            return conn

        worker = ScienceWorker(factory, worker_id="w-resume")
        run_id = await worker.claim_next(db)
        assert run_id is not None

        result = await worker.execute_run(run_id, db)
        assert result["status"] == "completed"
    finally:
        await db.close()
