import re
from uuid import uuid4

from anthropic.types.beta import BetaContentBlockParam, BetaMessageParam
from src.agents.implementer.models import (
    AssistantMessage,
    FullToolUseResult,
    UserMessage,
)


def extract_tag(html: str, tag_name: str) -> str | None:
    """Extract content between specified HTML tags, handling nested tags and other edge cases."""
    if not html.strip() or not tag_name.strip():
        return None

    # Escape special characters in the tag name
    escaped_tag = re.escape(tag_name)

    # Create regex pattern that handles:
    # 1. Self-closing tags
    # 2. Tags with attributes
    # 3. Nested tags of the same type
    # 4. Multiline content
    pattern: re.Pattern = re.compile(
        f"<{escaped_tag}(?:\\s+[^>]*)?>"  # Opening tag with optional attributes
        + "([\\s\\S]*?)"  # Content (non-greedy match)
        + f"<\\/{escaped_tag}>",  # Closing tag
        re.IGNORECASE,
    )

    opening_tag: re.Pattern = re.compile(
        f"<{escaped_tag}(?:\\s+[^>]*?)?>", re.IGNORECASE
    )
    closing_tag: re.Pattern = re.compile(f"<\\/{escaped_tag}>", re.IGNORECASE)

    depth: int = 0
    last_index: int = 0

    for match in pattern.finditer(html):
        content: str = match.group(1)
        before_match: str = html[last_index : match.start()]

        depth = sum(1 for _ in opening_tag.finditer(before_match))
        for _ in closing_tag.finditer(before_match):
            depth -= 1

        if depth == 0 and content:
            return content

        last_index = match.end()

    return None


def normalize_messages_for_api(
    messages: list[UserMessage | AssistantMessage],
) -> list[BetaMessageParam]:
    result: list[BetaMessageParam] = []

    messages_without_progress: list[UserMessage | AssistantMessage] = [
        m for m in messages if m.type != "progress"
    ]

    for message in messages_without_progress:
        if message.type == "user":
            if (
                not isinstance(message.message["content"], list)
                or message.message["content"][0]["type"] != "tool_result"
            ):
                result.append(message.message)
                continue

            last_message: BetaMessageParam | None = result[-1] if result else None
            if (
                not last_message
                or last_message["role"] == "assistant"
                or not isinstance(last_message["content"], list)
                or last_message["content"][0]["type"] != "tool_result"
            ):
                result.append(
                    BetaMessageParam(
                        role="user",
                        content=message.message["content"],
                    )
                )
                continue

            last_message_index: int = result.index(last_message)
            result[last_message_index] = {
                **last_message,
                "message": {
                    **last_message["message"],
                    "content": [
                        *last_message["message"]["content"],
                        *message["message"]["content"],
                    ],
                },
            }
        elif message.type == "assistant":
            result.append(
                BetaMessageParam(
                    role="assistant",
                    content=message.message.content,
                )
            )

    return result


def normalize_content_from_api(
    content: list[BetaContentBlockParam],
) -> list[BetaContentBlockParam]:
    filtered_content: list[BetaContentBlockParam] = [
        item
        for item in content
        if item.get("type") != "text" or item.get("text", "").strip()
    ]

    if not filtered_content:
        return [{"type": "text", "text": "(no content)", "citations": []}]

    return filtered_content


def create_user_message(
    content: str | list[BetaContentBlockParam],
    tool_use_result: FullToolUseResult | None = None,
) -> UserMessage:
    if not isinstance(content, str) and hasattr(content, "__iter__"):
        content = list(content)

    message: UserMessage = UserMessage(
        type="user",
        message={
            "role": "user",
            "content": content,
        },
        uuid=str(uuid4()),
        tool_use_result=tool_use_result,
    )
    return message
