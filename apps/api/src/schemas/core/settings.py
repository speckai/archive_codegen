from typing import Literal

from pydantic import BaseModel, Field


class AnnotatedSettings(BaseModel):
    package_manager: Literal["npm", "yarn", "pnpm", "bun"]
    port: int = Field(
        ...,
        description="The port to run the site on, based on the package manager and parameters.",
    )
    install_command: str = Field(
        ...,
        description="The command to install the dependencies, in terms of the package manager. Typically `{package_manager} install`.",
    )
    dev_command: str = Field(
        ...,
        description="The command to run the site, in terms of the package manager, like `{package_manager} run ...`",
    )
    tsconfig_path: str | None = Field(
        None,
        description="The path to the tsconfig.json file, if known. If null, it will be automatically determined.",
    )

    def xml(self) -> str:
        tsconfig_xml = (
            f"<tsconfig_path>{self.tsconfig_path}</tsconfig_path>"
            if self.tsconfig_path
            else "<tsconfig_path>None</tsconfig_path>"
        )

        return f"""
        <settings>
            <package_manager>{self.package_manager}</package_manager>
            <port>{self.port}</port>
            <install_command>{self.install_command}</install_command>
            <dev_command>{self.dev_command}</dev_command>
            {tsconfig_xml}
        </settings>
        """


class SettingsDetectionResponse(BaseModel):
    thinking: str = Field(
        ...,
        description="Concise chain of thought analysis of the files and thought process to extract the settings.",
    )
    package_manager: Literal["npm", "yarn", "pnpm", "bun"]
    port: int = Field(
        ...,
        description="The port to run the site on, based on the package manager and parameters.",
    )
    install_command: str = Field(
        ...,
        description="The command to install the dependencies, in terms of the package manager. Typically `{package_manager} install`.",
    )
    dev_command: str = Field(
        ...,
        description="The command to run the site, in terms of the package manager, like `{package_manager} run ...`. Must be a SINGLE specific command, not multiple alternatives separated by ||.",
    )
    tsconfig_path: str | None = Field(
        None,
        description="The path to the tsconfig.json file, if found. Include the full path from the root directory.",
    )

    def xml(self, attempt_number: int) -> str:
        tsconfig_xml = (
            f"<tsconfig_path>{self.tsconfig_path}</tsconfig_path>"
            if self.tsconfig_path
            else "<tsconfig_path>None</tsconfig_path>"
        )

        return f"""
        <settings_detection_response attempt="{attempt_number}">
            <thinking>{self.thinking}</thinking>
            <settings>
                <package_manager>{self.package_manager}</package_manager>
                <port>{self.port}</port>
                <install_command>{self.install_command}</install_command>
                <dev_command>{self.dev_command}</dev_command>
                {tsconfig_xml}
            </settings>
        </settings_detection_response>
        """


class SettingsUpdateResponse(BaseModel):
    analysis: str = Field(
        ...,
        description="Detailed analysis of what went wrong and why the suggested changes might fix it.",
    )
    package_manager: Literal["npm", "yarn", "pnpm", "bun"]
    port: int = Field(
        ...,
        description="The port to run the site on, based on the package manager and parameters.",
    )
    install_command: str = Field(
        ...,
        description="The command to install the dependencies, in terms of the package manager. Typically `{package_manager} install`.",
    )
    dev_command: str = Field(
        ...,
        description="The command to run the site, in terms of the package manager, like `{package_manager} run ...`. Must be a SINGLE specific command, not multiple alternatives separated by ||.",
    )
    tsconfig_path: str | None = Field(
        None,
        description="The path to the tsconfig.json file, if found. Include the full path from the root directory.",
    )

    def xml(self, attempt_number: int) -> str:
        tsconfig_xml = (
            f"<tsconfig_path>{self.tsconfig_path}</tsconfig_path>"
            if self.tsconfig_path
            else "<tsconfig_path>None</tsconfig_path>"
        )

        return f"""
        <settings_update_response attempt="{attempt_number}">
            <analysis>{self.analysis}</analysis>
            <settings>
                <package_manager>{self.package_manager}</package_manager>
                <port>{self.port}</port>
                <install_command>{self.install_command}</install_command>
                <dev_command>{self.dev_command}</dev_command>
                {tsconfig_xml}
            </settings>
        </settings_update_response>
        """


class RepoDetectionResponse(BaseModel):
    thinking: str = Field(
        ...,
        description="Concise chain of thought analysis of the files and thought process to detect if this is a monorepo.",
    )
    is_monorepo: bool = Field(
        ...,
        description="Whether the website is a monorepo or not.",
    )
    monorepo_apps: list[str] | None = Field(
        None,
        description="If the website is a monorepo, paths to all valid React websites in the monorepo. No servers, docs, packages or other non-React apps.",
    )

    def xml(self) -> str:
        apps_xml = (
            f"<monorepo_apps>{','.join(self.monorepo_apps)}</monorepo_apps>"
            if self.monorepo_apps
            else "<monorepo_apps>None</monorepo_apps>"
        )

        return f"""
        <repo_detection_response>
            <thinking>{self.thinking}</thinking>
            <is_monorepo>{self.is_monorepo}</is_monorepo>
            {apps_xml}
        </repo_detection_response>
        """


class PrivateWebsiteUpdateCommandResponse(BaseModel):
    package_manager: Literal["npm", "yarn", "pnpm", "bun"]
    thoughts_about_package_manager_syntax: str = Field(
        ...,
        description="Thoughts about the syntax of the package manager, like if it's correct, or if you need to add -- or not, etc",
    )
    how_to_fix: str = Field(
        ...,
        description="How to fix the website so that it is exposed publicly. (concise)",
    )
    rationale: str = Field(
        ...,
        description="Rationale for the changes made to the dev command. No longer than 7 words, and understandable by a non-technical person.",
    )
    dev_command: str = Field(
        ...,
        description="The new dev command to run the website in terms of the package manager, like `{package_manager} run ...`",
    )
