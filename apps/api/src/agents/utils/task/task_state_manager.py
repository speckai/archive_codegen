from typing import TYPE_CHECKING

import socketio
from src.database import Database
from src.prompts.summarize import TASK_SUMMARY_SYSTEM_PROMPT, TASK_SUMMARY_USER_PROMPT
from src.schemas.core.common import MessageType, TaskState
from src.schemas.llm import Model

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task

import time
from typing import TYPE_CHECKING

from src.database import UpdateResult
from src.repos.settings.utils import get_runtime_files
from src.schemas.core.common import (
    PopulatedWorkspace,
    RunningTaskProgress,
    SerializedTask,
)
from src.socket_manager import get_socket
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class TaskStateManager:
    def __init__(self, task: "Task"):
        self.task = task
        self.task_summary: str | None = None
        self.files_changed_hash: str | None = None
        self.latest_task_state: TaskState = TaskState.IDLE

    async def send_state_update(self, state: TaskState):
        if self.task.debug:
            logger.info(f"[DEBUG] Fake emitting state update {state.value}")
            return

        self.latest_task_state = state
        sio: socketio.AsyncServer = get_socket()
        await sio.emit(
            "task_data",
            {
                "message_type": "task_state_update",
                "data": {"state": state.value},
            },
            room=self.task.task_id,
        )

    async def sync_latest_task_state(self, from_disk: bool = False) -> bool:
        logger.info("Syncing latest task state")
        if not from_disk and self.task.website.is_running:
            preview_url: str = self.task.sandbox.preview_url

            await self.task.send_update_data(MessageType.INITIALIZATION_SUCCESS, {})
            await self.task.send_update_data(
                MessageType.SET_PREVIEW_URL, {"url": preview_url}
            )

        if from_disk:
            blacklisted_message_types: list[MessageType] = [
                MessageType.SET_PREVIEW_URL,
                MessageType.ALLOCATING,
                MessageType.INITIALIZING_SANDBOX,
                MessageType.CLONING_REPO,
                MessageType.INSTALLING_DEPS,
                MessageType.LOADING_STATE_INDEXING,
                MessageType.BUILDING,
                MessageType.INITIALIZATION_SUCCESS,
                MessageType.INITIALIZATION_ERROR,
            ]
            self.task.actions = [
                action
                for action in self.task.actions
                if action["message_type"] not in blacklisted_message_types
            ]

        await self.task.send_update_data(
            MessageType.SYNC_EVENT,
            {
                "latest_task_state": self.latest_task_state,
                "task_actions": self.task.actions,
                "chat_messages": [
                    chat_message.model_dump()
                    for chat_message in (self.task.chat.history)
                ],
            },
        )
        return True

    def get_saved_task(self) -> SerializedTask | None:
        repo = Database.repos_collection.find_one(
            {"git_repo_id": self.task.git.repo_id}
        )
        if repo and "tasks" in repo:
            for task in repo["tasks"]:
                if task["task_id"] == self.task.task_id:
                    return SerializedTask.from_serialized(task)
        return None

    async def load_saved_task_files(self, saved_task: SerializedTask):
        logger.info("Loading task state files")
        if saved_task.patch_content:
            await self.task.file_system.apply_patch(saved_task.patch_content)

    async def load_saved_task_actions(self, saved_task: SerializedTask):
        self.task.actions = saved_task.actions
        self.task.chat.history = saved_task.chat_history
        self.task.git.issue_number = saved_task.issue_number
        self.task.context = saved_task.context

        await self.sync_latest_task_state(from_disk=True)
        await self.task.set_workflow_running(False)

    async def start_new_task(self):
        """Triggered on new workflow so we can summarize everything"""
        task_summary: str = await self._summarize_task(
            self.task.context.xml,
        )

        return self._save_task_to_db(
            {
                "workspace_name": self.task.workspace.name,
                "task_progress": RunningTaskProgress.ACTIVE.value,
                "summary": task_summary.strip(),
                "issue_number": self.task.git.issue_number,
            },
            create_if_missing=True,
        )

    async def update_task_progress(self, task_progress: RunningTaskProgress) -> bool:
        return self._save_task_to_db({"task_progress": task_progress.value})

    async def update_patch_content(self) -> bool:
        patch_content: str = await self.task.file_system.create_patch()
        return self._save_task_to_db({"patch_content": patch_content})

    async def set_pr_task(self, pr_number: int) -> bool:
        return self._save_task_to_db(
            {
                "task_progress": RunningTaskProgress.OPEN_PR.value,
                "pr_number": pr_number,
            }
        )

    async def update_task_summary(self, task_summary: str) -> bool:
        try:
            return self._save_task_to_db({"summary": task_summary})
        except Exception as e:
            logger.error(f"Error updating task summary: {e}")
            return False

    async def send_task_details(self):
        """We use this when a user first initializes/reconnects to task, CORE info"""
        await self.task.send_update_data(
            MessageType.TASK_DETAILS,
            {
                "task_id": self.task.task_id,
                "workspace": PopulatedWorkspace(
                    git_repo_id=self.task.git.repo_id,
                    workspace_name=self.task.workspace.name,
                    repo_name=self.task.git.repo.name,
                    repo_full_name=self.task.git.repo.full_name,
                    repo_url=self.task.git.repo.html_url,
                    visibility=self.task.git.repo.visibility,
                    owner={
                        "id": self.task.git.repo.owner.id,
                        "name": self.task.git.repo.owner.login,
                        "url": self.task.git.repo.owner.html_url,
                        "avatar_url": self.task.git.repo.owner.avatar_url,
                    },
                    settings=await self.task.settings.get_saved_settings(),
                    runtime_files=get_runtime_files(self.task.git.repo_id),
                    browser_storage=Database.get_repo_property(
                        self.task.git.repo_id, "browser_storage"
                    ),
                    issue_number=self.task.git.issue_number,
                ).model_dump(),
            },
        )

    def _save_task_to_db(
        self, fields_to_update: dict, create_if_missing: bool = False
    ) -> bool:
        fields_to_update.update(
            {  # Common fields
                "last_updated_unix": int(time.time()),
                "actions": [
                    {
                        "message_type": (
                            action["message_type"].value
                            if isinstance(action["message_type"], MessageType)
                            else action["message_type"]
                        ),
                        "data": action["data"],
                    }
                    for action in self.task.actions
                ],
                "chat_history": [
                    message.model_dump() for message in self.task.chat.history
                ],
                "context": self.task.context.model_dump(),
            }
        )

        result: UpdateResult = Database.repos_collection.update_one(
            {
                "git_repo_id": self.task.git.repo_id,
                "tasks.task_id": self.task.task_id,
            },
            {"$set": {f"tasks.$.{k}": v for k, v in fields_to_update.items()}},
        )

        if result.modified_count == 0 and create_if_missing:
            saved_task: SerializedTask = SerializedTask(
                task_id=self.task.task_id,
                patch_content="",
                **fields_to_update,
            )
            result = Database.repos_collection.update_one(
                {"git_repo_id": self.task.git.repo_id},
                {"$push": {"tasks": saved_task.model_dump()}},
                upsert=True,
            )
            return True

        return result.modified_count > 0

    async def _summarize_task(self, context_xml: str) -> str:
        """Summarize the patch content in a sentence."""
        task_summary: str = await self.task.llm_chat(
            model_type=Model.GEMINI_2_0_FLASH_LITE,
            system=TASK_SUMMARY_SYSTEM_PROMPT(),
            message=TASK_SUMMARY_USER_PROMPT(context_xml),
            caller="task_state_manager",
            response_model=str,
        )
        return task_summary
