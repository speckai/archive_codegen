import traceback
from typing import TYPE_CHECKING

from src.prompts import MESSAGE_INTENT_SYSTEM_PROMPT, MESSAGE_INTENT_USER_PROMPT
from src.schemas.core.common import (
    ChatMessage,
    ChatMessageRole,
    MainMessage,
    MessageAction,
    MessageAttachments,
    MessageData,
    MessageIntent,
    MessageType,
)
from src.schemas.core.common.recordings import RecordingCollection
from src.schemas.llm import Model
from src.utils.logging import logger

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class Chat:
    def __init__(self, task: "Task"):
        self.task: Task = task
        self.history: list[ChatMessage] = []

    async def add_message(
        self,
        role: ChatMessageRole,
        message_data: MessageData,
    ):
        """Sends a chat message to the frontend and adds to the chat history"""
        chat_message: ChatMessage = ChatMessage(role=role, message_data=message_data)
        if (
            role == ChatMessageRole.ASSISTANT
        ):  # User messages are already in the frontend
            await self.task.send_update_data(
                MessageType.CHAT_MESSAGE, chat_message.model_dump()
            )
        self.history.append(chat_message)

    async def handle_user_message(
        self,
        user_message: str,
        recordings: RecordingCollection,
        is_autonomous: bool = False,
    ):
        await self.task.set_workflow_running(True)
        await self.add_message(
            ChatMessageRole.USER,
            MessageData(
                main_message=MainMessage(message=user_message),
                attachments=MessageAttachments(
                    recordings=recordings,
                ),
            ),
        )
        try:
            with self.task.session_recorder.start(self.task):
                await self._handle_user_message(
                    user_message,
                    recordings,
                    is_autonomous,
                )
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            await self.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(
                        message="I encountered an error and had to abandon the task, please try again."
                    )
                ),
            )
        finally:
            await self.task.set_workflow_running(False)

    async def _handle_user_message(
        self,
        user_message: str,
        recordings: RecordingCollection,
        is_autonomous: bool = False,
    ) -> None:
        await self.task.set_workflow_running(True)
        message_intent: MessageIntent = await self.task.llm_chat(
            model_type=Model.GEMINI_2_0_FLASH,
            system=MESSAGE_INTENT_SYSTEM_PROMPT(),
            message=MESSAGE_INTENT_USER_PROMPT(user_message, self.history),
            caller="task",
            response_model=MessageIntent,
        )

        if message_intent.action == MessageAction.TASK:
            await self.task.create_agent_task(
                user_message=user_message,
                relevant_chats=self.history,
                recordings=recordings,
                fully_autonomous=is_autonomous,
            )
        elif message_intent.action == MessageAction.QUESTION:
            await self.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(message="I can't handle questions yet!")
                ),
            )
        elif message_intent.action == MessageAction.GIT:
            if not await self.task.git.check_for_changes():
                await self.add_message(
                    ChatMessageRole.ASSISTANT,
                    MessageData(
                        main_message=MainMessage(
                            message="You don't have any changes yet!"
                        )
                    ),
                )
            else:
                await self.add_message(
                    ChatMessageRole.ASSISTANT,
                    MessageData(
                        main_message=MainMessage(
                            message="I've generated a commit message for you to review and commit your changes."
                        )
                    ),
                )

                await self.task.ui_functions.show_git_panel()

                # TODO: Fully implement git handling. For now we'll open up the dialogue on the frontend
                # await self.git.handle_git_message(user_message, relevant_chats)

        elif message_intent.action == MessageAction.VALIDATE_BUILD:
            build_success: bool = await self.task.validation_agent.test_build()
            if not build_success:
                await self.add_message(
                    ChatMessageRole.ASSISTANT,
                    MessageData(
                        main_message=MainMessage(message="The build failed!"),
                    ),
                )
            else:
                await self.add_message(
                    ChatMessageRole.ASSISTANT,
                    MessageData(
                        main_message=MainMessage(message="The build passed!"),
                    ),
                )
        elif message_intent.action == MessageAction.UNDEFINED:
            await self.add_message(
                ChatMessageRole.ASSISTANT,
                MessageData(
                    main_message=MainMessage(
                        message="I don't know what you want to do."
                    )
                ),
            )
        return
