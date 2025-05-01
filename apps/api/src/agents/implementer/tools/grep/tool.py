import asyncio
import contextlib
import time
from typing import Any

from pydantic import BaseModel, Field
from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.grep.prompt import DESCRIPTION
from src.agents.implementer.utils.fs import exists, is_absolute, stat
from src.agents.implementer.utils.persistent_shell import get_cwd, get_persistent_shell
from src.agents.implementer.utils.ripgrep import rip_grep

MAX_RESULTS = 100


class GrepInput(BaseModel):
    pattern: str = Field(
        ...,
        description="The regular expression pattern to search for in file contents",
    )
    path: str | None = Field(
        None,
        description="The directory to search in. Defaults to the current working directory.",
    )
    include: str | None = Field(
        None,
        description="File pattern to include in the search (e.g. '*.js', '*.{ts,tsx}')",
    )


class GrepTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "GrepTool"

    @property
    def prompt(self):
        return DESCRIPTION

    @property
    def input_schema(self):
        return GrepInput

    @property
    def is_read_only(self):
        return True

    async def validate_input(
        self, input: dict[str, Any], context: ToolUseContext
    ) -> dict[str, Any]:
        return {"result": True, "model": GrepInput}

    def render_result_for_assistant(self, data: dict[str, Any]):
        num_files: int = data["num_files"]
        filenames: list[str] = data["filenames"]
        if num_files == 0:
            return "No files found"
        result = f"Found {num_files} file{'' if num_files == 1 else 's'}\n{'\n'.join(filenames[:MAX_RESULTS])}"
        if num_files > MAX_RESULTS:
            result += "\n(Results are truncated. Consider using a more specific path or pattern.)"
        return result

    async def call(
        self,
        input: GrepInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        pattern: str = input.pattern
        path: str | None = input.path
        start: float = time.time()

        absolute_path: str = path if path and is_absolute(path) else get_cwd()

        print("Grepping in ", absolute_path, " with pattern ", pattern)

        if not await exists(absolute_path):
            return FullToolUseResult(
                result_for_assistant="No files found (directory does not exist)",
                data={"filenames": [], "duration_ms": 0, "num_files": 0},
            )

        args: list[str] = ["-li", pattern]

        if include := input.include:
            args.extend(["--glob", include])

        abort_signal: asyncio.Event = asyncio.Event()

        try:
            results: list[str] = await rip_grep(
                args, absolute_path, timeout=30, abort_signal=abort_signal
            )

            if results:
                file_stats: dict[str, int] = {}
                for result_path in results:
                    with contextlib.suppress(FileNotFoundError, PermissionError):
                        stats = await stat(result_path)
                        file_stats[result_path] = stats.st_mtime

                results.sort(key=lambda x: file_stats.get(x, 0), reverse=True)

                if len(results) > MAX_RESULTS:
                    results = results[:MAX_RESULTS]

                relative_results: list[str] = []
                for result_path in results:
                    try:
                        rel_path: str = await normalize_path(
                            get_persistent_shell().get_task(), result_path
                        )
                        relative_results.append(rel_path)
                    except ValueError:
                        relative_results.append(result_path)

                results = relative_results

        except Exception as e:
            return FullToolUseResult(
                result_for_assistant=f"Error searching for files: {str(e)}",
                data={
                    "filenames": [],
                    "duration_ms": 0,
                    "num_files": 0,
                    "error": str(e),
                },
            )

        output = {
            "filenames": results,
            "duration_ms": round((time.time() - start) * 1000),
            "num_files": len(results),
        }
        print(self.render_result_for_assistant(output))

        return FullToolUseResult(
            result_for_assistant=self.render_result_for_assistant(output),
            data=output,
        )
