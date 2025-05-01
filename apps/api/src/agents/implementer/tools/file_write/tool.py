import os
from typing import Any

from pydantic import BaseModel, Field
from src.agents.code_analyzer.utils.path_utils import absolute_path
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.file_read.prompt import PROMPT
from src.agents.implementer.utils.diffs import get_patch
from src.agents.implementer.utils.file import write_text_content
from src.agents.implementer.utils.file_utils import (
    add_line_numbers,
    detect_file_encoding,
    detect_line_endings,
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

MAX_LINES_TO_RENDER_FOR_ASSISTANT = 16000
TRUNCATED_MESSAGE = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with Grep in order to find the line numbers of what you are looking for.</NOTE>"


class FileWriteInput(BaseModel):
    file_path: str = Field(
        ...,
        description="The absolute path to the file to write (must be absolute, not relative)",
    )
    content: str = Field(..., description="The content to write to the file")


class FileWriteTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Replace"

    @property
    def prompt(self):
        return PROMPT

    @property
    def input_schema(self):
        return FileWriteInput

    @property
    def is_read_only(self):
        return False

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        file_path: str = input["file_path"]

        full_file_path: str = (
            file_path
            if is_absolute(file_path)
            else await absolute_path(get_persistent_shell().get_task(), file_path)
        )

        if not await exists(full_file_path):
            return {
                "result": True,  # Allow creating new files
                "model": FileWriteInput,
            }

        read_timestamp: int | None = context.read_file_timestamps.get(full_file_path)
        if not read_timestamp:
            return {
                "result": False,
                "message": "File has not been read yet. Read it first before writing to it.",
            }

        stats: FileStats = await stat(full_file_path)
        last_write_time: int = stats.st_mtime
        if last_write_time > read_timestamp:
            return {
                "result": False,
                "message": "File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.",
            }

        return {"result": True, "model": FileWriteInput}

    async def call(
        self,
        input: FileWriteInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        file_path: str = input.file_path
        content: str = input.content

        full_file_path: str = (
            file_path
            if is_absolute(file_path)
            else await absolute_path(get_persistent_shell().get_task(), file_path)
        )

        dir: str = os.path.dirname(full_file_path)
        old_file_exists: bool = await exists(full_file_path)
        enc: str = (
            await detect_file_encoding(full_file_path) if old_file_exists else "utf-8"
        )
        old_content: str | None = (
            await read_file(full_file_path) if old_file_exists else None
        )
        endings: str = (
            await detect_line_endings(full_file_path) if old_file_exists else os.linesep
        )  # not detecting repo endings

        await mkdir(dir)

        await write_text_content(full_file_path, content, enc, endings)

        stats = await stat(full_file_path)
        context.read_file_timestamps[full_file_path] = stats.st_mtime

        if old_content:
            patch = get_patch(file_path, old_content, old_content, content)
            data = {
                "type": "update",
                "file_path": file_path,
                "content": content,
                "structured_patch": patch,
            }
            return FullToolUseResult(
                data=data,
                result_for_assistant=self.render_result_for_assistant(data),
            )

        data = {
            "type": "create",
            "file_path": file_path,
            "content": content,
            "structured_patch": [],
        }

        return FullToolUseResult(
            data=data,
            result_for_assistant=self.render_result_for_assistant(data),
        )

    def render_result_for_assistant(self, data: dict[str, Any]) -> str:
        if data["type"] == "create":
            return f"File created successfully at: {data['file_path']}"
        elif data["type"] == "update":
            content_lines: list[str] = data["content"].split("\n")
            truncated: bool = len(content_lines) > MAX_LINES_TO_RENDER_FOR_ASSISTANT

            if truncated:
                display_content = (
                    "\n".join(content_lines[:MAX_LINES_TO_RENDER_FOR_ASSISTANT])
                    + "\n"
                    + TRUNCATED_MESSAGE
                )
            else:
                display_content = data["content"]

            return f"""The file {data["file_path"]} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:
{add_line_numbers(content=display_content, start_line=1)}"""
        else:
            raise ValueError(f"Unknown data type: {data['type']}")
