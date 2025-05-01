import asyncio
import re
from typing import TYPE_CHECKING, Literal

from morphcloud.api import InstanceExecResponse
from playwright.async_api import Browser, ConsoleMessage, Page, async_playwright
from pydantic import BaseModel
from src.database import Database
from src.schemas.core.validation import RuntimeResult
from src.utils.logging import logger

HEALTHY_CODES: list[str] = ["200", "500", "307", "201", "301", "302", "403", "304"]

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class WebsitePullRequest(BaseModel):
    branch_name: str
    pr_number: int
    pr_url: str


class WebsiteStatus(BaseModel):
    is_running: bool
    is_public: bool


class WebsiteFail(BaseModel):
    stage: Literal["installing", "starting"]
    stdout: str
    stderr: str


class TimeoutAsyncIterator:
    def __init__(self, aiter, timeout):
        self.aiter = aiter
        self.timeout = timeout
        self.start_time = None

    def __aiter__(self):
        self.iter = self.aiter.__aiter__()
        self.start_time = asyncio.get_event_loop().time()
        return self

    async def __anext__(self):
        now = asyncio.get_event_loop().time()
        remaining = self.timeout - (now - self.start_time)
        if remaining <= 0:
            raise StopAsyncIteration
        try:
            return await asyncio.wait_for(self.iter.__anext__(), timeout=remaining)
        except asyncio.TimeoutError as e:
            logger.info(f"Log reading timed out after {self.timeout} seconds.")
            raise StopAsyncIteration from e


class Website:
    def __init__(self, task: "Task"):
        self.task: Task = task
        self.modified_urls: list[str] = []

    async def _reset_process_logs(self):
        pass

    # async def build(self) -> list[CommandOutput]:
    #     return await self.task.sandbox.run_command(
    #         await self.task.settings.get_build_command()
    #     )

    async def _read_logs_for_time(
        self, timeout: float = 10
    ) -> list[InstanceExecResponse]:
        outputs: list[InstanceExecResponse] = []
        async for log in TimeoutAsyncIterator(self.process.stream(), timeout):
            outputs.append(log)
        return outputs

    async def start(self):
        pass

    async def restart(self):
        pass

    async def stop(self, override_port: int | None = None):
        pass

    async def perform_runtime_test(self, urls: list[str]) -> list[RuntimeResult]:
        if not urls:
            urls = ["/"]

        assert all(url.startswith("/") for url in urls), "All URLs must start with /"

        time_waited: int = 0
        while not self.is_running:
            await asyncio.sleep(1)
            time_waited += 1
            if time_waited > 10:
                raise Exception("Website took too long to start")

        runtime_results: list[RuntimeResult] = []
        for url in urls:
            await self.task.website._reset_process_logs()
            runtime_result: RuntimeResult = (
                await self.task.website.get_website_console_logs(url)
            )
            runtime_result.stderr = list(
                dict.fromkeys(error.strip() for error in runtime_result.stderr)
            )
            runtime_results.append(runtime_result)

            await self.task.sandbox.run_command(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{await self.task.settings.get_port()}{url}",
                timeout=15,
            )

            cli_logs: list[InstanceExecResponse] = (
                await self.task.website._read_logs_for_time(timeout=0.5)
            )

            for log in cli_logs:
                if log.stderr.strip() not in runtime_result.stderr:
                    runtime_result.stderr.append(log.stderr.strip())
                elif log.stdout.strip() not in runtime_result.stdout:
                    runtime_result.stdout.append(log.stdout.strip())

        return runtime_results

    async def get_website_console_logs(self, path: str) -> RuntimeResult:
        browser_storage: dict[str, str] | None = Database.get_repo_property(
            self.task.git.repo_id, "browser_storage"
        )
        if not browser_storage:
            browser_storage = {}

        cookies: dict = browser_storage.get("cookies", {})
        local_storage: dict = browser_storage.get("local_storage", {})
        session_storage: dict = browser_storage.get("session_storage", {})
        full_url: str = f"{self.task.sandbox.preview_url}{path}"

        async with async_playwright() as playwright:
            browser: Browser = await playwright.chromium.launch(headless=True)
            page: Page = await browser.new_page()

            for name, value in cookies.items():
                await page.context.add_cookies(
                    [
                        {
                            "name": name,
                            "value": value,
                            "url": full_url,
                        }
                    ]
                )

            logs: list[dict] = []
            errors: list[dict] = []

            def handle_console(msg: ConsoleMessage):
                if msg.type in ["warning", "debug", "info", "log"]:
                    logs.append({"type": msg.type, "text": msg.text})
                else:
                    errors.append({"type": msg.type, "text": msg.text})

            page.on("console", handle_console)

            try:
                await page.goto(full_url)

                for key, value in local_storage.items():
                    await page.evaluate(f"localStorage.setItem('{key}', '{value}')")

                for key, value in session_storage.items():
                    await page.evaluate(f"sessionStorage.setItem('{key}', '{value}')")

                await page.goto(full_url)

                await page.wait_for_load_state("networkidle")

                await page.wait_for_timeout(
                    2000
                )  # Wait for 2s to catch any delayed errors
            except Exception as e:
                await browser.close()
                raise e

            await browser.close()

            def clean_output(output: str | None) -> str | None:
                # TODO: This should NEVER be none. Figure out why
                if output is None:
                    logger.error("Output is None, check why")
                    return None

                ansi_escape = re.compile(r"\x1b\[([0-9]+)(;[0-9]+)*m")
                return ansi_escape.sub("", output)

            logs = [
                log["text"]
                for log in logs
                if log["type"] in ["warning", "debug", "info", "log"]
            ]
            errors = [
                error["text"]
                for error in errors
                if error["type"] not in ["warning", "debug", "info", "log"]
            ]
            logs = [clean_output(log) for log in logs]
            errors = [clean_output(error) for error in errors]

            return RuntimeResult(stdout=logs, stderr=errors, url_tested=full_url)

    @property
    def is_running(self) -> bool:
        return self.process and self.process.process_id is not None

    async def get_possible_urls(self) -> list[str]:
        res: InstanceExecResponse = await self.task.sandbox.run_command(
            "cd /repo && pnpx list-routes"
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
