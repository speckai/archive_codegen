import logging
from os import path
from typing import TypedDict

from src.agents.implementer.utils.persistent_shell import (
    _PersistentShell,
    get_persistent_shell,
)
from src.agents.utils.task.interfaces.sandbox import Sandbox
from src.utils.logging import logger

MAX_FILES = 1000

# Define a platform-independent separator for paths
PATH_SEP = "/"


class TreeNode(TypedDict):
    name: str
    path: str
    type: str
    children: list["TreeNode"] | None


def skip(file_path: str) -> bool:
    """Determine if a path should be skipped."""
    if file_path != "." and path.basename(file_path).startswith("."):
        return True
    return f"__pycache__{PATH_SEP}" in file_path


async def list_directory(initial_path: str, cwd: str) -> list[str]:
    """List all files and directories in a directory using the sandbox."""
    shell: _PersistentShell = get_persistent_shell()
    sandbox: Sandbox = shell.get_sandbox()
    results: list[str] = []

    try:
        # Use the find command to list all files and directories
        # The -type d and -type f options list directories and files separately
        dirs_cmd = f"find '{initial_path}' -type d | sort"
        files_cmd = f"find '{initial_path}' -type f | sort"

        # Get directories
        dirs_result = await sandbox.run_command(dirs_cmd)
        if dirs_result.exit_code == 0:
            dirs = [d.strip() for d in dirs_result.stdout.splitlines() if d.strip()]

            # Filter out directories to skip
            for dir_path in dirs:
                if skip(dir_path):
                    continue

                if dir_path != initial_path:
                    # Add trailing slash to directories
                    rel_path = path.relpath(dir_path, cwd) + PATH_SEP
                    results.append(rel_path)

                if len(results) > MAX_FILES:
                    return results
        else:
            logger.error(
                f"Error listing directories {initial_path}: {dirs_result.stderr}"
            )

        # Get files
        files_result = await sandbox.run_command(files_cmd)
        if files_result.exit_code == 0:
            files = [f.strip() for f in files_result.stdout.splitlines() if f.strip()]

            # Filter out files to skip
            for file_path in files:
                if skip(file_path):
                    continue

                rel_path = path.relpath(file_path, cwd)
                results.append(rel_path)

                if len(results) > MAX_FILES:
                    return results
        else:
            logger.error(f"Error listing files {initial_path}: {files_result.stderr}")

    except Exception as e:
        logging.error(f"Error listing directory {initial_path}: {e}")

    return results


def create_file_tree(sorted_paths: list[str]) -> list[TreeNode]:
    """Create a tree structure from a list of sorted paths."""
    root: list[TreeNode] = []

    for file_path in sorted_paths:
        parts: list[str] = file_path.split(PATH_SEP)
        current_level: list[TreeNode] = root
        current_path: str = ""

        for i, part in enumerate(parts):
            if not part:  # Skip empty parts (trailing slashes)
                continue

            current_path: str = path.join(current_path, part) if current_path else part
            is_last_part: bool = i == len(parts) - 1

            existing_node: TreeNode | None = next(
                (node for node in current_level if node["name"] == part), None
            )

            if existing_node:
                current_level = existing_node.get("children", [])
            else:
                new_node = {
                    "name": part,
                    "path": current_path,
                    "type": "file" if is_last_part else "directory",
                    "children": None if is_last_part else [],
                }

                current_level.append(new_node)
                current_level = new_node.get("children", [])

    return root


def print_tree(tree: list[TreeNode], cwd: str, level: int = 0, prefix: str = "") -> str:
    """Format a tree structure for display."""
    result: str = ""

    if level == 0:
        result += f"- {cwd}{PATH_SEP}\n"
        prefix = "  "

    for node in tree:
        node_type_indicator: str = PATH_SEP if node["type"] == "directory" else ""
        result += f"{prefix}- {node['name']}{node_type_indicator}\n"

        if node.get("children") and len(node["children"]) > 0:
            result += print_tree(node["children"], cwd, level + 1, f"{prefix}  ")

    return result
