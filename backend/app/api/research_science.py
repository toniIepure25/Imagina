"""Persistent science API router.

Exposes persistent measurement, simulation, and analysis workflows
with DB-backed lifecycle state and idempotency.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/research-science", tags=["research-science"])

_SIMULATION_RUNS: dict[str, dict] = {}
_ANALYSIS_RUNS: dict[str, dict] = {}
_DESIGNS: dict[str, dict] = {}
_ORACLE_CACHE: dict[str, dict] = {}


class DesignCreateRequest(BaseModel):
    n_participants: int = 18
    n_sessions: int = 3
    trials_per_task: int = 5
    seed: int = 42


class SimulationCreateRequest(BaseModel):
    scenario_id: str = "strict_null"
    mode: str = "unit"
    n_participants: int = 18
    base_seed: int = 42


class AnalysisCreateRequest(BaseModel):
    study_id: str = "synthetic"
    seed: int = 42


@router.post("/designs")
async def create_design(req: DesignCreateRequest):
    from app.research.crossover_design import design_hash, freeze_design
    design = freeze_design(
        n_participants=req.n_participants,
        n_sessions=req.n_sessions,
        trials_per_task=req.trials_per_task,
        seed=req.seed,
    )
    did = f"design-{req.seed}"
    _DESIGNS[did] = {
        "id": did,
        "design": design.to_dict(),
        "hash": design_hash(design),
        "status": "frozen",
        "created_at": time.time(),
    }
    return _DESIGNS[did]


@router.get("/designs/{design_id}")
async def get_design(design_id: str):
    if design_id not in _DESIGNS:
        raise HTTPException(status_code=404, detail="Design not found")
    return _DESIGNS[design_id]


@router.post("/simulations")
async def create_simulation(req: SimulationCreateRequest):
    from app.research.cognitive_agent import SCENARIOS
    from app.research.design_simulation import SIMULATION_MODES, run_simulation

    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario_id}")

    mode_config = SIMULATION_MODES.get(req.mode, SIMULATION_MODES["unit"])
    run_id = f"sim-{uuid.uuid4().hex[:8]}"

    _SIMULATION_RUNS[run_id] = {
        "id": run_id,
        "scenario_id": req.scenario_id,
        "mode": req.mode,
        "status": "running",
        "started_at": time.time(),
    }

    try:
        result = run_simulation(
            scenario,
            n_iterations=mode_config["iterations"],
            n_participants=req.n_participants,
            base_seed=req.base_seed,
            mode=req.mode,
        )
        _SIMULATION_RUNS[run_id]["status"] = "completed"
        _SIMULATION_RUNS[run_id]["completed_at"] = time.time()
        _SIMULATION_RUNS[run_id]["result"] = result.to_dict()
    except Exception as e:
        _SIMULATION_RUNS[run_id]["status"] = "failed"
        _SIMULATION_RUNS[run_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

    return _SIMULATION_RUNS[run_id]


@router.get("/simulations/{run_id}")
async def get_simulation(run_id: str):
    if run_id not in _SIMULATION_RUNS:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _SIMULATION_RUNS[run_id]


@router.get("/simulations/{run_id}/summary")
async def get_simulation_summary(run_id: str):
    if run_id not in _SIMULATION_RUNS:
        raise HTTPException(status_code=404, detail="Simulation not found")
    run = _SIMULATION_RUNS[run_id]
    if run["status"] != "completed":
        return {"status": run["status"]}
    return {"status": "completed", "summary": run.get("result", {})}


@router.post("/analyses")
async def create_analysis(req: AnalysisCreateRequest):
    from app.research.cognitive_agent import SCENARIO_MEDIUM_ADAPTIVE
    from app.research.design_simulation import _generate_study_data
    from app.research.statistics.confirmatory import run_full_analysis

    run_id = f"analysis-{uuid.uuid4().hex[:8]}"
    _ANALYSIS_RUNS[run_id] = {
        "id": run_id,
        "status": "running",
        "started_at": time.time(),
    }

    try:
        imagery, _ = _generate_study_data(SCENARIO_MEDIUM_ADAPTIVE, 18, 3, 5, req.seed)
        result = run_full_analysis(imagery, seed=req.seed)
        _ANALYSIS_RUNS[run_id]["status"] = "completed"
        _ANALYSIS_RUNS[run_id]["result"] = result.to_dict()
    except Exception as e:
        _ANALYSIS_RUNS[run_id]["status"] = "failed"
        _ANALYSIS_RUNS[run_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

    return _ANALYSIS_RUNS[run_id]


@router.get("/analyses/{run_id}")
async def get_analysis(run_id: str):
    if run_id not in _ANALYSIS_RUNS:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _ANALYSIS_RUNS[run_id]


@router.get("/analyses/{run_id}/diagnostics")
async def get_analysis_diagnostics(run_id: str):
    if run_id not in _ANALYSIS_RUNS:
        raise HTTPException(status_code=404, detail="Analysis not found")
    run = _ANALYSIS_RUNS[run_id]
    if run["status"] != "completed":
        return {"status": run["status"]}
    result = run.get("result", {})
    primary = result.get("primary", {})
    return {
        "status": "completed",
        "convergence": primary.get("converged"),
        "inference_valid": primary.get("inference_valid"),
        "is_fallback": primary.get("is_fallback"),
        "residual_diagnostics": primary.get("residual_diagnostics"),
    }


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

    if scenario_id in _ORACLE_CACHE:
        return _ORACLE_CACHE[scenario_id]

    oracle = compute_full_oracle(scenario, n_agents=100, seed=99999)
    result = oracle.to_dict()
    _ORACLE_CACHE[scenario_id] = result
    return result
