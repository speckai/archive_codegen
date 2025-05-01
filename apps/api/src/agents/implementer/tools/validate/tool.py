from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from src.agents.implementer.models import FullToolUseResult, ToolUseContext
from src.agents.implementer.tools.base_tool import BaseTool
from src.agents.implementer.tools.validate.prompt import DESCRIPTION
from src.agents.implementer.utils.persistent_shell import get_persistent_shell
from src.schemas.core.validation.visual import VisualValidationResponse

if TYPE_CHECKING:
    from src.agents.utils.task.task import Task


class ValidateInput(BaseModel):  # TODO: Make this optional
    confirmed: bool = Field(
        ...,
        description="Are we ready to validate the changes?",
    )


class ValidateTool(BaseTool):
    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "ValidateTool"

    @property
    def prompt(self):
        return DESCRIPTION

    @property
    def input_schema(self):
        return ValidateInput

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
            "model": ValidateInput,
        }

    async def call(
        self,
        input: ValidateInput,
        context: ToolUseContext,
    ) -> FullToolUseResult:
        task: "Task" = get_persistent_shell().get_task()
        validation_response: VisualValidationResponse = (
            await task.visual_tester.validate_functionality()
        )
        data: dict[str, Any] = {
            "overall_success": validation_response.overall_success,
            "events": validation_response.events,
        }

        return FullToolUseResult(
            data=data,
            result_for_assistant=self.render_result_for_assistant(validation_response),
        )

    def render_result_for_assistant(
        self, validation_response: VisualValidationResponse
    ) -> str | list[dict[str, Any]]:
        events: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": f"Overall Validation Success: {validation_response.overall_success}",
            }
        ]

        for idx, event in enumerate(validation_response.events):
            events.extend(
                [
                    {
                        "type": "text",
                        "text": f"Test Case {idx + 1}\nSuccess: {event.success}\nAnnotation: {event.annotation}\nRationale: {event.rationale}",
                    },
                    *event.before_screenshot.anthropic_dict_format(idx + 1),
                    *event.after_screenshot.anthropic_dict_format(idx + 1),
                ]
            )

        return events
