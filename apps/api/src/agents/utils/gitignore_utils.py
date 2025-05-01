"""
Utilities for handling gitignore-related file filtering.
"""

import time
import traceback
from typing import TYPE_CHECKING, List

from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


async def filter_ignored_files(task: "Task", file_paths: List[str]) -> List[str]:
    """
    Filter a list of file paths by checking if they are tracked by Git.
    Files ignored by gitignore rules won't be tracked.
    """
    if not file_paths:
        return []

    start_time = time.time()
    try:
        # Get all tracked files from Git
        git_cmd = "git ls-files"
        result = await task.sandbox.run_command(git_cmd, use_repo_subdir=False)
        tracked_files = {
            line.strip() for line in result.stdout.splitlines() if line.strip()
        }

        # Also get untracked files that aren't ignored
        untracked_cmd = "git ls-files --others --exclude-standard"
        result = await task.sandbox.run_command(untracked_cmd, use_repo_subdir=False)
        untracked_not_ignored = {
            line.strip() for line in result.stdout.splitlines() if line.strip()
        }

        # Combine both sets to get all non-ignored files
        non_ignored_files = tracked_files.union(untracked_not_ignored)

        # Normalize paths for comparison
        normalized_non_ignored = {
            await normalize_path(task, path) for path in non_ignored_files
        }

        # Keep files that are in the non-ignored set
        filtered_paths = []
        for path in file_paths:
            norm_path = await normalize_path(task, path)
            if norm_path in normalized_non_ignored:
                filtered_paths.append(path)
            else:
                logger.debug(f"File not tracked by Git (likely ignored): {path}")

        elapsed_time = time.time() - start_time
        logger.debug(
            f"filter_ignored_files took {elapsed_time:.3f} seconds to process {len(file_paths)} files, "
            f"found {len(filtered_paths)} non-ignored files"
        )

        return filtered_paths

    except Exception:
        logger.error(traceback.format_exc())
        return file_paths
