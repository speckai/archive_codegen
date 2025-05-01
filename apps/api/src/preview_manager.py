import time
import traceback

import socketio
from github import Github
from github.Repository import Repository
from src.database import Database
from src.github.utils import (
    get_github_token,
    get_installation_id_from_owner,
)
from src.repos.settings.utils import get_settings
from src.schemas.core.common import (
    AddedRepository,
    ChatMessage,
    Settings,
)
from src.schemas.core.common.files import FileObject
from src.schemas.core.common.state import SerializedTask
from src.schemas.core.common.types import MessageType
from src.socket_manager import get_socket
from src.utils.logging import logger


async def _send_socket_message(self, message_type: MessageType, data: dict, to: str):
    sio: socketio.AsyncServer = get_socket()
    await sio.emit(
        "preview_data",
        {
            "message_type": message_type.value,
            "data": data,
        },
        to=to,
    )


class PreviewTask:
    def __init__(self, task_id: str):
        self.task_id: str = task_id
        self.preview_url: str | None = None
        self.did_initialize: bool = False

        repo: AddedRepository | None = Database.get_repo_from_task_id_no_user(task_id)
        if not repo:
            raise ValueError(f"Task {task_id} not found")
        self.repo: AddedRepository = repo

        task_data: SerializedTask = next(t for t in repo.tasks if t.task_id == task_id)
        self.saved_task: SerializedTask = task_data
        self.workspace_name: str = task_data.workspace_name
        self.chat_messages: list[ChatMessage] = task_data.chat_history

        self.subdirectory: str | None = None
        self.settings: Settings = get_settings(repo.git_repo_id, self.workspace_name)

        self.connected_users: list[str] = []  # list of socket ids

    async def user_connect(self, socket_id: str):
        self.connected_users.append(socket_id)
        if not self.did_initialize:
            await self._initialize()

        await _send_socket_message(
            MessageType.SET_PREVIEW_URL, {"url": self.preview_url}, socket_id
        )
        for chat_message in self.chat_messages:
            await _send_socket_message(
                MessageType.CHAT_MESSAGE, chat_message.model_dump(), socket_id
            )

    async def user_disconnect(self, socket_id: str) -> bool:
        """
        Returns true if the task should be deleted (if the last user disconnected)
        """
        self.connected_users.remove(socket_id)
        if not self.connected_users:
            await self.destroy()
            return True
        return False

    async def _initialize_sandbox(self) -> str:
        """Returns preview url"""
        try:
            self.subdirectory = self.settings.root_directory
            logger.info(f"Initializing sandbox for {self.task_id}")
            self.container_info: ContainerInfo = await self.manager.start_container()
            return self.manager.public_preview_url
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Failed to initialize sandbox: {e}")
            await self.destroy()
            raise

    async def clone(self):
        _github_installation_id: str = get_installation_id_from_owner(
            self.repo.owner["id"]
        )

        github_token: str = get_github_token(_github_installation_id)
        branch_name: str = self.settings.branch
        github: Github = Github(github_token)
        repo: Repository = github.get_repo(self.repo.git_repo_id)

        tokenized_clone_url: str = repo.clone_url.replace(
            "https://github.com/",
            f"https://x-access-token:{github_token}@github.com/",
        )

        await self.manager.run_command(
            "ls /repo 2>/dev/null && rm -rf /repo", mode=CommandMode.WAIT
        )

        res: CommandResult = await self.manager.run_command(
            f"git clone --depth=1 --single-branch --branch={branch_name} {tokenized_clone_url} /repo",
            mode=CommandMode.WAIT,
        )

        if res.exit_code != 0:
            update_commands = [
                f"git remote set-url origin {tokenized_clone_url}",
                "git fetch",
                f"git reset --hard origin/{branch_name}",
                "git clean -fd",
            ]
            update_command: str = " && ".join(update_commands)
            res: CommandResult = await self.manager.run_command(update_command)
        else:
            await self.manager.run_command(f"git checkout {branch_name}")

        root_directory: str = self.settings.root_directory
        root_directory = root_directory.strip("/")

        start_time: float = time.time()
        await self._restore_cached_directories()
        logger.success(
            f"Restored cached directories in {time.time() - start_time:.2f} seconds"
        )

        runtime_files_raw: list[dict[str, str]] = Database.get_repo_property(
            self.repo.git_repo_id, "runtime_files"
        )
        runtime_files: list[FileObject] = [
            FileObject(**file) for file in runtime_files_raw
        ]

        for runtime_file in runtime_files:
            await self.manager.write_file(runtime_file.file_path, runtime_file.content)

        if self.saved_task.patch_content:
            await self.manager.apply_patch(self.saved_task.patch_content)

    async def _initialize(self):
        self.preview_url = await self._initialize_sandbox()
        self.did_initialize = True

    async def _destroy(self):
        await self.manager.cleanup()


class _PreviewManager:
    def __init__(self):
        self.tasks: dict[str, PreviewTask] = {}  # task_id -> PreviewTask
        self.socket_map: dict[str, str] = {}  # socket_id -> task_id

    async def user_connect(self, task_id: str, socket_id: str):
        self.socket_map[socket_id] = task_id
        if task_id not in self.tasks:
            self.tasks[task_id] = PreviewTask(task_id)
        await self.tasks[task_id].user_connect(socket_id)

    async def user_disconnect(self, socket_id: str):
        task_id: str = self.socket_map.get(socket_id)
        if not task_id:
            logger.error(f"Socket {socket_id} not found in socket map")
            return False
        del self.socket_map[socket_id]
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found in tasks")
            return False

        should_delete: bool = await self.tasks[task_id].user_disconnect(socket_id)
        if should_delete:
            del self.tasks[task_id]


PreviewManager: _PreviewManager = _PreviewManager()
