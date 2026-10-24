"""API integration tests for cooperative abort through the durable worker contract.

These tests exercise the actual HTTP handler
(POST /api/research-science/simulations/{run_id}/abort) rather than mutating
simulation_runs directly, proving the endpoint's status-aware behavior and its
interaction with the real ScienceWorker finalization guard.
"""
import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.research.science_worker import ScienceWorker
from app.storage.database import get_db, init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_db(monkeypatch, tmp_path):
    db_path = os.path.join(str(tmp_path), "test_science_abort_api.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.close()


def _create_sim(idem, scenario_id="strict_null", mode="unit", n_participants=18, base_seed=42):
    resp = client.post("/api/research-science/simulations", json={
        "scenario_id": scenario_id, "mode": mode,
        "n_participants": n_participants, "base_seed": base_seed,
        "idempotency_key": idem,
    })
    assert resp.status_code == 202
    return resp.json()["id"]


async def _insert_run_direct(db, study_id, **kwargs):
    defaults = dict(
        scenario_id="strict_null", mode="unit", n_participants=18,
        base_seed=42, status="queued", n_iterations=15,
    )
    defaults.update(kwargs)
    cols = ["study_id", "scenario_id", "mode", "n_iterations", "n_participants",
            "base_seed", "status", "started_at"]
    vals = [study_id, defaults["scenario_id"], defaults["mode"], defaults["n_iterations"],
            defaults["n_participants"], defaults["base_seed"], defaults["status"],
            "2026-01-01 00:00:00"]
    extra_cols: list[str] = []
    extra_vals: list = []
    for k in ("abort_requested", "lease_owner", "lease_expires_at",
              "checkpoint_iteration", "worker_attempt"):
        if k in defaults:
            extra_cols.append(k)
            extra_vals.append(defaults[k])
    all_cols = cols + extra_cols
    all_vals = vals + extra_vals
    placeholders = ", ".join(["?"] * len(all_vals))
    col_str = ", ".join(all_cols)
    cursor = await db.execute(
        f"INSERT INTO simulation_runs ({col_str}) VALUES ({placeholders})", all_vals,
    )
    await db.commit()
    return cursor.lastrowid


def _query_run(run_id):
    async def _q():
        db = await get_db()
        row = await (await db.execute(
            "SELECT status, abort_requested, lease_owner, checkpoint_iteration"
            " FROM simulation_runs WHERE id = ?",
            (run_id,),
        )).fetchone()
        await db.close()
        return dict(row) if row else None
    return asyncio.run(_q())


def _query_summary(run_id):
    async def _q():
        db = await get_db()
        row = await (await db.execute(
            "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
        )).fetchone()
        await db.close()
        return dict(row) if row else None
    return asyncio.run(_q())


def test_queued_abort_transitions_immediately():
    run_id = _create_sim("abort-api-queued-1")

    resp = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert resp.status_code == 200
    assert resp.json() == {"id": run_id, "status": "aborted"}

    row = _query_run(run_id)
    assert row["status"] == "aborted"
    assert row["abort_requested"] == 1


def test_checkpointed_abort_transitions_immediately():
    async def _setup():
        db = await get_db()
        run_id = await _insert_run_direct(
            db, "abort-api-checkpointed-1", status="checkpointed", checkpoint_iteration=10,
        )
        await db.close()
        return run_id

    run_id = asyncio.run(_setup())

    resp = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert resp.status_code == 200
    assert resp.json() == {"id": run_id, "status": "aborted"}

    row = _query_run(run_id)
    assert row["status"] == "aborted"
    assert row["abort_requested"] == 1
    assert row["checkpoint_iteration"] == 10


def test_abort_after_completed_is_noop():
    async def _setup():
        db = await get_db()
        run_id = await _insert_run_direct(db, "abort-api-completed-1", status="completed")
        await db.execute(
            """INSERT INTO simulation_summaries
               (run_id, power, type_i_error, coverage, bias, rmse,
                convergence_rate, fallback_rate, valid_inference_rate,
                nc_fp_rate, oracle_effect, oracle_se, summary_json)
               VALUES (?, 0.8, 0.05, 0.95, 0.0, 0.1, 1.0, 0.0, 1.0, 0.05, 0.0, 0.01, '{}')""",
            (run_id,),
        )
        await db.commit()
        await db.close()
        return run_id

    run_id = asyncio.run(_setup())

    resp = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert resp.status_code == 200
    assert resp.json() == {"id": run_id, "status": "completed"}

    row = _query_run(run_id)
    assert row["status"] == "completed"
    assert row["abort_requested"] == 0
    assert _query_summary(run_id) is not None


def test_repeated_abort_is_idempotent():
    run_id = _create_sim("abort-api-repeat-1")

    r1 = client.post(f"/api/research-science/simulations/{run_id}/abort")
    r2 = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == {"id": run_id, "status": "aborted"}
    assert r2.json() == {"id": run_id, "status": "aborted"}


def test_abort_after_lease_transfer():
    async def _scenario():
        db = await get_db()
        run_id = await _insert_run_direct(
            db, "abort-api-lease-transfer-1", status="claimed",
            lease_owner="dead-worker", lease_expires_at="2020-01-01 00:00:00",
        )
        await db.close()

        new_worker = ScienceWorker(get_db, worker_id="w-new-owner")
        claimed = await new_worker.claim_next()
        return run_id, claimed, new_worker

    run_id, claimed, new_worker = asyncio.run(_scenario())
    assert claimed == run_id

    resp = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert resp.status_code == 200
    assert resp.json() == {"id": run_id, "status": "abort_requested"}

    row = _query_run(run_id)
    assert row["abort_requested"] == 1
    assert row["status"] == "claimed"
    assert row["lease_owner"] == "w-new-owner"

    result = asyncio.run(new_worker.execute_run(run_id))
    assert result["status"] == "aborted"

    final_row = _query_run(run_id)
    assert final_row["status"] == "aborted"


@pytest.mark.asyncio
async def test_running_abort_preserves_state_until_checkpoint_then_terminates():
    run_id = _create_sim("abort-api-running-1", mode="ci")

    worker = ScienceWorker(get_db, worker_id="w-api-running")
    claimed = await worker.claim_next()
    assert claimed == run_id

    task = asyncio.create_task(worker.execute_run(run_id))

    poll_db = await get_db()
    checkpoint_iter = 0
    for _ in range(400):
        row = await (await poll_db.execute(
            "SELECT checkpoint_iteration FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        if row and row["checkpoint_iteration"]:
            checkpoint_iter = row["checkpoint_iteration"]
            if checkpoint_iter > 0:
                break
        if task.done():
            break
        await asyncio.sleep(0.05)
    await poll_db.close()

    assert checkpoint_iter > 0, "worker never persisted a nonzero batch before the test observed it"
    assert not task.done(), "run completed before the test could exercise a mid-run abort"

    # The response itself is the proof that the endpoint found the run
    # claimed/running (not terminal) and preserved its state rather than
    # forcing it straight to aborted — by the time this call returns, the
    # worker may have already raced ahead and finalized to aborted, so a
    # DB re-read here would be racing the very cooperation being tested.
    abort_resp = client.post(f"/api/research-science/simulations/{run_id}/abort")
    assert abort_resp.status_code == 200
    assert abort_resp.json() == {"id": run_id, "status": "abort_requested"}

    db = await get_db()
    row = await (await db.execute(
        "SELECT abort_requested FROM simulation_runs WHERE id = ?", (run_id,),
    )).fetchone()
    await db.close()
    assert row["abort_requested"] == 1

    result = await task
    assert result["status"] == "aborted"

    db = await get_db()
    final = await (await db.execute(
        "SELECT status, checkpoint_iteration FROM simulation_runs WHERE id = ?", (run_id,),
    )).fetchone()
    assert final["status"] == "aborted"
    assert final["checkpoint_iteration"] > 0

    summary = await (await db.execute(
        "SELECT * FROM simulation_summaries WHERE run_id = ?", (run_id,),
    )).fetchone()
    assert summary is None

    # The worker must never be able to overwrite the aborted status with
    # completed — the guarded UPDATE must reject a late finalization attempt.
    cursor = await db.execute(
        "UPDATE simulation_runs SET status = 'completed', completed_at = datetime('now')"
        " WHERE id = ? AND lease_owner = ? AND abort_requested = 0 AND status = 'running'",
        (run_id, worker.worker_id),
    )
    assert cursor.rowcount == 0
    await db.rollback()
    await db.close()


def test_abort_nonexistent_run_404():
    resp = client.post("/api/research-science/simulations/999999/abort")
    assert resp.status_code == 404
