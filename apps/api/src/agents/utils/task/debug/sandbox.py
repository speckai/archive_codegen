import asyncio
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from morphcloud.api import (
    InstanceExecResponse,
)
from src.agents.utils.task.debug.common import Debug, clean_output
from src.agents.utils.task.debug.manager import DebugContainerManager
from src.schemas.core.common.types import MessageType
from src.schemas.core.validation import RuntimeResult
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class DebugSandbox:
    """Local version of Sandbox for debug mode"""

    def __init__(self, debug: Debug, task: "Task"):
        self.debug = debug
        self.task = task
        self.ip = "localhost"
        self._current_process: asyncio.subprocess.Process | None = None
        self.pod_name = f"pod-{self.task.user.id}"
        self.manager = DebugContainerManager(self, debug=debug)
        self.subdirectory: str | None = debug.settings.root_directory

    async def initialize_sandbox(self) -> str:
        """Initialize the debug sandbox"""
        try:
            # Verify the path exists and has contents
            if not Path(self.manager.workspace_path).exists() or not any(
                Path(self.manager.workspace_path).iterdir()
            ):
                raise ValueError(
                    f"Path {self.manager.workspace_path} does not exist or is empty"
                )
            return self.ip
        except Exception as e:
            await self.task.send_update_data(MessageType.INITIALIZATION_ERROR, {})
            logger.error(f"Failed to initialize debug sandbox: {e}")
            raise

    async def run_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> InstanceExecResponse:
        """Run a command in the local repository directory"""
        # logger.debug(f"Running command: {command}, mode: {mode}, path: {subdirectory}")
        try:
            # Record action in debug mode
            self.task.debug_actions.append(
                {
                    "type": "run_command",
                    "command": command,
                    "timestamp": time.time(),
                }
            )

            # Create process
            self._current_process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.manager.workspace_path,
            )

            stdout, stderr = await asyncio.wait_for(
                self._current_process.communicate(), timeout=timeout
            )
            return InstanceExecResponse(
                exit_code=self._current_process.returncode,
                stdout=clean_output(stdout.decode() if stdout else ""),
                stderr=clean_output(stderr.decode() if stderr else ""),
            )

        except Exception as e:
            logger.error(f"Failed to run command: {e}")
            raise

    async def _stream_to_queue(self, queue: asyncio.Queue) -> None:
        """Stream process output to queue"""
        try:
            if self._current_process.stdout:
                async for line in self._current_process.stdout:
                    await queue.put(
                        InstanceExecResponse(
                            stdout=clean_output(line.decode()),
                            stderr="",
                            exit_code=self._current_process.returncode,
                        )
                    )
            if self._current_process.stderr:
                async for line in self._current_process.stderr:
                    await queue.put(
                        InstanceExecResponse(
                            stdout="",
                            stderr=clean_output(line.decode()),
                            exit_code=self._current_process.returncode,
                        )
                    )
            # Wait for process to complete
            await self._current_process.wait()
            # Send exit command
            await queue.put(
                InstanceExecResponse(
                    stdout="",
                    stderr="",
                    exit_code=self._current_process.returncode,
                )
            )
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            # Ensure we always send an exit command
            await queue.put(
                InstanceExecResponse(
                    stdout="",
                    stderr="",
                    exit_code=1,
                )
            )

    async def kill_all_processes(self) -> None:
        """Kill any running processes"""
        if self._current_process:
            try:
                self._current_process.terminate()
                await self._current_process.wait()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
            self._current_process = None

    async def get_file(self, file_path: str, use_repo_subdir: bool = True) -> str:
        """Get contents of a file from the local repository"""
        try:
            if use_repo_subdir:
                path = Path(
                    os.path.join(
                        await self.task.settings.get_root_directory(),
                        file_path,
                    )
                )
            else:
                path = Path(file_path)

            path = Path(self.manager.workspace_path) / file_path

            return path.read_text() if path.exists() else ""
        except Exception as e:
            blacklisted_file_paths: list[str] = [
                ".ico",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".xlsx",
                ".xls",
                ".doc",
                ".docx",
                ".ppt",
                ".pptx",
            ]
            if any(file_path.endswith(ext) for ext in blacklisted_file_paths):
                return ""
            if ".env" not in file_path:
                logger.error(f"Failed to get file {file_path}: {e}")
            return ""

    async def write_file(
        self,
        file_path: str,
        content: str,
        make_dirs: bool = False,
        use_repo_subdir: bool = True,
    ) -> dict:
        """Write contents to a file in the local repository"""
        try:
            if use_repo_subdir:
                file_path = os.path.join(
                    await self.task.settings.get_root_directory(), file_path
                )
            file_path = file_path.lstrip("/")
            path = Path(self.manager.workspace_path) / file_path

            # Record action in debug mode
            self.task.debug_actions.append(
                {
                    "type": "write_file",
                    "file_path": file_path,
                    "content": content,
                    "make_dirs": make_dirs,
                    "use_repo_subdir": use_repo_subdir,
                    "timestamp": time.time(),
                }
            )

            if make_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return {"success": False, "error": str(e)}

    async def get_website_console_logs(self, path: str) -> RuntimeResult:
        """Get console logs for a specific path by making a request and capturing logs"""
        logger.warning(
            "DebugSandbox.get_website_console_logs is deprecated, use Website.get_website_console_logs instead"
        )
        port = await self.task.settings.get_port()
        url = f"https://localhost:{port}{path}"

        # Make a request to the URL to trigger any console logs
        try:
            cmd = f"curl -s {url}"
            result = await self.run_command(cmd, timeout=15)

            # Return empty result if the command failed
            if not isinstance(result, InstanceExecResponse) or result.exit_code != 0:
                return RuntimeResult(stdout=[], stderr=[], url_tested=url)

            # Get any console logs from the process
            if self.task.website._current_process:
                logs = []
                errors = []

                # Read any available stdout and parse log types
                if self.task.website._current_process.stdout:
                    try:
                        while True:
                            line = await asyncio.wait_for(
                                self.task.website._current_process.stdout.readline(),
                                timeout=0.1,
                            )
                            if not line:
                                break
                            text = line.decode().strip()
                            # Try to detect log type from the content
                            if any(
                                level in text.lower() for level in ["warn", "warning"]
                            ):
                                logs.append({"type": "warning", "text": text})
                            elif "error" in text.lower():
                                errors.append({"type": "error", "text": text})
                            elif "debug" in text.lower():
                                logs.append({"type": "debug", "text": text})
                            elif "info" in text.lower():
                                logs.append({"type": "info", "text": text})
                            else:
                                logs.append({"type": "log", "text": text})
                    except asyncio.TimeoutError:
                        pass
                    except Exception as e:
                        logger.error(f"Error reading stdout: {e}")

                # Read any available stderr - all stderr goes to errors
                if self.task.website._current_process.stderr:
                    try:
                        while True:
                            line = await asyncio.wait_for(
                                self.task.website._current_process.stderr.readline(),
                                timeout=0.1,
                            )
                            if not line:
                                break
                            text = line.decode().strip()
                            errors.append({"type": "error", "text": text})
                    except asyncio.TimeoutError:
                        pass
                    except Exception as e:
                        logger.error(f"Error reading stderr: {e}")

                # Filter and process logs similar to the original implementation
                stdout_logs = [
                    log["text"]
                    for log in logs
                    if log["type"] in ["warning", "debug", "info", "log"]
                ]
                stderr_logs = [
                    error["text"]
                    for error in errors
                    if error["type"] not in ["warning", "debug", "info", "log"]
                ]

                return RuntimeResult(
                    stdout=stdout_logs, stderr=stderr_logs, url_tested=url
                )

            return RuntimeResult(stdout=[], stderr=[], url_tested=url)

        except Exception as e:
            logger.error(f"Error getting console logs: {e}")
            return RuntimeResult(stdout=[], stderr=[str(e)], url_tested=url)

    async def _create_service(self, ports: list[int]) -> None:
        """Mock method to simulate service creation in debug mode."""
        logger.warning(
            "DebugSandbox._create_service is deprecated and should not be used"
        )
        logger.info(f"DebugSandbox: Simulating service creation on ports {ports}")
        # No actual service creation needed for local debug
        pass

    async def _create_pod_and_service(
        self, retries: int = 3, use_cache: bool = True
    ) -> str:
        """Mock method to simulate pod and service creation."""
        logger.warning(
            "DebugSandbox._create_pod_and_service is deprecated and should not be used"
        )
        logger.info("DebugSandbox: Simulating pod and service creation")
        # Return the mock IP address
        return self.ip

    @property
    def preview_url(self) -> str:
        """Match the Sandbox interface by providing a preview_url property"""
        return self.manager.public_preview_url
