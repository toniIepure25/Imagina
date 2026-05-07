from fastapi import APIRouter

from app.schemas.task import ImageryTask
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[ImageryTask])
async def list_tasks():
    return task_service.list_tasks()
