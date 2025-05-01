from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    package_manager: Literal["npm", "yarn", "pnpm", "bun"]
    port: int
    install_command: str
    dev_command: str
    root_directory: str
    branch: str
    tsconfig_path: str | None = None


class PartialSettings(BaseModel):
    package_manager: Literal["npm", "yarn", "pnpm", "bun"] | None = None
    port: int | None = None
    install_command: str | None = None
    dev_command: str | None = None
    root_directory: str | None = None
    branch: str | None = None
    tsconfig_path: str | None = None


TemplateSettings: Settings = Settings(
    package_manager="bun",
    port=3000,
    install_command="bun install",
    dev_command="bun run dev",
    root_directory="/",
    branch="main",
)


class TemplateRepoOptions(StrEnum):
    NEXTJS_CHAKRA_TEMPLATE = "nextjs-chakra-ui"
    NEXTJS_TAILWIND_TEMPLATE = "nextjs-tailwind-css"
    NEXTJS_SHADCN_TEMPLATE = "nextjs-shadcn"


class TemplateRepoOptionsResponse(BaseModel):
    template_repo_option: TemplateRepoOptions
