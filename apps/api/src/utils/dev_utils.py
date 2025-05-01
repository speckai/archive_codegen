import asyncio
import contextlib
import os
import random
import subprocess
import threading
import time
import traceback

from src.utils.logging import logger

token_cache: dict[str, str] = {}


async def run_local_git_consumer() -> subprocess.Popen | None:
    """Run the local git consumer"""
    logger.info("Starting local git consumer")
    try:
        process: subprocess.Popen = subprocess.Popen(
            ["pnpm", "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd="../github-consumer",
        )

        start_time: float = time.time()

        def monitor_output(pipe, log_func, prefix):
            if time.time() - start_time < 2:
                return

            for line in pipe:
                log_func(f"{prefix}: {line.strip()}")

        stdout_thread: threading.Thread = threading.Thread(
            target=monitor_output,
            args=(process.stdout, logger.info, "Git consumer output"),
            daemon=True,
        )
        stderr_thread: threading.Thread = threading.Thread(
            target=monitor_output,
            args=(process.stderr, logger.warning, "Git consumer error"),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        return process

    except Exception as e:
        logger.error(f"Error starting local git consumer: {e}")
        logger.error(traceback.format_exc())
        return None


async def run_redis() -> None:
    """Start Redis using docker-compose in development"""
    try:
        api_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        compose_file: str = os.path.join(api_dir, "docker-compose.dev.yml")

        if await _is_redis_running():
            logger.info("Redis is already running")
            return

        await _cleanup_existing_container()
        await _start_redis_container(compose_file)

    except Exception as e:
        logger.error(f"Failed to start Redis: {str(e)}")
        raise


async def _is_redis_running() -> bool:
    """Check if Redis container is running"""
    result: subprocess.CompletedProcess = subprocess.run(
        ["docker", "container", "inspect", "-f", "{{.State.Running}}", "api-redis-1"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


async def _cleanup_existing_container() -> None:
    """Remove existing Redis container if any"""
    with contextlib.suppress(Exception):
        subprocess.run(
            ["docker", "rm", "-f", "api-redis-1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    # For race conditions
    await asyncio.sleep(random.uniform(0.1, 0.5))


async def _start_redis_container(compose_file: str) -> None:
    """Start Redis container using docker-compose"""
    try:
        subprocess.run(
            ["docker-compose", "-f", compose_file, "up", "-d", "redis"], check=True
        )
        await asyncio.sleep(2)
    except subprocess.CalledProcessError as e:
        if (
            "already in use" in str(e) or e.returncode == 1
        ) and await _is_redis_running():
            logger.info("Redis was started by another process")
            return
        raise


async def stop_redis() -> None:
    """Stop Redis docker container"""
    try:
        api_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        compose_file: str = os.path.join(api_dir, "docker-compose.dev.yml")

        subprocess.run(["docker-compose", "-f", compose_file, "down"], check=True)
    except Exception as e:
        logger.error(f"Failed to stop Redis: {str(e)}")
