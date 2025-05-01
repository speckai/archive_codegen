import subprocess
import threading
import traceback

from loguru import logger
from src.config import GITHUB_APP_SMEE_URL

token_cache: dict[str, str] = {}

SMEE_URL: str = GITHUB_APP_SMEE_URL or "https://smee.io/HrT3nN6VvCfg385T"


async def spawn_smee_client() -> subprocess.Popen | None:
    """Spawns a smee.io client to forward GitHub webhooks to localhost"""
    logger.info("Spawning smee client")
    try:
        # Check if smee-client is installed
        try:
            subprocess.run(
                ["npx", "smee-client", "--version"], capture_output=True, check=True
            )
        except subprocess.CalledProcessError:
            logger.info("Installing smee-client...")
            subprocess.run(["npm", "install", "smee-client", "-g"], check=True)

        process: subprocess.Popen = subprocess.Popen(
            [
                "npx",
                "smee-client",
                "-u",
                SMEE_URL,
                "-t",
                "http://127.0.0.1:8040/github/webhook",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This ensures the output is returned as string instead of bytes
            bufsize=1,  # Line buffered
            universal_newlines=True,  # Ensures proper line endings handling
        )

        # Start output monitoring in separate threads
        def monitor_output(pipe, log_func, prefix):
            for line in pipe:
                log_func(f"{prefix}: {line.strip()}")

        stdout_thread: threading.Thread = threading.Thread(
            target=monitor_output,
            args=(process.stdout, logger.info, "Smee Output > "),
            daemon=True,
        )
        stderr_thread: threading.Thread = threading.Thread(
            target=monitor_output,
            args=(process.stderr, logger.error, "Smee Error > "),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        return process

    except Exception as e:
        logger.error(f"Error spawning smee client: {e}")
        logger.error(traceback.format_exc())
        return None
