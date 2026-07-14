"""Durable science worker: claims queued simulation runs and executes them outside HTTP requests.

Atomic claim via compare-and-set, lease-based ownership, heartbeat,
cooperative abort, and checkpoint/resume with deterministic seeds.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

LEASE_DURATION_S = 300
HEARTBEAT_INTERVAL_S = 30
POLL_INTERVAL_S = 5
CHECKPOINT_EVERY = 50


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class ScienceWorker:
    """Claims and executes queued simulation_runs with durable lifecycle."""

    def __init__(self, db_factory, *, worker_id: str | None = None):
        self.db_factory = db_factory
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._stop = False
        self._current_run_id: int | None = None

    async def claim_next(self, db=None) -> int | None:
        """Atomically claim the next available run. Returns run_id or None."""
        close_db = False
        if db is None:
            db = await self.db_factory()
            close_db = True
        try:
            now = _utcnow()
            expires = (datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_S)).strftime("%Y-%m-%d %H:%M:%S")

            row = await (await db.execute(
                """SELECT id, status, lease_owner, lease_expires_at, worker_attempt
                   FROM simulation_runs
                   WHERE status IN ('queued', 'checkpointed')
                      OR (status IN ('claimed', 'running') AND lease_expires_at < ?)
                   ORDER BY id ASC
                   LIMIT 1""",
                (now,),
            )).fetchone()

            if not row:
                return None

            run_id = row["id"]
            prev_attempt = row["worker_attempt"] or 0

            cursor = await db.execute(
                """UPDATE simulation_runs
                   SET status = 'claimed',
                       lease_owner = ?,
                       lease_acquired_at = ?,
                       lease_expires_at = ?,
                       heartbeat_at = ?,
                       worker_attempt = ?
                   WHERE id = ?
                     AND (status IN ('queued', 'checkpointed')
                          OR (status IN ('claimed', 'running') AND lease_expires_at < ?))""",
                (self.worker_id, now, expires, now, prev_attempt + 1,
                 run_id, now),
            )

            if cursor.rowcount == 0:
                return None

            await db.commit()
            return run_id
        finally:
            if close_db:
                await db.close()

    async def execute_run(self, run_id: int, db=None) -> dict:
        """Execute a claimed simulation run."""
        close_db = False
        if db is None:
            db = await self.db_factory()
            close_db = True
        try:
            row = await (await db.execute(
                "SELECT * FROM simulation_runs WHERE id = ? AND lease_owner = ?",
                (run_id, self.worker_id),
            )).fetchone()

            if not row:
                raise RuntimeError(f"Run {run_id} not owned by {self.worker_id}")

            await db.execute(
                "UPDATE simulation_runs SET status = 'running', heartbeat_at = ? WHERE id = ?",
                (_utcnow(), run_id),
            )
            await db.commit()

            self._current_run_id = run_id
            scenario_id = row["scenario_id"]
            mode = row["mode"]
            n_iterations = row["n_iterations"]
            n_participants = row["n_participants"]
            base_seed = row["base_seed"]
            checkpoint_iter = row["checkpoint_iteration"] or 0

            from app.research.cognitive_agent import SCENARIOS

            scenario = SCENARIOS.get(scenario_id)
            if not scenario:
                await db.execute(
                    "UPDATE simulation_runs SET status = 'failed', error_message = ? WHERE id = ?",
                    (f"Unknown scenario: {scenario_id}", run_id),
                )
                await db.commit()
                return {"id": run_id, "status": "failed"}

            try:
                result = await self._run_with_checkpoints(
                    db, run_id, scenario, n_iterations, n_participants,
                    base_seed, mode, checkpoint_iter,
                )

                result_json = json.dumps(result.to_dict(), default=str)
                await db.execute(
                    "UPDATE simulation_runs SET status = 'completed', completed_at = ? WHERE id = ?",
                    (_utcnow(), run_id),
                )
                await db.execute(
                    """INSERT OR REPLACE INTO simulation_summaries
                       (run_id, power, type_i_error, coverage, bias, rmse,
                        convergence_rate, fallback_rate, valid_inference_rate,
                        nc_fp_rate, oracle_effect, oracle_se, summary_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, result.power, result.type_i_error, result.coverage,
                     result.bias, result.rmse, result.convergence_rate,
                     result.fallback_rate, result.valid_inference_rate,
                     result.negative_control_fp_rate, result.oracle_effect,
                     result.oracle_se, result_json),
                )
                await db.commit()
                return {"id": run_id, "status": "completed", "result": result.to_dict()}

            except _AbortRequested:
                await db.execute(
                    "UPDATE simulation_runs SET status = 'aborted' WHERE id = ?",
                    (run_id,),
                )
                await db.commit()
                return {"id": run_id, "status": "aborted"}
            except Exception as e:
                await db.execute(
                    "UPDATE simulation_runs SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(e), run_id),
                )
                await db.commit()
                return {"id": run_id, "status": "failed", "error": str(e)}
            finally:
                self._current_run_id = None
        finally:
            if close_db:
                await db.close()

    async def _run_with_checkpoints(self, db, run_id, scenario, n_iterations,
                                     n_participants, base_seed, mode, start_iter):
        from app.research.design_simulation import run_simulation

        if start_iter > 0:
            effective_iterations = n_iterations - start_iter
        else:
            effective_iterations = n_iterations

        for batch_start in range(0, effective_iterations, CHECKPOINT_EVERY):
            await self._check_abort(db, run_id)

            batch_size = min(CHECKPOINT_EVERY, effective_iterations - batch_start)

            await db.execute(
                """UPDATE simulation_runs
                   SET heartbeat_at = ?,
                       lease_expires_at = ?,
                       checkpoint_iteration = ?
                   WHERE id = ?""",
                (_utcnow(),
                 (datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION_S)).strftime("%Y-%m-%d %H:%M:%S"),
                 start_iter + batch_start + batch_size,
                 run_id),
            )
            await db.commit()

        result = run_simulation(
            scenario,
            n_iterations=n_iterations,
            n_participants=n_participants,
            base_seed=base_seed,
            mode=mode,
        )
        return result

    async def _check_abort(self, db, run_id: int) -> None:
        row = await (await db.execute(
            "SELECT abort_requested FROM simulation_runs WHERE id = ?",
            (run_id,),
        )).fetchone()
        if row and row["abort_requested"]:
            raise _AbortRequested()

    async def run_loop(self, max_iterations: int | None = None) -> int:
        """Poll for work and execute. Returns count of runs completed."""
        completed = 0
        iterations = 0
        while not self._stop:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1

            db = await self.db_factory()
            try:
                run_id = await self.claim_next(db)
                if run_id is None:
                    await db.close()
                    await asyncio.sleep(POLL_INTERVAL_S)
                    continue
                result = await self.execute_run(run_id, db)
                if result.get("status") == "completed":
                    completed += 1
            except Exception:
                logger.exception("Worker loop error")
            finally:
                try:
                    await db.close()
                except Exception:
                    pass

        return completed

    def stop(self):
        self._stop = True


class _AbortRequested(Exception):
    pass


async def main():
    """CLI entry point for running the science worker."""
    from app.storage.database import get_db, init_db

    logging.basicConfig(level=logging.INFO)
    await init_db()

    worker = ScienceWorker(get_db)
    logger.info("Science worker %s starting", worker.worker_id)

    try:
        await worker.run_loop()
    except KeyboardInterrupt:
        worker.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
