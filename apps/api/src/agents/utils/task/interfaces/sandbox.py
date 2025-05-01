import asyncio
import base64
import os
import time
from typing import TYPE_CHECKING, AsyncGenerator

from morphcloud.api import (
    Instance,
    InstanceExecResponse,
    InstanceStatus,
    MorphCloudClient,
    Snapshot,
)

from src.config import MORPHCLOUD_API_KEY
from src.repos.settings.utils import get_runtime_files
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Sandbox:
    def __init__(self, task: "Task"):
        self.task: Task = task
        self.client: MorphCloudClient = MorphCloudClient(MORPHCLOUD_API_KEY)
        self.instance: Instance | None = None
        self.preview_url: str | None = None
        self.session_name: str = "react_start"
        self.nginx_session_name: str = "nginx_proxy"

    async def initialize_sandbox(self) -> str:
        if not await self._does_root_repo_exist():
            await self._create_root_repo_instance()

        start_time: float = time.time()
        self.instance = await self.get_repo_instance()
        end_time: float = time.time()
        logger.info(f"Got repo instance in {end_time - start_time} seconds")

        start_time: float = time.time()
        await self.instance.aresume()
        end_time: float = time.time()
        logger.info(f"Resumed in {end_time - start_time} seconds")

        start_time: float = time.time()
        self.preview_url = await self.instance.aexpose_http_service(
            name="react_service", port=80
        )
        end_time: float = time.time()
        logger.info(f"Exposed in {end_time - start_time} seconds")

        # start_time: float = time.time()
        # await self.inject_runtime_files(self.instance, self.preview_url)
        # end_time: float = time.time()
        # logger.info(f"Queried and injected in {end_time - start_time} seconds")

        port: int = await self.task.settings.get_port()
        start_time: float = time.time()
        await self._wait_til_server_running(
            self.instance, self.session_name, port, timeout=60
        )
        end_time: float = time.time()
        logger.info(f"Waited for server in {end_time - start_time} seconds")

        logger.info(f"Service URL: {self.preview_url}")
        return self.preview_url

    async def setup_branched_instance(self, instance: Instance) -> str:
        start_time: float = time.time()
        await instance.aresume()
        end_time: float = time.time()
        logger.info(f"Resumed branched instance in {end_time - start_time} seconds")

        await instance.aexec(
            f"tmux kill-session -t {self.session_name} 2>/dev/null || true"
        )

        port: int = await self.task.settings.get_port()
        await instance.aexec(f"kill -9 $(lsof -t -i :{port}) 2>/dev/null || true")

        preview_url: str = await instance.aexpose_http_service(
            name="react_service", port=80
        )

        await self.inject_runtime_files(instance, preview_url)

        subdirectory: str = await self.task.settings.get_root_directory()
        dev_command: str = await self.task.settings.get_dev_command()
        await self._start_background_process(
            instance,
            f"cd /repo{subdirectory} && {dev_command}",
            self.session_name,
        )

        port: int = await self.task.settings.get_port()
        if not await self._wait_til_server_running(
            instance, self.session_name, port, timeout=60
        ):
            logger.warning("Timed out waiting for dev server, attempting to restart it")
            await instance.aexec(f"tmux kill-session -t {self.session_name}")
            await self._start_background_process(
                instance,
                f"cd /repo{subdirectory} && {dev_command}",
                self.session_name,
            )
            if not await self._wait_til_server_running(
                instance, self.session_name, port, timeout=120
            ):
                raise RuntimeError(f"Dev server failed to start on port {port}")

        logger.info(f"Branched instance service URL: {preview_url}")

        return preview_url

    async def _setup_nginx_proxy(
        self, app_port: int, instance: Instance | None = None
    ) -> None:
        if instance is None:
            instance = self.instance

        nginx_conf: str = f"""
server {{
    listen 80 default_server;
    server_name _;
    
    location / {{
        proxy_pass http://localhost:{app_port};
        
        # Force host header to be localhost:3000 to match allowed hostnames
        proxy_set_header Host "localhost:{app_port}";
        
        # Set other headers for proper proxying
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host "localhost:{app_port}";
        proxy_set_header X-Forwarded-Port {app_port};
        
        # Increase gateway timeout
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        
        # Allow embedding in iframes
        add_header X-Frame-Options "ALLOWALL";
        add_header Content-Security-Policy "frame-ancestors *";
    }}
}}
"""
        # install_result: InstanceExecResponse = await instance.aexec(
        #     "which nginx || apt-get update && apt-get install -y nginx"
        # )
        # print(install_result.stdout)

        await instance.aexec("systemctl stop nginx || true")
        await instance.aexec("rm -f /etc/nginx/sites-enabled/default")

        conf_result: InstanceExecResponse = await instance.aexec(
            f"echo '{nginx_conf}' > /etc/nginx/sites-available/app"
        )
        if conf_result.exit_code != 0:
            raise RuntimeError(
                f"Failed to create Nginx configuration: {conf_result.stderr}"
            )

        link_result: InstanceExecResponse = await instance.aexec(
            "ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app"
        )
        if link_result.exit_code != 0:
            raise RuntimeError(f"Failed to enable Nginx site: {link_result.stderr}")

        test_result: InstanceExecResponse = await instance.aexec("nginx -t")
        if test_result.exit_code != 0:
            logger.error(f"Nginx configuration test failed: {test_result.stderr}")
            raise RuntimeError(f"Invalid Nginx configuration: {test_result.stderr}")

        nginx_cmd: str = 'nginx -g "daemon off;"'
        await self._start_background_process(
            instance, nginx_cmd, self.nginx_session_name
        )

        logger.info(
            f"Nginx reverse proxy set up on port 80, forwarding to application port {app_port}"
        )

    async def get_repo_instance(self) -> Instance:
        root_instances: list[Instance] = await self.client.instances.alist(
            metadata={
                "purpose": "sandbox_root_repo",
                "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
            }
        )
        if len(root_instances) == 0:
            raise RuntimeError(
                f"No sandbox_repo with identifier = {self.task.git.repo_id}-{self.task.workspace.name} found"
            )

        if len(root_instances) > 1:
            raise RuntimeError(
                f"Multiple sandbox_repo with identifier = {self.task.git.repo_id}-{self.task.workspace.name} found"
            )

        root_instance: Instance = root_instances[0]

        instances: list[Instance] = await self.client.instances.alist(
            metadata={
                "purpose": "sandbox_user_repo",
                "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
                "branched": "true",
            }
        )

        paused_instances: list[Instance] = [
            instance
            for instance in instances
            if instance.status != InstanceStatus.READY
        ]

        logger.info(f"Found {len(paused_instances)} paused instances")
        initial_time: float = time.time()
        if not paused_instances:
            logger.info("No paused instances found, creating new instance")
            await root_instance.aresume()
            _, clones = await root_instance.abranch(count=2)

            instance: Instance = clones[0]

            # Set up the first clone
            preview_url: str = await self.setup_branched_instance(instance)
            self.preview_url = preview_url

            async def cleanup_instances():
                other_instance: Instance = clones[1]
                # Set up the second clone in the background
                await self.setup_branched_instance(other_instance)
                await other_instance.apause()
                await root_instance.apause()

                await instance.aset_metadata(
                    {
                        "purpose": "sandbox_user_repo",
                        "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
                        "branched": "true",
                    }
                )
                await other_instance.aset_metadata(
                    {
                        "purpose": "sandbox_user_repo",
                        "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
                        "branched": "true",
                    }
                )

            asyncio.create_task(cleanup_instances())
        elif len(paused_instances) == 1:
            logger.info("Found 1 paused instance, using it")
            instance = paused_instances[0]

            self.preview_url = await instance.aexpose_http_service(
                name="react_service", port=80
            )

            async def create_new_instance():
                await root_instance.aresume()
                _, clones = await root_instance.abranch(count=1)

                # Set up the new clone
                new_instance: Instance = clones[0]
                await self.setup_branched_instance(new_instance)

                await new_instance.apause()
                await root_instance.apause()

                await new_instance.aset_metadata(
                    {
                        "purpose": "sandbox_user_repo",
                        "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
                        "branched": "true",
                    }
                )

            logger.info("Creating new instance in the background")
            start_time: float = time.time()
            asyncio.create_task(create_new_instance())
            end_time: float = time.time()
            logger.info(f"Created new instance in {end_time - start_time} seconds")

        elif len(paused_instances) > 1:
            logger.info("Found multiple paused instances, using the first one")
            instance = paused_instances[0]

            self.preview_url = await instance.aexpose_http_service(
                name="react_service", port=80
            )

        initial_end_time: float = time.time()
        logger.info(f"Initial setup in {initial_end_time - initial_time} seconds")

        return instance

    async def _does_root_repo_exist(self) -> bool:
        instances: list[Instance] = await self.client.instances.alist(
            metadata={
                "purpose": "sandbox_root_repo",
                "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
            }
        )
        return len(instances) > 0

    async def _create_root_repo_instance(self) -> Instance:
        start_time: float = time.time()
        base_sandbox_snapshot: Snapshot = await self._get_base_sandbox_snapshot()
        root_instance: Instance = await self.client.instances.astart(
            snapshot_id=base_sandbox_snapshot.id
        )
        end_time: float = time.time()
        logger.info(f"Instance started in {end_time - start_time} seconds")

        branch_name: str = await self.task.settings.get_current_branch()
        clone_result: InstanceExecResponse = await root_instance.aexec(
            command=f"git clone --branch={branch_name} {self.task.git.tokenized_clone_url} /repo"
        )
        if clone_result.exit_code != 0:
            raise RuntimeError(f"Failed to clone repo: {clone_result.stderr}")

        await root_instance.aexec(command="cd /repo && nvm install && nvm use")

        port: int = await self.task.settings.get_port()

        await self._setup_nginx_proxy(port, root_instance)

        await self.inject_runtime_files(root_instance)

        subdirectory: str = await self.task.settings.get_root_directory()
        install_command: str = await self.task.settings.get_install_command()
        logger.info(f"Installing {install_command} in {subdirectory}")
        install_time: float = time.time()

        if (
            install_command.startswith("yarn") and "--immutable" not in install_command
        ):  # FOR CAL.COM ONLY FOR NOW
            install_command += " --immutable"

        if (
            install_command.startswith("pnpm")
            and "--frozen-lockfile" not in install_command
        ):
            install_command += " --frozen-lockfile"

        install_result: InstanceExecResponse = await root_instance.aexec(
            command=f"export COREPACK_ENABLE_DOWNLOAD_PROMPT=0 && cd /repo{subdirectory} && {install_command} > /tmp/install_output.txt 2>&1",
        )
        exit_code: int = install_result.exit_code
        stdout: str = install_result.stdout
        stderr: str = install_result.stderr

        if exit_code > 0:
            with open("install_result.txt", "w") as f:
                f.write(f"Error: {stderr}\nOutput: {stdout}")
            raise RuntimeError(f"Failed to install - exit code {exit_code}")

        install_end_time: float = time.time()
        logger.info(f"Installed in {install_end_time - install_time} seconds")

        start_time: float = time.time()
        dev_command: str = await self.task.settings.get_dev_command()

        await self._start_background_process(
            root_instance, f"cd /repo{subdirectory} && {dev_command}", self.session_name
        )
        port: int = await self.task.settings.get_port()
        logger.info(f"Waiting for server to be running on port {port}")
        await self._wait_til_server_running(root_instance, self.session_name, port)
        await asyncio.sleep(2)
        end_time: float = time.time()
        logger.info(f"Started dev command in {end_time - start_time} seconds")

        instances: list[Instance] = await self.client.instances.alist(
            metadata={
                "purpose": "sandbox_root_repo",
                "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
            }
        )
        for x_instance in instances:
            logger.info(f"Deleting instance {x_instance.id}")
            await x_instance.astop()

        await root_instance.aset_metadata(
            {
                "purpose": "sandbox_root_repo",
                "identifier": f"{self.task.git.repo_id}-{self.task.workspace.name}",
            }
        )

        pause_time: float = time.time()
        await root_instance.apause()
        pause_end_time: float = time.time()
        logger.info(f"Paused in {pause_end_time - pause_time} seconds")

    async def _wait_til_server_running(
        self,
        instance: Instance,
        session_name: str,
        port: int,
        timeout: float | None = 300,
    ) -> bool:
        start_time: float = time.time()
        healthy_codes: set[str] = {
            "200",
            "500",
            "307",
            "201",
            "301",
            "302",
            "403",
            "304",
        }

        # TODO: Readd this without introducing more latency
        # result: InstanceExecResponse = await instance.aexec(
        #     f"tmux ls | grep {session_name}"
        # )
        # if result.exit_code != 0:
        #     logger.info("Tmux session not running")
        #     return False

        logger.info("Session name:", session_name)
        end_time: float = time.time()
        logger.info(f"Tmux session running in {end_time - start_time:.2f} seconds")
        start_time: float = time.time()
        while True:
            if timeout is not None and time.time() - start_time > timeout:
                logger.info(f"Server not running after {timeout} seconds")
                return False

            result: InstanceExecResponse = await instance.aexec(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}"
            )
            print(result.stdout)
            if result.stdout in healthy_codes:
                logger.info(
                    f"Server running after {time.time() - start_time:.2f} seconds"
                )
                return True
            await asyncio.sleep(1)

    async def _get_base_sandbox_snapshot(self) -> Snapshot:
        base_sandbox_snapshots: list[Snapshot] = await self.client.snapshots.alist(
            metadata={"purpose": "sandbox_base"}
        )

        if len(base_sandbox_snapshots) == 0:
            logger.info("No base sandbox snapshot found")
            exit()

        base_sandbox_snapshot: Snapshot = base_sandbox_snapshots[0]

        for snapshot in base_sandbox_snapshots:
            current_version: str = snapshot.metadata.get("version", "0.0.0")
            base_version: str = base_sandbox_snapshot.metadata.get("version", "0.0.0")

            current_parts: list[str] = current_version.split(".")
            base_parts: list[str] = base_version.split(".")

            is_newer: bool = False
            for i in range(max(len(current_parts), len(base_parts))):
                current_part: int = (
                    int(current_parts[i]) if i < len(current_parts) else 0
                )
                base_part: int = int(base_parts[i]) if i < len(base_parts) else 0

                if current_part > base_part:
                    is_newer = True
                    break
                elif current_part < base_part:
                    break

            if is_newer:
                logger.info(
                    f"Snapshot {snapshot.id} has a higher version ({current_version}) than {base_sandbox_snapshot.id} ({base_version})"
                )
                base_sandbox_snapshot = snapshot

        logger.info(
            f"Using base sandbox snapshot `{base_sandbox_snapshot.id}` on version {base_sandbox_snapshot.metadata['version']}"
        )

        return base_sandbox_snapshot

    async def _start_background_process(
        self, instance: Instance, command: str, session_name: str = "background_session"
    ) -> None:
        await instance.aexec(f"tmux kill-session -t {session_name} 2>/dev/null || true")

        escaped_command: str = command.replace('"', '\\"')
        tmux_cmd: str = f'tmux new-session -d -s {session_name} "{escaped_command}"'

        result: InstanceExecResponse = await instance.aexec(tmux_cmd)

        if result.exit_code != 0:
            raise RuntimeError(
                f"Failed to start tmux session ({tmux_cmd}): \nOutput:{result.stdout}\nError:{result.stderr}"
            )

        verify_result = await instance.aexec(f"tmux has-session -t {session_name}")
        if verify_result.exit_code != 0:
            raise RuntimeError(
                f"Failed to verify tmux session {session_name} is running"
            )

        logger.info(f"Started background process in tmux session: {session_name}")

    async def _stream_logs(
        self, instance: Instance, session_name: str, duration: float | None = None
    ) -> None:
        logger.info(f"\n{'─' * 50}")
        logger.info(f"\nAttaching to logs of session {session_name}:")

        start_time: float = time.time()

        with instance.ssh() as ssh:
            ssh.run(f"tmux pipe-pane -t {session_name} 'cat > /tmp/{session_name}.log'")

            last_position = 0
            while True:
                if duration is not None and time.time() - start_time > duration:
                    logger.info(f"\nStopped streaming after {duration} seconds")
                    break

                result = ssh.run(f"cat /tmp/{session_name}.log")
                current_output = result.stdout

                if len(current_output) > last_position:
                    new_output = current_output[last_position:]
                    logger.info(new_output, end="", flush=True)
                    last_position = len(current_output)

                try:
                    await asyncio.sleep(0.2)
                except KeyboardInterrupt:
                    logger.info("\nStreaming interrupted")
                    break

        logger.info(f"\n{'─' * 50}")
        logger.info("Detached from logs (process still running)")

    async def run_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> InstanceExecResponse:
        if timeout is not None:
            try:
                return await asyncio.wait_for(
                    asyncio.create_task(self.instance.aexec(command)), timeout=timeout
                )
            except asyncio.TimeoutError:
                return InstanceExecResponse(
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    exit_code=124,  # 124 is the exit code for timeout in Linux
                )

        return await self.instance.aexec(command)

    async def command_stream(
        self, command: str, instance: Instance | None = None
    ) -> AsyncGenerator[dict[str, str | int | list[str]], None]:
        last_stdout: str = ""
        last_stderr: str = ""
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        if not instance:
            if not self.instance:
                raise RuntimeError("No instance provided")
            instance = self.instance

        with instance.ssh() as ssh:
            with ssh.run(command, background=True) as process:
                while not process.completed:
                    current_stdout: str = process.stdout
                    if current_stdout != last_stdout:
                        new_output: str = current_stdout[len(last_stdout) :]
                        last_stdout = current_stdout
                        stdout_lines.extend(new_output.splitlines())
                        yield {
                            "status": "partial",
                            "output": new_output,
                            "type": "stdout",
                        }

                    current_stderr: str = process.stderr
                    if current_stderr != last_stderr:
                        new_stderr: str = current_stderr[len(last_stderr) :]
                        last_stderr = current_stderr
                        stderr_lines.extend(new_stderr.splitlines())
                        yield {
                            "status": "partial",
                            "output": new_stderr,
                            "type": "stderr",
                        }

                    await asyncio.sleep(0.01)

                returncode: int = process.channel.recv_exit_status()

                yield {
                    "status": "final",
                    "exit_code": returncode,
                    "stdout": stdout_lines,
                    "stderr": stderr_lines,
                }

    async def get_file(self, file_path: str) -> str | None:
        result: InstanceExecResponse = await self.instance.aexec(f"ls -l {file_path}")
        if result.exit_code != 0:
            return None

        return (await self.instance.aexec(f"cat {file_path}")).stdout

    async def write_file(
        self,
        file_path: str,
        content: str,
    ) -> bool:
        result: InstanceExecResponse = await self.instance.aexec(
            f"echo '{content}' > {file_path}"
        )
        return result.exit_code == 0

    async def destroy(self):
        if self.instance:
            await self.instance.astop()

    async def inject_runtime_files(
        self, instance: Instance, preview_url: str | None = None
    ) -> None:
        start_time: float = time.time()
        port: int = await self.task.settings.get_port()
        runtime_files: list[dict[str, str]] = get_runtime_files(self.task.git.repo_id)
        end_time: float = time.time()
        logger.info(f"Got runtime files in {end_time - start_time} seconds")

        start_time: float = time.time()
        for runtime_file in runtime_files:
            print(
                f"Writing {runtime_file['file_path']} with length {len(runtime_file['content'])}"
            )

            content = runtime_file["content"]
            if preview_url:
                content = content.replace(f"http://localhost:{port}", preview_url)

            encoded_content: str = base64.b64encode(content.encode()).decode()
            file_dir: str = os.path.dirname(runtime_file["file_path"])
            if file_dir:
                await instance.aexec(f"mkdir -p /repo/{file_dir}")

            result: InstanceExecResponse = await instance.aexec(
                f"echo '{encoded_content}' | base64 -d > /repo/{runtime_file['file_path']}"
            )

            if result.exit_code != 0:
                logger.warning(
                    f"Error writing file {runtime_file['file_path']}: {result.stderr}"
                )
        end_time: float = time.time()
        logger.info(f"Injected in {end_time - start_time} seconds")
