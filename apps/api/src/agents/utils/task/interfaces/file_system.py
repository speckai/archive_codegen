import asyncio
import json
from typing import TYPE_CHECKING

from morphcloud.api import InstanceExecResponse

from src.database import Database
from src.schemas.core.common import FileObject, MessageType, ProjectDependencies

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class FileSystem:
    def __init__(self, task: "Task"):
        self.task: Task = task
        self.original_file_contents: dict[
            str, str
        ] = {}  # List of changed files and their original contents
        self.runtime_files: list[FileObject] = []

    def fetch_runtime_files(self) -> list[FileObject]:
        runtime_files_raw: list[dict[str, str]] = Database.get_repo_property(
            self.task.git.repo_id, "runtime_files"
        )
        runtime_files: list[FileObject] = [
            FileObject(**file) for file in runtime_files_raw
        ]
        self.runtime_files = runtime_files
        return runtime_files

    async def modify_file(
        self,
        path: str,
        contents: str,
        save_to_file: bool = True,
        use_repo_subdir: bool = True,
    ):
        if path not in self.original_file_contents:
            original_content: FileObject = await self.get_file(path, use_repo_subdir)
            await self.register_file_change(path, original_content.content)

        await self.task.send_update_data(
            MessageType.MODIFY_FILE, {"file_path": path, "content": contents}
        )
        if save_to_file:
            await self.task.set_has_changes(True)
            await self.task.sandbox.write_file(
                path, contents, make_dirs=True, use_repo_subdir=use_repo_subdir
            )

    async def create_file(
        self,
        path: str,
        contents: str,
        save_to_file: bool = True,
    ) -> bool:
        await self.register_file_change(path, "")
        await self.task.send_update_data(
            MessageType.CREATE_FILE, {"file_path": path, "content": contents}
        )
        if save_to_file:
            await self.task.set_has_changes(True)
            return await self.task.sandbox.write_file(path, contents)
        return False

    async def delete_file(self, path: str):
        """Delete a file from both the frontend and filesystem if save_to_file is True"""
        await self.task.set_has_changes(True)
        if path not in self.original_file_contents:
            original_content: FileObject = await self.get_file(path)
            await self.register_file_change(path, original_content.content)

        await self.task.send_update_data(MessageType.DELETE_FILE, {"file_path": path})
        await self.task.sandbox.run_command(f"rm {path}")

    async def register_file_change(self, path: str, contents: str):
        if path not in self.original_file_contents:
            self.original_file_contents[path] = contents

        await self.task.send_update_data(
            MessageType.ORIGINAL_FILE_CONTENTS,
            {"files": self.original_file_contents},
        )

    async def reset_original_file_contents(self):
        self.original_file_contents = {}
        await self.task.send_update_data(
            MessageType.ORIGINAL_FILE_CONTENTS,
            {"files": self.original_file_contents},
        )

    async def get_file(self, file_path: str) -> FileObject | None:
        content: str = await self.task.sandbox.get_file(file_path)
        return FileObject(file_path=file_path, content=content)

    async def get_all_tracked_file_paths(self) -> list[str]:
        # Get tracked and untracked files w/o stuff in .gitignore
        # extra processing to filter out submodules (had a problem with an empty submodule)
        file_results: InstanceExecResponse = await self.task.sandbox.run_command(
            "cd /repo && bash -c 'git ls-files --cached --others --exclude-standard | grep -v -f <(git submodule status | awk \"{print \\$2}\")'",
        )

        file_paths: list[str] = [
            result.strip()
            for result in file_results.stdout.split("\n")
            if result.strip()
        ]

        if self.runtime_files:
            runtime_file_paths = [
                f.file_path.strip().removeprefix("./") for f in self.runtime_files
            ]
            file_paths.extend(f for f in runtime_file_paths if f not in file_paths)

        # starting_len: int = len(file_paths)

        banned_extensions: set[str] = {
            ".png",
            ".jpg",
            ".gif",
            ".pyc",
            ".woff",
            ".webp",
            ".ico",
            ".svg",
            ".avif",
            ".lockb",
            ".jpeg",
            ".ttf",
            ".woff2",
            ".eot",
            ".otf",
            ".mp4",
            ".gz",
            ".mp3",
            ".wav",
            ".m4a",
            ".m4v",
            ".m4b",
            ".m4p",
            ".xlsx",
            ".xls",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".parquet",
        }
        file_paths = [
            file_path
            for file_path in file_paths
            if not any(file_path.endswith(ext) for ext in banned_extensions)
        ]
        # banned_removed_len: int = starting_len - len(file_paths)

        file_paths = [
            file_path
            for file_path in file_paths
            if "package-lock.json" not in file_path
        ]
        # package_lock_removed_len: int = starting_len - len(file_paths)

        file_paths = [
            file_path
            for file_path in file_paths
            if not file_path.startswith("build/") and "/build/" not in file_path
        ]
        # build_removed_len: int = starting_len - len(file_paths)

        # if build_removed_len != starting_len:
        #     logger.warning(
        #         f"Pruned bad files. Start {starting_len}, banned {banned_removed_len}, package-lock {package_lock_removed_len}, build {build_removed_len}"
        #     )
        return file_paths

    async def get_all_tracked_file_path_trees(self) -> str:
        file_paths: list[str] = await self.get_all_tracked_file_paths()

        tree: dict = {}
        current: dict = tree
        for path in sorted(file_paths):
            current = tree
            parts: list[str] = path.split("/")
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = None
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        def build_tree_str(node: dict, prefix: str = "") -> str:
            output: list[str] = []
            if node is None:
                return ""

            items: list[tuple[str, dict]] = list(node.items())
            for i, (name, subtree) in enumerate(items):
                is_last_item: bool = i == len(items) - 1
                output.append(prefix + ("└── " if is_last_item else "├── ") + name)
                if subtree is not None:
                    extension: str = "    " if is_last_item else "│   "
                    output.append(build_tree_str(subtree, prefix + extension))

            return "\n".join(output)

        return build_tree_str(tree)

    async def get_all_tracked_files(
        self, use_repo_subdir: bool = True
    ) -> list[FileObject]:
        file_paths: list[str] = await self.get_all_tracked_file_paths(
            use_repo_subdir=use_repo_subdir
        )
        banned_extensions: tuple[str, ...] = (
            ".png",
            ".jpg",
            ".gif",
            ".pyc",
            ".lockb",
            ".xlsx",
            ".xls",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".parquet",
        )
        file_paths = [
            file_path
            for file_path in file_paths
            if not file_path.endswith(banned_extensions)
        ]
        return await asyncio.gather(
            *[
                self.get_file(file_path, use_repo_subdir=use_repo_subdir)
                for file_path in file_paths
            ]
        )

    async def get_dependencies(self) -> ProjectDependencies:
        """
        Get the dependencies and devDependencies from package.json
        """
        package_json: FileObject | None = await self.get_file("package.json")
        if package_json is None:
            raise ValueError("package.json not found")

        package_json_data: dict[str, any] = json.loads(package_json.content)
        dependencies: dict[str, str] = package_json_data.get("dependencies", {})
        dev_dependencies: dict[str, str] = package_json_data.get("devDependencies", {})
        return ProjectDependencies(
            dependencies=dependencies, dev_dependencies=dev_dependencies
        )

    async def create_patch(self) -> str:
        """
        Create a patch (including binary changes) for all changes in the repo
        including new/untracked files.
        """
        add_result: InstanceExecResponse = await self.task.sandbox.run_command(
            "git add -A"
        )
        if add_result.exit_code != 0:
            raise RuntimeError(f"Failed to stage untracked files: {add_result.stderr}")

        diff_result: InstanceExecResponse = await self.task.sandbox.run_command(
            "cd /repo && git diff --cached --binary"
        )
        if diff_result.exit_code != 0:
            raise RuntimeError(f"Failed to create patch: {diff_result.stderr}")

        return diff_result.stdout

    async def apply_patch(self, patch_content: str = None) -> None:
        """
        Apply a patch to the repo. If no content is provided, use the last patch stored.
        """
        if not patch_content:
            raise ValueError("No patch content available to apply.")

        temp_patch_path: str = "/repo/changes.patch"
        await self.task.sandbox.write_file(temp_patch_path, patch_content)

        apply_result: InstanceExecResponse = await self.task.sandbox.run_command(
            f"cd /repo && git apply {temp_patch_path}"
        )
        if apply_result.exit_code != 0:
            raise RuntimeError(f"Failed to apply patch: {apply_result.stderr}")

        await self.task.sandbox.run_command(f"rm {temp_patch_path}")
