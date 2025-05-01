from pydantic import BaseModel, Field
from src.schemas.core.common.files import Image
from src.schemas.core.common.recordings import (
    EventType,
)


class VisualValidationEvent(BaseModel):  # Only tied to events that have a screenshot
    event_type: EventType
    before_screenshot: Image
    after_screenshot: Image
    annotation: str
    success: bool
    rationale: str


class LLMValidationResponse(BaseModel):
    thinking: str = Field(
        ...,
        description="Deep chain of thought reasoning on the context and the validation criteria",
    )
    rationale: str = Field(
        ...,
        description="Detailed validation feedback that is shown to the developer",
    )
    success: bool = Field(..., description="Whether the validation criteria were met")


class VisualValidationResponse(BaseModel):
    overall_success: bool
    events: list[VisualValidationEvent]
