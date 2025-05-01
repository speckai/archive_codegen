import time
from typing import TYPE_CHECKING

from pydantic import BaseModel
from src.agents.planner.planner_agent import Planner as PlannerAgent
from src.agents.short_circuit.short_circuit_agent import ShortCircuitAgent
from src.agents.utils.base_agent import BaseAgent
from src.agents.utils.task.context import Context
from src.prompts.summarize import (
    AUTONOMOUS_DONE_MESSAGE_WITH_DESCRIPTION,
    DONE_MESSAGE_SYSTEM,
    RESPONSE_DONE_MESSAGE_WITH_DESCRIPTION,
)
from src.schemas.core.common import ModificationsPlan, ShortCircuitAction
from src.schemas.core.common.chat import ChatMessageRole, MainMessage, MessageData
from src.utils.llm.handler import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        user_message: str,
        task: "Task",
    ):
        super().__init__(task)
        self.user_message: str = user_message

        # children agents
        self.shortcircuit_agent: ShortCircuitAgent = ShortCircuitAgent(task=self.task)
        self.planner_agent: PlannerAgent = PlannerAgent(self.task)

    async def kickoff_task(self) -> bool:
        """
        Runs task, returns bool for agent success
        """
        change_message: str = self.user_message

        start_time: float = time.time()
        logger.info("Starting shortcircuit agent")
        short_circuit_action: ShortCircuitAction = (
            await self.shortcircuit_agent.get_action_to_perform(change_message)
        )
        self.task.current_workflow.current_plan = (
            short_circuit_action.modifications_plan
        )
        logger.info(
            f"Shortcircuit agent finished in {time.time() - start_time} seconds"
        )

        if (
            short_circuit_action.ask_clarifying_questions
            and not self.task.current_workflow.context.fully_autonomous
        ):
            start_time = time.time()
            logger.info("Starting context agent")
            new_change_message: str = await self.context_agent.get_new_change_message(
                change_message,
            )
            change_message = new_change_message
            logger.info(f"Context agent finished in {time.time() - start_time} seconds")
        else:
            await self.context_agent.override_send_start_message(change_message)

        start_time = time.time()
        logger.info("Starting to request modifications plan")
        modifications_plan: ModificationsPlan = (
            await self.planner_agent.request_modifications_plan(
                change_message,
                short_circuit_action=short_circuit_action,
            )
        )
        if modifications_plan:
            self.task.current_workflow.current_plan = modifications_plan
        logger.info(
            f"Modifications plan requested in {time.time() - start_time} seconds"
        )

        start_time = time.time()
        logger.info("Starting to implement plan")
        await self.task.implementer.implement_plan(modifications_plan)
        logger.info(f"Plan implemented in {time.time() - start_time} seconds")

        start_time = time.time()
        logger.info("Starting validation agent")
        validation_success: bool = await self.task.validation_agent.validate_changes()
        logger.info(f"Validation agent finished in {time.time() - start_time} seconds")

        if validation_success:
            logger.info("Validation Success")
        else:
            logger.warning("Validation Failed")

        done_message: str = await self.get_done_message()
        await self.task.chat.add_message(
            ChatMessageRole.ASSISTANT,
            MessageData(
                main_message=MainMessage(message=done_message, is_italic=False)
            ),
        )

        await self.task.set_workflow_running(False)

        await self.task.task_state_manager.update_patch_content()
        return validation_success

    async def get_done_message(self) -> str:
        """Gets the done message."""
        context: Context = self.task.current_workflow.context
        git_diffs: str = await self.task.git.get_limited_git_diffs()

        user_llm_prompt: str
        if self.task.current_workflow.context.fully_autonomous:
            user_llm_prompt = AUTONOMOUS_DONE_MESSAGE_WITH_DESCRIPTION
        else:
            user_llm_prompt = RESPONSE_DONE_MESSAGE_WITH_DESCRIPTION

        class DoneMessage(BaseModel):
            msg: str

        done_message: DoneMessage = await self.llm_response(
            Model.GEMINI_2_0_FLASH_LITE,
            DONE_MESSAGE_SYSTEM,
            user_llm_prompt(user_context=context.user_message, diffs=git_diffs),
            response_model=DoneMessage,
        )
        return done_message.msg

    def __del__(self) -> None:
        if hasattr(self, "task") and self.task is not None:
            logger.info(f"[Deleting OrchestratorAgent] User: {self.task.user.id}")
        else:
            logger.info("[Deleting OrchestratorAgent] Task is None")

    def destroy(self) -> None:
        if hasattr(self, "shortcircuit_agent"):
            del self.shortcircuit_agent
        if hasattr(self, "context_agent"):
            del self.context_agent
        if hasattr(self, "planner_agent"):
            del self.planner_agent
