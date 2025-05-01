import json
import os
from typing import TYPE_CHECKING

from src.agents.code_analyzer.utils.cache import CodebaseGraphCache
from src.agents.code_analyzer.utils.path_utils import absolute_path, normalize_path
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class ImportFinder:
    """
    Handles finding import relationships between files with caching support.
    Abstracts the cache management and provides a clean interface for import lookups.
    """

    def __init__(self, task: "Task"):
        """
        Initialize the ImportFinder with a Task instance and CodebaseGraphCache.

        :param task: Task object containing sandbox and settings
        :param cache: CodebaseGraphCache instance for storing/retrieving import relationships
        """
        self.task: "Task" = task
        self.cache: CodebaseGraphCache = CodebaseGraphCache()

    async def get_imports(self, target_file: str) -> list[str]:
        """
        Gets the import relationships for a specific file.

        :param target_file: Path to the file to find imports for
        :return: List of file paths
        """
        try:
            if not self.cache.is_valid:
                await self._refresh_cache()

            normalized_target_file: str = await normalize_path(self.task, target_file)
            return self.cache.get_surrounding_files(normalized_target_file)

        except Exception as e:
            logger.error(f"Error finding imports of {target_file}: {str(e)}")
            return []

    async def _refresh_cache(self) -> None:
        """
        Refreshes the imports cache by running a single command via list-routes,
        storing the result in memory.
        """
        try:
            rel_root_dir: str = (await self.task.settings.get_root_directory()).lstrip(
                "/"
            )

            tsconfig_path: str | None = await self.task.settings.get_tsconfig_path()
            if not tsconfig_path:
                logger.error("No tsconfig.json found, we shouldn't have this happen")

            if not tsconfig_path:
                tsconfig_path = os.path.join(rel_root_dir, "tsconfig.json")

            logger.debug(f"tsconfig_path: {tsconfig_path}")
            normalized_tsconfig_path: str = await absolute_path(
                self.task, tsconfig_path
            )
            logger.debug(f"normalized_tsconfig_path: {normalized_tsconfig_path}")

            temp_file = "imports_cache.json"

            await self.task.sandbox.run_command(
                f'npx --yes --package=list-routes@latest find-imports "{normalized_tsconfig_path}" --dump-cache > {self.task.sandbox.manager.workspace_path}/{temp_file}'
            )

            # Read from the temp file instead of stdout
            file_content = await self.task.sandbox.get_file(
                temp_file, use_repo_subdir=False
            )
            if not file_content:
                logger.error(f"No file content found for {temp_file}")
            last_line = file_content.strip().split("\n")[-1]
            raw_cache: dict = json.loads(last_line)

            await self.task.sandbox.run_command(
                f"rm {self.task.sandbox.manager.workspace_path}/{temp_file}"
            )

            cache_data: dict[str, dict[str, list[str]]] = {}
            for k, imports in raw_cache.items():
                normalized_imports: dict[str, list[str]] = {}
                for m, v in imports.items():
                    normalized_m: str = await normalize_path(self.task, m)
                    normalized_v: list[str] = [
                        await normalize_path(self.task, f) for f in v
                    ]
                    normalized_imports[normalized_m] = normalized_v

                cache_data[k] = normalized_imports

            self.cache.set_cache(cache_data)
            logger.debug("Codebase graph cache refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing imports cache: {str(e)}")
            raise

    def invalidate_cache(self) -> None:
        """
        Invalidates the cache to force a refresh on next query.

        :return: None
        """
        self.cache.invalidate()
        logger.debug("Codebase graph cache invalidated")

    async def ensure_fresh_cache(self) -> None:
        """
        Ensures the cache is fresh, refreshing if needed.

        :return: None
        """
        if not self.cache.is_valid:
            logger.debug("Codebase graph cache invalid or expired, refreshing...")
            await self._refresh_cache()
