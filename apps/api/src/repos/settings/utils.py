from pymongo.results import UpdateResult
from src.database import Database
from src.schemas.core.common import Settings, Workspace
from src.schemas.repos import TemplateSettings
from src.utils.logging import logger


def get_settings(git_repo_id: int, workspace_name: str) -> Settings | None:
    if git_repo_id == -1:
        return TemplateSettings

    space_settings: dict | None = Database.get_workspace_property(
        git_repo_id, workspace_name, "settings"
    )

    if not space_settings:
        if "new-space" not in workspace_name:
            logger.warning(f"Workspace not found: {git_repo_id}, {workspace_name}")
        return None

    return Settings(**space_settings)


def update_settings(git_repo_id: int, workspace_name: str, settings: Settings) -> bool:
    return Database.update_workspace_property(
        git_repo_id, workspace_name, "settings", settings.model_dump()
    )


def get_runtime_files(git_repo_id: int) -> list[dict[str, str]] | None:
    """Returns list of dicts {file_path: str, content: str}"""
    return Database.get_repo_property(git_repo_id, "runtime_files")


def create_workspace(
    git_repo_id: int, workspace: Workspace, settings: Settings
) -> bool:
    result: UpdateResult = Database.repos_collection.update_one(
        {"git_repo_id": git_repo_id},
        {"$push": {"workspaces": workspace.model_dump()}},
    )

    if result.matched_count == 0:
        logger.warning(f"Repo not found: {git_repo_id}")
        return False

    return True
