from asyncio import create_task, gather
from typing import AsyncGenerator

from anthropic import BaseModel
from anthropic.types.beta import BetaMessageParam, BetaToolUseBlock
from src.agents.implementer.models import (
    AssistantMessage,
    FullToolUseResult,
    ToolUseContext,
    UserMessage,
)
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.utils.llm import query_sonnet
from src.agents.implementer.utils.messages import (
    create_user_message,
    normalize_messages_for_api,
)
from src.agents.implementer.utils.persistent_shell import get_cwd
from src.utils.logging import logger

MAX_TOOL_USE_CONCURRENCY = 10


def format_system_prompt_with_context(
    system_prompt: list[str], context: dict
) -> list[str]:
    assert isinstance(system_prompt, list)
    if not context:
        return system_prompt
    formatted_context: list[str] = [
        f'<context name="{key}">{value}</context>' for key, value in context.items()
    ]
    return (
        system_prompt
        + ["\nAs you answer the user's questions, you can use the following context:\n"]
        + formatted_context
    )


def normalize_tool_input(tool: BaseTool, tool_input: dict) -> dict:
    """Normalize tool input based on the tool type."""
    if tool.name != "bash":
        return tool_input

    command: str = tool_input.get("command", "")
    timeout: int | None = tool_input.get("timeout")

    # Remove cd prefix if present
    if command.startswith(f"cd {get_cwd()} && "):
        command = command.replace(f"cd {get_cwd()} && ", "")

    normalized_input: dict = {"command": command}
    if timeout:
        normalized_input["timeout"] = timeout

    return normalized_input


def validate_input(tool: BaseTool, tool_input: dict) -> tuple[bool, str]:
    """Validate tool input based on the tool type."""
    try:
        tool.input_schema(**tool_input)  # type: ignore
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"


async def check_permissions_and_call_tool(
    tool: BaseTool,
    tool_use_id: str,
    sibling_tool_use_ids: set[str],
    tool_input: dict,
    context: "ToolUseContext",
    assistant_message: BetaMessageParam,
) -> UserMessage:
    is_valid_input, error_message = validate_input(tool, tool_input)
    if not is_valid_input:
        return create_user_message(
            [
                {
                    "type": "tool_result",
                    "content": error_message,
                    "is_error": True,
                    "tool_use_id": tool_use_id,
                }
            ]
        )

    normalized_input: dict = normalize_tool_input(tool, tool_input)

    validation_result: dict = await tool.validate_input(normalized_input, context)
    if not validation_result["result"]:
        return create_user_message(
            [
                {
                    "type": "tool_result",
                    "content": validation_result["message"],
                    "is_error": True,
                    "tool_use_id": tool_use_id,
                }
            ]
        )

    result_input: BaseModel = validation_result["model"](**normalized_input)

    result: FullToolUseResult = await tool.call(result_input, context)

    return create_user_message(
        [
            {
                "type": "tool_result",
                "content": result.result_for_assistant,
                "tool_use_id": tool_use_id,
            }
        ],
        FullToolUseResult(
            data=result.data,
            result_for_assistant=result.result_for_assistant,
        ),
    )


async def run_tool_use(
    tool_use: BetaToolUseBlock,
    sibling_tool_use_ids: set[str],
    assistant_message: BetaMessageParam,
    tool_use_context: "ToolUseContext",
) -> UserMessage:
    tool_name: str = tool_use.name
    tool: BaseTool | None = next(
        (t for t in tool_use_context.options.tools if t.name == tool_name),
        None,
    )
    if not tool:
        print("TOOL NOT FOUND - ", tool_name)
        return create_user_message(
            [
                {
                    "type": "tool_result",
                    "content": f"Error: No such tool available: {tool_name}",
                    "is_error": True,
                    "tool_use_id": tool_use.id,
                }
            ]
        )

    tool_input: dict = tool_use.input
    return await check_permissions_and_call_tool(
        tool,
        tool_use.id,
        sibling_tool_use_ids,
        tool_input,
        tool_use_context,
        assistant_message,
    )


