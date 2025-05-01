from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from src.agents.utils.task.context import Context

from .chat import ChatMessage
from .types import MessageType


class RunningTaskProgress(StrEnum):
    ACTIVE = "active"  # If the task is in progress
    COMPLETED = "completed"  # If Speck has completed the task
    OPEN_PR = "pr_open"  # If the user has opened a PR to the website (not merged)
    MERGED_PR = "pr_merged"  # If the user has merged a PR to the website
    CLOSED_PR = "pr_closed"  # If the user has closed a PR to the website (not merged)
    BLOCKED = "blocked"  # If the user needs to open the task
    CANCELLED = "cancelled"  # If the user has cancelled the task or errored


class SerializedTask(BaseModel):
    task_id: str
    workspace_name: str
    task_progress: RunningTaskProgress
    patch_content: str
    summary: str
    chat_history: list[ChatMessage]
    actions: list[dict]  # Each dict has message_type and data keys
    last_updated_unix: int
    context: Context

    pr_number: int | None = None
    issue_number: int | None = None
    issue_closed: bool | None = None

    @classmethod
    def from_serialized(cls, serialized_task: dict):
        return cls(
            task_id=serialized_task["task_id"],
            workspace_name=serialized_task["workspace_name"],
            task_progress=RunningTaskProgress(serialized_task["task_progress"]),
            patch_content=serialized_task["patch_content"],
            summary=serialized_task["summary"],
            chat_history=[
                ChatMessage(**chat_message)
                for chat_message in serialized_task["chat_history"]
            ],
            actions=serialized_task["actions"],
            last_updated_unix=serialized_task["last_updated_unix"],
            context=serialized_task["context"],
            pr_number=serialized_task.get("pr_number"),
            issue_number=serialized_task.get("issue_number"),
            issue_closed=serialized_task.get("issue_closed"),
        )

    def model_dump(self, *args, **kwargs) -> dict:
        data: dict[str, Any] = super().model_dump(*args, **kwargs)
        actions: list[dict[str, Any]] = []
        for action in self.actions:
            actions.append(
                {
                    "message_type": (
                        action["message_type"].value
                        if isinstance(action["message_type"], MessageType)
                        else action["message_type"]
                    ),
                    "data": action["data"],
                }
            )
        data["actions"] = actions
        return data
