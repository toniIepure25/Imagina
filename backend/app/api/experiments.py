from fastapi import APIRouter, HTTPException

from app.schemas.experiments import ExperimentRun, ExperimentRunCreate, ExperimentSessionAttach
from app.services import experiment_service

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("/protocols")
async def protocols():
    return [p.model_dump(mode="json") for p in experiment_service.list_protocols()]


@router.post("/runs", response_model=ExperimentRun)
async def create_run(data: ExperimentRunCreate):
    try:
        return await experiment_service.create_run(data)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/runs/{run_id}", response_model=ExperimentRun)
async def get_run(run_id: str):
    run = await experiment_service.get_run(run_id)
    if not run:
        raise HTTPException(404, "Experiment run not found")
    return run


@router.post("/runs/{run_id}/next-session")
async def next_session(run_id: str, user_id: str | None = None):
    session = await experiment_service.next_session(run_id, user_id=user_id)
    if not session:
        raise HTTPException(404, "Experiment run not found or no planned sessions remain")
    return session


@router.post("/runs/{run_id}/attach-session", response_model=ExperimentRun)
async def attach_session(run_id: str, data: ExperimentSessionAttach):
    run = await experiment_service.attach_session(run_id, data.session_id, completed=data.completed)
    if not run:
        raise HTTPException(404, "Experiment run not found")
    return run


@router.get("/runs/{run_id}/progress")
async def progress(run_id: str):
    data = await experiment_service.run_progress(run_id)
    if not data:
        raise HTTPException(404, "Experiment run not found")
    return data


@router.post("/runs/{run_id}/complete", response_model=ExperimentRun)
async def complete(run_id: str):
    run = await experiment_service.complete_run(run_id)
    if not run:
        raise HTTPException(404, "Experiment run not found")
    return run


@router.get("/runs/{run_id}/summary")
async def summary(run_id: str):
    data = await experiment_service.run_summary(run_id)
    if not data:
        raise HTTPException(404, "Experiment run not found")
    return data
