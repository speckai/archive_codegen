import asyncio
import contextlib
import hashlib
import json
import os
import signal
import subprocess
import time
from asyncio.subprocess import Process
from datetime import datetime
from enum import StrEnum

import socketio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

app: FastAPI = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio: socketio.AsyncServer = socketio.AsyncServer(
    async_mode="asgi",
    max_http_buffer_size=10_000_000,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    reconnection=True,
    reconnection_attempts=3,
    reconnection_delay=1000,
    reconnection_delay_max=5000,
)
socket_app: socketio.ASGIApp = socketio.ASGIApp(socketio_server=sio)
app.mount("/socket.io", socket_app)

active_processes: dict[int, Process] = {}
_last_disconnect: float = 0
_cleanup_task: asyncio.Task | None = None
_cleanup_event: asyncio.Event | None = None
INACTIVITY_TIMEOUT = 30
CLEANUP_CHECK_INTERVAL = 15

PNPM_STORE_DIR = os.getenv("PNPM_STORE_DIR", "/efs/pnpm-store")
NPM_CACHE_DIR = os.getenv("NPM_CACHE_DIR", "/efs/npm-cache")
YARN_CACHE_FOLDER = os.getenv("YARN_CACHE_FOLDER", "/efs/yarn-cache")
BUN_CACHE_DIR = os.getenv("BUN_CACHE_DIR", "/efs/bun-cache")
EFS_MOUNT_PATH = os.getenv("EFS_MOUNT_PATH", "/efs")
DIR_CACHE_DIR = os.getenv("DIR_CACHE_DIR", "/efs/dir-cache")
CACHE_METADATA_FILE = os.path.join(DIR_CACHE_DIR, "cache_metadata.json")


class ExecutionMode(StrEnum):
    WAIT = "wait"
    BACKGROUND = "background"
    STREAM = "stream"


async def _cleanup_handler():
    """Background task to handle cleanup when triggered."""
    global _cleanup_event

    if not _cleanup_event:
        _cleanup_event = asyncio.Event()

    try:
        while True:
            await _cleanup_event.wait()
            _cleanup_event.clear()

            current_time = time.time()
            if (
                _last_disconnect > 0
                and current_time - _last_disconnect > INACTIVITY_TIMEOUT
            ):
                logger.info("Container disconnected and inactive, cleaning up...")
                await cleanup_all()
    except asyncio.CancelledError:
        logger.info("Cleanup handler cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in cleanup handler: {e}")


async def schedule_cleanup():
    """Schedule a cleanup check."""
    if _cleanup_event:
        _cleanup_event.set()


