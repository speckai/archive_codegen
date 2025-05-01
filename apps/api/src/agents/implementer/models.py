from typing import Any, Literal, Union

from anthropic.types import ImageBlockParam, TextBlockParam
from anthropic.types.beta import BetaMessage
from pydantic import BaseModel
from src.agents.implementer.tools.base_tool import BaseTool
from typing_extensions import TypeAlias

Content: TypeAlias = Union[TextBlockParam, ImageBlockParam]


class ToolUseOptions(BaseModel):
    tools: list[BaseTool]
    max_thinking_tokens: int

    model_config = {"arbitrary_types_allowed": True}


class ToolUseContext(BaseModel):
    options: ToolUseOptions
    read_file_timestamps: dict[str, float] = (
        {}
    )  # TODO: Move this into a handler that accesses it


class FullToolUseResult(BaseModel):
    data: Any
    result_for_assistant: str | list[dict]


class AssistantMessage(BaseModel):
    type: Literal["assistant"]
    message: BetaMessage
    uuid: str
    is_api_error_message: bool | None = None

    model_config = {"arbitrary_types_allowed": True}


class UserMessage(BaseModel):
    type: Literal["user"]
    message: dict
    uuid: str
    tool_use_result: FullToolUseResult | None = None