async def run_tools_concurrently(
    tool_use_messages: list[BetaToolUseBlock],
    assistant_message: BetaMessageParam,
    tool_use_context: "ToolUseContext",
) -> AsyncGenerator[UserMessage, None]:
    sibling_tool_use_ids: set[str] = {message.id for message in tool_use_messages}

    tasks: list = [
        create_task(
            run_tool_use(
                tool_use,
                sibling_tool_use_ids,
                assistant_message,
                tool_use_context,
            )
        )
        for tool_use in tool_use_messages
    ]

    for result in await gather(*tasks):
        yield result


async def run_tools_serially(
    tool_use_messages: list[BetaToolUseBlock],
    assistant_message: BetaMessageParam,
    tool_use_context: "ToolUseContext",
) -> AsyncGenerator[UserMessage, None]:
    sibling_tool_use_ids: set[str] = {message.id for message in tool_use_messages}

    for tool_use in tool_use_messages:
        yield await run_tool_use(
            tool_use,
            sibling_tool_use_ids,
            assistant_message,
            tool_use_context,
        )


async def query(
    messages: list[UserMessage | AssistantMessage],
    system_prompt: list[str],
    context: dict,
    tool_use_context: "ToolUseContext",
) -> AsyncGenerator[AssistantMessage | UserMessage, None]:
    """
    This function is the main entry point for the query. It takes a list of messages, a system prompt, a context, and a tool use context.

    :param messages: A list of messages to query.
    :param system_prompt: A list of strings representing the system prompt.
    :param context: A dictionary representing the context.
    :param tool_use_context: A ToolUseContext object representing the tool use context.
    :return: An async generator of UserMessage objects.
    """

    full_system_prompt: list[str] = format_system_prompt_with_context(
        system_prompt, context
    )
    messages_for_api: list[BetaMessageParam] = normalize_messages_for_api(messages)

    assistant_message: AssistantMessage = await query_sonnet(
        messages_for_api,
        full_system_prompt,
        tool_use_context.options.max_thinking_tokens,
        tool_use_context.options.tools,
    )

    yield assistant_message

    tool_use_messages: list[BetaToolUseBlock] = [
        x for x in assistant_message.message.content if x.type == "tool_use"
    ]
    logger.debug(f"Doing tools: {', '.join([x.name for x in tool_use_messages])}")

    if not tool_use_messages:
        for block in assistant_message.message.content:
            if hasattr(block, "text"):
                logger.debug(block.text)
        logger.debug("***EXITING LOOP***")
        return

    tool_results: list[UserMessage] = []

    # Prefer to run tools concurrently, if we can
    if all(
        next((t for t in tool_use_context.options.tools if t.name == msg.name), None)
        is not None
        and next(
            (t for t in tool_use_context.options.tools if t.name == msg.name), None
        ).is_read_only
        for msg in tool_use_messages
    ):
        async for message in run_tools_concurrently(
            tool_use_messages, assistant_message, tool_use_context
        ):
            yield message

            if message.type == "user":
                tool_results.append(message)
    else:
        async for message in run_tools_serially(
            tool_use_messages, assistant_message, tool_use_context
        ):
            yield message
            if message.type == "user":
                tool_results.append(message)

    ordered_tool_results: list[dict] = sorted(
        tool_results,
        key=lambda a: next(
            (
                i
                for i, tu in enumerate(tool_use_messages)
                if a.message
                and "content" in a.message
                and (
                    content_list := (
                        list(a.message["content"])
                        if hasattr(a.message["content"], "__iter__")
                        and not isinstance(a.message["content"], (list, str, dict))
                        else a.message["content"]
                    )
                )
                and len(content_list) > 0
                and "tool_use_id" in content_list[0]
                and tu.id == content_list[0]["tool_use_id"]
            ),
            0,  # Default index if not found
        ),
    )

    next_messages = messages + [assistant_message] + ordered_tool_results

    async for message in query(
        next_messages,
        system_prompt,
        context,
        tool_use_context,
    ):
        yield message
