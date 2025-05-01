from typing import Any

from fastapi import APIRouter, Depends
from src.account.security import verify_jwt_token
from src.database import Database
from src.repos.entries.router import router as entries_router
from src.repos.settings.router import router as settings_router
from src.schemas.account import User
from src.task_manager import Task, TaskManager
from src.utils.logging import logger

router: APIRouter = APIRouter(prefix="/repos")
router.include_router(entries_router)
router.include_router(settings_router)


@router.post("/website-data")
async def save_website_data(
    body: dict[str, Any], user: User = Depends(verify_jwt_token)
):
    storage_state: str = body.get("state")
    task_id: str = body.get("task_id")

    task: Task | None = TaskManager.get_task_from_id(task_id)
    if not task:
        logger.warning("Task not found for browser")
        return {"success": False, "message": "Task not found"}

    browser_storage: dict[str, str] = {
        "cookies": storage_state.get("cookies"),
        "local_storage": storage_state.get("localStorage"),
        "session_storage": storage_state.get("sessionStorage"),
    }

    Database.update_repo_property(task.git.repo_id, "browser_storage", browser_storage)

    return {"success": True}
