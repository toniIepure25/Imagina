from fastapi import APIRouter, HTTPException

from app.schemas.profile import ImageryProfile, UserProfileCreate
from app.services import personalization_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/local", response_model=ImageryProfile)
async def create_local(data: UserProfileCreate | None = None):
    return await personalization_service.create_local_profile(data or UserProfileCreate())


@router.get("/{user_id}/profile", response_model=ImageryProfile)
async def profile(user_id: str):
    result = await personalization_service.get_profile(user_id)
    if not result:
        raise HTTPException(404, "Profile not found")
    return result


@router.get("/{user_id}/progress")
async def progress(user_id: str):
    profile = await personalization_service.get_profile(user_id)
    rec = await personalization_service.recommendation(user_id)
    if not profile or not rec:
        raise HTTPException(404, "Profile not found")
    return {"profile": profile.model_dump(mode="json"), "recommendation": rec.model_dump(mode="json")}


@router.get("/{user_id}/longitudinal-report")
async def longitudinal_report(user_id: str):
    result = await personalization_service.longitudinal_report(user_id)
    if not result:
        raise HTTPException(404, "Profile not found")
    return result


@router.post("/{user_id}/reset-progress", response_model=ImageryProfile)
async def reset(user_id: str):
    result = await personalization_service.reset_progress(user_id)
    if not result:
        raise HTTPException(404, "Profile not found")
    return result
