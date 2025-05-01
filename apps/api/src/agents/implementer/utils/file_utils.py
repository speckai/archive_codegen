import os
from typing import TYPE_CHECKING, TypedDict

from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.agents.implementer.utils.fs import exists
from src.agents.implementer.utils.persistent_shell import (
    _PersistentShell,
    get_persistent_shell,
)
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.utils.logging import logger

if TYPE_CHECKING:
    pass

MAX_OUTPUT_SIZE = 0.25 * 1024 * 1024  # 0.25MB in bytes
MAX_IMAGE_SIZE = 3.75 * 1024 * 1024  # 3.75MB in bytes (with base64 encoding)
MAX_WIDTH = 2000
MAX_HEIGHT = 2000
N_LINES_SNIPPET = 4  # Number of lines of context before/after for edit snippets

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class ImageResponse(TypedDict):
    type: str
    file: dict[str, str]


class TextResponse(TypedDict):
    type: str
    file: dict[str, str | int]


FileResponse = ImageResponse | TextResponse


async def detect_file_encoding(file_path: str) -> str:
    """Detects the encoding of a file using sandbox."""
    if not await exists(file_path):
        return "utf-8"

    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    # Check for BOM markers first
    result = await sandbox.run_command(f"head -c 4 '{file_path}' | hexdump -C")
    if result.exit_code == 0:
        hex_output = result.stdout.lower()
        if "ff fe" in hex_output:
            return "utf-16le"
        if "ef bb bf" in hex_output:
            return "utf-8"
    else:
        logger.error(f"Error detecting file encoding for {file_path}: {result.stderr}")

    # Use file command as fallback
    result = await sandbox.run_command(f"file -i '{file_path}'")
    return "utf-16le" if "charset=utf-16" in result.stdout.lower() else "utf-8"


async def detect_line_endings(file_path: str) -> str:
    """Detect line endings using sandbox."""
    if not await exists(file_path):
        return "\n"  # Default to LF

    try:
        shell: _PersistentShell = get_persistent_shell()
        sandbox: Sandbox = shell.get_sandbox()
        # Look at first line's endings using hexdump
        result = await sandbox.run_command(f"head -n 1 '{file_path}' | hexdump -C")

        if result.exit_code == 0:
            hex_output = result.stdout.lower()
            # Check for CRLF (Windows)
            if "0d 0a" in hex_output:
                return "\r\n"
            # Check for CR (old Mac)
            elif "0d" in hex_output and "0a" not in hex_output:
                return "\r"
        else:
            logger.error(
                f"Error detecting line endings for {file_path}: {result.stderr}"
            )

        # Default to LF (Unix/Linux/macOS)
        return "\n"
    except Exception as e:
        logger.error(f"Error detecting line endings for {file_path}: {e}")
        return "\n"  # Default to LF


async def read_text_content(
    file_path: str, offset: int = 0, limit: int | None = None
) -> tuple[str, int, int]:
    """Read text content from a file with offset and limit using sandbox."""
    if not await exists(file_path):
        return "", 0, 0

    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    file_path: str = await normalize_path(shell.get_task(), file_path)
    content = await sandbox.get_file(file_path, use_repo_subdir=False)
    all_lines = content.splitlines(keepends=True)

    total_lines: int = len(all_lines)
    if offset >= total_lines:
        return "", 0, total_lines

    start: int = offset
    end: int = total_lines if limit is None else min(offset + limit, total_lines)

    selected_lines: list[str] = all_lines[start:end]
    content: str = "".join(selected_lines)
    line_count: int = len(selected_lines)

    return content, line_count, total_lines


def add_line_numbers(content: str, start_line: int = 1) -> str:
    """Adds line numbers to the content (cat -n style)."""
    if not content:
        return ""

    result: list[str] = []
    for index, line in enumerate(content.split("\n")):
        line_num: int = index + start_line
        num_str: str = str(line_num)
        if len(num_str) >= 6:
            result.append(f"{num_str}\t{line}")
        else:
            n: str = num_str.rjust(6)
            result.append(f"{n}\t{line}")

    return "\n".join(result)


async def find_similar_file(path: str) -> str | None:
    """Find a similar file with different extension."""
    try:
        shell: _PersistentShell = get_persistent_shell()
        sandbox: Sandbox = shell.get_sandbox()
        dir_path: str = os.path.dirname(path)
        file_base_name: str = os.path.splitext(os.path.basename(path))[0]
        if not await exists(dir_path):
            return None
        # Use the sandbox to list files in the directory
        cmd_result = await sandbox.run_command(f"ls -1 {dir_path}")
        files: list[str] = [
            f.strip() for f in cmd_result.stdout.splitlines() if f.strip()
        ]
        similar_files: list[str] = [
            file
            for file in files
            if os.path.splitext(file)[0] == file_base_name
            and os.path.join(dir_path, file) != path
        ]
        return os.path.join(dir_path, similar_files[0]) if similar_files else None
    except Exception as e:
        print(f"Error finding similar file for {path}: {e}")
        return None
