import asyncio
import traceback
from typing import TYPE_CHECKING

from src.agents.orchestrator.orchestrator_agent import OrchestratorAgent
from src.agents.utils.task.context import Context
from src.agents.utils.task.debug.common import Debug
from src.config import DEV
from src.database import Database
from src.schemas.core.common import (
    ChatMessage,
    ChatMessageRole,
    MainMessage,
    MessageData,
    MessageType,
    ModificationsPlan,
    RunningTaskProgress,
    WorkflowState,
)
from src.schemas.core.common.recordings import RecordingCollection
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Workflow:
    def __init__(
        self,
        task: "Task",
        user_message: str,
        recordings: RecordingCollection,
        relevant_chats: list[ChatMessage],
        fully_autonomous: bool,
        is_cloning_site: bool,
        debug: Debug | None = None,
    ):
        self.debug: Debug | None = debug
        self.task: Task = task
        user_rules, repo_rules = self._update_custom_rules()
        self.user_rules: str | None = user_rules
        self.repo_rules: str | None = repo_rules

        self.context: Context = Context(
            user_message=user_message,
            recordings=recordings,
            relevant_chats=relevant_chats,
            fully_autonomous=fully_autonomous,
            user_rules=self.user_rules,
            repo_rules=self.repo_rules,
        )
        self.last_state: WorkflowState | None = None
        self.orchestrator_agent: OrchestratorAgent = None
        self.is_cloning_site: bool = is_cloning_site
        self.current_plan: ModificationsPlan | None = None

        self._destroyed: bool = False
        self._task: asyncio.Task | None = None

    async def send_update_data(self, message_type: MessageType, data: dict):
        await self.task.send_update_data(message_type, data)

    async def send_state_update(self, state: WorkflowState):
        await self.task.send_state_update(state)
        self.last_state = state

    async def start_task(self) -> bool:
        self.orchestrator_agent: OrchestratorAgent = OrchestratorAgent(
            user_message=self.context.user_message,
            task=self.task,
        )
        await self.task.task_state_manager.start_new_task()
        await self.task.task_state_manager.update_task_progress(
            RunningTaskProgress.ACTIVE
        )

        logger.info(f"Created agent for user: {self.task.user.id}")
        try:
            self._task = asyncio.current_task()
            success: bool = await self.orchestrator_agent.kickoff_task()

            if success and self.task.git and self.task.git.issue_number:
                base_url: str = (
                    "http://localhost:3000" if DEV else "https://app.speck.sh"
                )
                task_url: str = f"{base_url}/repo/{self.task.task_id}"
                comment_text: str = f"I've finished the task, view it here {task_url}"
                await self.task.git.add_issue_comment(comment_text)

            return success
        except asyncio.CancelledError:
            logger.info("Task was cancelled")
            return False

        except Exception as e:
            # TODO: Send error to frontend
            logger.error(f"Error in orchestrator: {str(e)}")
            logger.error(traceback.format_exc())

            try:
                await self.task.chat.add_message(
                    role=ChatMessageRole.ASSISTANT,
                    message_data=MessageData(
                        main_message=MainMessage(
                            message="I'm sorry, but I encountered an error. Please try again."
                        )
                    ),
                )
            except Exception as e:
                logger.error(f"Error adding message: {str(e)}")
                logger.error(traceback.format_exc())
                logger.warning("Could not add message to session")

            return False

    def _update_custom_rules(self) -> tuple[str | None, str | None]:
        if self.debug:
            user_rules: str | None = self.debug.user_rules
            repo_rules: str | None = self.debug.repo_rules
        else:
            user_rules: str | None = Database.get_user_property(
                self.task.user.id, "custom_rules"
            )
            repo_rules: str | None = Database.get_repo_property(
                self.task.git.repo_id, "custom_rules"
            )
        return user_rules, repo_rules

    def cancel(self):
        if self._task:
            self._task.cancel()

    def destroy(self):
        """Clean up task resources and cancel any running operations"""
        self.cancel()
        if hasattr(self, "orchestrator_agent") and self.orchestrator_agent:
            self.orchestrator_agent.destroy()
            del self.orchestrator_agent
