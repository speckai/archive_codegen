import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


async def normalize_path(task: "Task", file_path: str) -> str:
    """
    Normalizes a file path to be relative to the root directory.

    :param task: Task object containing settings and sandbox information
    :param file_path: The file path to normalize
    :return: Normalized file path relative to the root directory
    """
    workspace_path: str = task.sandbox.manager.workspace_path
    return file_path.removeprefix(workspace_path).removeprefix("/")


async def absolute_path(task: "Task", file_path: str) -> str:
    """
    Returns the absolute path of a file.
    """
    normalized_path: str = await normalize_path(task, file_path)
    return os.path.join(task.sandbox.manager.workspace_path, normalized_path)
