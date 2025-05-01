from typing import TYPE_CHECKING, Optional, TypedDict
from uuid import uuid4

from src.agents.utils.task.interfaces.file_system import FileSystem
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class ExecResult(TypedDict):
    stdout: str
    stderr: str
    code: int
    interrupted: bool


class _PersistentShell:
    def __init__(self, cwd: str, debug: bool = False):
        self.cwd: str = cwd
        self.is_alive: bool = False
        self.command_interrupted: bool = False
        self.sandbox: Optional[Sandbox] = None
        self.file_system: Optional[FileSystem] = None
        self.env_vars: dict[str, str] = {"GIT_EDITOR": "true"}
        self.shell_id: str = str(uuid4())
        self.debug: bool = debug

    def set_file_system(self, file_system: FileSystem) -> None:
        """Set the file system instance to use for file operations."""
        self.file_system = file_system

    def set_sandbox(self, sandbox: Sandbox) -> None:
        """Set the sandbox instance to use for command execution."""
        self.sandbox = sandbox
        self.is_alive = True
        self.command_interrupted = False

    def set_task(self, task: "Task") -> None:
        """Set the task instance to use for task-related operations."""
        self.task = task

    def get_sandbox(self) -> Sandbox:
        """Get the sandbox instance."""
        if not self.sandbox:
            raise RuntimeError("Sandbox not initialized or not available")
        return self.sandbox

    def get_file_system(self) -> FileSystem:
        """Get the file system instance."""
        if not self.file_system:
            raise RuntimeError("File system not initialized or not available")
        return self.file_system

    def get_task(self) -> "Task":
        """Get the task instance."""
        if not self.task:
            raise RuntimeError("Task not initialized or not available")
        return self.task

    def _ensure_sandbox_alive(self) -> None:
        """Ensure the sandbox is available."""
        if not self.is_alive or not self.sandbox:
            raise RuntimeError("Sandbox not initialized or not available")

    def set_env_var(self, key: str, value: str) -> None:
        """Set an environment variable to be applied to all future commands."""
        self.env_vars[key] = value

    def send_to_shell(self, command: str) -> None:
        """Send a command to the shell (compatibility method)."""
        # This is now a no-op as we'll directly execute in exec()
        pass

    async def exec(self, command: str, timeout: int | None = None) -> ExecResult:
        """Execute a command in the sandbox."""
        if not timeout:
            timeout = 30 * 60  # 30 minutes default timeout

        try:
            self._ensure_sandbox_alive()

            # Skip empty commands
            if not command.strip():
                return {"stdout": "", "stderr": "", "code": 0, "interrupted": False}

            env_setup = " ".join(
                [f"export {key}='{value}';" for key, value in self.env_vars.items()]
            )

            combined_cmd = f"{env_setup} cd '{self.cwd}' && {command}"
            result = await self.sandbox.run_command(combined_cmd, timeout=timeout)

            if result.exit_code == 0:
                pwd_result = await self.sandbox.run_command("pwd")
                if pwd_result.exit_code == 0:
                    new_cwd = pwd_result.stdout.strip()
                    if new_cwd and new_cwd != self.cwd:
                        self.cwd = new_cwd
                        set_cwd(new_cwd)
            else:
                logger.error(f"Error executing command {command}: {result.stderr}")

            return {
                "stdout": result.stdout.strip() if result.stdout else "",
                "stderr": result.stderr.strip() if result.stderr else "",
                "code": result.exit_code or 0,
                "interrupted": self.command_interrupted or result.exit_code < 0,
            }
        except Exception as e:
            self.command_interrupted = True
            return {
                "stdout": "",
                "stderr": f"Command execution error: {str(e)}",
                "code": -1,
                "interrupted": True,
            }

    async def set_cwd(self, cwd: str) -> None:
        """Change the working directory."""
        self._ensure_sandbox_alive()

        # Try to change to the directory directly instead of checking existence
        cd_result = await self.sandbox.run_command(f"cd '{cwd}' && pwd")

        if cd_result.exit_code != 0:
            raise FileNotFoundError(
                f"Path '{cwd}' does not exist in sandbox: {cd_result.stderr}"
            )

        # Get the actual path (resolves symlinks, etc.)
        actual_path = cd_result.stdout.strip()

        # Update our internal state
        self.cwd = actual_path
        # Also update the global state for compatibility
        set_cwd(actual_path)

    async def close(self) -> None:
        """Mark the shell as closed (actual sandbox cleanup handled elsewhere)."""
        self.is_alive = False
        self.sandbox = None


# Global state for compatibility
_original_cwd: str = "/"  # Will be set properly when sandbox is initialized
_current_cwd: str = _original_cwd
_shell_instance = None


async def init_shell(
    sandbox: Sandbox,
    file_system: FileSystem,
    initial_cwd: str,
    task: "Task",
    debug: bool = False,
) -> None:
    """Initialize the shell with the given sandbox and directory."""
    global _original_cwd, _current_cwd, _shell_instance, PersistentShell

    # debug means local -> assume we're on macos
    if _shell_instance is None:
        _shell_instance = _PersistentShell(initial_cwd, debug)

    _shell_instance.set_sandbox(sandbox)
    _shell_instance.set_file_system(file_system)
    _shell_instance.set_task(task)

    # Try to cd to the initial directory directly
    cd_result = await sandbox.run_command(f"cd '{initial_cwd}' && pwd")

    if cd_result.exit_code == 0:
        # Directory exists, get the actual full path
        actual_path = cd_result.stdout.strip()
        _original_cwd = actual_path
        _current_cwd = actual_path
        _shell_instance.cwd = actual_path
    else:
        # Fall back to root if the specified directory doesn't exist
        _original_cwd = "/"
        _current_cwd = "/"
        _shell_instance.cwd = "/"

    PersistentShell = _shell_instance
    print("shell instance", _shell_instance)


def set_cwd(cwd: str) -> None:
    """Update the global current working directory."""
    global _current_cwd
    _current_cwd = cwd


def set_original_cwd(cwd: str) -> None:
    """Update the global original working directory."""
    global _original_cwd
    _original_cwd = cwd


def get_original_cwd() -> str:
    """Get the global original working directory."""
    return _original_cwd


def get_cwd() -> str:
    """Get the global current working directory."""
    return _current_cwd


PersistentShell = None  # Start with None


def get_persistent_shell() -> _PersistentShell:
    """Get the singleton instance of PersistentShell, creating it if needed."""
    global PersistentShell, _shell_instance

    if PersistentShell is None:
        if _shell_instance is None:
            _shell_instance = _PersistentShell(_original_cwd)
        PersistentShell = _shell_instance

    return PersistentShell
