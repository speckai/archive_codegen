import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.agents.utils.task.debug.common import Debug
from src.agents.utils.task.debug.settings import DebugSettings
from src.agents.utils.task.task import Task
from src.schemas.account import User
from src.schemas.core.common.modifications import ModificationsPlan
from src.utils.logging import logger

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"


class AgentDebugHarness:
    def __init__(self, debug_data_path: str):
        self.debug_data_path = Path(debug_data_path)

        if not self.debug_data_path.exists():
            raise ValueError(f"Debug data file not found: {debug_data_path}")

        # Load debug data
        with open(self.debug_data_path) as f:
            self.debug_data = json.load(f)

        # Setup directories
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_root = Path(os.getcwd())
        self.cache_dir = self.project_root / ".cache"
        self.test_runs_dir = self.project_root / "agent_test_runs"
        self.current_run_dir = self.test_runs_dir / self.timestamp
        self.repos_dir = self.current_run_dir / "repos"

        # Create directories
        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "node_modules").mkdir(exist_ok=True)
        self.test_runs_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def _setup_node_modules_cache(self, repo_dir: str) -> tuple[bool, Optional[str]]:
        """Setup node_modules caching using symlinks"""
        repo_path = Path(repo_dir)
        node_modules = repo_path / "node_modules"

        # Generate cache key based on package.json
        if not (repo_path / "package.json").exists():
            return False, None

        import hashlib

        with open(repo_path / "package.json", "rb") as f:
            cache_key = hashlib.md5(f.read()).hexdigest()

        cache_dir = self.cache_dir / "node_modules" / cache_key

        try:
            # If we have a valid cache
            if cache_dir.exists():
                logger.info(f"Using cached node_modules from {cache_dir}")
                if node_modules.exists():
                    if node_modules.is_symlink():
                        node_modules.unlink()
                    else:
                        shutil.rmtree(node_modules)
                # Create symlink to cached node_modules
                node_modules.symlink_to(cache_dir, target_is_directory=True)
                return True, str(cache_dir)

            # If node_modules exists and we don't have a cache yet
            if node_modules.exists() and not node_modules.is_symlink():
                logger.info(f"Creating new cache at {cache_dir}")
                cache_dir.parent.mkdir(parents=True, exist_ok=True)
                # Move existing node_modules to cache and symlink back
                shutil.move(str(node_modules), str(cache_dir))
                node_modules.symlink_to(cache_dir, target_is_directory=True)
                return True, str(cache_dir)

        except Exception as e:
            logger.error(f"Error setting up node_modules cache: {e}")
            if node_modules.is_symlink():
                node_modules.unlink()
            return False, None

        return False, None

    def run_git_command(self, cmd: list[str], cwd: str = None) -> str:
        """Run a git command in the specified directory"""
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if result.returncode != 0:
            raise ValueError(f"Git command failed: {result.stderr}")
        return result.stdout

    async def setup_session(self) -> Task:
        """Setup debug session and replay actions"""
        test_dir = self.repos_dir / "test_repo"
        original_repo_dir = self.debug_data["debug_settings"]["original_repo_dir"]

        # Clone the repo
        self.run_git_command(["git", "clone", original_repo_dir, str(test_dir)])

        # Checkout the specific commit if provided
        if self.debug_data["initial_commit"]:
            self.run_git_command(
                ["git", "checkout", self.debug_data["initial_commit"]],
                cwd=str(test_dir),
            )

        # Copy .env file if specified in debug settings
        env_file = self.debug_data["debug_settings"].get("env_file")
        if env_file and os.path.exists(env_file):
            shutil.copy2(env_file, test_dir / ".env")

        # Setup node_modules caching
        should_skip_install, cached_path = self._setup_node_modules_cache(str(test_dir))

        # Initialize debug session
        user = User.model_validate_json(self.debug_data["debug_settings"]["user"])
        debug_config = Debug(
            repo_dir=test_dir,
            original_repo_dir=original_repo_dir,
            debug_agent=True,
            env_file=env_file if env_file else None,
            settings=DebugSettings(
                user=user,
                created_repo_id="test-repo",
                package_manager="yarn",
                port=3000,
                install_command="" if should_skip_install else "yarn install",
                dev_command="yarn dev",
                root_directory="/",
            ),
            initial_commit=self.debug_data["initial_commit"],
            target_commit=self.debug_data["target_commit"],
        )

        # Set cache-related attributes
        debug_config.settings.skip_install = should_skip_install
        debug_config.settings.cached_node_modules_path = cached_path

        # Initialize session
        session = Session(user, "test-session", debug=debug_config)
        await session.initializer.initialize()

        # Replay debug actions
        for action in self.debug_data["debug_actions"]:
            if action["type"] == "run_command":
                await session.sandbox.run_command(
                    command=action["command"],
                    timeout=action.get("timeout"),
                )
            elif action["type"] == "write_file":
                await session.sandbox.write_file(
                    file_path=str(action["file_path"]),
                    content=str(action["content"]),
                )

        return session

    def cleanup(self):
        """Clean up test directories"""
        try:
            if self.repos_dir.exists():
                for repo_dir in self.repos_dir.iterdir():
                    node_modules = repo_dir / "node_modules"
                    if node_modules.is_symlink():
                        node_modules.unlink()
                shutil.rmtree(self.repos_dir)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Example usage of the harness"""
    # This would be the path to a debug data file generated by the @debug_agent_function decorator
    debug_data_path = (
        ".debug/ImplementerAgent/implement_plan/20241225_141133/debug_data.json"
    )

    harness = AgentDebugHarness(debug_data_path)
    try:
        session = await harness.setup_session()
        modifications_plan = ModificationsPlan.model_validate(
            harness.debug_data["args"][0]
        )
        override_files = harness.debug_data["kwargs"].get("override_files")
        mock_task = Task(
            user_message="Test task message",
            session=session,
            selected_components=None,
            api_requests=[],
            images=[],
            relevant_chats=[],
            fully_autonomous=True,
            is_cloning_site=False,
        )
        session.current_workflow = mock_task
        await session.implementer.implement_plan(
            modifications_plan, override_files=override_files
        )

    finally:
        harness.cleanup()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
