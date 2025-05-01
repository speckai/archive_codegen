import asyncio
import json

from pydantic import BaseModel
from src.agents.implementer.context import get_context
from src.agents.implementer.models import (
    AssistantMessage,
    ToolUseContext,
    ToolUseOptions,
    UserMessage,
)
from src.agents.implementer.prompts import get_system_prompt
from src.agents.implementer.query import query
from src.agents.implementer.tools.tools import get_all_tools
from src.config import DEV

USER_INPUT = "Make the site into dark mode. YOU MUST USE THE DISPATCH_AGENT TOOL TO SEARCH, IT SHOULD BE YOUR FIRST TOOL CALL."


class SerializableMessage(BaseModel):
    """A simplified version of message that can be serialized to JSON"""

    type: str
    uuid: str
    content: str


class Messages(BaseModel):
    messages: list[UserMessage | AssistantMessage]

    model_config = {"arbitrary_types_allowed": True}

    def to_json(self) -> str:
        """Custom serialization method to handle complex objects"""
        serializable_messages = []

        for msg in self.messages:
            if msg.type == "assistant":
                # Extract text content from BetaMessage
                content = ""
                for block in msg.message.content:
                    if hasattr(block, "text"):
                        content = block.text

                serializable_messages.append(
                    {"type": "assistant", "uuid": msg.uuid, "content": content}
                )
            else:
                # For user messages
                if isinstance(msg.message["content"], str):
                    content = msg.message["content"]
                else:
                    # Handle tool results in user messages
                    content = str(msg.message["content"])

                serializable_messages.append(
                    {"type": "user", "uuid": msg.uuid, "content": content}
                )

        return json.dumps({"messages": serializable_messages}, indent=2)


async def process_user_input(
    messages: list[UserMessage | AssistantMessage],
    system_prompt: list[str],
    context: dict[str, str],
    tool_use_context: ToolUseContext,
) -> None:
    async for message in query(
        messages,
        system_prompt,
        context,
        tool_use_context,
    ):
        # print(message.model_dump_json(indent=2))
        # Write to messages.json

        messages.append(message)

        if DEV:
            try:
                with open("temp_response_messages.json", "w") as f:
                    f.write(Messages(messages=messages).to_json())
            except Exception as e:
                print(e)
                with open("temp_response_messages_error.txt", "w") as f:
                    f.write(str(messages))


async def main():
    tool_context = ToolUseContext(
        options=ToolUseOptions(
            tools=get_all_tools(),
            max_thinking_tokens=0,
        )
    )
    context: dict[str, str] = await get_context()

    await process_user_input(USER_INPUT, get_system_prompt(), context, tool_context)


if __name__ == "__main__":
    asyncio.run(main())
