from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.bash.prompt import BANNED_COMMANDS, BASH_PROMPT
from src.agents.implementer.tools.bash.utils import (
    format_output,
    get_command_file_paths,
)
from src.agents.implementer.utils.commands import split_command
from src.agents.implementer.utils.file import is_in_directory
from src.agents.implementer.utils.fs import stat
from src.agents.implementer.utils.persistent_shell import (
    get_cwd,
    get_original_cwd,
    get_persistent_shell,
)


class BashInput(BaseModel):
    command: str = Field(..., description="The bash command to execute")
    timeout: int = Field(
        default=30 * 60, description="The timeout for the command in seconds"
    )


class BashTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def prompt(self):
        return BASH_PROMPT

    @property
    def input_schema(self):
        return BashInput

    @property
    def is_read_only(self):
        return False

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        commands: list[str] = split_command(input["command"])
        for command in commands:
            parts: list[str] = command.split(" ")
            base_cmd: str = parts[0]

            if base_cmd and base_cmd.lower() in BANNED_COMMANDS:
                return {
                    "result": False,
                    "message": f"Command '{base_cmd}' is not allowed for security reasons",
                }

            if base_cmd == "cd" and parts[1]:
                target_dir: str = parts[1].replace("'", "").replace('"', "")
                full_target_dir: str = str(Path(target_dir).resolve())
                if not is_in_directory(get_cwd(), full_target_dir):
                    return {
                        "result": False,
                        "message": f"ERROR: cd to '{full_target_dir}' was blocked. For security, you may only change directories to child directories of the original working directory ({get_original_cwd()}) for this session.",
                    }

        return {
            "result": True,
            "model": BashInput,
        }

    def render_result_for_assistant(self, result: dict) -> str:
        interrupted: bool = result.get("interrupted", False)
        stdout: str = result.get("stdout", "").strip()
        stderr: str = result.get("stderr", "").strip()

        error_message: str = stderr
        if interrupted:
            if error_message:
                error_message += "\n"
            error_message += "<error>Command was aborted before completion</error>"

        has_both: bool = stdout and error_message

        if has_both:
            return f"{stdout}\n{error_message}"
        elif stdout:
            return stdout
        else:
            return error_message

    async def call(
        self,
        input: BashInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        command: str = input.command
        timeout: int = input.timeout

        print("Executing command: ", command)
        shell = get_persistent_shell()
        result = await shell.exec(command, timeout)

        stdout: str = result["stdout"]
        stderr: str = result["stderr"]

        current_cwd: str = get_cwd()
        original_cwd: str = get_original_cwd()

        if not is_in_directory(current_cwd, original_cwd):
            await shell.set_cwd(original_cwd)
            stderr = f"{stderr.strip()}\nShell cwd was reset to {original_cwd}"

        filepaths: list[str] = await get_command_file_paths(command, stdout)
        for filepath in filepaths:
            try:
                full_path: str = str(Path(filepath).resolve())
                context.read_file_timestamps[full_path] = (
                    await stat(full_path)
                ).st_mtime
            except Exception as e:
                print(f"Error updating timestamp for {filepath}: {e}")

        out_num_lines, stdout = format_output(stdout)
        err_num_lines, stderr = format_output(stderr)

        data: dict[str, Any] = {
            "stdout": stdout,
            "std_lines": out_num_lines,
            "stderr": stderr,
            "err_lines": err_num_lines,
            "interrupted": result["interrupted"],
        }

        return FullToolUseResult(
            result_for_assistant=self.render_result_for_assistant(data),
            data=data,
        )
