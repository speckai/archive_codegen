from typing import Any

from pydantic import BaseModel, Field
from src.agents.code_analyzer.utils.path_utils import absolute_path
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.ls.prompt import DESCRIPTION
from src.agents.implementer.tools.ls.utils import (
    create_file_tree,
    list_directory,
    print_tree,
)
from src.agents.implementer.utils.persistent_shell import get_cwd, get_persistent_shell

MAX_LINES = 4
MAX_FILES = 1000
TRUNCATED_MESSAGE = f"There are more than {MAX_FILES} files in the repository. Use the LS tool (passing a specific path), Bash tool, and other tools to explore nested directories. The first {MAX_FILES} files and directories are included below:\n\n"


class LSInput(BaseModel):
    path: str = Field(
        ...,
        description="The absolute path to the directory to list (must be absolute, not relative)",
    )


class LSTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "LS"

    @property
    def prompt(self):
        return DESCRIPTION

    @property
    def input_schema(self):
        return LSInput

    @property
    def is_read_only(self) -> bool:
        return True

    async def validate_input(
        self, input: dict[str, Any], context: ToolUseContext
    ) -> dict[str, Any]:
        return {"result": True, "model": LSInput}

    def render_result_for_assistant(self, data: str) -> str:
        return data

    async def call(
        self,
        input: LSInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        path: str = input.path

        full_file_path: str = (
            await absolute_path(get_persistent_shell().get_task(), path) or get_cwd()
        )
        print("Doing LS in ", full_file_path)
        result: list[str] = await list_directory(full_file_path, get_cwd())
        result.sort()

        user_tree: str = print_tree(create_file_tree(result), get_cwd())
        assistant_tree: str = user_tree

        if len(result) < MAX_FILES:
            return FullToolUseResult(
                data=user_tree,
                result_for_assistant=self.render_result_for_assistant(assistant_tree),
            )

        user_data: str = f"{TRUNCATED_MESSAGE}{user_tree}"
        assistant_data: str = f"{TRUNCATED_MESSAGE}{assistant_tree}"

        return FullToolUseResult(
            data=user_data,
            result_for_assistant=self.render_result_for_assistant(assistant_data),
        )
