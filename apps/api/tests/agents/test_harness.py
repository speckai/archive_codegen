import asyncio
import json
import os
import shutil
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Optional, Tuple

from playwright.async_api import async_playwright
from src.agents.utils.task.debug.common import Debug
from src.agents.utils.task.debug.settings import DebugSettings
from src.schemas.account import User
from src.schemas.core.common.files import SelectedComponents
from tests.agents.test_config import TestConfig

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"


class TestHarness:
    def __init__(self, config: TestConfig):
        self.config = config
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup base directories
        self.project_root = Path(os.getcwd())
        self.cache_dir = self.project_root / ".cache"
        self.test_runs_dir = self.project_root / "test_runs"

        # Setup current test run directory
        self.current_run_dir = self.test_runs_dir / self.timestamp
        self.repos_dir = self.current_run_dir / "repos"
        self.outputs_dir = self.current_run_dir / "outputs"

        # Create necessary directories
        self._setup_directories()

        # Track directories for cleanup
        self.test_dir = None
        self.target_dir = None

        # Setup signal handlers for cleanup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_directories(self):
        """Create the directory structure for the test run"""
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "node_modules").mkdir(exist_ok=True)

        # Create test run directories
        self.test_runs_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        (self.outputs_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.outputs_dir / "diffs").mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(self, repo_dir: str) -> Optional[str]:
        """Generate cache key based on package.json and lock files"""
        repo_path = Path(repo_dir)
        files_to_hash = []

        # Add package.json if it exists
        package_json = repo_path / "package.json"
        if package_json.exists():
            files_to_hash.append(package_json)
        else:
            return None

        if not files_to_hash:
            return None

        # Generate hash from all files
        import hashlib

        hasher = hashlib.md5()
        for file in files_to_hash:
            with open(file, "rb") as f:
                hasher.update(f.read())
        return hasher.hexdigest()

    def _signal_handler(self, signum, frame):
        """Handle cleanup on interrupt signals"""
        print("\nReceived interrupt signal. Cleaning up...")
        self.cleanup()
        exit(1)

    def run_git_command(self, cmd: list[str], cwd: str = None) -> str:
        """Run a git command in the specified directory"""
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            raise Exception(f"Git command failed: {result.stderr}")
        return result.stdout

    def setup_repo(self, commit_hash: str, is_target: bool = False) -> str:
        """Clone the repo at the specified commit"""
        # Determine repo directory name
        dir_name = "target" if is_target else "initial"
        repo_dir = self.repos_dir / dir_name

        # Clone the repo
        self.run_git_command(["git", "clone", self.config.repo_dir, str(repo_dir)])

        # Checkout the specific commit
        self.run_git_command(["git", "checkout", commit_hash], cwd=str(repo_dir))

        # Copy .env file if specified and exists
        if self.config.env_file and os.path.exists(self.config.env_file):
            shutil.copy2(self.config.env_file, repo_dir / ".env")

        return str(repo_dir)

    def setup_node_modules_cache(self, repo_dir: str) -> Tuple[bool, Optional[str]]:
        """Setup node_modules caching using symlinks"""
        repo_path = Path(repo_dir)
        node_modules = repo_path / "node_modules"

        # Generate cache key
        cache_key = self._generate_cache_key(repo_dir)
        if not cache_key:
            print("No package.json found or invalid configuration, skipping cache")
            return False, None

        cache_dir = self.cache_dir / "node_modules" / cache_key
        self.config.cached_node_modules_path = str(cache_dir)

        try:
            # If we have a valid cache
            if cache_dir.exists():
                print(f"Using cached node_modules from {cache_dir}")
                if node_modules.exists():
                    if node_modules.is_symlink():
                        node_modules.unlink()
                    else:
                        shutil.rmtree(node_modules)
                # Create symlink to cached node_modules
                node_modules.symlink_to(cache_dir, target_is_directory=True)
                return True, str(cache_dir)
        except Exception as e:
            print(f"Error setting up node_modules cache: {e}")
            # Clean up any partial setup
            if node_modules.is_symlink():
                node_modules.unlink()
            return False, None

        return False, None

    async def take_screenshots(
        self, urls: list[str], port: int = 3000, state: str = ""
    ) -> dict[str, str]:
        """Take screenshots of URLs using Playwright and return a dict mapping URLs to screenshot paths"""
        screenshots = {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for url in urls:
                try:
                    full_url = f"http://localhost:{port}{url}"
                    await page.goto(full_url, wait_until="networkidle")
                    await page.wait_for_timeout(2000)  # Wait for any dynamic content

                    # Create a sanitized filename from the URL
                    filename = url.replace("/", "_").strip("_")
                    if not filename:
                        filename = "root"
                    # Add state to filename if provided
                    if state:
                        filename = f"{filename}_{state}"
                    screenshot_path = str(
                        self.outputs_dir / "screenshots" / f"{filename}.png"
                    )

                    await page.screenshot(path=screenshot_path, full_page=True)
                    screenshots[url] = screenshot_path
                except Exception as e:
                    print(f"Error taking screenshot of {url}: {e}")

            await browser.close()
        return screenshots

    async def run_test(self) -> dict:
        """Run the test and return results"""
        try:
            # Setup repos
            print("Setting up test repositories...")
            self.test_dir = self.setup_repo(self.config.initial_commit)
            self.target_dir = self.setup_repo(self.config.target_commit, is_target=True)

            # Setup node_modules caching
            should_skip_install, cached_path = self.setup_node_modules_cache(
                self.test_dir
            )

            # Initialize debug session
            user = self.config.user
            debug_config = Debug(
                original_repo_dir=self.config.repo_dir,
                repo_dir=self.test_dir,
                env_file=self.config.env_file if self.config.env_file else None,
                settings=DebugSettings(
                    user=user,
                    created_repo_id="test-repo",
                    package_manager="yarn",
                    port=3000,
                    install_command="" if should_skip_install else "yarn install",
                    dev_command="yarn dev",
                    root_directory="/",
                ),
                initial_commit=self.config.initial_commit,
                target_commit=self.config.target_commit,
            )

            # Set cache-related attributes
            debug_config.settings.skip_install = should_skip_install
            debug_config.settings.cached_node_modules_path = cached_path

            # Initialize and run session
            session = Session(user, "test-session", debug=debug_config)
            await session.initializer.initialize()

            await session.chat.handle_user_message(
                self.config.user_input,
                selected_components=SelectedComponents(selected_components=[]),
                api_requests=[],
                images=[],
            )

            # Get diffs
            # Exclude package manager lock files from diff
            lock_files = [
                ":!package-lock.json",
                ":!pnpm-lock.yaml",
                ":!yarn.lock",
                ":!bun.lockb",
            ]
            result_diff = self.run_git_command(
                ["git", "diff", "HEAD", "--"] + lock_files, cwd=self.test_dir
            )
            expected_diff = self.run_git_command(
                [
                    "git",
                    "diff",
                    self.config.initial_commit,
                    self.config.target_commit,
                    "--",
                ]
                + lock_files,
                cwd=self.config.repo_dir,
            )

            # Save diffs to files
            (self.outputs_dir / "diffs" / "result_diff.patch").write_text(result_diff)
            (self.outputs_dir / "diffs" / "expected_diff.patch").write_text(
                expected_diff
            )

            # Create screenshots directory
            (self.outputs_dir / "screenshots").mkdir(parents=True, exist_ok=True)

            # Get URLs to screenshot
            urls_to_screenshot = set()
            if self.config.url_paths:
                urls_to_screenshot.update(self.config.url_paths)
            urls_to_screenshot.update(session.website.modified_urls)

            # Take screenshots of initial state
            print("Taking screenshots of initial state...")
            initial_screenshots = await self.take_screenshots(
                list(urls_to_screenshot), state="initial"
            )

            # Stop the current dev server
            try:
                await session.website.stop()
            except ProcessLookupError:
                print("Warning: Process already terminated")

            # Start the target repo's dev server
            target_debug_config = Debug(
                original_repo_dir=self.config.repo_dir,
                repo_dir=self.target_dir,
                settings=DebugSettings(
                    user=user,
                    created_repo_id="target-repo",
                    package_manager="yarn",
                    port=3000,
                    install_command="" if should_skip_install else "yarn install",
                    dev_command="yarn dev",
                    root_directory="/",
                ),
                initial_commit=self.config.initial_commit,
                target_commit=self.config.target_commit,
            )
            target_session = Session(user, "target-session", debug=target_debug_config)
            await target_session.initializer.initialize()

            # Take screenshots of target state
            print("Taking screenshots of target state...")
            target_screenshots = await self.take_screenshots(
                list(urls_to_screenshot), state="target"
            )

            # Stop the target dev server
            try:
                await target_session.website.stop()
            except ProcessLookupError:
                print("Warning: Target process already terminated")

            # Prepare results
            result = {
                "timestamp": self.timestamp,
                "initial_commit": self.config.initial_commit,
                "target_commit": self.config.target_commit,
                "user_input": self.config.user_input,
                "evaluator_text": self.config.evaluator_text,
                "result_diff": result_diff,
                "expected_diff": expected_diff,
                "test_repo_dir": self.test_dir,
                "target_repo_dir": self.target_dir,
                "cache_used": should_skip_install,
                "cache_path": cached_path,
                "modified_urls": list(session.website.modified_urls),
                "screenshots": {
                    "initial": initial_screenshots,
                    "target": target_screenshots,
                },
            }

            # Save results
            (self.current_run_dir / "results.json").write_text(
                json.dumps(result, indent=2)
            )

            return result
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up test directories and handle symlinks properly"""
        try:
            if self.test_dir:
                test_dir_path = Path(self.test_dir)
                node_modules = test_dir_path / "node_modules"

                # Remove symlink if it exists
                if node_modules.is_symlink():
                    node_modules.unlink()

                if test_dir_path.exists():
                    shutil.rmtree(test_dir_path)

            if self.target_dir:
                target_dir_path = Path(self.target_dir)
                node_modules = target_dir_path / "node_modules"

                # Remove symlink if it exists
                if node_modules.is_symlink():
                    node_modules.unlink()

                if target_dir_path.exists():
                    shutil.rmtree(target_dir_path)

        except Exception as e:
            print(f"Error during cleanup: {e}")


async def main():
    """Run a single test"""
    ISSUE_TRACKER_CONFIG = TestConfig(
        repo_dir="tests/eval_repos/issue-tracker-eval-repo",
        initial_commit="2ba002896ca525343c09b14b04e664ac6c4c684d",
        target_commit="5b89f63962ec4edb1c60305e1525295428228407",
        url_paths=["/custom-fields"],
        env_file="tests/eval_repos/issue-tracker-eval-repo/.env",
        user=User(id="e2534d13-0bda-42a1-8cf1-cb376b1a73bf", email="degtrdg@gmail.com"),
        evaluator_text=dedent(
            """
            Verify that:
            1. There is an API file with a POST endpoint for custom fields to edit the db
            2. There is a dedicated custom fields page
            3. The custom fields page is accessible from the navbar
            4. The custom fields form follows the same styling/pattern as the issues form
            5. The page shows existing custom fields
            6. The page has a form to add new custom fields

            if it is roughly correct given the user input, then it is good, no need to be pedantic
        """
        ).strip(),
        user_input="I want to make a new page for making custom fields. It should show the current custom fields and have an interface to add a new one.",
    )

    harness = TestHarness(ISSUE_TRACKER_CONFIG)
    try:
        await harness.run_test()
        print(
            f"\nTest completed successfully. Results saved in: {harness.current_run_dir}"
        )
    finally:
        harness.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
