"""Persistent science API router.

All state is stored in the authoritative SQLite database.
Simulation runs follow a durable lifecycle:
  queued → claimed → running → completed | failed | aborted

Supports poll, restart recovery, idempotency, and abort.
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage.database import get_db

router = APIRouter(prefix="/api/research-science", tags=["research-science"])

VALID_STATUSES = {"queued", "claimed", "running", "checkpointed", "completed", "failed", "aborted"}


class DesignCreateRequest(BaseModel):
    n_participants: int = 18
    n_sessions: int = 3
    trials_per_task: int = 5
    seed: int = 42
    idempotency_key: str | None = None


class SimulationCreateRequest(BaseModel):
    scenario_id: str = "strict_null"
    mode: str = "unit"
    n_participants: int = 18
    base_seed: int = 42
    idempotency_key: str | None = None


class AnalysisCreateRequest(BaseModel):
    scenario_id: str = "medium_adaptive"
    seed: int = 42
    n_participants: int = 18
    idempotency_key: str | None = None


@router.post("/designs", status_code=201)
async def create_design(req: DesignCreateRequest):
    from app.research.crossover_design import design_hash, freeze_design

    idem_key = req.idempotency_key or f"design-{req.seed}-{req.n_participants}"
    db = await get_db()
    try:
        existing = await db.execute(
            "SELECT id, spec_hash FROM analysis_specifications WHERE study_id = ? AND spec_type = 'design'",
            (idem_key,),
        )
        row = await existing.fetchone()
        if row:
            return {"id": row[0], "idempotency_key": idem_key, "hash": row["spec_hash"], "status": "exists"}

        design = freeze_design(
            n_participants=req.n_participants,
            n_sessions=req.n_sessions,
            trials_per_task=req.trials_per_task,
            seed=req.seed,
        )
        d_hash = design_hash(design)
        cursor = await db.execute(
            """INSERT INTO analysis_specifications
               (study_id, spec_type, formula, estimand_id, model_version, spec_hash)
               VALUES (?, 'design', ?, 'design_spec', '1.0', ?)""",
            (idem_key, json.dumps(design.to_dict(), default=str), d_hash),
        )
        await db.commit()
        return {"id": cursor.lastrowid, "idempotency_key": idem_key, "hash": d_hash, "status": "created"}
    finally:
        await db.close()


@router.get("/designs/{design_id}")
async def get_design(design_id: str):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT * FROM analysis_specifications WHERE id = ? OR study_id = ?",
            (design_id, design_id),
        )).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Design not found")
        return {
            "id": row["id"], "study_id": row["study_id"],
            "hash": row["spec_hash"], "status": "frozen",
            "design": json.loads(row["formula"]) if row["formula"] else {},
        }
    finally:
        await db.close()


@router.post("/simulations", status_code=202)
async def create_simulation(req: SimulationCreateRequest):
    from app.research.cognitive_agent import SCENARIOS
    from app.research.design_simulation import SIMULATION_MODES, run_simulation

    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario_id}")

    idem_key = req.idempotency_key or f"sim-{req.scenario_id}-{req.mode}-{req.base_seed}"
    mode_config = SIMULATION_MODES.get(req.mode, SIMULATION_MODES["unit"])

    db = await get_db()
    try:
        existing = await (await db.execute(
            "SELECT id, status FROM simulation_runs WHERE study_id = ?", (idem_key,),
        )).fetchone()

        if existing:
            run_id = existing["id"]
            status = existing["status"]
            if status == "completed":
                summary = await (await db.execute(
                    "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (run_id,),
                )).fetchone()
                return {"id": run_id, "status": "completed",
                        "result": json.loads(summary["summary_json"]) if summary else {}}
            if status == "aborted":
                return {"id": run_id, "status": "aborted"}
            if status in ("queued", "claimed", "running", "checkpointed"):
                await db.execute(
                    "UPDATE simulation_runs SET status = 'claimed', started_at = datetime('now') WHERE id = ?",
                    (run_id,),
                )
                await db.commit()
            elif status == "failed":
                await db.execute(
                    "UPDATE simulation_runs SET status = 'claimed', started_at = datetime('now'), error_message = NULL WHERE id = ?",
                    (run_id,),
                )
                await db.commit()
        else:
            cursor = await db.execute(
                """INSERT INTO simulation_runs
                   (study_id, scenario_id, mode, n_iterations, n_participants,
                    base_seed, status, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'claimed', datetime('now'))""",
                (idem_key, req.scenario_id, req.mode, mode_config["iterations"],
                 req.n_participants, req.base_seed),
            )
            run_id = cursor.lastrowid
            await db.commit()
    finally:
        await db.close()

    db = await get_db()
    try:
        await db.execute(
            "UPDATE simulation_runs SET status = 'running' WHERE id = ?", (run_id,),
        )
        await db.commit()
    finally:
        await db.close()

    try:
        result = run_simulation(
            scenario,
            n_iterations=mode_config["iterations"],
            n_participants=req.n_participants,
            base_seed=req.base_seed,
            mode=req.mode,
        )
        db = await get_db()
        try:
            result_json = json.dumps(result.to_dict(), default=str)
            await db.execute(
                "UPDATE simulation_runs SET status = 'completed', completed_at = datetime('now') WHERE id = ?",
                (run_id,),
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
        finally:
            await db.close()
    except Exception as e:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE simulation_runs SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), run_id),
            )
            await db.commit()
        finally:
            await db.close()
        raise HTTPException(status_code=500, detail=str(e))

    return {"id": run_id, "status": "completed", "result": result.to_dict()}


@router.get("/simulations/{run_id}")
async def get_simulation(run_id: int):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT * FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Simulation not found")
        response: dict = {
            "id": row["id"], "scenario_id": row["scenario_id"],
            "mode": row["mode"], "status": row["status"],
            "started_at": row["started_at"],
        }
        if row["status"] == "completed":
            summary = await (await db.execute(
                "SELECT summary_json FROM simulation_summaries WHERE run_id = ?", (run_id,),
            )).fetchone()
            if summary:
                response["result"] = json.loads(summary["summary_json"])
        return response
    finally:
        await db.close()


@router.post("/simulations/{run_id}/abort", status_code=200)
async def abort_simulation(run_id: int):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT status FROM simulation_runs WHERE id = ?", (run_id,),
        )).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Simulation not found")
        if row["status"] in ("completed", "aborted"):
            return {"id": run_id, "status": row["status"], "message": "already terminal"}
        await db.execute(
            "UPDATE simulation_runs SET status = 'aborted' WHERE id = ?", (run_id,),
        )
        await db.commit()
        return {"id": run_id, "status": "aborted"}
    finally:
        await db.close()


@router.post("/analyses", status_code=202)
async def create_analysis(req: AnalysisCreateRequest):
    from app.research.cognitive_agent import SCENARIOS
    from app.research.design_simulation import _generate_study_data
    from app.research.statistics.confirmatory import run_full_analysis

    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario_id}")

    idem_key = req.idempotency_key or f"analysis-{req.scenario_id}-{req.seed}"

    db = await get_db()
    try:
        existing_spec = await (await db.execute(
            "SELECT id FROM analysis_specifications WHERE study_id = ? AND spec_type = 'confirmatory'",
            (idem_key,),
        )).fetchone()

        if existing_spec:
            spec_id = existing_spec["id"]
            existing_run = await (await db.execute(
                "SELECT id, status FROM analysis_runs WHERE spec_id = ?", (spec_id,),
            )).fetchone()
            if existing_run and existing_run["status"] == "completed":
                results = await (await db.execute(
                    "SELECT estimator_type, result_json FROM analysis_results WHERE run_id = ?",
                    (existing_run["id"],),
                )).fetchall()
                return {
                    "id": existing_run["id"], "status": "completed",
                    "results": {r["estimator_type"]: json.loads(r["result_json"]) for r in results},
                }
            if existing_run:
                return {"id": existing_run["id"], "status": existing_run["status"]}

        from app.research.statistics.confirmatory import GEE_FORMULA, MODEL_SPEC_VERSION, _spec_hash

        spec_cursor = await db.execute(
            """INSERT INTO analysis_specifications
               (study_id, spec_type, formula, estimand_id, model_version, spec_hash)
               VALUES (?, 'confirmatory', ?, 'ate_adaptive_vs_yoked', ?, ?)""",
            (idem_key, GEE_FORMULA, MODEL_SPEC_VERSION, _spec_hash(GEE_FORMULA)),
        )
        spec_id = spec_cursor.lastrowid

        run_cursor = await db.execute(
            """INSERT INTO analysis_runs (spec_id, status, started_at, seed, mode)
               VALUES (?, 'running', datetime('now'), ?, 'confirmatory')""",
            (spec_id, req.seed),
        )
        run_id = run_cursor.lastrowid
        await db.commit()
    finally:
        await db.close()

    try:
        imagery, _ = _generate_study_data(scenario, req.n_participants, 3, 5, req.seed)
        multi = run_full_analysis(imagery, seed=req.seed)

        db = await get_db()
        try:
            await db.execute(
                "UPDATE analysis_runs SET status = 'completed', completed_at = datetime('now') WHERE id = ?",
                (run_id,),
            )
            for est_type, est_result in [
                ("primary", multi.primary),
                ("hierarchical", multi.hierarchical),
                ("randomization", multi.randomization),
            ]:
                if est_result is None:
                    continue
                await db.execute(
                    """INSERT OR REPLACE INTO analysis_results
                       (run_id, estimator_type, effect_estimate, standard_error,
                        ci_lower, ci_upper, p_value, converged, is_fallback,
                        inference_valid, n_participants, n_trials, result_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, est_type, est_result.effect_estimate,
                     est_result.standard_error, est_result.ci_lower,
                     est_result.ci_upper, est_result.p_value,
                     int(est_result.converged), int(est_result.is_fallback),
                     int(est_result.inference_valid), est_result.n_participants,
                     est_result.n_trials, json.dumps(est_result.to_dict(), default=str)),
                )
            await db.commit()
        finally:
            await db.close()
    except Exception as e:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE analysis_runs SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), run_id),
            )
            await db.commit()
        finally:
            await db.close()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id": run_id, "status": "completed",
        "primary": multi.primary.to_dict(),
        "valid_inference": multi.valid_inference,
    }


