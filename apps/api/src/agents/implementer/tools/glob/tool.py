import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.glob.prompt import DESCRIPTION
from src.agents.implementer.utils.fs import glob
from src.agents.implementer.utils.persistent_shell import get_cwd
from src.utils.logging import logger


class GlobInput(BaseModel):
    pattern: str = Field(..., description="The glob pattern to match files against")
    path: str | None = Field(
        None,
        description="The directory to search in. Defaults to the current working directory.",
    )


class GlobTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "GlobTool"

    @property
    def prompt(self):
        return DESCRIPTION

    @property
    def input_schema(self):
        return GlobInput

    @property
    def is_read_only(self):
        return True

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        return {
            "result": True,
            "model": GlobInput,
        }

    async def call(
        self,
        input: GlobInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        pattern: str = input.pattern
        path: str | None = input.path
        start: float = time.time()

        base_path: Path = Path(path or get_cwd())

        files, truncated = await self._glob(pattern, base_path, limit=100, offset=0)
        logger.debug(f"glob: {pattern} {base_path} {files} {truncated}")

        output: dict[str, Any] = {
            "file_names": files,
            "duration_ms": time.time() - start,
            "num_files": len(files),
            "truncated": truncated,
        }

        return FullToolUseResult(
            data=output,
            result_for_assistant=self.render_result_for_assistant(output),
        )

    async def _glob(
        self, pattern: str, base_path: Path, limit: int, offset: int
    ) -> tuple[list[str], bool]:
        base_path_str: str = str(base_path)
        # Use the glob utility function which handles sorting by modification time
        file_paths, truncated = await glob(pattern, base_path_str, limit, offset)
        # Reverse the order to get newest files first (the glob function sorts oldest first)
        file_paths.reverse()

        return file_paths, truncated

    def render_result_for_assistant(self, output: dict[str, Any]) -> str:
        result: str = "\n".join(output["file_names"])
        if len(output["file_names"]) == 0:
            result = "No files found"
        elif output["truncated"]:
            result += "\n(Results are truncated. Consider using a more specific path or pattern.)"
        return result
