from typing import TYPE_CHECKING, Callable

from morphcloud.api import InstanceExecResponse
from src.schemas.core.common import MessageType

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Terminal:
    def __init__(self, task: "Task"):
        self.task: Task = task

    async def run_command(
        self,
        command: str,
    ) -> InstanceExecResponse:
        """
        Runs a command in the sandbox and returns the output, errors, and status code.
        :param command: The command to run
        :return: The output, errors, and status code
        """
        await self.task.ui_functions.show_terminal_window()
        await self.forward_command_to_frontend(command)

        result: InstanceExecResponse = await self.task.sandbox.run_command(command)

        await self.task.ui_functions.hide_terminal_window()
        return result

    async def forward_command_to_frontend(self, command: str):  # TODO: Fix fn
        fn: Callable[[str], None] = self.task.send_update_data
        if hasattr(self.task, "current_workflow") and self.task.current_workflow:
            fn = self.task.current_workflow.send_update_data

        await fn(
            MessageType.USER_COMMAND,
            {
                "command": command,
            },
        )

    async def forward_output_to_frontend(self, output_str: str, is_error: bool):
        fn: Callable[[str], None] = self.task.send_update_data
        if hasattr(self.task, "current_workflow") and self.task.current_workflow:
            fn = self.task.current_workflow.send_update_data

        await fn(
            MessageType.TERMINAL_OUTPUT,
            {
                "output": output_str,
                "is_error": is_error,
            },
        )
