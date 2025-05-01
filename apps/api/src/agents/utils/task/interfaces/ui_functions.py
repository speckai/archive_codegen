from typing import TYPE_CHECKING, Callable

from src.schemas.core.common import MessageType

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class UIFunctions:
    def __init__(self, task: "Task"):
        self.task: Task = task

    async def refresh_page(self) -> None:
        await self.task.send_update_data(MessageType.REFRESH_PAGE, {})

    async def show_editor_tab(self, file_path: str | None = None) -> None:
        """Show the editor for the given file path, if no file path then it'll show the last modified file"""
        await self.task.send_update_data(
            MessageType.SHOW_EDITOR, {"file_path": file_path}
        )

    async def show_workspace_tab(self) -> None:
        await self.task.send_update_data(MessageType.SHOW_WORKSPACE, {})

    async def show_bug_report_tab(self) -> None:
        await self.task.send_update_data(MessageType.SHOW_BUG_REPORT, {})

    async def expand_sidebar(self) -> None:
        await self.task.send_update_data(MessageType.EXPAND_SIDEBAR, {})

    async def show_issue_tab(self) -> None:
        await self.task.send_update_data(MessageType.SHOW_ISSUE, {})

    async def show_git_panel(self) -> None:
        await self.task.send_update_data(
            MessageType.SHOW_GIT_PANEL,
            {},
        )

    async def show_settings_panel(self) -> None:
        await self.task.send_update_data(
            MessageType.SHOW_SETTINGS_PANEL,
            {},
        )

    async def show_env_files_panel(self) -> None:
        await self.task.send_update_data(
            MessageType.SHOW_ENV_FILES_PANEL,
            {},
        )

    async def show_terminal_window(self):
        fn: Callable[[str], None] = self.task.send_update_data
        if hasattr(self.task, "current_workflow") and self.task.current_workflow:
            fn = self.task.current_workflow.send_update_data

        await fn(
            MessageType.SHOW_TERMINAL,
            {},
        )

    async def hide_terminal_window(self):
        fn: Callable[[str], None] = self.task.send_update_data
        if hasattr(self.task, "current_workflow") and self.task.current_workflow:
            fn = self.task.current_workflow.send_update_data

        await fn(
            MessageType.HIDE_TERMINAL,
            {},
        )

    async def show_plan(self, plan: str) -> None:
        await self.task.send_update_data(
            MessageType.DISPLAY_PLAN,
            {"plan_markdown": plan},
        )

    async def open_chat_panel(self) -> None:
        await self.task.send_update_data(
            MessageType.OPEN_CHAT_PANEL,
            {},
        )