async def cleanup_all():
    """Clean up all processes and workspace."""
    await kill_all_processes()

    try:
        env: dict[str, str] = os.environ.copy()
        env["PATH"] = (
            "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
            + env.get("PATH", "")
        )

        proc = await asyncio.create_subprocess_shell(
            "rm -rf /workspace/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        await proc.communicate()
        logger.info("Cleaned up /workspace/repo directory")
    except Exception as e:
        logger.error(f"Error cleaning up repo directory: {e}")


async def load_cache_metadata() -> dict:
    """Load cache metadata from file."""
    try:
        if os.path.exists(CACHE_METADATA_FILE):
            with open(CACHE_METADATA_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading cache metadata: {e}")
        return {}


async def save_cache_metadata(metadata: dict):
    """Save cache metadata to file."""
    try:
        logger.info(f"Saving cache metadata to {CACHE_METADATA_FILE}")
        os.makedirs(os.path.dirname(CACHE_METADATA_FILE), exist_ok=True)
        with open(CACHE_METADATA_FILE, "w") as f:
            json.dump(metadata, f)
    except Exception as e:
        logger.error(f"Error saving cache metadata: {e}")


def ensure_package_cache_dirs():
    """Ensure package cache directories exist and have correct permissions."""
    try:
        if not os.path.ismount(EFS_MOUNT_PATH):
            logger.warning(f"EFS does not appear to be mounted at {EFS_MOUNT_PATH}")

        os.makedirs(PNPM_STORE_DIR, exist_ok=True)
        os.makedirs(NPM_CACHE_DIR, exist_ok=True)
        os.makedirs(YARN_CACHE_FOLDER, exist_ok=True)
        os.makedirs(BUN_CACHE_DIR, exist_ok=True)
        os.makedirs(DIR_CACHE_DIR, exist_ok=True)

        try:
            subprocess.run(["chmod", "777", EFS_MOUNT_PATH], check=False)
            subprocess.run(["chmod", "777", PNPM_STORE_DIR], check=False)
            subprocess.run(["chmod", "777", NPM_CACHE_DIR], check=False)
            subprocess.run(["chmod", "777", YARN_CACHE_FOLDER], check=False)
            subprocess.run(["chmod", "777", BUN_CACHE_DIR], check=False)
            subprocess.run(["chmod", "777", DIR_CACHE_DIR], check=False)
            logger.info("Set permissions on cache directories")
        except Exception as chmod_error:
            logger.warning(f"Non-critical error setting permissions: {chmod_error}")

        logger.info(f"Package cache directories configured at {EFS_MOUNT_PATH}")
        logger.info(f"PNPM store: {PNPM_STORE_DIR}")
        logger.info(f"NPM: {NPM_CACHE_DIR}")
        logger.info(f"Yarn: {YARN_CACHE_FOLDER}")
        logger.info(f"Bun: {BUN_CACHE_DIR}")
        logger.info(f"Directory Cache: {DIR_CACHE_DIR}")

        # home_dir = os.path.expanduser("~")

        # with open(os.path.join(home_dir, ".npmrc"), "w") as f:
        #     f.write(f"cache={NPM_CACHE_DIR}\n")

        # with open(os.path.join(home_dir, ".pnpmrc"), "w") as f:
        #     f.write(f"store-dir={PNPM_STORE_DIR}\n")

        os.makedirs("/etc/pnpm", exist_ok=True)
        with open("/etc/pnpm/rc", "w") as f:
            f.write(f"store-dir={PNPM_STORE_DIR}\n")

        # for cmd in [
        #     f"pnpm config set store-dir {PNPM_STORE_DIR}",
        #     f"npm config set cache {NPM_CACHE_DIR}",
        #     f"yarn config set cache-folder {YARN_CACHE_FOLDER}",
        # ]:
        #     result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        #     if result.returncode != 0:
        #         logger.warning(f"Failed to configure package manager: {cmd}")
        #         logger.warning(f"Error: {result.stderr}")

        os.environ["BUN_INSTALL_CACHE_DIR"] = BUN_CACHE_DIR
        logger.info(
            f"Set BUN_INSTALL_CACHE_DIR environment variable to {BUN_CACHE_DIR}"
        )

    except Exception as e:
        logger.error(f"Error setting up package cache directories: {e}")


@app.on_event("startup")
async def startup_event():
    """Start the cleanup handler on startup."""
    global _cleanup_task
    if not _cleanup_task:
        _cleanup_task = asyncio.create_task(_cleanup_handler())

    ensure_package_cache_dirs()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    if _cleanup_task:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
    await cleanup_all()


@app.get("/health")
async def health_check():
    """Health check endpoint for ALB."""
    efs_status: str = "healthy" if os.path.ismount(EFS_MOUNT_PATH) else "not_mounted"

    return {
        "status": "healthy",
        "last_disconnect": _last_disconnect,
        "efs_status": efs_status,
        "package_cache": {
            "pnpm_dir": os.path.exists(PNPM_STORE_DIR),
            "npm_dir": os.path.exists(NPM_CACHE_DIR),
            "yarn_dir": os.path.exists(YARN_CACHE_FOLDER),
            "bun_dir": os.path.exists(BUN_CACHE_DIR),
        },
        "dir_cache": os.path.exists(DIR_CACHE_DIR),
    }


@app.post("/run_command")
async def run_command(data: dict):
    command: str = data.get("command", "")
    path: str = data.get("path", "/")
    mode: ExecutionMode = data.get("mode", ExecutionMode.WAIT)
    timeout: int = data.get("timeout", 300)

    env = os.environ.copy()
    env.update(
        {
            "PNPM_STORE_DIR": PNPM_STORE_DIR,
            "NPM_CONFIG_CACHE": NPM_CACHE_DIR,
            "BUN_CACHE": BUN_CACHE_DIR,
            "NODE_OPTIONS": "--max-old-space-size=6144 --max-http-header-size=16384 --dns-result-order=ipv4first",
            "PNPM_NETWORK_CONCURRENCY": "192",
            "PNPM_CHILD_CONCURRENCY": "16",
            "PNPM_SHAMEFULLY_HOIST": "true",
            "PNPM_PREFER_OFFLINE": "true",
            "PNPM_REGISTRY_TIMEOUT": "60000",
            "PNPM_FETCH_TIMEOUT": "60000",
            "PNPM_FETCH_RETRIES": "5",
            "PNPM_NO_VERIFY_STORE_INTEGRITY": "true",
            "PNPM_REPORTER": "append-only",
            "UV_THREADPOOL_SIZE": "32",
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "NO_PROXY": "*",
            "NVM_DIR": os.path.expanduser("~/.nvm"),
            # Ensure PATH includes standard binary locations and preserves the existing path
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
            + env.get("PATH", ""),
        }
    )

    logger.info(f"NVM_DIR: {os.path.expanduser('~/.nvm')}")

    if not command or command.isspace():
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path does not exist")

    if mode in [ExecutionMode.STREAM, ExecutionMode.BACKGROUND]:
        try:
            process: Process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=path,
                env=env,
                preexec_fn=os.setsid,
            )
            active_processes[process.pid] = process
            return {"process_id": process.pid}
        except Exception as e:
            logger.error(f"Failed to start command: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    elif mode == ExecutionMode.WAIT:
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=path,
                env=env,
                preexec_fn=os.setsid,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                return {
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "exit_code": process.returncode,
                }
            except asyncio.TimeoutError as e:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except Exception as e:
                    logger.error(f"Failed to kill process group: {e}")
                raise HTTPException(status_code=504, detail="Command timed out") from e
            except Exception as e:
                logger.error(f"Error during command execution: {e}")
                raise HTTPException(status_code=500, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Failed to start command: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/kill_command")
async def kill_command(data: dict) -> dict:
    if not (process_id := data.get("process_id")):
        return {"error": "Invalid process ID"}

    if not (process := active_processes.get(int(process_id))):
        raise HTTPException(status_code=404, detail="Process not found")

    try:
        try:
            pgid: int = os.getpgid(process.pid)
            os.killpg(pgid, signal.SIGTERM)
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except (ProcessLookupError, asyncio.TimeoutError):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, signal.SIGKILL)
                await process.wait()
        except Exception:
            for pid in (
                subprocess.run(
                    ["pgrep", "-P", str(process.pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                .stdout.strip()
                .split()
            ):
                subprocess.run(["kill", "-9", pid], check=False)

            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        del active_processes[int(process_id)]
        return {"status": "killed", "exit_code": process.returncode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/kill_all_processes")
async def kill_all_processes() -> dict:
    """Kill all tracked processes and any lingering processes."""
    failed_processes: list[dict] = []

    async def kill_process_with_timeout(
        process: Process, pid: int, timeout: int = 5
    ) -> dict | None:
        try:
            logger.info(f"Sending SIGTERM to process {pid}")
            try:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=timeout)
                    logger.info(f"Process {pid} terminated with SIGTERM")
                    return None
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Process {pid} did not respond to SIGTERM, trying SIGKILL"
                    )
                    process.kill()
                    await process.wait()
                    logger.info(f"Process {pid} killed with SIGKILL")
                    return None
            except ProcessLookupError:
                logger.info(f"Process {pid} already terminated")
                return None
            except Exception as e:
                logger.error(f"Error terminating process {pid} with SIGTERM: {e}")
                try:
                    process.kill()
                    await process.wait()
                    logger.info(
                        f"Process {pid} killed with SIGKILL after SIGTERM failed"
                    )
                    return None
                except Exception as e2:
                    logger.error(f"Error killing process {pid} with SIGKILL: {e2}")
                    return {"pid": pid, "error": str(e2)}
        except Exception as e:
            error_msg: str = str(e) or "Unknown error killing process"
            logger.error(f"Error killing process {pid}: {error_msg}")
            try:
                os.kill(pid, signal.SIGKILL)
                logger.info(f"Process {pid} killed with OS SIGKILL")
                return None
            except Exception as e3:
                logger.error(f"Failed to kill process {pid} with OS SIGKILL: {e3}")
                return {"pid": pid, "error": error_msg}

    kill_tasks: list[asyncio.Task] = [
        kill_process_with_timeout(process, pid)
        for pid, process in list(active_processes.items())
    ]
    results: list[dict | Exception] = await asyncio.gather(
        *kill_tasks, return_exceptions=True
    )
    failed_processes.extend([r for r in results if r is not None])
    active_processes.clear()

    env = os.environ.copy()
    env["PATH"] = (
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
        + env.get("PATH", "")
    )

    cleanup_commands: list[str] = [
        "pkill -9 -f 'node|npm|next|pnpm|yarn'",
        "pkill -9 -f 'docker-proxy|socat'",
        "pkill -9 -f 'sh|bash'",
    ]

    for cmd in cleanup_commands:
        logger.info(f"Running cleanup command: {cmd}")
        cleanup_process: Process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await cleanup_process.communicate()
        if stdout:
            logger.info(f"Cleanup stdout: {stdout.decode()}")
        if stderr:
            logger.warning(f"Cleanup stderr: {stderr.decode()}")
        await cleanup_process.wait()

    logger.info("Clearing all ports in range 1000-6999...")
    port_clear_commands: list[str] = [
        "for port in $(seq 1000 6999); do fuser -k $port/tcp 2>/dev/null || true; done",
        "for port in $(seq 1000 6999); do lsof -t -i :$port | xargs -r kill -9 2>/dev/null || true; done",
        'for port in $(seq 1000 6999); do pkill -f "docker-proxy.*:$port" 2>/dev/null || true; done',
    ]

    for cmd in port_clear_commands:
        logger.info(f"Running port cleanup command: {cmd}")
        cleanup_process: Process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await cleanup_process.communicate()
        if stdout:
            logger.info(f"Port cleanup stdout: {stdout.decode()}")
        if stderr:
            logger.warning(f"Port cleanup stderr: {stderr.decode()}")
        await cleanup_process.wait()

    ps_process: Process = await asyncio.create_subprocess_shell(
        "ps aux | grep -E 'node|npm|next|pnpm|yarn|docker-proxy|socat|python|sh|bash' | grep -v grep",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True,
        env=env,
    )
    stdout, stderr = await ps_process.communicate()
    if stdout:
        logger.warning(f"Remaining processes after cleanup:\n{stdout.decode()}")

    logger.info(f"Failed processes: {failed_processes}")
    return {"success": not failed_processes, "failed_processes": failed_processes}


@app.post("/write_file")
async def write_file(request: Request):
    data: dict = await request.json()
    file_path: str = data.get("file_path")
    content: str = data.get("content")
    make_dirs: bool = data.get("make_dirs", False)

    if make_dirs:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, "w") as f:
            f.write(content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/delete_file")
async def delete_file(request: Request):
    data: dict = await request.json()
    file_path: str = data.get("file_path")
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/read_file")
async def read_file(request: Request, file_path: str):
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r") as f:
            content: str = f.read()
        return JSONResponse({"content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/expose_port")
async def expose_port(data: dict):
    port: int | None = data.get("port")
    is_app: bool = data.get("is_app", False)
    if not port:
        raise HTTPException(status_code=400, detail="Port number is required")

    try:
        process: Process = await asyncio.create_subprocess_shell(
            f"docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port {port} -container-ip 127.0.0.1 -container-port {port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        active_processes[process.pid] = process

        socat_process: Process = await asyncio.create_subprocess_shell(
            f"socat TCP-LISTEN:{port},fork,reuseaddr TCP:localhost:{port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        active_processes[socat_process.pid] = socat_process

        return {
            "status": "exposed",
            "port": port,
            "is_app": is_app,
            "process_ids": [process.pid, socat_process.pid],
        }
    except Exception as e:
        logger.error(f"Failed to expose port {port}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/unexpose_port")
async def unexpose_port(data: dict):
    port: int | None = data.get("port")
    if not port:
        raise HTTPException(status_code=400, detail="Port number is required")

    try:
        process: Process = await asyncio.create_subprocess_shell(
            f"pgrep -f 'docker-proxy.*:{port}|socat.*:{port}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()

        pids: list[int] = [int(pid) for pid in stdout.decode().strip().split()]

        for pid in pids:
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                continue

        await asyncio.sleep(1)
        for pid in pids:
            try:
                os.kill(pid, 9)
            except ProcessLookupError:
                continue

        for pid in pids:
            active_processes.pop(pid, None)

        return {"status": "unexposed", "port": port}
    except Exception as e:
        logger.error(f"Failed to unexpose port {port}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _check_port(port: int) -> str:
    """Check what processes are using a port."""
    proc: Process = await asyncio.create_subprocess_shell(
        f"lsof -i :{port} || true",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode()


@app.post("/clear_port")
async def clear_port(request: Request) -> dict:
    """Force kill any processes using the specified port."""
    data: dict = await request.json()
    port: int | None = data.get("port")
    if not port:
        return {"success": False, "error": "Port not specified"}

    logger.info(f"Checking processes on port {port}...")
    stdout: str = await _check_port(port)

    if stdout:
        logger.info(f"Found processes using port {port}:\n{stdout}")

        kill_commands: list[str] = [
            f"fuser -k {port}/tcp || true",
            f"lsof -t -i :{port} | xargs -r kill -9 || true",
            f"pkill -f 'docker-proxy.*:{port}' || true",
        ]

        for cmd in kill_commands:
            proc: Process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

        await asyncio.sleep(1)
        check_stdout: str = await _check_port(port)

        if not check_stdout:
            logger.info(f"Successfully cleared port {port}")
            return {"success": True}
        else:
            logger.warning(
                f"Port {port} still in use after clearing attempt:\n{check_stdout}"
            )
            return {"success": False, "error": f"Port {port} still in use"}
    else:
        logger.info(f"Port {port} is already clear")
        return {"success": True}


@sio.on("connect")
async def connect(sid, environ):
    """Client connected."""
    global _last_disconnect
    logger.info(f"Client {sid} connected")
    _last_disconnect = 0


@sio.on("disconnect")
async def disconnect(sid):
    """Client disconnected."""
    global _last_disconnect
    logger.info(f"Client {sid} disconnected")
    _last_disconnect = time.time()

    asyncio.create_task(schedule_cleanup())


@sio.on("start_command_stream")
async def start_command_stream(sid, data):
    process_id: int = int(data.get("process_id"))
    process: Process | None = active_processes.get(process_id)

    if not process:
        await sio.emit(
            "command_error",
            {"error": f"Process {process_id} not found"},
            room=sid,
        )
        return

    async def stream_output():
        try:

            async def read_stream(stream, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    await sio.emit(
                        "command_output",
                        {
                            "output": line.decode(),
                            "type": stream_type,
                            "process_id": process_id,
                        },
                        room=sid,
                    )

            stdout_task: asyncio.Task = asyncio.create_task(
                read_stream(process.stdout, "stdout")
            )
            stderr_task: asyncio.Task = asyncio.create_task(
                read_stream(process.stderr, "stderr")
            )

            await asyncio.gather(stdout_task, stderr_task)

        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            await sio.emit(
                "command_error",
                {"error": str(e), "process_id": process_id},
                room=sid,
            )
        finally:
            try:
                exit_code: int = await process.wait()
                del active_processes[process_id]
                await sio.emit(
                    "command_exit",
                    {
                        "exit_code": exit_code,
                        "process_id": process_id,
                    },
                    room=sid,
                )
            except Exception as e:
                if str(e) == "137":
                    logger.info(f"Process {process_id} was killed with SIGKILL")
                else:
                    logger.error(f"Error during process cleanup: {e}")

                with contextlib.suppress(KeyError):
                    del active_processes[process_id]
                await sio.emit(
                    "command_exit",
                    {
                        "exit_code": 137 if str(e) == "137" else -1,
                        "process_id": process_id,
                    },
                    room=sid,
                )

    await stream_output()


async def calculate_directory_hash(path: str) -> str:
    """
    Calculate a hash for a directory based on file names only.
    This is a fast way to detect changes in directory structure.
    For node_modules directories, only the first level of files is considered.
    """
    logger.info(f"Calculating hash for directory: {path}")
    hash_start_time = time.time()

    try:
        is_node_modules: bool = (
            path.endswith("node_modules") or "/node_modules/" in path
        )

        # For node_modules, only get the first level of files
        if is_node_modules:
            cmd: str = f"ls -1 '{path}' 2>/dev/null | sort"
        else:
            # For regular directories, get all files recursively
            cmd: str = f"find '{path}' -type f -not -path '*/\\.*' | sort"

        proc: Process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"Error getting directory file names: {stderr.decode()}")
            return ""

        # Create hash from the file names
        filenames = stdout.decode()

        # Add directory name to the hash calculation
        dir_info = f"{path}"

        hash_input = f"{dir_info}\n{filenames}".encode()
        dir_hash = hashlib.blake2b(hash_input, digest_size=32).hexdigest()

        duration = time.time() - hash_start_time
        logger.info(
            f"Directory hash calculation took {duration:.2f} seconds for {path}"
        )
        return dir_hash
    except Exception as e:
        logger.error(f"Error calculating directory hash: {e}")
        return ""


@app.post("/dir_cache/save")
async def save_dir_cache(data: dict):
    """Save a directory to the cache as a tar.gz file."""
    path: str = data.get("path", "")
    cache_name: str = data.get("cache_name", "")
    force: bool = data.get("force", False)
    start_time: float = time.time()

    if not cache_name:
        logger.error("Cache name is required")
        return JSONResponse(
            status_code=400,
            content={"error": "Cache name is required", "status": "error"},
        )

    if not path or not os.path.isdir(path):
        logger.error(f"Directory not found: {path}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Directory not found: {path}", "status": "error"},
        )

    file_name: str = f"{cache_name}.tar.lz4"
    os.makedirs(DIR_CACHE_DIR, exist_ok=True)
    output_path: str = os.path.join(DIR_CACHE_DIR, file_name)

    start_time: float = time.time()
    dir_hash = await calculate_directory_hash(path)
    logger.info(
        f"Directory hash calculation took {time.time() - start_time:.2f} seconds for {path}"
    )

    if not force and dir_hash:
        cache_metadata = await load_cache_metadata()
        if (
            file_name in cache_metadata
            and cache_metadata[file_name].get("hash") == dir_hash
        ):
            logger.info(
                f"Directory {path} unchanged (hash: {dir_hash}), skipping compression"
            )
            return {
                "status": "unchanged",
                "cache_name": cache_name,
                "file_name": file_name,
                "hash": dir_hash,
            }

    size_cmd: Process = await asyncio.create_subprocess_shell(
        f"du -sm '{path}' | cut -f1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await size_cmd.communicate()
    size_mb: int = 0
    with contextlib.suppress(ValueError):
        size_mb = int(stdout.decode().strip())

    tar_start_time: float = time.time()
    tar_cmd: Process = await asyncio.create_subprocess_shell(
        f"cd '{os.path.dirname(path)}' && tar cf - '{os.path.basename(path)}' | lz4 -7 -f - '{output_path}'",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await tar_cmd.communicate()
    logger.info(
        f"Tar command took {time.time() - tar_start_time:.2f} seconds to complete"
    )

    if tar_cmd.returncode != 0:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to create archive: {stderr.decode()}",
                "status": "error",
            },
        )

    cache_metadata: dict = await load_cache_metadata()
    cache_metadata[file_name] = {
        "created": datetime.now().isoformat(),
        "size_mb": size_mb,
        "hash": dir_hash,
    }
    await save_cache_metadata(cache_metadata)
    logger.info(
        f"Saved cache {cache_name} to {file_name} in {time.time() - start_time:.2f} seconds"
    )

    return {
        "status": "saved",
        "cache_name": cache_name,
        "file_name": file_name,
        "size_mb": size_mb,
        "hash": dir_hash,
    }


@app.post("/dir_cache/restore")
async def restore_dir_cache(data: dict):
    """Restore a directory cache from the cache."""
    cache_name: str = data.get("cache_name", "")
    path: str = data.get("path", "")

    if not cache_name or ".." in cache_name:
        logger.error(f"Invalid cache name: {cache_name}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid cache name", "status": "error"},
        )

    if not path:
        logger.error("Target path is required")
        return JSONResponse(
            status_code=400,
            content={"error": "Target path is required", "status": "error"},
        )

    file_name: str = (
        cache_name if cache_name.endswith(".tar.lz4") else f"{cache_name}.tar.lz4"
    )

    cache_path: str = os.path.join(DIR_CACHE_DIR, file_name)
    if not os.path.exists(cache_path):
        logger.error(f"Cache not found: {cache_name}")
        return JSONResponse(
            status_code=404,
            content={"error": f"Cache not found: {cache_name}", "status": "error"},
        )

    cache_metadata: dict = await load_cache_metadata()
    dir_hash = cache_metadata.get(file_name, {}).get("hash", "")

    if os.path.exists(path):
        rm_cmd = await asyncio.create_subprocess_shell(
            f"rm -rf '{path}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await rm_cmd.communicate()

    extract_start_time: float = time.time()
    extract_cmd: Process = await asyncio.create_subprocess_shell(
        f"cd '{os.path.dirname(path)}' && lz4 -d '{cache_path}' - | tar xf -",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await extract_cmd.communicate()
    logger.info(
        f"Extract command took {time.time() - extract_start_time:.2f} seconds to complete"
    )

    if extract_cmd.returncode != 0:
        logger.error(f"Failed to extract archive: {stderr.decode()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to extract archive: {stderr.decode()}",
                "status": "error",
            },
        )

    logger.info(f"Restored cache {cache_name} to {path}")
    if file_name in cache_metadata:
        cache_metadata[file_name]["last_restored"] = datetime.now().isoformat()
        await save_cache_metadata(cache_metadata)

    return {
        "status": "restored",
        "hash": dir_hash,
    }
