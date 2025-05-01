from typing import TYPE_CHECKING

from morphcloud.api import InstanceExecResponse
from src.agents.code_analyzer.utils.path_utils import normalize_path
from src.schemas.core.common.files import FileObject

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


async def read_files_into_fileinfo(task: "Task", files: set[str]) -> list[FileObject]:
    """
    Creates FileObject objects for each file by reading their content.
    All files are concatenated with a marker for efficient retrieval.

    :param task: Task object containing sandbox for file operations
    :param files: Set of file paths to read
    :param main_file: Main file path to mark in the FileObject objects
    :return: List of FileObject objects with file content and metadata
    """
    # TODO: remove this to have a function optimized for the sandbox
    if not files:
        return []

    relative_paths: list[str] = [
        await normalize_path(task, file_path) for file_path in files
    ]

    marker: str = "###UNIQUE_FILE_BOUNDARY_MARKER###"
    cat_command: str = (
        f"for f in {' '.join(f'"{path}"' for path in relative_paths)}; do "
        f"echo '{marker}' \"$f\"; "
        f'cat "$f"; '
        f"echo; "
        f"done"
    )
    result: InstanceExecResponse = await task.sandbox.run_command(cat_command)

    sections: list[str] = result.stdout.split(marker)[1:]

    file_infos: list[FileObject] = []
    for section in sections:
        lines: list[str] = section.strip().split("\n")
        if lines:
            path: str = lines[0].strip()
            content: str = "\n".join(lines[1:]).strip()
            file_infos.append(FileObject(file_path=path, content=content))

    return file_infos
