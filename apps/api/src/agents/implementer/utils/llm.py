from typing import Any
from uuid import uuid4

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaTextBlockParam
from src.agents.implementer.models import AssistantMessage
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.utils.persistent_shell import get_persistent_shell
from src.config import (
    ANTHROPIC_API_KEY,
    DEV,
    HELICONE_API_KEY,
    POSTHOG_HOST,
    POSTHOG_KEY,
)
from src.utils.llm.utils import get_helicone_headers


async def query_haiku(
    system_prompt: str,
    user_prompt: str,
    assistant_prompt: str | None = None,  # TODO: Add prompt caching function too
) -> AssistantMessage:
    client: AsyncAnthropic = AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url="https://anthropic.helicone.ai/",
        default_headers={
            "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
            "Helicone-Posthog-Key": POSTHOG_KEY,
            "Helicone-Posthog-Host": POSTHOG_HOST,
        },
    )

    messages: list[BetaMessageParam] = [
        {"role": "user", "content": user_prompt},
    ]
    if assistant_prompt:
        messages.append({"role": "assistant", "content": assistant_prompt})

    shell = get_persistent_shell()

    extra_headers = get_helicone_headers(None, shell.shell_id, "claude-code-port", None)
    message: BetaMessage = await client.beta.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1000,
        temperature=0,
        system=system_prompt,
        messages=messages,  # TODO: Use metadata fn
        extra_headers=extra_headers,
    )
    return AssistantMessage(
        type="assistant",
        message=message,
        uuid=str(uuid4()),
    )


async def query_sonnet(
    messages: list[dict[str, str]],
    system_prompt: list[str],
    max_thinking_tokens: int,
    tools: list[BaseTool],
) -> AssistantMessage:
    client: AsyncAnthropic = AsyncAnthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url="https://anthropic.helicone.ai/",
        default_headers={
            "Helicone-Auth": f"Bearer {HELICONE_API_KEY}",
            "Helicone-Posthog-Key": POSTHOG_KEY,
            "Helicone-Posthog-Host": POSTHOG_HOST,
        },
    )

    betas: list[str] = get_betas()

    tool_dicts: list[dict] = [tool.to_dict() for tool in tools]

    system: list[BetaTextBlockParam] = [
        {
            "type": "text",
            "text": "\n".join(system_prompt),
            "cache_control": {"type": "ephemeral"},
        }
    ]

    shell = get_persistent_shell()
    extra_headers = get_helicone_headers(None, shell.shell_id, "claude-code-port", None)
    kwargs: dict[str, Any] = {
        "model": "claude-3-7-sonnet-20250219",
        "system": system,
        "messages": add_cache_breakpoints(messages),
        "max_tokens": max(
            max_thinking_tokens + 1,
            get_max_tokens_for_model("claude-3-7-sonnet-20250219"),
        ),
        "temperature": 1,
        "tools": tool_dicts,
        "betas": betas,
        # "metadata": get_metadata(), # TODO: Add metadata
        "extra_headers": extra_headers,
    }

    if max_thinking_tokens > 0:
        kwargs["thinking"] = {
            "budget_tokens": max_thinking_tokens,
            "type": "enabled",
        }

    if DEV:
        with open("kwargs.txt", "w") as f:
            f.write(str(kwargs))

    message: BetaMessage = await client.beta.messages.create(**kwargs)
    return AssistantMessage(
        type="assistant",
        message=message,
        uuid=str(uuid4()),
    )


def get_max_tokens_for_model(model: str) -> int:
    if "3-5" in model:
        return 8192
    return 8192 if "haiku" in model else 20000


def get_betas() -> list[str]:
    betas: list[str] = [
        "claude-code-20250219",
        "token-efficient-tools-2025-02-19",
    ]  # Idk what these do
    # if (process.env.USER_TYPE === 'ant' || process.env.SWE_BENCH) {
    #     const useTokenEfficientTools = await checkGate(GATE_TOKEN_EFFICIENT_TOOLS) # Benchmark with this
    #     if (useTokenEfficientTools) { # Benchmark with  this
    #         betaHeaders.push(BETA_HEADER_TOKEN_EFFICIENT_TOOLS)
    #     }
    # }

    # export const GATE_TOKEN_EFFICIENT_TOOLS = 'tengu-token-efficient-tools'
    # export const BETA_HEADER_TOKEN_EFFICIENT_TOOLS =
    # 'token-efficient-tools-2024-12-11'
    # export const GATE_USE_EXTERNAL_UPDATER = 'tengu-use-external-updater'
    # export const CLAUDE_CODE_20250219_BETA_HEADER = 'claude-code-20250219'
    return betas


def get_metadata(message: dict[str, str]) -> dict[str, str]:
    return {
        "type": message["type"],
        "uuid": message["uuid"],
        "content": message["content"],
    }


def add_cache_breakpoints(
    messages: list[BetaMessageParam],
) -> list[BetaMessageParam]:
    return [
        (
            user_message_to_message_param(message, index > len(messages) - 3)
            if message["role"] == "user"
            else assistant_message_to_message_param(message, index > len(messages) - 3)
        )
        for index, message in enumerate(messages)
    ]


def user_message_to_message_param(
    message: BetaMessageParam, add_cache: bool = False
) -> BetaMessageParam:
    if add_cache:
        if isinstance(message["content"], str):
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        else:
            return {
                "role": "user",
                "content": [
                    {
                        **(
                            content.model_dump()
                            if hasattr(content, "model_dump")
                            else content
                        ),
                        "cache_control": (
                            {"type": "ephemeral"}
                            if i == len(message["content"]) - 1
                            else None
                        ),
                    }
                    for i, content in enumerate(message["content"])
                ],
            }
    return {"role": "user", "content": message["content"]}


def assistant_message_to_message_param(
    message: BetaMessageParam, add_cache: bool = False
) -> BetaMessageParam:
    if add_cache:
        if isinstance(message["content"], str):
            return {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": message["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        else:
            return {
                "role": "assistant",
                "content": [
                    {
                        **(
                            content.model_dump()
                            if hasattr(content, "model_dump")
                            else content
                        ),
                        "cache_control": (
                            {"type": "ephemeral"}
                            if i == len(message["content"]) - 1
                            and (
                                content.get("type")
                                if isinstance(content, dict)
                                else getattr(content, "type", None)
                            )
                            not in ["thinking", "redacted_thinking"]
                            else None
                        ),
                    }
                    for i, content in enumerate(message["content"])
                ],
            }
    return {"role": "assistant", "content": message["content"]}


def split_sys_prompt_prefix(system_prompt: list[str]) -> list[str]:
    system_prompt_first_block = system_prompt[0] if system_prompt else ""
    system_prompt_rest = system_prompt[1:]
    return [system_prompt_first_block, system_prompt_rest.join("\n")]
