from typing import Any

from pydantic import BaseModel, Field
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.think.prompt import PROMPT


class ThinkInput(BaseModel):
    thought: str = Field(..., description="Your thoughts.")


class ThinkTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "Think"

    @property
    def prompt(self):
        return PROMPT

    @property
    def input_schema(self):
        return ThinkInput

    @property
    def is_read_only(self):
        return True

    async def validate_input(
        self, input: dict[str, Any], context: ToolUseContext
    ) -> dict[str, Any]:
        return {"result": True, "model": ThinkInput}

    def render_result_for_assistant(self) -> str:
        # TODO: is this the way?!! id think that you need to send the thought up
        return "Your thought has been logged."

    async def call(
        self,
        input: ThinkInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        thought: str = input.thought

        return FullToolUseResult(
            result_for_assistant=self.render_result_for_assistant(),
            data={"thought": thought},
        )
