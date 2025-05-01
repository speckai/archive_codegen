from typing import TYPE_CHECKING, Optional, Set

from morphcloud.api import (
    InstanceExecResponse,
)
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.debug.common import Debug
    from src.agents.utils.task.debug.sandbox import DebugSandbox


class DebugContainerManager:
    """Mock implementation of ContainerManager for debug mode"""

    def __init__(self, sandbox: "DebugSandbox", debug: "Debug"):
        self.sandbox = sandbox
        self.workspace_path = str(debug.repo_dir)
        self.exposed_ports: Set[int] = set()  # Track exposed ports
        self.preview_port: Optional[int] = debug.settings.port

    @property
    def public_preview_url(self) -> str:
        """Get the public preview URL based on the exposed ports"""
        if self.preview_port:
            return f"https://{self.sandbox.ip}:{self.preview_port}"
        elif self.exposed_ports:
            # Use the first exposed port if preview port not set
            return f"https://{self.sandbox.ip}:{next(iter(self.exposed_ports))}"
        return f"https://{self.sandbox.ip}"

    async def read_file(self, file_path: str) -> str:
        """Read a file from the local filesystem"""
        return await self.sandbox.get_file(file_path, use_repo_subdir=False)

    async def write_file(
        self,
        file_path: str,
        content: str,
        make_dirs: bool = False,
        use_repo_subdir: bool = False,
    ) -> dict:
        """Write a file to the local filesystem"""
        return await self.sandbox.write_file(file_path, content)

    async def run_command(
        self,
        command: str,
    ) -> InstanceExecResponse:
        """Run a command in the local environment"""
        return await self.sandbox.run_command(
            command,
        )

    async def expose_port(self, port: int, is_app: bool = False) -> dict:
        """Mock implementation for exposing a port"""
        logger.info(f"Debug MockManager: Exposing port {port} (mock implementation)")
        self.exposed_ports.add(port)
        if is_app:
            self.preview_port = port
        return {"status": "exposed", "port": port}

    async def unexpose_port(self, port: int) -> dict:
        """Mock implementation for unexposing a port"""
        logger.info(f"Debug MockManager: Unexposing port {port} (mock implementation)")
        self.exposed_ports.discard(port)
        if self.preview_port == port:
            self.preview_port = None
        return {"status": "unexposed", "port": port}

    async def set_preview_port(self, port: int) -> bool:
        """Mock implementation for setting preview port"""
        logger.info(
            f"Debug MockManager: Setting preview port to {port} (mock implementation)"
        )
        self.preview_port = port
        return True

    async def clear_port(self, port: int) -> bool:
        """Mock implementation for clearing port"""
        logger.info(f"Debug MockManager: Clearing port {port} (mock implementation)")
        return True

    async def cleanup(self) -> bool:
        """Cleanup any resources used by the mock manager"""
        await self.sandbox.kill_all_processes()
        self.exposed_ports.clear()
        self.preview_port = None
        return True
