from src.database import Database
from src.schemas.core.common import Workspace, WorkspaceType
from src.schemas.repos import TemplateSettings


def get_workspace(git_repo_id: int, workspace_name: str) -> Workspace | None:
    if workspace_name == "new-space":
        return Workspace(name=workspace_name, settings=None, type=WorkspaceType.NEW)

    if git_repo_id == -1:
        return Workspace(
            name=workspace_name, settings=TemplateSettings, type=WorkspaceType.EXISTING
        )

    raw_workspaces: list[dict] = Database.get_repo_property(git_repo_id, "workspaces")
    workspaces: list[Workspace] = [
        Workspace(**workspace) for workspace in raw_workspaces
    ]
    workspace: Workspace | None = next(
        (workspace for workspace in workspaces if workspace.name == workspace_name),
        None,
    )

    return workspace
