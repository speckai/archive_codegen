import asyncio
import shlex
from typing import List, Optional

from src.agents.implementer.utils.persistent_shell import (
    _PersistentShell,
    get_persistent_shell,
)
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.utils.logging import logger


async def rip_grep(
    args: list[str],
    target: str,
    timeout: int = 10,
    abort_signal: Optional[asyncio.Event] = None,
) -> list[str]:
    """
    Execute ripgrep with the given arguments and target path using a sandbox.

    Args:
        sandbox: Sandbox instance to use for execution
        args: List of arguments to pass to ripgrep
        target: The target path to search in
        timeout: Maximum time in seconds to wait for ripgrep to complete
        abort_signal: Optional event that can be used to abort the operation

    Returns:
        List of matching lines (filtered to remove empty lines)
    """
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    # Default ripgrep command
    rg_command = "rg"

    # Properly escape all arguments and the target path
    escaped_args = [shlex.quote(arg) for arg in args]
    escaped_target = shlex.quote(target)
    full_command = f"{rg_command} {' '.join(escaped_args)} {escaped_target}"
    logger.debug(f"Running ripgrep command in sandbox: {full_command}")

    try:
        # If abort_signal is provided, we need to create a separate task
        # to watch for it and handle timeout ourselves
        if abort_signal and not abort_signal.is_set():
            abort_task = asyncio.create_task(abort_signal.wait())

            command_task = asyncio.create_task(
                sandbox.run_command(full_command, timeout=timeout)
            )

            done, pending = await asyncio.wait(
                [command_task, abort_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            # Check if command was aborted
            if abort_task in done:
                logger.debug("Ripgrep command aborted by signal")
                # The command is still running in the sandbox, but we've
                # dropped our reference to the result
                return []

            result = await command_task
        else:
            # No abort signal, just run the command
            result = await sandbox.run_command(full_command, timeout=timeout)

        if result.exit_code != 0:
            if result.exit_code != 1:  # 1 means no matches, which is normal
                logger.debug(f"ripgrep error: {result.stderr}")
            return []

        return [line for line in result.stdout.splitlines() if line]

    except asyncio.TimeoutError:
        logger.debug(f"ripgrep timed out after {timeout} seconds")
        return []
    except Exception as e:
        logger.debug(f"Error executing ripgrep: {e}")
        return []


async def list_all_content_files(
    sandbox: Sandbox,
    path: str,
    abort_signal: Optional[asyncio.Event] = None,
    limit: int = 100,
) -> List[str]:
    """
    List all content files in a directory using ripgrep.
    Uses ripgrep to find non-empty files, skipping ignored files.

    Args:
        sandbox: Sandbox instance to use for execution
        path: Directory to scan
        abort_signal: Optional signal to abort the operation
        limit: Maximum number of files to return

    Returns:
        List of file paths
    """
    try:
        # Use ripgrep to find any file with at least one character
        results = await rip_grep(sandbox, ["-l", "."], path, abort_signal=abort_signal)
        return results[:limit]
    except Exception as e:
        logger.debug(f"list_all_content_files failed: {e}")
        return []
