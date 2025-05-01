import asyncio
import contextlib
import logging
import os
import re
from typing import AsyncIterator

import aiohttp
import socketio
from aiohttp import ClientConnectorError, ServerDisconnectedError

from ._types import (
    CommandError,
    CommandExit,
    CommandKilled,
    CommandMode,
    CommandOutput,
    CommandResult,
    ContainerInfo,
    SandboxException,
)

logger: logging.Logger = logging.getLogger("sandbox")


class BackgroundProcess:
    def __init__(self, process_id: str | int, client: "ContainerClient"):
        self.process_id: int = process_id
        self._client: "ContainerClient" = client

    async def kill(self) -> CommandKilled:
        return await self._client.kill_command(str(self.process_id))


class StreamProcess:
    def __init__(
        self,
        process_id: int,
        stream_queue: asyncio.Queue,
        client: "ContainerClient",
    ):
        self.process_id: int = process_id
        self.stream_queue: asyncio.Queue[CommandOutput | CommandExit] = stream_queue
        self._finished: asyncio.Event = asyncio.Event()
        self.error: str | None = None
        self._client: "ContainerClient" = client

    async def kill(self) -> CommandKilled:
        return await self._client.kill_command(str(self.process_id))

    async def stream(self) -> AsyncIterator[CommandOutput | CommandExit]:
        while True:
            output: CommandOutput | CommandExit = await self.stream_queue.get()
            if isinstance(output, CommandExit):
                if self.error:
                    raise RuntimeError(f"Stream process error: {self.error}")
                yield output
                break
            if isinstance(output, CommandOutput):
                output.output = clean_output(output.output)
            yield output

    def __aiter__(self):
        return self.stream()

    async def __anext__(self):
        if self._finished.is_set():
            raise StopAsyncIteration

        data = await self.stream_queue.get()
        if isinstance(data, CommandExit):
            self._finished.set()
            raise StopAsyncIteration
        return data


