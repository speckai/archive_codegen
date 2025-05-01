from typing import Optional

from pydantic import BaseModel
from src.schemas.account import User
from src.schemas.repos import Settings


class DebugSettings(BaseModel):
    user: User
    created_repo_id: str
    package_manager: str = "npm"
    port: int = 3000
    install_command: Optional[str] = None
    dev_command: Optional[str] = None
    root_directory: str = "apps/web"
    tsconfig_path: Optional[str] = None
    # Caching attributes
    skip_install: bool = False
    cached_node_modules_path: Optional[str] = None

    async def get_saved_settings(self) -> Settings | None:
        if self.package_manager and self.port and self.root_directory:
            return Settings(
                package_manager=self.package_manager,
                port=self.port,
                install_command=self.install_command,
                dev_command=self.dev_command,
                root_directory=self.root_directory,
                branch="main",
                tsconfig_path=self.tsconfig_path,
            )

    async def get_package_manager(self) -> str:
        return self.package_manager

    async def get_port(self) -> int:
        return self.port

    async def get_install_command(self) -> str:
        if not self.install_command:
            return f"{self.package_manager} install"
        return self.install_command

    async def get_dev_command(self) -> str:
        if not self.dev_command:
            return f"{self.package_manager} run dev"
        return self.dev_command

    async def get_build_command(self) -> str:
        if self.package_manager == "npm":
            return "npm run build"
        elif self.package_manager == "yarn":
            return "yarn build"
        elif self.package_manager == "pnpm":
            return "pnpm run build"
        else:
            return f"{self.package_manager} run build"

    async def get_root_directory(self) -> str:
        return self.root_directory

    async def get_tsconfig_path(self) -> str | None:
        return self.tsconfig_path
