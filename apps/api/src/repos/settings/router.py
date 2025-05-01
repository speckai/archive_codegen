from typing import Any

from fastapi import APIRouter, Depends
from src.account.security import verify_jwt_token
from src.agents.utils.task.task import Task
from src.database import Database
from src.repos.settings.utils import get_runtime_files, get_settings, update_settings
from src.schemas.account import User
from src.schemas.repos import Settings
from src.task_manager import TaskManager
from src.utils.logging import logger

router: APIRouter = APIRouter(prefix="/settings")


@router.get("/get/{task_id}")
async def get_repo_settings_route(task_id: str, user: User = Depends(verify_jwt_token)):
    task: Task | None = TaskManager.get_task_from_id(task_id)
    if not task:
        return {"success": False, "message": "Task not found"}

    git_repo_id: int = task.git.repo_id
    workspace_name: str = task.workspace.name

    repo_settings: Settings | None = get_settings(git_repo_id, workspace_name)
    if not repo_settings:
        return {"success": False, "message": "Repo settings not found"}

    repo_settings_dict: dict[str, any] = repo_settings.model_dump()
    repo_settings_dict["available_branches"] = await task.git.get_branch_names()
    repo_settings_dict["workspace_name"] = workspace_name

    return {"success": True, "settings": repo_settings_dict}


@router.post("/save")
async def save_repo_settings(
    body: dict[str, Any], user: User = Depends(verify_jwt_token)
):
    git_repo_id: int = body.get("git_repo_id")
    workspace_name: str = body.get("workspace_name")
    repo_settings_dict: dict[str, any] = body.get("repo_settings")
    new_workspace_name: str | None = body.get("new_workspace_name")

    required_keys: set[str] = {
        "package_manager",
        "port",
        "install_command",
        "dev_command",
        "root_directory",
        "branch",
    }
    if not required_keys.issubset(repo_settings_dict):
        logger.warning(f"Missing required keys in repo settings: {repo_settings_dict}")
        return {"success": False, "message": "Missing required keys in repo settings"}

    if new_workspace_name:
        Database.update_workspace_property(
            git_repo_id, workspace_name, "workspace_name", new_workspace_name
        )

    repo_settings: Settings = Settings.model_validate(repo_settings_dict)
    is_updated: bool = update_settings(git_repo_id, workspace_name, repo_settings)

    return {"success": is_updated}


@router.post("/runtime_files/save")
async def save_runtime_files(
    body: dict[str, Any], user: User = Depends(verify_jwt_token)
):
    git_repo_id: int = body.get("git_repo_id")
    workspace_name: str = body.get("workspace_name")
    runtime_files: list[dict[str, str]] = body.get("runtime_files")

    if not git_repo_id or not workspace_name or not isinstance(runtime_files, list):
        return {"success": False, "message": "Missing required data"}

    result = Database.repos_collection.update_one(
        {
            "git_repo_id": git_repo_id,
            "workspaces": {"$elemMatch": {"name": workspace_name}},
        },
        {"$set": {"workspaces.$.runtime_files": runtime_files}},
    )

    if result.modified_count > 0:
        return {"success": True, "message": "Runtime files saved successfully"}
    else:
        return {"success": False, "message": "No changes were made"}


@router.get("/runtime_files/get/{git_repo_id}")
async def get_runtime_files_route(
    git_repo_id: int, user: User = Depends(verify_jwt_token)
):
    runtime_files: list[dict[str, str]] | None = get_runtime_files(git_repo_id)
    if runtime_files is None:
        return {"success": False, "message": "Runtime files not found"}

    return {"success": True, "runtime_files": runtime_files}


@router.get("/custom_rules/user/get")
async def get_custom_rules_user(user: User = Depends(verify_jwt_token)):
    user_data: dict[str, any] = Database.users_collection.find_one({"id": user.id})
    if not user_data:
        return {"success": False, "message": "User not found"}

    custom_rules: str = user_data.get("custom_rules", "")

    return {"success": True, "rules": custom_rules}


@router.post("/custom_rules/user/save")
async def save_custom_rules_user(
    body: dict[str, Any], user: User = Depends(verify_jwt_token)
):
    custom_rules: str = body.get("rules")
    Database.update_user_property(user.id, "custom_rules", custom_rules)
    return {"success": True, "message": "Custom rules saved successfully"}


# TODO: SAVE THESE TO SPACES
@router.get("/custom_rules/repo/get/{git_repo_id}")
async def get_custom_rules_repo(
    git_repo_id: int, user: User = Depends(verify_jwt_token)
):
    custom_rules: str = Database.get_repo_property(git_repo_id, "custom_rules")

    return {"success": True, "rules": custom_rules}


@router.post("/custom_rules/repo/save")
async def save_custom_rules_repo(
    body: dict[str, Any], user: User = Depends(verify_jwt_token)
):
    git_repo_id: int = body.get("git_repo_id")
    custom_rules: str = body.get("rules")

    Database.update_repo_property(git_repo_id, "custom_rules", custom_rules)

    return {"success": True, "message": "Custom rules saved successfully"}
