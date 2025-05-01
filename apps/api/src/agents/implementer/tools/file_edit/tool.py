import os
from typing import Any

from pydantic import BaseModel, Field
from src.agents.code_analyzer.utils.path_utils import absolute_path
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.file_edit.prompt import DESCRIPTION
from src.agents.implementer.tools.file_edit.utils import apply_edit
from src.agents.implementer.utils.file import write_text_content
from src.agents.implementer.utils.file_utils import (
    N_LINES_SNIPPET,
    add_line_numbers,
    detect_file_encoding,
    detect_line_endings,
    find_similar_file,
)
from src.agents.implementer.utils.fs import (
    FileStats,
    exists,
    is_absolute,
    mkdir,
    read_file,
    stat,
)
from src.agents.implementer.utils.persistent_shell import get_persistent_shell
from src.utils.logging import logger


class FileEditInput(BaseModel):
    file_path: str = Field(..., description="The path to the file to edit")
    old_string: str = Field(..., description="The string to replace")
    new_string: str = Field(
        ..., description="The new string to replace the old_string with"
    )


class FileEditTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Edit"

    @property
    def prompt(self):
        return DESCRIPTION

    @property
    def input_schema(self) -> BaseModel:
        return FileEditInput

    @property
    def is_read_only(self):
        return False

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        file_path: str = input["file_path"]
        old_string: str = input["old_string"]
        new_string: str = input["new_string"]

        if old_string == new_string:
            return {
                "result": False,
                "message": "No changes to make: old_string and new_string are exactly the same",
                "meta": {"old_string": old_string},
            }

        full_file_path: str = (
            file_path
            if is_absolute(file_path)
            else await absolute_path(get_persistent_shell().get_task(), file_path)
        )

        if await exists(full_file_path) and not old_string:
            return {
                "result": False,
                "message": "Cannot create new file - file already exists",
            }

        if not await exists(full_file_path) and not old_string:
            return {"result": True, "model": FileEditInput}

        if not await exists(full_file_path):
            similar_file: str | None = await find_similar_file(full_file_path)
            message: str = "File does not exist."

            if similar_file:
                message += f" Did you mean {similar_file}?"

            return {"result": False, "message": message}

        if full_file_path.endswith(".ipynb"):
            return {
                "result": False,
                "message": "File is a Jupyter Notebook. We cannot edit this file.",
            }

        read_timestamp: int | None = context.read_file_timestamps.get(full_file_path)
        if not read_timestamp:
            return {
                "result": False,
                "message": "File has not been read yet. Read it first before writing to it.",
                "meta": {"is_file_path_absolute": is_absolute(file_path)},
            }

        stats: FileStats = await stat(full_file_path)
        last_write_time: int = stats.st_mtime
        if last_write_time > read_timestamp:
            return {
                "result": False,
                "message": "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.",
            }

        await detect_file_encoding(full_file_path)
        file_content: str = await read_file(full_file_path)

        if old_string not in file_content:
            return {
                "result": False,
                "message": "String to replace not found in file.",
                "meta": {"is_file_path_absolute": is_absolute(file_path)},
            }

        matches: int = file_content.count(old_string)
        if matches > 1:
            return {
                "result": False,
                "message": f"Found {matches} matches of the string to replace. For safety, this tool only supports replacing exactly one occurrence at a time. Add more lines of context to your edit and try again.",
            }

        return {"result": True, "model": FileEditInput}

    async def call(
        self,
        input: FileEditInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        file_path: str = input.file_path
        old_string: str = input.old_string
        new_string: str = input.new_string

        logger.debug(f"Editing file: {file_path}")

        full_file_path: str = (
            file_path
            if is_absolute(file_path)
            else await absolute_path(get_persistent_shell().get_task(), file_path)
        )
        logger.debug(f"Applying edit to file: {full_file_path}")

        try:
            patch, updated_file = await apply_edit(
                full_file_path, old_string, new_string
            )

            full_file_path = (
                file_path
                if is_absolute(file_path)
                else await absolute_path(get_persistent_shell().get_task(), file_path)
            )
            dir: str = os.path.dirname(full_file_path)
            await mkdir(dir)

            file_exists = await exists(full_file_path)
            enc: str = (
                await detect_file_encoding(full_file_path) if file_exists else "utf-8"
            )
            endings: str = (
                await detect_line_endings(full_file_path) if file_exists else "LF"
            )
            original_file: str = await read_file(full_file_path) if file_exists else ""
            await write_text_content(full_file_path, updated_file, enc, endings)

            stats = await stat(full_file_path)
            context.read_file_timestamps[full_file_path] = stats.st_mtime

            data: dict = {
                "original_file": original_file,
                "old_string": old_string,
                "new_string": new_string,
                "diff": patch,
                "file_path": file_path,
            }

            return FullToolUseResult(
                data=data,
                result_for_assistant=self.render_result_for_assistant(data),
            )
        except Exception as e:
            return FullToolUseResult(
                data={"error": str(e)},
                result_for_assistant=f"Error editing file: {str(e)}",
            )

    def render_result_for_assistant(self, data: dict) -> str:
        """Render the result for the assistant."""
        try:
            before_lines: list[str] = []
            if data["old_string"]:
                before_lines = (
                    data["original_file"].split(data["old_string"])[0].split("\n")
                )
            replacement_line: int = len(before_lines)

            content: str = data["original_file"].replace(
                data["old_string"], data["new_string"], 1
            )
            new_file_lines: list[str] = content.split("\n")

            start_line: int = max(0, replacement_line - N_LINES_SNIPPET)
            new_string_lines: list[str] = data["new_string"].split("\n")
            end_line: int = min(
                len(new_file_lines),
                replacement_line + len(new_string_lines) + N_LINES_SNIPPET,
            )

            snippet_lines: list[str] = new_file_lines[start_line:end_line]
            snippet: str = "\n".join(snippet_lines)

            return f"""The file {data["file_path"]} has been updated. Here's the result of running `cat -n` on a snippet of the edited file: 
{add_line_numbers(content=snippet, start_line=start_line + 1)}"""

        except Exception as e:
            return f"File was edited, but could not display snippet: {str(e)}"
