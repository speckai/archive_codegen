import traceback

import socketio

from src.agents.utils.task.task import Task
from src.config import DEV
from src.database import Database
from src.redis_manager import RedisManager
from src.repos.entries.utils import get_workspace
from src.schemas.account import User

# import tracemalloc
from src.schemas.core.common import (
    AddedRepository,
    BugReport,
    ChatMessage,
    ChatMessageRole,
    MainMessage,
    MessageData,
    MessageType,
    RecordingCollection,
    Workspace,
)
from src.schemas.core.common.recordings import Recording
from src.socket_manager import get_socket
from src.utils.logging import logger


class _TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}  # task_id -> Task

    async def create_task(self, user: User, task_id: str, socket_id: str) -> Task:
        task: Task | None = None

        git_repo_id: int | None = None
        workspace_name: str | None = None

        repo: AddedRepository | None = Database.get_repo_from_task_id(user.id, task_id)
        if repo:
            git_repo_id = repo.git_repo_id
            task_data = next(t for t in repo.tasks if t.task_id == task_id)
            workspace_name = task_data.workspace_name
            issue_number = task_data.issue_number

        try:
            if not (git_repo_id and workspace_name):
                (
                    git_repo_id,
                    workspace_name,
                    issue_number,
                ) = await RedisManager.retrieve_task_id(task_id)
            if not (git_repo_id and workspace_name):
                logger.error(f"Failed to retrieve task ID {task_id}")
                return None

            new_workspace: Workspace = get_workspace(git_repo_id, workspace_name)

            task: Task = Task(
                user=user,
                task_id=task_id,
                git_repo_id=git_repo_id,
                issue_number=issue_number,
                workspace=new_workspace,
            )
            task.user_socket_id = socket_id
            logger.info(f"Created task for user: {user.name}")
            self.tasks[task_id] = task
            await task.initializer.initialize()
        except Exception as e:
            sio: socketio.AsyncServer = get_socket()
            await sio.emit(
                "task_data",
                {
                    "message_type": MessageType.INITIALIZATION_ERROR.value,
                    "data": {},
                },
                to=task_id,
            )
            if task:
                await task.destroy()

            logger.error(f"Error creating task for user: {user.name}")
            logger.error(traceback.format_exc())
            raise e

    async def restart_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not in task")
        task: Task = self.tasks[task_id]
        await task.initializer.initialize()

    async def _handle_user_message(self, data: dict[str, str | int]) -> None:
        task_id: str = data["task_id"]
        git_repo_id: int = data["git_repo_id"]
        workspace_name: str = data["workspace_name"]

        if task_id not in self.tasks:
            raise ValueError("Task not in task")

        task: Task = self.tasks[task_id]
        if task.git.repo_id != git_repo_id or task.workspace.name != workspace_name:
            raise ValueError("Repo ID does not match")

        message: str = data["message"]

        recordings: list[dict] = data["recordings"]
        recordings: RecordingCollection = RecordingCollection(
            recordings=[Recording(**recording) for recording in recordings]
        )
        is_autonomous: bool = data.get("is_autonomous", False)
        await task.chat.handle_user_message(
            message,
            recordings,
            is_autonomous,
        )

    async def handle_user_message(
        self, user: User, data: dict[str, str], sio: socketio.AsyncServer
    ) -> None:
        try:
            await self._handle_user_message(data)
        except Exception as e:
            await sio.emit(
                "task_data",
                {
                    "message_type": MessageType.CHAT_MESSAGE.value,
                    "data": ChatMessage(
                        role=ChatMessageRole.ASSISTANT,
                        message_data=MessageData(
                            main_message=MainMessage(
                                message="I've encountered an error, please try reloading the page."
                            ),
                        ),
                    ).model_dump(),
                },
            )
            logger.error(e)
            logger.error(traceback.format_exc())

    async def handle_submitted_recording(
        self, user: User, data: dict[str, str | int]
    ) -> None:
        task_id: str = data["task_id"]
        git_repo_id: int = data["git_repo_id"]
        workspace_name: str = data["workspace_name"]
        recording_data: dict = data["recording_data"]

        if task_id not in self.tasks:
            raise ValueError("Task not in task")

        task: Task = self.tasks[task_id]
        if DEV:
            import json

            with open("temp_recording.json", "w") as f:
                json.dump(recording_data, f)
        try:
            recording: Recording = Recording(**recording_data)
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            with open("recording_data.json", "w") as f:
                json.dump(recording_data, f)
            raise e

        if task.git.repo_id != git_repo_id or task.workspace.name != workspace_name:
            raise ValueError("Repo ID does not match")

        await task.generate_bug_report(recording)

    async def handle_submitted_report(
        self, user: User, data: dict[str, str | int]
    ) -> None:
        task_id: str = data["task_id"]
        git_repo_id: int = data["git_repo_id"]
        workspace_name: str = data["workspace_name"]
        report_data: dict = data["report_data"]

        if task_id not in self.tasks:
            raise ValueError("Task not in task")

        task: Task = self.tasks[task_id]
        bug_report: BugReport = BugReport(**report_data)

        if task.git.repo_id != git_repo_id or task.workspace.name != workspace_name:
            raise ValueError("Repo ID does not match")

        logger.info("Creating issue")
        await task.create_issue(bug_report)

    def get_task_from_id(self, task_id: str) -> Task | None:
        return self.tasks.get(task_id)

    async def user_connect(self, user: User, task_id: str, socket_id: str) -> None:
        task: Task | None = self.tasks.get(task_id)

        if task is None:
            await self.create_task(user, task_id, socket_id)
        else:
            success: bool = await task.task_state_manager.sync_latest_task_state()
            self.register_task(task_id, task)
            task.user_socket_id = socket_id

            if not success:
                await self.restart_task(user)

    def register_task(self, task_id: str, task: Task) -> None:
        self.tasks[task_id] = task

    def deregister_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            logger.info(f"Task {task_id} not in tasks, skipping mem deletion")
            return
        logger.info(f"Deleting task B {task_id}")

        self.tasks.pop(task_id)

    def socket_disconnect(self, task_id: str) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].user_socket_id = None

    async def soft_close_task(self, user: User, task_id: str) -> None:
        if task_id not in self.tasks:
            logger.info(f"Task {task_id} not in tasks, skipping disconnect")
            return
        self.tasks[task_id].user_socket_id = None
        logger.info(
            f"Soft closing task {task_id}, is_workflow_running: {self.tasks[task_id].is_workflow_running}"
        )
        if not self.tasks[task_id].is_workflow_running:
            logger.info(f"Task {task_id} is not running, deleting task")
            await self.delete_task(task_id)

    async def stop_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            logger.info(f"Task {task_id} not in tasks, skipping stop")
            return
        await self.tasks[task_id].stop_task()

    async def delete_task(self, task_id: str) -> None:
        if task_id not in self.tasks:
            logger.info(f"Task {task_id} not in tasks, skipping obj deletion")
            return

        await self.tasks[task_id].destroy()
        logger.info(f"Deleted task {task_id}")


TaskManager = _TaskManager()
