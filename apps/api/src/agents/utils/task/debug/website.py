import asyncio
import os
import shutil
from typing import TYPE_CHECKING, Optional

from morphcloud.api import (
    InstanceExecResponse,
)
from playwright.async_api import Browser, Page, async_playwright
from src.agents.utils.task.debug.common import Debug
from src.agents.utils.task.interfaces.website import WebsitePullRequest, WebsiteStatus
from src.database import Database
from src.schemas.core.validation import RuntimeResult
from src.schemas.repos import Settings
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class DebugWebsite:
    """Local version of Website for debug mode with the same interface as Website."""

    def __init__(self, debug: Debug, task: "Task"):
        self.debug = debug
        self.task = task
        self.is_running = False
        self._current_process: Optional[asyncio.subprocess.Process] = None
        self._dependencies_installed = False

    async def _reset_process_logs(self):
        """Reset process logs by clearing stdout and stderr buffers more robustly."""

        async def drain_stream(stream: Optional[asyncio.StreamReader], name: str):
            if not stream:
                return
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(stream.read(1024), timeout=0.1)
                        if not chunk:
                            # EOF – nothing left to read
                            break
                    except asyncio.TimeoutError:
                        # No data within timeout; assume buffer is empty for now
                        break
                    except asyncio.CancelledError:
                        # Loop is shutting down – break quickly
                        break
            except Exception as e:
                logger.debug(f"Error clearing {name} buffer: {e}")

        if self._current_process:
            await drain_stream(self._current_process.stdout, "stdout")
            await drain_stream(self._current_process.stderr, "stderr")

    async def build(self) -> list[dict[str, any]]:
        """Simulate build process"""
        logger.info("DebugWebsite: Simulating build")
        try:
            result = await self.task.sandbox.run_command(
                await self.debug.settings.get_build_command(),
                timeout=300,
            )
            if isinstance(result, InstanceExecResponse):
                if result.exit_code != 0:
                    logger.error(f"Build failed: {result.stderr}")
                    raise Exception("Build failed")
                logger.info(f"Build successful: {result.stdout}")
                return []
        except Exception as e:
            logger.error(f"Build error: {e}")
            raise
        return []

    async def _read_logs_for_time(
        self, timeout: float = 10
    ) -> list[InstanceExecResponse]:
        """Read logs from the process for a specified duration"""
        outputs: list[InstanceExecResponse] = []
        if not self._current_process:
            return outputs

        start_time = asyncio.get_event_loop().time()
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time >= timeout:
                break

            remaining_time = timeout - (current_time - start_time)
            try:
                # Read from stdout
                if self._current_process.stdout:
                    line = await asyncio.wait_for(
                        self._current_process.stdout.readline(), timeout=remaining_time
                    )
                    if line:
                        outputs.append(
                            InstanceExecResponse(
                                stdout=line.decode(),
                                stderr="",
                                exit_code=self._current_process.returncode,
                            )
                        )

                # Read from stderr
                if self._current_process.stderr:
                    line = await asyncio.wait_for(
                        self._current_process.stderr.readline(), timeout=remaining_time
                    )
                    if line:
                        outputs.append(
                            InstanceExecResponse(
                                stdout="",
                                stderr=line.decode(),
                                exit_code=self._current_process.returncode,
                            )
                        )

            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Error reading logs: {e}")
                break

        return outputs

    async def push(
        self,
        commit_message: str,
        commit_description: str,
        branch_name: str,
        create_pr: bool = True,
    ) -> WebsitePullRequest:
        """Simulate pushing changes and creating a pull request"""
        logger.info(f"DebugWebsite: Simulating push to branch {branch_name}")
        try:
            commands = [
                "git add .",
                f"git checkout -b {branch_name}",
                'git config user.email "speck-engineer[bot]@users.noreply.github.com"',
                'git config user.name "speck-engineer[bot]"',
                f"git commit -m '{commit_message}' -m '{commit_description}'",
            ]

            for cmd in commands:
                await self.task.sandbox.run_command(cmd, timeout=60)

            return WebsitePullRequest(branch_name=branch_name, pr_number=0)
        except Exception as e:
            logger.error(f"Failed to push changes: {e}")
            raise

    async def start(
        self,
        show_progress: bool = True,
        override_settings: Optional[Settings] = None,
    ) -> WebsiteStatus:
        """Start the local development server"""
        logger.info("DebugWebsite: Starting local development server")
        try:
            # Only run installation if not already installed and not skipped
            if (
                not self._dependencies_installed
                and not self.debug.settings.skip_install
            ):
                if show_progress:
                    logger.info("DebugWebsite: Installing dependencies...")

                await self.task.sandbox.run_command(
                    await self.debug.settings.get_install_command(), timeout=300
                )
                # Cache node_modules
                if self.debug.settings.cached_node_modules_path:
                    # Move node_modules to cache location
                    node_modules_path = os.path.join(
                        self.debug.repo_dir, "node_modules"
                    )
                    if os.path.exists(node_modules_path):
                        shutil.move(
                            node_modules_path,
                            self.debug.settings.cached_node_modules_path,
                        )
                        # Create symlink from cache back to repo
                        os.symlink(
                            self.debug.settings.cached_node_modules_path,
                            node_modules_path,
                        )
                self._dependencies_installed = True
            elif show_progress and not self.debug.settings.skip_install:
                logger.info(
                    "DebugWebsite: Dependencies already installed, skipping installation"
                )

            if show_progress:
                logger.info("DebugWebsite: Starting dev server...")

            # Start dev server
            self._current_process = await asyncio.create_subprocess_shell(
                await self.debug.settings.get_dev_command(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.debug.settings.workspace_path,
            )
            self.is_running = True

            # Optionally, monitor the process or handle logs
            return WebsiteStatus(is_running=True, is_public=True)

        except Exception as e:
            logger.error(f"Failed to start local development server: {e}")
            return WebsiteStatus(is_running=False, is_public=False)

    async def _wait_for_website_ready(
        self,
        max_attempts: int = 15,
        delay: int = 1,
        override_port: Optional[int] = None,
    ) -> WebsiteStatus:
        """Check if the website is running"""
        logger.info("DebugWebsite: Waiting for website to be ready")
        port: int = override_port or await self.debug.settings.get_port()
        for attempt in range(max_attempts):
            try:
                cmd = (
                    f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}"
                )
                result = await self.task.sandbox.run_command(cmd, timeout=10)
                if isinstance(result, InstanceExecResponse):
                    if result.stdout in ["200", "500"]:
                        if result.stdout == "500":
                            logger.warning("Website is running but returned 500")
                        logger.info(f"Website is ready on port {port}")
                        return WebsiteStatus(is_running=True, is_public=True)
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1}: Website not ready yet ({e})")
            await asyncio.sleep(delay)
        logger.critical("Website did not become ready in time")
        return WebsiteStatus(is_running=False, is_public=False)

    async def restart(self):
        """Restart the local development server"""
        logger.info("DebugWebsite: Restarting local development server")
        await self.stop()
        await self.start()

    async def stop(
        self, override_port: Optional[int] = None, ignore_running: bool = False
    ):
        """Stop the local development server"""
        if not self.is_running and not ignore_running:
            logger.info("DebugWebsite: Server is not running. Nothing to stop.")
            return
        logger.info("DebugWebsite: Stopping local development server")
        try:
            if self._current_process:
                self._current_process.terminate()
                await self._current_process.wait()
                self._current_process = None
            self.is_running = False
            logger.info("DebugWebsite: Server stopped.")
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            raise

    async def _get_browser_logs(self, url: str) -> list[dict[str, str]]:
        """Use a headless browser to capture client-side JS logs and errors."""
        logs: list[dict[str, str]] = []
        # Get browser storage
        browser_storage: dict[str, str] = Database.get_repo_property(
            self.task.git.repo_id, "browser_storage"
        )
        try:
            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(headless=True)
                page: Page = await browser.new_page()

                if browser_storage and "cookies" in browser_storage:
                    logger.info(f"Setting cookies for {url}")
                    for name, value in browser_storage["cookies"].items():
                        await page.context.add_cookies(
                            [
                                {
                                    "name": name,
                                    "value": value,
                                    "url": url,
                                }
                            ]
                        )

                def on_console(msg):
                    logs.append({"type": msg.type, "text": msg.text})

                page.on("console", on_console)

                def on_page_error(exc):
                    logs.append({"type": "error", "text": str(exc)})

                page.on("pageerror", on_page_error)

                await page.goto(url)

                if browser_storage and "localStorage" in browser_storage:
                    logger.info(f"Setting localStorage for {url}")
                    for key, value in browser_storage["localStorage"].items():
                        await page.evaluate(f"localStorage.setItem('{key}', '{value}')")

                if browser_storage and "sessionStorage" in browser_storage:
                    logger.info(f"Setting sessionStorage for {url}")
                    for key, value in browser_storage["sessionStorage"].items():
                        await page.evaluate(
                            f"sessionStorage.setItem('{key}', '{value}')"
                        )

                await page.wait_for_load_state("networkidle")

                # Take screenshot and save as url.png
                await page.screenshot(path=f"{url}.png")

                # Wait briefly to gather any post-load logs
                await asyncio.sleep(1)

                await browser.close()
        except Exception as e:
            logger.error(f"Browser test failed for {url}: {e}")
        return logs

    async def perform_runtime_test(self, urls: list[str]) -> list[RuntimeResult]:
        """Perform runtime tests on the given URLs and track modified URLs"""
        if not urls:
            urls = ["/"]

        logger.info("DebugWebsite: Performing runtime tests")

        # Wait for website to be running
        time_waited: int = 0
        while not self.is_running:
            await asyncio.sleep(1)
            time_waited += 1
            if time_waited > 10:
                raise Exception("Website took too long to start")

        runtime_results: list[RuntimeResult] = []
        print(f"Testing URLs: {urls}")
        for path in urls:
            print(f"Testing URL: {path}")
            # Reset process logs before testing each URL
            await self._reset_process_logs()

            # Get console logs for the URL (server logs):
            runtime_result: RuntimeResult = await self.get_website_console_logs(path)

            # Deduplicate stderr messages
            runtime_result.stderr = list(
                dict.fromkeys(error.strip() for error in runtime_result.stderr)
            )
            runtime_results.append(runtime_result)

            # Test URL accessibility (server response code):
            port = await self.task.settings.get_port()
            await self.task.sandbox.run_command(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}{path}",
                timeout=15,
            )

            # Read additional server logs that might have been generated:
            cli_logs = await self._read_logs_for_time(timeout=0.5)

            for log in cli_logs:
                if isinstance(log, InstanceExecResponse) or log is None:
                    continue

                if log.stderr.strip() not in runtime_result.stderr:
                    runtime_result.stderr.append(log.stderr.strip())
                elif log.stdout.strip() not in runtime_result.stdout:
                    runtime_result.stdout.append(log.stdout.strip())

            browser_logs = await self._get_browser_logs(
                f"http://localhost:{port}{path}"
            )
            # Parse out 'error' vs everything else:
            logger.info(f"Browser logs: {browser_logs}")
            for entry in browser_logs:
                if (
                    entry["type"].lower() == "error"
                    and entry["text"] not in runtime_result.stderr
                ):
                    runtime_result.stderr.append(entry["text"])
                else:
                    runtime_result.stdout.append(entry["text"])

        logger.info(f"DebugWebsite: Runtime results: {runtime_results}")
        return runtime_results

    def get_runtime_files(self) -> list[dict[str, str]]:
        """Get runtime files from the local repository"""
        logger.info("DebugWebsite: Getting runtime files from local repository")
        # Implement logic to retrieve runtime files if needed
        return []

    async def get_possible_urls(self) -> list[str]:
        import re

        res: InstanceExecResponse = await self.task.sandbox.run_command(
            "pnpx list-routes", use_repo_subdir=True
        )

        if res.exit_code != 0:
            logger.error(f"Failed to get possible urls: {res.stderr}")
            return []

        try:
            match = re.search(r"\[(.*?)\]", res.stdout, re.DOTALL)
            if not match:
                return []

            return [
                url.strip().strip("\"'")
                for url in match.group(1).split(",")
                if url.strip()
            ]
        except Exception as e:
            logger.error(f"Failed to parse urls from output: {e}")
            return []

    @property
    def is_running_property(self) -> bool:
        """Property to check if the server is running"""
        return self.is_running

    async def get_website_console_logs(self, path: str) -> RuntimeResult:
        """Get console logs for a specific URL path (debug version)."""
        port = await self.debug.settings.get_port()
        url = f"http://localhost:{port}{path}"

        # Use existing browser logging infrastructure
        browser_logs = await self._get_browser_logs(url)

        # Convert logs to RuntimeResult format
        stdout_logs = []
        stderr_logs = []

        for entry in browser_logs:
            if entry["type"].lower() in ["warning", "debug", "info", "log"]:
                stdout_logs.append(entry["text"])
            else:
                stderr_logs.append(entry["text"])

        return RuntimeResult(stdout=stdout_logs, stderr=stderr_logs, url_tested=url)