class ContainerManager:
    def __init__(
        self,
        user_id: str,
        session_id: str,
        base_url: str = "http://localhost:8000",  # Default to manager service port
        is_local: bool = False,
    ):
        self.client: ContainerClient = ContainerClient(base_url)
        self.user_id: str = user_id
        self.session_id: str = session_id
        self.container_info: ContainerInfo | None = None
        self.manager_url: str = base_url
        self.is_local: bool = is_local  # Default to local mode
        self.exposed_ports: set[int] = set()  # Track exposed ports
        self.workspace_path: str = ""  # Where commands/file ops are executed

    async def start_container(self) -> ContainerInfo:
        """Start the container and establish connection."""
        container_info: ContainerInfo | None = None
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.manager_url}/containers/start",
                json={"user_id": self.user_id, "session_id": self.session_id},
            ) as response:
                if response.status != 200:
                    raise SandboxException(
                        f"Failed to start container: {await response.text()}"
                    )
                container_info_raw: dict = await response.json()
                container_info = ContainerInfo(**container_info_raw)

        if container_info is None:
            raise SandboxException("Failed to start container")

        self.container_info = container_info
        if self.is_local:
            self.client.url = "http://localhost:8002"  # WebSocket port
        else:
            self.client.url = (
                f"http://{container_info.container_ip}:{container_info.container_port}"
            )

        await self.client.connect()
        return container_info

    async def cleanup(self):
        """Cleanup resources and stop the container."""
        for port in list(self.exposed_ports):
            try:
                await self.unexpose_port(port)
            except Exception as e:
                logger.warning(f"Failed to unexpose port {port}: {e}")

        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self.manager_url}/containers/stop",
                json={"user_id": self.user_id, "session_id": self.session_id},
            )
        await self.client.disconnect()

    def _clean_path(self, path: str | None) -> str:
        if path is None or path == "":
            return self.workspace_path or "/"

        clean_path: str = os.path.normpath(path)
        if clean_path.startswith(".."):
            raise ValueError("Path cannot navigate above root directory")

        if self.workspace_path:
            return os.path.join(self.workspace_path, clean_path.lstrip("/"))
        else:
            return "/" + clean_path.lstrip("/")

    async def run_command(
        self,
        command: str,
        mode: CommandMode = CommandMode.WAIT,
        path: str | None = None,
        timeout: int | None = None,
    ) -> CommandResult | BackgroundProcess | StreamProcess:
        full_path: str = self._clean_path(path)
        return await self.client.run_command(
            command=command,
            mode=mode,
            path=full_path,
            timeout=timeout,
        )

    async def write_file(
        self, path: str, content: str, make_dirs: bool = False
    ) -> bool:
        """Write content to a file in the container."""
        full_path: str = self._clean_path(path)
        return await self.client.write_file(
            file_path=full_path,
            content=content,
            make_dirs=make_dirs,
        )

    async def read_file(self, path: str) -> str:
        """Read content from a file in the container."""
        full_path: str = self._clean_path(path)
        return await self.client.read_file(file_path=full_path)

    async def delete_file(self, path: str) -> bool:
        """Delete a file in the container."""
        full_path: str = self._clean_path(path)
        return await self.client.delete_file(file_path=full_path)

    async def set_preview_port(self, port: int) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.manager_url}/containers/set_preview_port",
                json={
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "port": str(port),
                },
            ) as response:
                if response.status != 200:
                    raise SandboxException(
                        f"Failed to set preview port: {await response.text()}"
                    )
                res: dict = await response.json()
                success: bool = res.get("success", False)
                return success

    async def expose_port(self, port: int, is_app: bool = False) -> dict:
        """Expose a new port for the container."""
        result: dict = await self.client.expose_port(port, is_app=is_app)
        if status := result.get("status") == "exposed":
            self.exposed_ports.add(port)
        if not status:
            logger.warning(f"Failed to expose port {port}: {result}")
        return result

    async def unexpose_port(self, port: int) -> dict:
        """Stop exposing a port."""
        result: dict = await self.client.unexpose_port(port)
        if status := result.get("status") == "unexposed":
            self.exposed_ports.discard(port)
        if not status:
            logger.warning(f"Failed to unexpose port {port}: {result}")
        return result

    async def clear_port(self, port: int) -> bool:
        """Force kill any processes using the specified port."""
        return await self.client.clear_port(port)

    async def kill_all_processes(self) -> bool:
        """Force kill all processes running in the container."""
        return await self.client.kill_all_processes()

    async def list_dir_caches(self) -> list[dict]:
        """List all available directory caches in EFS.

        Returns:
            List of cache information dictionaries.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.manager_url}/dir_cache/list",
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error listing directory caches: {error_text}")
                    return []

                result = await response.json()
                return result.get("caches", [])

    async def delete_dir_cache(self, cache_name: str) -> bool:
        """Delete a directory cache from EFS.

        Args:
            cache_name: Name of the cache to delete

        Returns:
            Success status
        """
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.manager_url}/dir_cache/delete/{cache_name}",
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error deleting directory cache: {error_text}")
                    return False

                return True

    async def save_dir_cache(self, path: str, cache_name: str) -> tuple[bool, str]:
        """Save a directory to the cache.

        Args:
            path: Path to the directory to cache
            cache_name: Name to use for the cache

        Returns:
            Tuple of (success, cache_name)
        """
        return await self.client.save_dir_cache(path, cache_name)

    async def restore_dir_cache(self, cache_name: str, path: str) -> bool:
        """Restore a directory cache.

        Args:
            cache_name: Name of the cache to restore
            path: Path where to restore the cache

        Returns:
            Success status
        """
        return await self.client.restore_dir_cache(cache_name, path)

    @property
    def public_preview_url(self) -> str:
        return f"{self.manager_url}/preview/{self.user_id}/{self.session_id}/"


class ContainerClient:
    def __init__(self, url: str = "http://localhost:80"):
        self.url = url
        self.sio = socketio.AsyncClient()
        self.client_session: aiohttp.ClientSession | None = None
        self.connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.sessions = {}
        self.initialized_event = asyncio.Event()
        self.stream_queues: dict[int, asyncio.Queue] = {}
        self.result_event = asyncio.Event()
        self.result_data = None

        self.sio.on("connect", self.on_connect)
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("initialized", self.on_initialized)
        self.sio.on("command_output", self.on_command_output)
        self.sio.on("command_exit", self.on_command_exit)
        self.sio.on("command_result", self.on_command_result)
        self.sio.on("command_killed", self.on_killed)
        self.sio.on("command_error", self.on_command_error)

    async def on_connect(self):
        logger.debug("Connected to the server")

    async def on_disconnect(self):
        logger.debug("Disconnected from the server")

    async def on_initialized(self, data):
        logger.debug("Initialization response: %s", data)
        self.initialized_event.set()

    async def on_command_output(self, data):
        data: CommandOutput = CommandOutput(**data)
        data.output = clean_output(data.output)
        await self.get_stream_queue(data.process_id).put(data)

    async def on_command_exit(self, data):
        exit_info: CommandExit = CommandExit(**data)
        logger.debug(
            "Command exited with code %s (Process ID: %s)",
            exit_info.exit_code,
            exit_info.process_id,
        )
        await self.stream_queues[exit_info.process_id].put(exit_info)

    async def on_command_result(self, data):
        self.result_data: CommandResult = CommandResult(**data)
        self.result_data.stdout = clean_output(self.result_data.stdout)
        self.result_data.stderr = clean_output(self.result_data.stderr)
        self.result_event.set()

    async def on_killed(self, data):
        killed_info: CommandKilled = CommandKilled(**data)
        logger.debug("Command killed: %s", killed_info)

    async def on_command_error(self, data):
        error_info: CommandError = CommandError(**data)
        error_info.error = clean_output(error_info.error)
        process_id = data.get("process_id")
        if process_id and process_id in self.stream_queues:
            stream_queue = self.stream_queues[process_id]
            await stream_queue.put(CommandExit(exit_code=1, process_id=process_id))

    async def connect(self):
        max_attempts: int = 10
        for attempt in range(max_attempts):
            try:
                if self.sio.connected:
                    await self.sio.disconnect()

                if not self.client_session or self.client_session.closed:
                    self.client_session = aiohttp.ClientSession(
                        connector=self.connector
                    )

                ws_url: str = self.url.replace("http://", "ws://")
                await self.sio.connect(ws_url, transports=["websocket"])
                logger.info("Successfully connected to websocket server")
                return

            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                else:
                    raise ConnectionError(
                        f"Failed to connect after {max_attempts} attempts"
                    ) from e

    async def ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if not self.sio.connected:
                await self.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to establish connection: {e}")
            raise

    async def _make_request(
        self, method: str, endpoint: str, max_retries: int = 3, **kwargs
    ) -> aiohttp.ClientResponse:
        for attempt in range(1, max_retries + 1):
            try:
                await self.ensure_connection()

                if not self.client_session or self.client_session.closed:
                    self.client_session = aiohttp.ClientSession(
                        connector=self.connector
                    )

                try:
                    if method.lower() == "get":
                        return await self.client_session.get(
                            f"{self.url}/{endpoint}", **kwargs
                        )
                    else:
                        return await self.client_session.post(
                            f"{self.url}/{endpoint}", **kwargs
                        )
                except RuntimeError as e:
                    if str(e) == "Session is closed":
                        # Force session recreation on next attempt
                        await self.client_session.close()
                        self.client_session = None
                        if attempt < max_retries:
                            continue
                    raise

            except (ServerDisconnectedError, ClientConnectorError) as e:
                logger.warning(
                    f"Connection error during {method.upper()} {endpoint}: {e}. "
                    f"Attempt {attempt} of {max_retries}."
                )
                if attempt < max_retries:
                    await asyncio.sleep(2)
                else:
                    logger.error(
                        f"All {max_retries} retries failed for {method.upper()} {endpoint}."
                    )
                    raise

    def get_stream_queue(self, process_id: int) -> asyncio.Queue:
        assert isinstance(process_id, int)
        if process_id not in self.stream_queues:
            self.stream_queues[process_id] = asyncio.Queue()
        return self.stream_queues[process_id]

    async def run_command(
        self,
        command: str,
        mode: CommandMode = CommandMode.STREAM,
        path: str | None = None,
        timeout: int | None = None,
    ) -> CommandResult | BackgroundProcess | StreamProcess:
        assert mode in [CommandMode.WAIT, CommandMode.STREAM, CommandMode.BACKGROUND]
        await self.ensure_connection()

        payload: dict[str, str | int] = {
            "command": command,
            "mode": mode.value,
            "path": path,
            "timeout": timeout,
        }

        response: aiohttp.ClientResponse = await self._make_request(
            "POST", "run_command", json=payload
        )

        if response.status != 200:
            error_text = await response.text()
            raise SandboxException(f"Failed to execute command: {error_text}")

        response_data = await response.json()

        if "error" in response_data:
            return CommandResult(
                stdout="",
                stderr=response_data["error"],
                exit_code=1,
                finished=False,
            )

        if mode == CommandMode.WAIT:
            return CommandResult(
                stdout=response_data.get("stdout", ""),
                stderr=response_data.get("stderr", ""),
                exit_code=response_data.get("exit_code", 1),
            )

        elif mode == CommandMode.STREAM:
            process_id: int = response_data["process_id"]
            stream_queue: asyncio.Queue[CommandOutput | CommandExit] = asyncio.Queue()
            self.stream_queues[process_id] = stream_queue

            await self.sio.emit(
                "start_command_stream",
                {"process_id": process_id},
            )

            return StreamProcess(
                process_id=process_id,
                stream_queue=stream_queue,
                client=self,
            )

        elif mode == CommandMode.BACKGROUND:
            process_id: int = response_data["process_id"]
            return BackgroundProcess(process_id=process_id, client=self)

    async def kill_all_processes(self) -> bool:
        async with await self._make_request(
            "post",
            "kill_all_processes",
        ) as response:
            response_body: dict = await response.json()
            _failed_processes: list[str] = response_body.get("failed_processes", [])
            return response_body.get("success", False)

    async def kill_command(self, process_id: str) -> CommandKilled:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.url}/kill_command",
                json={"process_id": process_id},
            ) as response:
                result = await response.json()

        if "status" not in result:
            result["status"] = "not found"

        return CommandKilled(**result)

    async def disconnect(self):
        """Disconnect from the server and clean up resources."""
        for queue in self.stream_queues.values():
            while not queue.empty():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
        self.stream_queues.clear()

        if self.client_session and not self.client_session.closed:
            await self.client_session.close()

        await self.sio.disconnect()
        await self.sio.eio.disconnect()

    async def read_file(self, file_path: str) -> str:
        async with await self._make_request(
            "get",
            "read_file",
            params={"file_path": file_path},
        ) as response:
            response_body: dict = await response.json()
            if response.status == 200 and "content" in response_body:
                return response_body["content"]
            else:
                raise SandboxException(
                    f"Failed to get file ({file_path}): {response.status}"
                )

    async def write_file(self, file_path: str, content: str, make_dirs: bool = False):
        async with await self._make_request(
            "post",
            "write_file",
            json={
                "file_path": file_path,
                "content": content,
                "make_dirs": make_dirs,
            },
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise SandboxException(
                    f"Failed to write file ({file_path}): {response.status}"
                )

    async def delete_file(self, file_path: str) -> bool:
        async with await self._make_request(
            "post",
            "delete_file",
            json={"file_path": file_path},
        ) as response:
            response_body: dict = await response.json()
            if response.status == 200:
                return response_body.get("success", False)
            else:
                raise SandboxException(
                    f"Failed to delete file ({file_path}): {response.status}"
                )

    async def file_exists(self, file_path: str) -> bool:
        async with await self._make_request(
            "get",
            "file_exists",
            params={"file_path": file_path},
        ) as response:
            if response.status == 200:
                return bool((await response.json())["exists"])
            elif response.status == 404:
                return False
            else:
                raise SandboxException(
                    f"Failed to check if file exists ({file_path}): {response.status}"
                )

    async def expose_port(self, port: int, is_app: bool = False) -> dict:
        """Expose a new port for the container."""
        await self.ensure_connection()
        async with await self._make_request(
            "POST",
            "expose_port",
            json={"port": port, "is_app": is_app},
        ) as response:
            return await response.json()

    async def unexpose_port(self, port: int) -> dict:
        """Stop exposing a port."""
        await self.ensure_connection()
        async with await self._make_request(
            "POST",
            "unexpose_port",
            json={"port": port},
        ) as response:
            return await response.json()

    async def clear_port(self, port: int) -> bool:
        """Force kill any processes using the specified port."""
        await self.ensure_connection()
        async with await self._make_request(
            "POST",
            "clear_port",
            json={"port": port},
        ) as response:
            result = await response.json()
            return result.get("success", False)

    async def save_dir_cache(self, path: str, cache_name: str) -> tuple[bool, str]:
        """Save a directory to the cache.

        Args:
            path: Path to the directory to cache
            cache_name: Name to use for the cache

        Returns:
            Tuple of (success, cache_name)
        """
        try:
            await self.ensure_connection()
            async with await self._make_request(
                "post",
                "dir_cache/save",
                json={
                    "path": path,
                    "cache_name": cache_name,
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error saving directory cache: {error_text}")
                    return False, ""

                result = await response.json()
                return True, result.get("cache_name", "")
        except Exception as e:
            logger.error(f"Error saving directory cache: {e}")
            return False, ""

    async def restore_dir_cache(self, cache_name: str, path: str) -> bool:
        """Restore a directory cache.

        Args:
            cache_name: Name of the cache to restore
            path: Path where to restore the cache

        Returns:
            Success status
        """
        try:
            await self.ensure_connection()
            async with await self._make_request(
                "post",
                "dir_cache/restore",
                json={
                    "path": path,
                    "cache_name": cache_name,
                },
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Error restoring directory cache: {error_text}")
                    return False

                result: dict = await response.json()
                return result.get("status", "error") == "restored"
        except Exception as e:
            logger.error(f"Error restoring directory cache: {e}")
            return False


def clean_output(output: str | None) -> str | None:
    """Clean ANSI escape sequences from output."""
    if output is None:
        logger.warning("clean_output received None value")
        return ""

    ansi_escape: re.Pattern = re.compile(r"\x1b\[([0-9]+)(;[0-9]+)*m")
    return ansi_escape.sub("", output)
