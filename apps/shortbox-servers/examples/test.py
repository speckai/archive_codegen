#!/usr/bin/env python3
import asyncio
import logging
import time
import uuid

import aiohttp
import typer
from rich.console import Console
from shortbox import (
    CommandExit,
    CommandMode,
    CommandOutput,
    CommandResult,
    ContainerManager,
    StreamProcess,
)

console = Console()
app = typer.Typer()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/speckai/paige-nextjs-shadcn-template"


async def get_user_sandboxes(base_url: str, user_id: str) -> dict:
    """Get all sandboxes for a user."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/containers/{user_id}/list") as response:
            return await response.json()


async def run_test():
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    user_id = "test-user"
    base_url = (
        "http://sandbox-alb-103265220.us-west-1.elb.amazonaws.com"  # Manager API URL
    )

    logger.info(f"Using session ID: {session_id}")
    logger.info(f"Using user ID: {user_id}")

    # List containers before starting
    logger.info("Listing containers before starting...")
    containers = await get_user_sandboxes(base_url, user_id)
    logger.info(f"Current containers for user {user_id}:")
    logger.info(f"Total count: {len(containers.get('sandboxes', {}))}")
    for session_id, info in containers.get("sandboxes", {}).items():
        logger.info(f"  Session: {session_id}")
        logger.info(f"    Status: {info['status']}")
        logger.info(f"    Created At: {info['created_at']}")

    sandbox = ContainerManager(
        user_id=user_id, session_id=session_id, base_url=base_url, is_local=False
    )

    try:
        # Start the container
        logger.info("\nStarting container...")
        start_time = time.time()
        container_info = await sandbox.start_container()
        logger.info(f"Container started successfully: {container_info}")
        logger.info(f"Container started in {time.time() - start_time:.2f} seconds")

        # Test port exposure
        logger.info("\nTesting port exposure...")
        port = 3000
        result = await sandbox.expose_port(port)
        logger.info(f"Port exposure result: {result}")

        # Test preview port
        logger.info("\nTesting preview port...")
        success = await sandbox.set_preview_port(port)
        logger.info(f"Preview port set: {success}")

        # Test unexposing port
        logger.info("\nTesting port unexposure...")
        result = await sandbox.unexpose_port(port)
        logger.info(f"Port unexposure result: {result}")

        # Check if /repo exists on the container, warn if so but delete it. use commands
        result = await sandbox.run_command("ls /repo")
        if result.stdout:
            logger.warning("/repo exists on the container. Deleting it...")
            await sandbox.run_command("rm -rf /repo", mode=CommandMode.WAIT)

        # Clone the repository
        logger.info(f"Cloning repository: {REPO_URL}")
        result = await sandbox.run_command(f"git clone {REPO_URL} /repo")
        if result.exit_code != 0:
            raise Exception(f"Failed to clone repository: {result.stderr}")
        logger.info(f"Clone result: exit_code={result.exit_code}")
        logger.info(f"Clone result: stdout={result.stdout}")
        sandbox.workspace_path = "/repo"

        # Run LS
        result: CommandResult = await sandbox.run_command("ls")
        if result.exit_code != 0:
            raise Exception(f"Failed to run LS: {result.stderr}")
        logger.info(f"LS result: exit_code={result.exit_code}, stdout={result.stdout}")

        # Install dependencies with optimizations for speed
        logger.info("Installing dependencies...")
        result: CommandResult = await sandbox.run_command(
            "pnpm install --prefer-offline --no-strict-peer-dependencies",
            timeout=300,
        )
        if result.exit_code != 0:
            raise Exception(f"Failed to install dependencies: {result.stderr}")

        # Start the development server
        logger.info("Starting Next.js development server...")
        logger.warning(f"URL: {base_url}/preview/{user_id}/{session_id}")

        dev_server: StreamProcess = await sandbox.run_command(
            "pnpm run dev", mode=CommandMode.STREAM
        )

        async def kill_after_delay():
            await asyncio.sleep(30)
            logger.info("Killing dev server after 30 seconds...")
            killed = await dev_server.kill()
            logger.info(f"Dev server killed: {killed}")

        kill_task: asyncio.Task = asyncio.create_task(kill_after_delay())

        try:
            async for output in dev_server:
                if isinstance(output, CommandOutput):
                    if output.type == "stdout":
                        logger.info(f"[stdout] {output.output}")
                    else:
                        logger.error(f"[stderr] {output.output}")
                elif isinstance(output, CommandExit):
                    logger.info(f"Process exited with code {output.exit_code}")
                    break
        except Exception as e:
            logger.error(f"Error streaming output: {e}")
        finally:
            if not kill_task.done():
                kill_task.cancel()

        # Wait a bit for the server to start
        logger.info("Waiting for dev server to start...")
        await asyncio.sleep(10)  # Reduced wait time since we're monitoring the output

        # Check if the dev server is running
        check_output: CommandResult = await sandbox.run_command(
            "ps aux | grep '[n]ode' || true"
        )
        if check_output.stdout:
            logger.info("Dev server process found:")
            logger.info(check_output.stdout)
        else:
            logger.error("Dev server process not found!")

        # Wait for server to be fully ready
        await asyncio.sleep(10)

    finally:
        # Always cleanup
        logger.info("\nCleaning up...")
        await sandbox.cleanup()
        logger.info("Test completed successfully!")


def test_sandbox():
    """Test the sandbox functionality with Next.js template"""
    try:
        asyncio.run(run_test())
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    test_sandbox()
