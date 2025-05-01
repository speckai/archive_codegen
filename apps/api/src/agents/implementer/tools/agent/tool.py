from typing import Any

from pydantic import BaseModel, Field
from src.agents.implementer.context import get_context
from src.agents.implementer.models import (
    AssistantMessage,
    FullToolUseResult,
    ToolUseContext,
    ToolUseOptions,
)
from src.agents.implementer.prompts import get_agent_prompt
from src.agents.implementer.query import query
from src.agents.implementer.tools.agent.prompt import AGENT_PROMPT
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.utils.messages import create_user_message


class AgentInput(BaseModel):
    prompt: str = Field(..., description="The task for the agent to perform")


class AgentTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self):
        return "dispatch_agent"

    @property
    def prompt(self):
        from src.agents.implementer.tools.tools import get_all_tools

        tool_names: list[str] = [tool.name for tool in get_all_tools()]
        return AGENT_PROMPT(tool_names=tool_names)

    @property
    def input_schema(self):
        return AgentInput

    @property
    def is_read_only(self):
        return True

    async def validate_input(
        self,
        input: dict[str, Any],
        context: ToolUseContext,
    ) -> dict[str, Any]:
        return {
            "result": True,
            "model": AgentInput,
        }

    async def call(
        self,
        input: AgentInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        from src.agents.implementer.tools.tools import get_agent_tools

        initial_message = create_user_message(input.prompt)
        tools: list[BaseTool] = get_agent_tools(read_only=False)
        agent_prompt: str = get_agent_prompt()
        original_gangster_context: str = await get_context()
        new_tool_context: ToolUseContext = ToolUseContext(
            options=ToolUseOptions(
                tools=tools,
                max_thinking_tokens=0,
            ),
            read_file_timestamps=context.read_file_timestamps,
        )

        last_message: AssistantMessage | None = None
        async for message in query(
            [initial_message],
            agent_prompt,
            original_gangster_context,
            new_tool_context,
        ):
            last_message = message

        last_text_block = next(
            (block for block in last_message.message.content if block.type == "text"),
            None,
        )

        return FullToolUseResult(
            data=last_text_block,
            result_for_assistant=last_text_block.text,
        )