@router.get("/analyses/{run_id}")
async def get_analysis(run_id: int):
    db = await get_db()
    try:
        row = await (await db.execute(
            "SELECT * FROM analysis_runs WHERE id = ?", (run_id,),
        )).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        response: dict = {"id": row["id"], "status": row["status"]}
        if row["status"] == "completed":
            results = await (await db.execute(
                "SELECT estimator_type, result_json FROM analysis_results WHERE run_id = ?",
                (run_id,),
            )).fetchall()
            response["results"] = {
                r["estimator_type"]: json.loads(r["result_json"]) for r in results
            }
        return response
    finally:
        await db.close()


@router.get("/endpoint-registry")
async def get_endpoint_registry():
    from app.research.objective_endpoints import ENDPOINT_REGISTRY, registry_hash
    return {
        "endpoints": {k: v.to_dict() for k, v in ENDPOINT_REGISTRY.items()},
        "hash": registry_hash(),
    }


@router.get("/oracles/{scenario_id}")
async def get_oracle(scenario_id: str):
    from app.research.causal_oracle import compute_full_oracle
    from app.research.cognitive_agent import SCENARIOS

    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")

    db = await get_db()
    try:
        existing = await (await db.execute(
            "SELECT * FROM oracle_estimands WHERE scenario_id = ? ORDER BY id DESC LIMIT 1",
            (scenario_id,),
        )).fetchone()
        if existing:
            all_contrasts = await (await db.execute(
                "SELECT * FROM oracle_estimands WHERE scenario_id = ? AND oracle_seed = ?",
                (scenario_id, existing["oracle_seed"]),
            )).fetchall()
            return {
                "scenario_id": scenario_id,
                "contrasts": {
                    r["contrast_id"]: {
                        "effect": r["oracle_effect"],
                        "se": r["oracle_se"],
                        "n_agents": r["n_agents"],
                    } for r in all_contrasts
                },
            }
    finally:
        await db.close()

    oracle = compute_full_oracle(scenario, n_agents=100, seed=99999)

    db = await get_db()
    try:
        for cid, contrast in oracle.contrasts.items():
            await db.execute(
                """INSERT INTO oracle_estimands
                   (scenario_id, contrast_id, oracle_effect, oracle_se,
                    n_agents, oracle_seed, oracle_version, endpoint_id, spec_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scenario_id, cid, contrast.effect, contrast.clustered_se,
                 contrast.n_agents, contrast.oracle_seed,
                 contrast.oracle_version, contrast.endpoint_id,
                 oracle.scenario_hash),
            )
        await db.commit()
    finally:
        await db.close()

    return oracle.to_dict()
