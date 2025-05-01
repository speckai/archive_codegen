from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.account.security import verify_jwt_token
from src.database import Database
from src.github.utils import (
    get_installation_ids,
    get_installed_repos,
    get_repo_data_from_id,
)
from src.redis_manager import RedisManager
from src.schemas.account import User
from src.schemas.core.common import AddedRepository, RunningTaskProgress
from src.task_manager import TaskManager
from src.utils.logging import logger

router: APIRouter = APIRouter(prefix="/entries")


class TaskStatus(BaseModel):
    task_id: str
    git_repo_id: int
    owner: dict
    title: str
    workspace_name: str
    repo_name: str
    last_action_time_unix: int
    task_status: RunningTaskProgress
    pr_number: int | None
    issue_number: int | None
    issue_closed: bool | None


def _get_added_repos_objs(user_id: str) -> list[AddedRepository] | None:
    added_repo_ids: list[int] = Database.get_user_property(user_id, "added_repos")
    if not added_repo_ids:
        return None

    added_repo_objs: list[AddedRepository] = [
        Database.get_repo(repo_id) for repo_id in added_repo_ids
    ]
    added_repo_objs = [
        repo for repo in added_repo_objs if repo is not None
    ]  # For removing nones
    if len(added_repo_objs) != len(added_repo_ids):
        logger.warning(f"Some repos are missing: {added_repo_ids}")
    return added_repo_objs


@router.get("/installations/get")
async def get_installations(user: User = Depends(verify_jwt_token)):
    return {"success": True, "installations": get_installation_ids(user.id)}


@router.get("/installed/get")
async def get_repos(user: User = Depends(verify_jwt_token)) -> dict[str, Any]:
    repos: dict[str, list[dict[str, str | int]] | list[str]] = get_installed_repos(
        user.id
    )
    installed_repos: list[dict[str, str | int]] = repos.get("installed_repos", [])
    failed_installations: list[str] = repos.get("failed_installations", [])
    existing_repos: list[str] = repos.get("existing_repos", [])

    if not installed_repos:
        return {"success": False, "status": "NO_INSTALLATION_ID"}

    return {
        "success": True,
        "installed_repos": installed_repos,
        "failed_installations": failed_installations,
        "existing_repos": existing_repos,
    }


@router.get("/added/get")
async def get_added_repos(user: User = Depends(verify_jwt_token)) -> dict[str, Any]:
    user_data: dict[str, any] = Database.users_collection.find_one({"id": user.id})
    if not user_data:
        return {"success": False, "message": "User not found"}

    github_installations: list[int] = user_data.get("github_installations", [])
    if not github_installations:
        return {"success": False, "status": "NO_INSTALLATION_ID"}

    added_repos: list[AddedRepository] | None = _get_added_repos_objs(user.id)
    if added_repos is None:
        return {"success": False, "message": "NO_REPOS_FOUND"}
    return {"success": True, "added_repos": added_repos}


@router.post("/workspace/create_task")
async def open_added_repo(body: dict[str, Any], user: User = Depends(verify_jwt_token)):
    git_repo_id: str = body.get("git_repo_id")
    workspace_name: str = body.get("workspace_name")
    issue_number: str | None = body.get("issue_number")

    if not (git_repo_id and workspace_name):
        return {"success": False, "message": "Missing required fields"}

    task_id: str = await RedisManager.request_task_id(
        git_repo_id, workspace_name, issue_number
    )
    return {"success": True, "task_id": task_id}


@router.post("/added/add")
async def add_repo(body: dict[str, Any], user: User = Depends(verify_jwt_token)):
    repo_ids: list[str] = body.get("git_repo_ids", [])

    repos_to_add: list[int] = []
    for repo_id in repo_ids:
        found_repo: AddedRepository | None = Database.get_repo(repo_id)
        if found_repo is None:
            repos_to_add.append(repo_id)

    repos_to_insert: list[AddedRepository] = []
    for repo_id in repos_to_add:
        repo_data: dict | None = await get_repo_data_from_id(repo_id, user.id)
        if repo_data is None:
            continue

        repo: AddedRepository = AddedRepository(
            git_repo_id=repo_id,
            name=repo_data["name"],
            full_name=repo_data["full_name"],
            url=repo_data["url"],
            visibility=repo_data["visibility"],
            owner=repo_data["owner"],
            last_opened_unix=int(datetime.now().timestamp()),
            runtime_files=[],
            browser_storage=None,
            workspaces=[],
            tasks=[],
        )
        repos_to_insert.append(repo)

    if repos_to_insert:
        Database.repos_collection.insert_many(
            [repo.model_dump() for repo in repos_to_insert]
        )
    Database.users_collection.update_one(
        {"id": user.id},
        {"$addToSet": {"added_repos": {"$each": repo_ids}}},  # TODO: Make more robust
    )

    return {
        "success": True,
        "message": "Repos added successfully",
        "added_repos": _get_added_repos_objs(user.id),
    }


@router.post("/added/remove")
async def remove_repo(body: dict[str, Any], user: User = Depends(verify_jwt_token)):
    git_repo_id: str = body.get("git_repo_id")

    result = Database.users_collection.update_one(
        {"id": user.id}, {"$pull": {"added_repos": git_repo_id}}
    )

    removed: bool = result.modified_count > 0

    return {
        "success": removed,
        "message": "Repo removed successfully" if removed else "Repo not found",
        "added_repos": _get_added_repos_objs(user.id),
    }


@router.get("/tasks/get")
async def get_tasks(user: User = Depends(verify_jwt_token)) -> dict[str, Any]:
    added_repos: list[AddedRepository] | None = _get_added_repos_objs(user.id)
    if not added_repos:
        return {"success": True, "message": "No repos added", "tasks": []}

    task_statuses: list[TaskStatus] = []
    for repo in added_repos:
        if not repo:
            continue
        for task in repo.tasks:
            task_statuses.append(
                TaskStatus(
                    task_id=task.task_id,
                    git_repo_id=repo.git_repo_id,
                    owner=repo.owner,
                    title=task.summary,
                    workspace_name=task.workspace_name,
                    repo_name=repo.name,
                    last_action_time_unix=task.last_updated_unix,
                    task_status=task.task_progress,
                    pr_number=task.pr_number,
                    issue_number=task.issue_number,
                    issue_closed=task.issue_closed,
                )
            )

    return {"success": True, "tasks": task_statuses}


@router.get("/tasks/remove/{git_repo_id}/{task_id}")
async def remove_task(
    git_repo_id: int, task_id: str, user: User = Depends(verify_jwt_token)
) -> dict[str, Any]:
    await TaskManager.delete_task(task_id)

    repo: AddedRepository | None = Database.get_repo(git_repo_id)
    if not repo:
        return {"success": False, "message": "Repo not found"}

    Database.repos_collection.update_one(
        {"git_repo_id": git_repo_id},
        {"$pull": {"tasks": {"task_id": task_id}}},
    )
    return {"success": True}
