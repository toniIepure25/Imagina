"""Local-first Imagine lab API. Diffusion fails closed until a worker is configured."""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse, Response

from app.core.config import settings
from app.core.imagine.providers import DiffusionUnavailable, ProviderError, RemoteDiffusionProvider
from app.core.imagine.service import ArtifactNotFound, ImagineService, JobConflict, JobNotFound
from app.core.imagine.store import ImagineStore, ImagineStoreError
from app.schemas.imagine import (
    ImagineCapabilities,
    ImagineError,
    ImagineJobList,
    ImagineJobPublic,
    ImagineJobRequest,
)

router = APIRouter(prefix="/animus/imagine", tags=["imagine"])

imagine_service = ImagineService(
    ImagineStore(settings.imagine_data_dir),
    RemoteDiffusionProvider(
        base_url=settings.imagine_diffusion_url,
        token=settings.imagine_diffusion_token,
        enabled=settings.imagine_enable_remote_diffusion,
        timeout_seconds=settings.imagine_diffusion_timeout_seconds,
    ),
)


def _error(status: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ImagineError(code=code, message=message, retryable=retryable).model_dump(),
    )


@router.get("/capabilities", response_model=ImagineCapabilities)
async def capabilities() -> dict:
    return await imagine_service.capabilities()


@router.post("/jobs", response_model=ImagineJobPublic, status_code=202)
async def create_job(request: ImagineJobRequest):
    try:
        return await imagine_service.create_job(request.model_dump())
    except DiffusionUnavailable as exc:
        return _error(503, "diffusion_unavailable", exc.reason, True)
    except ProviderError as exc:
        return _error(502, exc.code, exc.message, exc.retryable)
    except ImagineStoreError:
        return _error(503, "local_store_unavailable", "The local Imagine store is unavailable.", True)


@router.get("/jobs", response_model=ImagineJobList)
async def list_jobs(limit: int = Query(default=10, ge=1, le=50)):
    return {"jobs": imagine_service.list_jobs(limit)}


@router.get("/jobs/{job_id}", response_model=ImagineJobPublic)
async def get_job(job_id: str):
    try:
        return await imagine_service.get_job(job_id)
    except JobNotFound:
        return _error(404, "job_not_found", "Unknown Imagine job.")
    except ProviderError as exc:
        return _error(502, exc.code, exc.message, exc.retryable)


@router.post("/jobs/{job_id}/cancel", response_model=ImagineJobPublic)
async def cancel_job(job_id: str):
    try:
        return await imagine_service.cancel_job(job_id)
    except JobNotFound:
        return _error(404, "job_not_found", "Unknown Imagine job.")
    except JobConflict as exc:
        return _error(409, "job_not_cancellable", str(exc))


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str):
    try:
        imagine_service.delete_job(job_id)
        return Response(status_code=204)
    except JobNotFound:
        return _error(404, "job_not_found", "Unknown Imagine job.")
    except JobConflict as exc:
        return _error(409, "job_not_terminal", str(exc))


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str):
    try:
        path, media_type = imagine_service.asset(asset_id)
    except ArtifactNotFound:
        return _error(404, "artifact_not_found", "Unknown or expired artifact.")
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=3600, immutable",
            "ETag": f'"{asset_id}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
