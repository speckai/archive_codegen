import os
from typing import TYPE_CHECKING

from pydantic import BaseModel
from src.agents.code_analyzer.utils.path_utils import absolute_path, normalize_path
from src.agents.implementer.utils.persistent_shell import (
    _PersistentShell,
    get_cwd,
    get_persistent_shell,
)
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


def is_absolute(path: str) -> bool:
    """Check if a path is absolute."""
    return os.path.isabs(path)


async def exists(path: str) -> bool:
    """Check if a file exists using the sandbox."""
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    # needs to be absolute since it needs to be a valid path
    path = await absolute_path(shell.get_task(), path)
    try:
        result = await sandbox.run_command(
            f"[ -e '{path}' ] && echo 'yes' || echo 'no'"
        )
        return result.stdout.strip() == "yes"
    except Exception:
        return False


async def mkdir(path: str) -> None:
    """Create a directory using the sandbox."""
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    await sandbox.run_command(f"mkdir -p '{path}'")


async def read_file(path: str, enc: str = "utf-8") -> str:
    """Read a file using the sandbox."""
    if enc != "utf-8":
        raise NotImplementedError("Only UTF-8 encoding is supported")
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    task: "Task" = shell.get_task()
    path = await normalize_path(task, path)
    logger.debug(f"read_file: {path}")
    return await sandbox.get_file(path, use_repo_subdir=False)


async def write_file(path: str, content: str, enc: str, endings: str) -> None:
    """Write a file using the sandbox."""
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    if enc != "utf-8":
        raise NotImplementedError("Only UTF-8 encoding is supported")
    norm_path: str = await normalize_path(shell.get_task(), path)
    await sandbox.write_file(norm_path, content, make_dirs=True, use_repo_subdir=False)


class FileStats(BaseModel):
    """
    File statistics from sandbox environment.
    Currently provides modification time and size.
    """

    st_mtime: float
    st_size: float


async def stat(path: str) -> FileStats:
    """
    Get file stats using the sandbox.
    Uses appropriate stat command based on environment:
    - macOS format when in debug mode (local development)
    - Linux format when not in debug mode (production)
    """
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    abs_path: str = await absolute_path(shell.get_task(), path)

    # Choose stat command format based on debug mode
    if shell.debug:
        # macOS/BSD format for local development
        stat_cmd = f"stat -f '%m,%z' '{abs_path}'"
    else:
        # Linux format for production
        stat_cmd = f"stat -c '%Y,%s' '{abs_path}'"

    result = await sandbox.run_command(stat_cmd)

    if result.exit_code == 0:
        parts = result.stdout.strip().split(",")
        if len(parts) == 2:
            return FileStats(st_mtime=float(parts[0]), st_size=float(parts[1]))

    # If stat command failed, check if file exists at all
    result = await sandbox.run_command(f"ls -la '{abs_path}' 2>/dev/null")
    if result.exit_code == 1:
        print(f"Warning: File exists but couldn't get stats: {path}")

    return FileStats(st_mtime=0, st_size=0)


async def glob(
    pattern: str,
    path: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[str], bool]:
    """
    Perform a recursive glob search using ripgrep.
    Supports all glob patterns including brace expansions.
    """
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    base_path: str = await absolute_path(shell.get_task(), path) or get_cwd()

    # Use ripgrep to find files matching pattern
    # --files: only show file names
    # -g: apply glob pattern
    # --no-ignore-vcs: ensure all files are included
    # --no-line-number: we just want file names
    cmd = f"rg --files --no-ignore --no-line-number -g '{pattern}' {base_path} 2>/dev/null || echo ''"

    logger.debug(f"glob: {cmd}")
    result = await sandbox.run_command(cmd)

    matches = []
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    for file in files:
        stats = await stat(file)
        matches.append((file, stats.st_mtime))

    sorted_matches = sorted(matches, key=lambda x: x[1], reverse=True)
    truncated: bool = len(sorted_matches) > offset + limit
    result_files: list[str] = [f[0] for f in sorted_matches[offset : offset + limit]]

    return result_files, truncated


async def read_file_binary(path: str) -> bytes:
    """Read a file in binary mode using the sandbox."""
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    result = await sandbox.run_command(f"cat '{path}' | base64")
    if result.exit_code == 0:
        import base64

        return base64.b64decode(result.stdout)
    else:
        logger.error(f"Error reading file {path}: {result.stderr}")
    return b""
