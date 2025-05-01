from typing import TYPE_CHECKING

from src.repos.settings.utils import get_settings
from src.schemas.repos import Settings as RepoSettings
from src.schemas.repos import TemplateSettings

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Settings:
    def __init__(self, task: "Task"):
        self.task: "Task" = task

    async def get_saved_settings(self) -> RepoSettings | None:
        if self.task.git.repo_id == -1:
            return TemplateSettings

        return get_settings(self.task.git.repo_id, self.task.workspace.name)

    async def get_package_manager(self) -> str:
        repo_settings: RepoSettings = await self.get_saved_settings()
        return repo_settings.package_manager

    async def get_port(self) -> int | None:
        repo_settings: RepoSettings = await self.get_saved_settings()
        return repo_settings.port if repo_settings else None

    async def get_install_command(self) -> str:
        repo_settings: RepoSettings | None = await self.get_saved_settings()
        if not repo_settings.install_command:
            package_manager: str = await self.get_package_manager()
            return f"{package_manager} install"
        return repo_settings.install_command

    async def get_dev_command(self) -> str:
        repo_settings: RepoSettings = await self.get_saved_settings()
        if not repo_settings.dev_command:
            package_manager: str = await self.get_package_manager()
            return f"{package_manager} run dev"
        return repo_settings.dev_command

    async def get_build_command(self) -> str:
        package_manager: str = await self.get_package_manager()
        if package_manager == "npm":
            return "npm run build"
        elif package_manager == "yarn":
            return "yarn build"
        elif package_manager == "pnpm":
            return "pnpm run build"
        else:
            return f"{package_manager} run build"

    async def get_root_directory(self) -> str:
        repo_settings: RepoSettings = await self.get_saved_settings()
        if not repo_settings or not hasattr(repo_settings, "root_directory"):
            return "/"
        return repo_settings.root_directory

    async def get_current_branch(self) -> str:
        repo_settings: RepoSettings = await self.get_saved_settings()
        if not hasattr(repo_settings, "branch"):
            return "main"
        return repo_settings.branch

    async def get_tsconfig_path(self) -> str | None:
        repo_settings: RepoSettings = await self.get_saved_settings()
        if not repo_settings or not hasattr(repo_settings, "tsconfig_path"):
            return None
        return repo_settings.tsconfig_path
