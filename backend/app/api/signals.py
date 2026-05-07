from fastapi import APIRouter, HTTPException

from app.signals import get_provider, list_providers

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/providers")
async def providers():
    return [provider.metadata() | {"health": provider.health()} for provider in list_providers()]


@router.get("/providers/{provider_id}/health")
async def provider_health(provider_id: str):
    provider = get_provider(provider_id)
    if not provider:
        raise HTTPException(404, "Signal provider not found")
    return provider.health()
