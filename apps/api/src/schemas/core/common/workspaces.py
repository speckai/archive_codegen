from enum import StrEnum

from pydantic import BaseModel
from src.agents.utils.task.debug.settings import DebugSettings
from src.schemas.core.common import SerializedTask
from src.schemas.repos import Settings


class WorkspaceType(StrEnum):
    EXISTING = "existing"
    NEW = "new"


class Workspace(BaseModel):
    name: str
    settings: DebugSettings | Settings | None = None
    type: WorkspaceType


class BrowserStorage(BaseModel):
    cookies: dict[str, str]
    local_storage: dict[str, str]
    session_storage: dict[str, str]


class AddedRepository(BaseModel):
    git_repo_id: int
    name: str
    full_name: str
    url: str
    visibility: str
    owner: dict
    last_opened_unix: int
    runtime_files: list[dict[str, str]]
    browser_storage: BrowserStorage | None
    workspaces: list[Workspace]
    tasks: list[SerializedTask]


class PopulatedWorkspace(BaseModel):
    git_repo_id: int
    workspace_name: str
    repo_name: str
    repo_full_name: str
    repo_url: str
    visibility: str
    owner: dict[str, str | int]
    settings: Settings | None = None
    runtime_files: list[dict[str, str]] | None
    browser_storage: BrowserStorage | None
    issue_number: int | None = None
