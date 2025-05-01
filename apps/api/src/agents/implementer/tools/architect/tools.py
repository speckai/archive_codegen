from pydantic import BaseModel, Field
from src.agents.implementer.models import (
    AssistantMessage,
    FullToolUseResult,
    ToolUseContext,
    UserMessage,
)
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.file_read.prompt import PROMPT
from src.agents.implementer.utils.messages import create_user_message
from src.utils.logging import logger


class ArchitectInput(BaseModel):
    prompt: str = Field(
        ..., description="The technical request or coding task to analyze"
    )
    context: str | None = Field(
        None,
        description="Optional context from previous conversation or system state",
    )


class ArchitectTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Architect"

    @property
    def prompt(self):
        return PROMPT

    @property
    def input_schema(self):
        return ArchitectInput

    @property
    def is_read_only(self):
        return True

    def render_result_for_assistant(self, data):
        return data

    async def call(
        self, input: ArchitectInput, context: ToolUseContext
    ) -> FullToolUseResult:
        content = (
            f"<context>{input.context}</context>\n\n{input.prompt}"
            if input.context
            else input.prompt
        )
        user_message = create_user_message(content)

        messages: list[UserMessage | AssistantMessage] = [
            user_message,
        ]
        logger.info(f"Architect tool called with messages: {messages}")
        return NotImplementedError
